import os
import sys
# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.processing.semantic_curator import get_curator

def test_curator():
    print("Initializing Curator...")
    c = get_curator()
    print(f"Model: {c.generation_model}")
    
    headline = "Singapore's DBS Bank posts record profit, eyes regional expansion"
    print(f"\nTesting curation for: {headline}")
    
    try:
        result = c.curate(headline, "DBS reported strong Q4 earnings...")
        print("\nSUCCESS!")
        print(f"Is Relevant: {result.get('is_relevant')}")
        print(f"Section: {result.get('section')}")
        print(f"Reason: {result.get('reason')}")
    except Exception as e:
        print(f"\nFAILED: {e}")

if __name__ == "__main__":
    test_curator()
