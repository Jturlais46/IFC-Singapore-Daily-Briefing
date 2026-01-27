import asyncio
from datetime import datetime
from backend.main import _fetch_rss

async def test_filtering():
    print("Testing Backend Source Filtering...")
    
    date_from = datetime.now()
    
    # Test 1: Fetch ONLY "The Business Times"
    print("\n--- Test 1: Only 'The Business Times' ---")
    items = await asyncio.to_thread(_fetch_rss, date_from, ["The Business Times"])
    
    bt_items = [i for i in items if i['source'] == "The Business Times"]
    other_items = [i for i in items if i['source'] != "The Business Times"]
    
    print(f"Total items: {len(items)}")
    print(f"Business Times items: {len(bt_items)}")
    print(f"Other items: {len(other_items)}")
    
    if len(bt_items) > 0 and len(other_items) == 0:
        print("✅ SUCCESS: Only Business Times fetched.")
    else:
        print("❌ FAILURE: Filtering failed.")

    # Test 2: Fetch "The Straits Times" AND "The Diplomat"
    print("\n--- Test 2: 'The Straits Times' + 'The Diplomat' ---")
    items = await asyncio.to_thread(_fetch_rss, date_from, ["The Straits Times", "The Diplomat"])
    
    st_items = [i for i in items if i['source'] == "The Straits Times"]
    dip_items = [i for i in items if i['source'] == "The Diplomat"]
    other_items = [i for i in items if i['source'] not in ["The Straits Times", "The Diplomat"]]
    
    print(f"Total items: {len(items)}")
    print(f"Straits Times items: {len(st_items)}")
    print(f"Diplomat items: {len(dip_items)}")
    print(f"Other items: {len(other_items)}")
    
    if len(other_items) == 0:
        print("✅ SUCCESS: Only selected sources fetched.")
    else:
        print("❌ FAILURE: Found unrequested sources.")

if __name__ == "__main__":
    asyncio.run(test_filtering())
