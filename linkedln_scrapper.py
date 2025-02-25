import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
import json
import logging
from datetime import datetime
import os
import re
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

class LinkedInScraper:
    def __init__(self, email, password):
        """
        Initialize the LinkedIn scraper with login credentials and setup logging
        
        Args:
            email (str): LinkedIn login email
            password (str): LinkedIn login password
        """
        self.email = email
        self.password = password
        self.setup_logging()
        self.setup_driver()
        
    def setup_logging(self):
        """Configure logging to track scraping progress and errors"""
        logging.basicConfig(
            filename=f'linkedin_scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """Configure and initialize Chrome WebDriver with appropriate options"""
        chrome_options = Options()
    
        # Add these lines to clear cache
        chrome_options.add_argument("--disable-cache")
        chrome_options.add_argument("--disk-cache-size=1")
        chrome_options.add_argument("--media-cache-size=1")
        chrome_options.add_argument("--disk-cache-dir=/dev/null")
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        
        # Add user agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36')
        
        # Initialize Chrome WebDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        
        # Mask webdriver
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        })
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def login_to_linkedin(self):
        """
        Log into LinkedIn using provided credentials
        
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # First navigate to LinkedIn homepage
            self.driver.get('https://www.linkedin.com/')
            time.sleep(3)
            
            # Check if already logged in
            if "feed" in self.driver.current_url:
                self.logger.info("Already logged in to LinkedIn")
                return True
                
            # If not logged in, go to login page
            self.driver.get('https://www.linkedin.com/login')
            time.sleep(3)
            
            # Find and fill email field
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'username'))
            )
            email_field.clear()
            email_field.send_keys(self.email)
            time.sleep(1)
            
            # Find and fill password field
            password_field = self.driver.find_element(By.ID, 'password')
            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(1)
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, '[type="submit"]')
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Verify login success
            if "feed" in self.driver.current_url:
                self.logger.info("Successfully logged into LinkedIn")
                
                # Add cookies handling
                cookies = self.driver.get_cookies()
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
                
                # Visit homepage again to ensure cookies are applied
                self.driver.get('https://www.linkedin.com/')
                time.sleep(3)
                
                return True
            else:
                self.logger.error("Failed to verify login success")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to login to LinkedIn: {str(e)}")
            return False

    def _get_experience(self):
        """Extract work experience"""
        experience = {}
        try:
            # Scroll to experience section
            self.driver.execute_script("window.scrollBy(0, 500)")
            time.sleep(2)
            
            # Find experience entries
            experience_entries = self.driver.find_elements(By.CSS_SELECTOR, "div.experience-group-header")
            
            for entry in experience_entries:
                try:
                    # Get company and role
                    company = entry.find_element(By.CSS_SELECTOR, ".experience-group-header__company").text.strip()
                    role = entry.find_element(By.CSS_SELECTOR, ".experience-group-header__role").text.strip()
                    experience[company] = role
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Error extracting experience: {str(e)}")
            
        return experience

    def _get_education(self):
        """Extract education information"""
        education = {}
        try:
            # Wait for education section to load and try multiple possible selectors
            education_selectors = [
                "section.education-section",
                "#education",
                "[class*='education-section']",
                "[class*='education']"
            ]
            
            for selector in education_selectors:
                try:
                    # Scroll to bring education section into view
                    self.driver.execute_script("window.scrollBy(0, 300)")
                    time.sleep(2)
                    
                    education_items = self.driver.find_elements(By.CSS_SELECTOR, 
                        f"{selector} li.artdeco-list__item")
                    
                    if education_items:
                        for item in education_items:
                            try:
                                school = item.find_element(By.CSS_SELECTOR, 
                                    "[class*='school-name']").text.strip()
                                degree = item.find_element(By.CSS_SELECTOR, 
                                    "[class*='degree-name']").text.strip()
                                education[school] = degree
                            except NoSuchElementException:
                                continue
                        break
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Error extracting education: {str(e)}")
            
        return education

    def extract_profile_data(self, profile_url):
        """
        Extract data from a single LinkedIn profile
        """
        try:
            # Visit the profile page
            self.driver.get(profile_url)
            time.sleep(5)
            
            # Check if we're still logged in
            if "login" in self.driver.current_url or "authenticate" in self.driver.current_url:
                self.logger.warning("Session expired, attempting to login again")
                if not self.login_to_linkedin():
                    raise Exception("Failed to re-authenticate")
                self.driver.get(profile_url)
                time.sleep(5)
            
            # Continue with data extraction...
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            profile_data = {
                'LinkedIn URL': profile_url,
                'Name': self._get_name(),
                'Bio': self._get_bio(),
                'Socials': self._get_socials(),
                'Experience': self._get_experience(),
                'Education': self._get_education()
            }
            
            self.logger.info(f"Successfully scraped profile: {profile_url}")
            return profile_data
            
        except Exception as e:
            self.logger.error(f"Error scraping profile {profile_url}: {str(e)}")
            return None

    def _get_name(self):
        """Extract profile name"""
        try:
            # Try multiple selectors for name
            name_selectors = [
                "h1.text-heading-xlarge",
                "h1.inline.t-24",
                "h1.WwpKLhFquVWNpiqSRLWEUisZfBDLUJgoYzTryo",
                "h1[class*='inline t-24']"
            ]
            
            for selector in name_selectors:
                try:
                    name_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    name = name_element.text.strip()
                    if name:
                        return name
                except NoSuchElementException:
                    continue
            return ""
        except Exception as e:
            self.logger.warning(f"Error extracting name: {str(e)}")
            return ""

    def _get_bio(self):
        """Extract profile bio/headline"""
        try:
            bio_element = self.driver.find_element(By.CLASS_NAME, 'text-body-medium')
            return bio_element.text.strip()
        except NoSuchElementException:
            return ""

    def _get_socials(self):
        """Extract social media links"""
        socials = {}
        try:
            # Find and click the contact info button using JavaScript
            contact_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="overlay/contact-info"]'))
            )
            
            # Use JavaScript to click the button
            self.driver.execute_script("arguments[0].click();", contact_button)
            time.sleep(2)
            
            # Wait for the modal to appear
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.artdeco-modal__content'))
            )
            
            # Get all social links
            social_elements = self.driver.find_elements(By.CSS_SELECTOR, '.pv-contact-info__ci-container')
            
            for element in social_elements:
                try:
                    platform = element.find_element(By.CSS_SELECTOR, '.pv-contact-info__header').text.strip()
                    link = element.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                    if platform and link:
                        socials[platform] = link
                except NoSuchElementException:
                    continue
            
            # Close the modal
            close_button = self.driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Dismiss"]')
            self.driver.execute_script("arguments[0].click();", close_button)
                    
        except Exception as e:
            self.logger.warning(f"Error extracting social links: {str(e)}")
            
        return socials

    def _get_experience(self):
        """Extract work experience"""
        experience = {}
        try:
            # Wait and scroll to ensure content is loaded
            self.driver.execute_script("window.scrollBy(0, 300)")
            time.sleep(2)
            
            # Find the experience section using the new selector
            experience_section = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Experience')]/ancestor::section")
            
            # Get all experience items
            exp_items = experience_section.find_elements(By.CSS_SELECTOR, "div.pvs-list__outer-container li.artdeco-list__item")
            
            for item in exp_items:
                try:
                    # Get role and company using the updated structure
                    role = item.find_element(By.CSS_SELECTOR, "span.mr1.t-bold span[aria-hidden='true']").text.strip()
                    company = item.find_element(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']").text.strip()
                    
                    if role and company:
                        experience[company] = role
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Error extracting experience: {str(e)}")
            
        return experience

    def _get_education(self):
        """Extract education information"""
        education = {}
        try:
            # Wait and scroll to ensure content is loaded
            self.driver.execute_script("window.scrollBy(0, 500)")
            time.sleep(2)
            
            # Find the education section using the new selector
            education_section = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Education')]/ancestor::section")
            
            # Get all education items
            edu_items = education_section.find_elements(By.CSS_SELECTOR, "div.pvs-list__outer-container li.artdeco-list__item")
            
            for item in edu_items:
                try:
                    # Get school and degree using the updated structure
                    school = item.find_element(By.CSS_SELECTOR, "span.mr1.t-bold span[aria-hidden='true']").text.strip()
                    degree = item.find_element(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']").text.strip()
                    
                    if school and degree:
                        education[school] = degree
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Error extracting education: {str(e)}")
            
        return education

    
    def _get_projects(self):
        """Extract projects (Bonus feature)"""
        projects = {}
        try:
            projects_section = self.driver.find_element(By.ID, 'projects-section')
            project_items = projects_section.find_elements(By.CLASS_NAME, 'pv-project-entity')
            
            for item in project_items:
                try:
                    project_name = item.find_element(By.CLASS_NAME, 'pv-entity__title').text.strip()
                    description = item.find_element(By.CLASS_NAME, 'pv-entity__description').text.strip()
                    projects[project_name] = description
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Error extracting projects: {str(e)}")
            
        return projects

    def scrape_profiles(self, excel_file):
        try:
            # Read Excel file and immediately close it
            with pd.ExcelFile(excel_file) as xls:
                df = pd.read_excel(xls)
            urls = df['LinkedIn URLs'].tolist()
            
            print("URLs to be scraped:", urls)  # Debug print
            
            urls = urls[:10]
            
            # Login to LinkedIn
            if not self.login_to_linkedin():
                return False
            
            # Scrape each profile
            scraped_data = []
            for url in urls:
                profile_data = self.extract_profile_data(url)
                if profile_data:
                    scraped_data.append(profile_data)
                time.sleep(3)  # Increased delay between requests
            
            # Save to CSV
            output_df = pd.DataFrame(scraped_data)
            output_df.to_csv('scraped_output.csv', index=False)
            
            self.logger.info(f"Successfully scraped {len(scraped_data)} profiles")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in scrape_profiles: {str(e)}")
            return False
            
        finally:
            self.driver.quit()

if __name__ == "__main__":
    # Initialize scraper with your LinkedIn credentials
    scraper = LinkedInScraper(
        email="salonichopra0021@gmail.com",
        password="Scaler!@#123"
    )
    
    # Start scraping
    scraper.scrape_profiles("Assignment.xlsx")