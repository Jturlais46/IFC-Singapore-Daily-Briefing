import os
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config import FT_BASE_URL, SEARCH_KEYWORDS, BASE_DIR, BROWSER_EXECUTABLE_PATH

# Persistent context directory - use LOCALAPPDATA to avoid OneDrive sync issues
LOCAL_APP_DATA = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')))
USER_DATA_DIR = LOCAL_APP_DATA / "IFC_Daily_Briefing" / "ft_session"

class FTScraper:
    def __init__(self):
        self.user_data_dir = USER_DATA_DIR
        os.makedirs(self.user_data_dir, exist_ok=True)

    def scrape(self, target_date: datetime) -> List[Dict]:
        """
        Scrapes FT for all configured keywords.
        Returns list of news items matching the date criteria.
        """
        all_news = []
        seen_urls = set()

        with sync_playwright() as p:
            # Launch with persistent context to keep login state
            print(f"Launching browser (Arc: {BROWSER_EXECUTABLE_PATH}) for FT...")
            launch_args = {
                "user_data_dir": self.user_data_dir,
                "headless": False,
                "viewport": {"width": 1280, "height": 720}
            }
            if BROWSER_EXECUTABLE_PATH:
                launch_args["executable_path"] = BROWSER_EXECUTABLE_PATH
            
            browser = p.chromium.launch_persistent_context(**launch_args)
            
            page = browser.new_page()
            
            try:
                # 1. Check Login State
                print("Checking FT login status...")
                page.goto("https://www.ft.com", timeout=60000)
                
                # Check for login buttons
                try:
                    # Give it a moment - networkidle is safer for full SPA loads
                    page.wait_for_load_state("networkidle")
                    
                    # If "Sign In" is present and "My Account" is NOT
                    if page.get_by_text("Sign In").count() > 0:
                        if page.get_by_text("My Account").count() == 0:
                            print("❗️ NOT LOGGED IN. Please log in to FT in the opened browser window.")
                            print("Waiting up to 3 minutes for you to log in...")
                            
                            try:
                                # Wait for "My Account" to appear (meaning login success)
                                page.wait_for_selector("text=My Account", timeout=180000)
                                print("✅ Login detected! Proceeding...")
                            except PlaywrightTimeoutError:
                                print("⚠️ Login timeout. Trying to proceed anyway...")
                except Exception as e:
                    print(f"Login logic warning: {e}")
            
                # 2. Search Loop
                for keyword in SEARCH_KEYWORDS:
                    print(f"Scraping FT for keyword: {keyword}")
                    encoded_query = urllib.parse.quote(keyword)
                    url = f"{FT_BASE_URL}{encoded_query}"
                    
                    try:
                        page.goto(url, timeout=30000)
                        page.wait_for_selector('.search-results__list, .o-teaser-collection', timeout=10000)
                        
                        results = page.locator('.o-teaser-collection__item')
                        count = results.count()
                        print(f"Found {count} items for '{keyword}'")
                        
                        for i in range(count):
                            item = results.nth(i)
                            
                            # Extract Time/Date
                            time_element = item.locator('time')
                            if time_element.count() > 0:
                                date_str = time_element.get_attribute('datetime')
                                try:
                                    article_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                    if article_date.date() < target_date.date():
                                        continue 
                                except Exception:
                                    continue
                            else:
                                continue

                            # Extract Headline and Link
                            heading_link = item.locator('.o-teaser__heading a')
                            if heading_link.count() > 0:
                                headline = heading_link.inner_text().strip()
                                link = heading_link.get_attribute('href')
                                
                                if link and not link.startswith('http'):
                                    link = "https://www.ft.com" + link
                                    
                                if link in seen_urls:
                                    continue
                                seen_urls.add(link)

                                # Snippet
                                snippet = ""
                                standfirst = item.locator('.o-teaser__standfirst')
                                if standfirst.count() > 0:
                                    snippet = standfirst.inner_text().strip()

                                all_news.append({
                                    "headline": headline,
                                    "url": link,
                                    "snippet": snippet,
                                    "source": "Financial Times",
                                    "date": article_date
                                })
                                
                    except PlaywrightTimeoutError:
                        print(f"Timeout searching for {keyword}")
                        continue
                    except Exception as e:
                        print(f"Error scraping FT for {keyword}: {e}")
                        continue
            
            finally:
                browser.close()
            
        return all_news
