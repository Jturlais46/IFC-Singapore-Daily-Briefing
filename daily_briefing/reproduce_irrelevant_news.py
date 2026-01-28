
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.processing.semantic_curator import SemanticCurator

BAD_EXAMPLES = [
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

async def reproduce_issues():
    curator = SemanticCurator()
    print(f"Testing {len(BAD_EXAMPLES)} items that should be REJECTED...")
    
    items = [{"id": str(i), "headline": ex, "snippet": ex, "semantic_score": 0.5, "semantic_reason": "Testing"} for i, ex in enumerate(BAD_EXAMPLES)]
    
    # We use _ai_batch_judgment as that's the main gatekeeper
    results = await asyncio.to_thread(curator._ai_batch_judgment, items)
    
    failed_count = 0
    passed_count = 0
    
    print("\n--- RESULTS ---")
    for item in items:
        res = results.get(item['id'])
        if res and res.get('is_relevant'):
            print(f"[FAIL] Accepted: {item['headline']}")
            print(f"       Reason: {res.get('reason')}")
            failed_count += 1
        else:
            reason = res.get('reason') if res else "Rejected (Implicitly)"
            print(f"[PASS] Rejected: {item['headline']}")
            print(f"       Reason: {reason}")
            passed_count += 1
            
    print(f"\nSummary: {passed_count} Passed (Rejected), {failed_count} Failed (Accepted)")

if __name__ == "__main__":
    asyncio.run(reproduce_issues())
