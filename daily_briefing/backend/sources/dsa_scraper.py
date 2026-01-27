import os
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path
from playwright.sync_api import sync_playwright

from config import DSA_BASE_URL, BASE_DIR, BROWSER_EXECUTABLE_PATH

# Persistent context directory - use LOCALAPPDATA to avoid OneDrive sync issues
LOCAL_APP_DATA = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')))
DSA_USER_DATA_DIR = LOCAL_APP_DATA / "IFC_Daily_Briefing" / "dsa_session"

class DSAScraper:
    def __init__(self):
        self.user_data_dir = DSA_USER_DATA_DIR
        os.makedirs(self.user_data_dir, exist_ok=True)

    def scrape(self, target_date: datetime) -> List[Dict]:
        """
        Scrapes Deal Street Asia Singapore section.
        """
        all_news = []
        
        with sync_playwright() as p:
            print(f"[DSA] Launching browser (Arc: {BROWSER_EXECUTABLE_PATH})...")
            launch_args = {
                "user_data_dir": str(self.user_data_dir),
                "headless": False,
                "viewport": {"width": 1280, "height": 720}
            }
            if BROWSER_EXECUTABLE_PATH:
                launch_args["executable_path"] = BROWSER_EXECUTABLE_PATH
            
            browser = p.chromium.launch_persistent_context(**launch_args)
            
            page = browser.new_page()
            
            try:
                print(f"[DSA] Navigating to {DSA_BASE_URL}...")
                page.goto(DSA_BASE_URL, timeout=30000)
                
                # Wait for page to fully load
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except:
                    page.wait_for_timeout(3000)  # fallback wait
                
                print("[DSA] Page loaded, extracting articles...")
                
                # Get all links on the page that look like article links
                # DSA articles typically have links in the stories section
                all_links = page.locator('a[href*="/stories/"]').all()
                print(f"[DSA] Found {len(all_links)} story links")
                
                seen_urls = set()
                
                for link in all_links[:30]:  # Check first 30 links
                    try:
                        href = link.get_attribute('href')
                        text = link.inner_text().strip()
                        
                        # Skip if no text, too short, or already seen
                        if not text or len(text) < 15 or href in seen_urls:
                            continue
                        
                        # Skip navigation/utility links
                        skip_keywords = ['subscribe', 'login', 'sign', 'menu', 'newsletter', 'podcast']
                        if any(kw in text.lower() for kw in skip_keywords):
                            continue
                            
                        seen_urls.add(href)
                        
                        # Make URL absolute if needed
                        if not href.startswith('http'):
                            href = f"https://www.dealstreetasia.com{href}"
                        
                        all_news.append({
                            "headline": text,
                            "url": href,
                            "snippet": "",  # DSA is paywalled, no snippets
                            "source": "Deal Street Asia",
                            "date": datetime.now()  # Assume recent
                        })
                        print(f"[DSA] Added: {text[:60]}...")
                        
                    except Exception as e:
                        continue  # Skip problematic links
                
                print(f"[DSA] Extracted {len(all_news)} articles")

            except Exception as e:
                print(f"[DSA] Error: {e}")
            
            browser.close()
            
        return all_news
