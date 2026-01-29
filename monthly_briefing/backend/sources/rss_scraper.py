import feedparser
import datetime
from typing import List, Dict
import logging
import requests
import urllib3

# Suppress InsecureRequestWarning since we are explicitly disabling verify
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_rss_feed(url: str, source_name: str, date_start: datetime.datetime = None, date_end: datetime.datetime = None) -> List[Dict]:
    """
    Fetches and parses a single RSS feed.
    Returns a list of dictionaries with normalized keys:
    {
        'title': str,
        'url': str,
        'date': str (YYYY-MM-DD),
        'source': str,
        'summary': str
    }
    """
    logger.info(f"Fetching RSS feed for {source_name}: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Use requests to fetch content, bypassing SSL verification if needed
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        response.raise_for_status()
        
        # Parse the content with feedparser
        feed = feedparser.parse(response.content)
        
        if feed.bozo:
             # Just log warning, but try to process anyway as often it's minor XML issues
            logger.warning(f"Potential XML issue parsing feed {source_name}: {feed.bozo_exception}")
        
        items = []
        for entry in feed.entries:
            # multiple date fields might exist, try published first, then updated
            published = getattr(entry, 'published_parsed', None)
            if not published:
                published = getattr(entry, 'updated_parsed', None)
            
            if published:
                dt = datetime.datetime(*published[:6])
                date_str = dt.strftime('%Y-%m-%d')
                
                # Filter by date range if provided
                if date_start:
                    if dt < date_start:
                        continue
                if date_end:
                     if dt >= date_end:
                         continue
            else:
                dt = datetime.datetime.now()
                date_str = dt.strftime('%Y-%m-%d')

            # Summary handling (some feeds use 'summary', others 'description')
            summary_text = getattr(entry, 'summary', '')
            if not summary_text:
                summary_text = getattr(entry, 'description', '')

            # Safely get title and link
            title = getattr(entry, 'title', 'No Title')
            link = getattr(entry, 'link', '')

            items.append({
                'headline': title,
                'url': link,
                'date': date_str,
                'source': source_name,
                'summary': summary_text
            })
            
        logger.info(f"Found {len(items)} items from {source_name}")
        return items

    except Exception as e:
        logger.error(f"Error fetching feed {source_name}: {e}")
        return []

def get_rss_news(feed_config: Dict[str, List[str]], date_start: datetime.datetime = None, date_end: datetime.datetime = None) -> List[Dict]:
    """
    Aggregates news from multiple RSS feeds defined in feed_config.
    feed_config format: {'Source Name': ['url1', 'url2']}
    """
    all_news = []
    
    # If date_start/end passed, ensure naive
    if date_start and date_start.tzinfo:
        date_start = date_start.replace(tzinfo=None)
    if date_end and date_end.tzinfo:
        date_end = date_end.replace(tzinfo=None)
    
    for source, urls in feed_config.items():
        if isinstance(urls, str):
            urls = [urls]
            
        for url in urls:
            news_items = fetch_rss_feed(url, source, date_start, date_end)
            all_news.extend(news_items)
            
    return all_news
