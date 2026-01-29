import asyncio
from datetime import datetime, timedelta
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from processing.keywords_agent import KeywordsAgent
from sources.google_scraper import GoogleSearchScraper

async def test_google_research():
    try:
        print("--- Testing KeywordsAgent ---")
        agent = KeywordsAgent()
        target_date = datetime.now() - timedelta(days=1)
        queries = agent.generate_search_queries(target_date)
        print(f"Generated {len(queries)} queries:")
        for q in queries:
            print(f" - {q}")
        
        print("\n--- Testing GoogleSearchScraper ---")
        scraper = GoogleSearchScraper()
        # Test with broader queries to verify selectors
        test_queries = ["Singapore business news", "Temasek acquisitions", "Singapore startups"]
        print(f"Scraping for: {test_queries}")
        results = await asyncio.to_thread(scraper.scrape, test_queries, target_date)
        
        print(f"\nFound {len(results)} items:")
        for item in results:
            print(f"[{item['source']}] {item['headline']}")
            # print(f"URL: {item['url']}")
            # print(f"Snippet: {item['snippet'][:100]}...")
            print("-" * 20)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_google_research())
