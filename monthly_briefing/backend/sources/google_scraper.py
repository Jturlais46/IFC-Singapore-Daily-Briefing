import os
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config import BROWSER_EXECUTABLE_PATH
LOCAL_APP_DATA = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')))
GOOGLE_USER_DATA_DIR = LOCAL_APP_DATA / "IFC_Monthly_Briefing" / "google_session"

class GoogleSearchScraper:
    def __init__(self):
        self.user_data_dir = GOOGLE_USER_DATA_DIR
        os.makedirs(self.user_data_dir, exist_ok=True)

    def scrape(self, queries: List[str], date_start: datetime, date_end: datetime) -> List[Dict]:
        """
        Scrapes Google News/Search for given queries, strictly filtered by date range.
        """
        all_news = []
        seen_urls = set()
        
        # Format dates for Google Search (MM/DD/YYYY)
        # cd_min and cd_max
        d_min = date_start.strftime("%m/%d/%Y")
        d_max = (date_end - timedelta(days=1)).strftime("%m/%d/%Y") # date_end is exclusive start of next month usually
        
        tbs_date = f"cdr:1,cd_min:{d_min},cd_max:{d_max}"

        with sync_playwright() as p:
            logger.info(f"Launching browser (Arc: {BROWSER_EXECUTABLE_PATH}) for Google Search...")
            launch_args = {
                "user_data_dir": self.user_data_dir,
                "headless": False, # Switch to False to pass corporate blocks/interact if needed
                "viewport": {"width": 1280, "height": 720}
            }
            if BROWSER_EXECUTABLE_PATH:
                launch_args["executable_path"] = BROWSER_EXECUTABLE_PATH
            
            browser = p.chromium.launch_persistent_context(**launch_args)
            
            page = browser.new_page()
            
            try:
                for query in queries:
                    encoded_query = urllib.parse.quote(query)
                    url = f"https://www.google.com/search?q={encoded_query}&tbs={tbs_date}&tbm=nws"
                    
                    logger.info(f"Searching Google News with filter: {url}")
                    
                    try:
                        page.goto(url, timeout=30000)
                        
                        # Broadly find all result containers or direct links
                        # Google News often uses 'div.g' or 'div.SoI6e' or just <a> with specific structure
                        results_selector = 'div#rso div.g, div#rso div.SoI6e, div#rso div.nS4ojb, div#rso div.WlyS9b, div#rso div.fP1uSe'
                        result_blocks = page.locator(results_selector)
                        count = result_blocks.count()
                        
                        if count == 0:
                            # Fallback: Just look for ALL h3 tags in the search results area
                            result_blocks = page.locator('div#rso h3')
                            count = result_blocks.count()
                            logger.info(f"Fallback: Found {count} h3 headers for '{query}'")
                        else:
                            logger.info(f"Found {count} result blocks for '{query}'")

                        for i in range(count):
                            item = result_blocks.nth(i)
                            
                            try:
                                # If we are looking at an h3 directly (fallback)
                                if item.evaluate("node => node.tagName") == "H3":
                                    headline = item.inner_text().strip()
                                    # Link is likely parent or grandparent
                                    link_el = item.locator('xpath=./ancestor::a').first
                                    if link_el.count() == 0: continue
                                    link = link_el.get_attribute('href')
                                    snippet = "" # Hard to find from h3 only
                                else:
                                    # Standard block logic
                                    title_el = item.locator('h3, h4').first
                                    if title_el.count() > 0:
                                        headline = title_el.inner_text().strip()
                                    else:
                                        continue
                                    
                                    link_el = item.locator('a').first
                                    if link_el.count() == 0: continue
                                    link = link_el.get_attribute('href')
                                    
                                    # Snippet fallback
                                    snippet = ""
                                    try:
                                        snippet_el = item.locator('div.VwiC3b, div.mCBkyc, div[style*="clamp"]').first
                                        if snippet_el.count() > 0:
                                            snippet = snippet_el.inner_text().strip()
                                    except: pass
                                
                                if not headline or not link or not link.startswith('http'):
                                    continue
                                    
                                if link in seen_urls:
                                    continue
                                seen_urls.add(link)
                                
                                # Extract Snippet
                                # Usually in a div with some class like "GI74S" or similar
                                # Let's try to find the text that isn't the headline or the source
                                snippet = ""
                                try:
                                    # This is a bit heuristic as Google classes change
                                    snippet_element = item.locator('div[style*="clamp"], div.VwiC3b, div.mCBkyc')
                                    if snippet_element.count() > 0:
                                        snippet = snippet_element.first.inner_text().strip()
                                except:
                                    pass
                                
                                # Extract Source
                                source = "Google Research"
                                try:
                                    source_element = item.locator('div.Mg7Gbe, span.SJ77j, div.UP5eWb')
                                    if source_element.count() > 0:
                                        source = source_element.first.inner_text().strip()
                                except:
                                    pass

                                all_news.append({
                                    "headline": headline,
                                    "url": link,
                                    "snippet": snippet,
                                    "source": f"Google: {source}",
                                    "date": date_start # Approximate date for grouping
                                })
                            except Exception as item_e:
                                logger.warning(f"Error parsing item: {item_e}")
                                continue
                                
                    except PlaywrightTimeoutError:
                        logger.warning(f"Timeout searching for {query}")
                        continue
                    except Exception as e:
                        logger.error(f"Error scraping Google for {query}: {e}")
                        continue
                        
            finally:
                browser.close()
                
        return all_news
