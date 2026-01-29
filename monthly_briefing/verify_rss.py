from backend.config import RSS_FEEDS
from backend.sources.rss_scraper import get_rss_news
import logging

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)

def test_rss_fetching():
    print("Testing RSS Feed Fetching...")
    
    # Test each source individually to identify specific failures
    for source, urls in RSS_FEEDS.items():
        print(f"\n--- Testing Source: {source} ---")
        try:
            # Create a mini-config for just this source
            mini_config = {source: urls}
            items = get_rss_news(mini_config)
            
            if items:
                print(f"SUCCESS: Fetched {len(items)} items.")
                print(f"First item: {items[0]['title']}")
                print(f"Date: {items[0]['date']}")
            else:
                print("WARNING: No items returned.")
        except Exception as e:
            print(f"ERROR: Failed to fetch {source}. Reason: {e}")

if __name__ == "__main__":
    test_rss_fetching()
