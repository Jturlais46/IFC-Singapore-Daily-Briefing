
import asyncio
import logging
from backend.processing.semantic_curator import get_curator

# Setup basic logging
logging.basicConfig(level=logging.INFO)

def test_batch_curation():
    curator = get_curator()
    
    # Mock news items
    items = [
        # Explicit Keywords (Should be auto-kept)
        {"headline": "IFC invests in Singapore green bond", "snippet": "The International Finance Corporation announced..."},
        
        # Relevant Semantic (Strong match)
        {"headline": "Singtel explores $500m data center sale", "snippet": "Singapore telecom giant looking to divest assets..."},
        
        # Irrelevant (Should be auto-rejected or rejected by AI)
        {"headline": "Local cat rescued from tree in Jurong", "snippet": "SCDF was called to the scene..."},
        
        # Borderline (AI should judge)
        {"headline": "Singapore inflation rate holds steady", "snippet": "MAS says core inflation remains manageable..."}
    ]
    
    print("\n--- Testing Batch Curation ---")
    results = curator.curate_batch(items)
    
    print(f"\nProcessed {len(items)} items, resulting in {len(results)} relevant items.")
    
    for item in results:
        print(f"\n[KEPT] {item['headline']}")
        print(f"Reason: {item.get('reason')}")
        print(f"Section: {item.get('section')}")

if __name__ == "__main__":
    test_batch_curation()
