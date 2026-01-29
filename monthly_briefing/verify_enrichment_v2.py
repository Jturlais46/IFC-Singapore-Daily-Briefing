import sys
import os
import asyncio
import json

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.processing.semantic_curator import SemanticCurator

def verify_enrichment_v2():
    print("Initializing SemanticCurator...")
    curator = SemanticCurator()
    print("Curator initialized.")
    
    # User's exact failing examples, populated with typical snippets that WOULD contain the data
    samples = [
        {
            "id": "1",
            "headline": "Singapore dollar hits 11-year high against the greenback",
            "snippet": "The Singapore dollar strengthened to 1.28 against the US dollar, the highest level since 2014, driven by MAS policy settings.",
            "expect_in_headline": ["1.28"]
        },
        {
            "id": "2",
            "headline": "Singapore factory output sees fourth straight month of growth",
            "snippet": "Manufacturing output increased by 11.8% year-on-year in September, beating analyst forecasts of 5%.",
            "expect_in_headline": ["11.8%"]
        },
        {
            "id": "3",
            "headline": "MAS focuses on inflation risk amid Singapore's strong growth trajectory",
            "snippet": "The central bank remains wary as core inflation is projected to average 3.0–4.0% this year, despite upgrading GDP forecasts.",
            "expect_in_headline": ["3.0", "4.0", "3-4%"] # Check for range or values
        }
    ]

    print(f"\nRunning enrichment V2 verification on {len(samples)} samples...\n")
    
    passed = 0
    
    for sample in samples:
        print(f"[{sample['id']}] Input: {sample['headline']}")
        print(f"       Snippet Data: {sample['snippet']}")
        try:
            result = curator.curate(sample['headline'], sample['snippet'])
            rewritten = result.get('rewritten_headline', '')
            
            print(f"       Output: {rewritten}")
            
            # Check for matches
            is_match = False
            for item in sample['expect_in_headline']:
                # broad check
                if item.lower() in rewritten.lower():
                    is_match = True
                    break
            
            if is_match:
                print(f"RESULT: [PASS] Found expected data.")
                passed += 1
            else:
                print(f"RESULT: [FAIL] Missing expected data: {sample['expect_in_headline']}")
                
        except Exception as e:
            print(f"ERROR: {e}")
        print("-" * 50)
        
    print(f"\nFINAL RESULTS: {passed}/{len(samples)} PASSED.")

if __name__ == "__main__":
    verify_enrichment_v2()
