import sys
import os
import asyncio
import logging

# Configure logging to see our new retry logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.processing.semantic_curator import SemanticCurator

def reproduction_test():
    print("Initializing SemanticCurator...")
    try:
        curator = SemanticCurator()
    except Exception as e:
        print(f"Failed to init curator: {e}")
        return

    irrelevant_examples = [
        "Canada and India pledge to grow oil and petroleum trade in energy reset.",
        "India to slash car tariffs to 40% in pending trade deal with the EU.",
        "Thai gold traders with transactions exceeding 10bn baht must report to the central bank.",
        "Stricter SkillsFuture course funding guidelines implemented for 9,500 courses across 500 training providers.",
        "DPM Gan notes Singapore’s fertility rate has not stabilised and the citizen core will shrink without action.",
        "Singapore must increase integration as immigration is crucial for the economy amid low birth rates.",
        "Singapore appears to clarify liability for errors caused by artificial intelligence.",
        "RCEP was a major breakthrough, but it still needs work.",
        "India scraps 10-minute delivery requirement for food and grocery platforms.",
        "Malaysia’s Maybank aims to mobilize $74bn in sustainable finance by 2030.",
        "Malaysia’s Maybank to invest $2.5bn in AI and technology through 2030.",
        "Hidden risks build at Vietnam banks due to mounting debt guarantees.",
        "China’s Eastroc beverage seeks to raise HK$10.14bn in its Hong Kong IPO.",
        "Indonesian stocks plunge 7% following MSCI warning regarding market investability."
    ]

    print(f"\nTesting {len(irrelevant_examples)} irrelevant examples reported by user...")
    
    items = []
    for i, headline in enumerate(irrelevant_examples):
        items.append({
            "id": f"test_{i}",
            "headline": headline,
            "snippet": headline, 
            "link": "http://test.com",
            "published_date": "2026-01-28"
        })
        
    print("Running curate_batch...")
    # Run synchronously as this is a test script
    results, rejected = curator.curate_batch(items, queue=None, loop=None)
    
    print("\n--- RESULTS ---")
    print(f"Total: {len(items)}")
    print(f"Relevant (FALSE POSITIVES): {len(results)}")
    print(f"Rejected (CORRECT): {len(rejected)}")
    
    if results:
        print("\n[FALSE POSITIVES - These should have been rejected]")
        for item in results:
            print(f"- {item['headline']}")
            print(f"  Reason: {item.get('relevance_reason', 'N/A')}")
            print(f"  Section: {item.get('section', 'N/A')}")
            print("-" * 40)
            
    if rejected:
        print("\n[CORRECTLY REJECTED]")
        for item in rejected:
            print(f"- {item['headline']}")
            print(f"  Reason: {item.get('relevance_reason', 'N/A')}")
            
if __name__ == "__main__":
    reproduction_test()
