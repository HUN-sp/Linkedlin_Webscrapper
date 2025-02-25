# LinkedIn Webscrapper

A Python tool that scrapes LinkedIn profiles to extract information like name and bio.

## Prerequisites

- Python 3.x
- Git

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/HUN-sp/LinkedIn_Webscrapper.git
   cd LinkedIn_Webscrapper
   ```

2. Install required dependencies:
  
   ```bash
   pip install pandas selenium beautifulsoup4 webdriver-manager
   ```

## Configuration

Before running the script, make sure you have:
1. Chrome browser installed
2. LinkedIn account credentials ready

## Usage

Run the script with your LinkedIn credentials:

```bash
python linkedin_scraper.py
```

You will be prompted to enter your LinkedIn email and password for authentication.

## Features

- Scrapes LinkedIn profile information
- Extracts name and bio
- Extracts education and experience details
- Exports data to CSV format

## File Structure

- `linkedin_scraper.py`: Main script for scraping
- `scraped_output.csv`: Output file containing scraped data (not tracked in git)

## Notes

- This tool is for educational purposes only
- Be mindful of LinkedIn's scraping policies to avoid account restrictions
- The script includes waiting times to avoid being detected as a bot

## Troubleshooting

If you encounter issues with ChromeDriver:
1. Ensure Chrome is updated to the latest version
2. The script uses webdriver-manager to automatically download the appropriate ChromeDriver version
3. If manual installation is needed, download the correct version from [ChromeDriver website](https://chromedriver.chromium.org/downloads)

## License

[MIT License](LICENSE)