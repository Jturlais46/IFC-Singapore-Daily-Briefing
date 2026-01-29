
import sys
import os
import hashlib
from typing import List, Dict

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.processing.parser import clean_and_deduplicate

def reproduction_test():
    print("Testing deduplication logic...")
    
    # User examples
    duplicates = [
        {
            "headline": "Singapore’s STI breaches 4,900 as DBS, OCBC, UOL, and Jardine Matheson hit record highs.",
            "source": "Business Times", 
            "url": "http://bt.com"
        },
        {
            "headline": "Singapore’s STI breaches 4,900 as DBS, OCBC, UOL, and Jardine Matheson close at record highs.",
            "source": "Straits Times",
            "url": "http://st.com"
        }
    ]
    
    # Add a distinct item to ensure we don't clear everything
    items = duplicates + [
        {
            "headline": "Something completely different happened in Singapore.",
            "source": "CNA",
            "url": "http://cna.com"
        }
    ]
    
    cleaned = clean_and_deduplicate(items)
    
    print(f"\nInput items: {len(items)}")
    print(f"Output items: {len(cleaned)}")
    
    for item in cleaned:
        print(f"- {item['headline']}")

    if len(cleaned) == 2:
        print("\n[OK] SUCCESS: Duplicates were removed.")
    elif len(cleaned) == 3:
        print("\nX FAILURE: Duplicates still present.")
    else:
        print(f"\n[?] Unexpected count: {len(cleaned)}")

if __name__ == "__main__":
    reproduction_test()
