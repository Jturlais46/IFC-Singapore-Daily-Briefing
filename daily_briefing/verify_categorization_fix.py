
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.processing.semantic_curator import SemanticCurator

async def verify_categorization():
    print("Initializing Semantic Curator...")
    # Initialize without loading full examples to speed up if possible, 
    # but the class loads them by default.
    curator = SemanticCurator()
    
    # Test case: An article that MIGHT have been miscategorized as a portfolio highlight
    # We want to ensure it gets categorized as something else (e.g. Real-Sector Deal Flow or Financial Institutions)
    # or rejected, but definitely NOT "IFC Portfolio / Pipeline Highlights"
    
    test_item = {
        "id": "test_1",
        "headline": "Keppel infrastructure trust acquires new portfolio asset",
        "snippet": "Keppel Infrastructure Trust has added a new wind farm to its portfolio in a deal worth $200m.",
        "semantic_score": 0.8,
        "semantic_reason": "Strong keyword match"
    }
    
    print("\nRunning batch judgment on test item...")
    start_result = await asyncio.to_thread(curator._ai_batch_judgment, [test_item])
    
    result = start_result.get("test_1")
    
    if not result:
        print("ERROR: No result returned from AI.")
        return

    print("\n--- AI Result ---")
    print(f"Is Relevant: {result.get('is_relevant')}")
    print(f"Section: {result.get('section')}")
    print(f"Reason: {result.get('reason')}")
    
    invalid_category = "IFC Portfolio / Pipeline Highlights"
    
    if result.get("section") == invalid_category:
        print(f"\n[FAIL] Article was assigned to forbidden category: {invalid_category}")
    else:
        print(f"\n[PASS] Article was NOT assigned to forbidden category. Assigned to: {result.get('section')}")

    # Also test force_categorize
    print("\nRunning force_categorize on test item...")
    force_result = await asyncio.to_thread(curator.force_categorize, test_item['headline'], test_item['snippet'])
    
    print("\n--- Force Categorize Result ---")
    print(f"Section: {force_result.get('section')}")
    
    if force_result.get("section") == invalid_category:
        print(f"\n[FAIL] force_categorize assigned to forbidden category: {invalid_category}")
    else:
        print(f"\n[PASS] force_categorize did NOT assign to forbidden category. Assigned to: {force_result.get('section')}")

if __name__ == "__main__":
    asyncio.run(verify_categorization())
