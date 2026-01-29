import time
import asyncio
import logging
from backend.processing.semantic_curator import get_curator

# Configure logging to see rate limit warnings
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diagnose")

async def test_fetch_latency():
    print("--- Diagnostic: Simulating Fetch Latency ---")
    curator = get_curator()
    
    # Simulate 5 news items
    items = [
        {"headline": "Singapore GDP grows by 3%", "snippet": "Economy expands in Q1."},
        {"headline": "Temasek invests in AI startup", "snippet": "Sovereign fund leads round."},
        {"headline": "Indonesia elections update", "snippet": "Voting continues."},
        {"headline": "Malaysia ringgit falls", "snippet": "Currency hits low."},
        {"headline": "IFC partners with DBS", "snippet": "Green trade finance deal."}
    ]
    
    print(f"Processing {len(items)} items in PARALLEL...")
    start_time = time.time()
    
    async def process_item(item):
        print(f"Starting: {item['headline']}")
        # Simulating the main app logic
        res = await asyncio.to_thread(curator.curate, item['headline'], item['snippet'])
        print(f"Done: {item['headline']}")
        return res

    results = await asyncio.gather(*[process_item(item) for item in items])
        
    total_time = time.time() - start_time
    print(f"\nTotal time: {total_time:.2f}s")
    print(f"Average time per item: {total_time/len(items):.2f}s")
    
if __name__ == "__main__":
    asyncio.run(test_fetch_latency())
