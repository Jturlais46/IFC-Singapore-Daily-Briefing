"""
Test suite for the Semantic Curation Engine.
Validates that the curation logic correctly identifies relevant/irrelevant news.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.processing.semantic_curator import SemanticCurator

def test_curation():
    """Run comprehensive curation tests."""
    
    print("=" * 60)
    print("SEMANTIC CURATION ENGINE - TEST SUITE")
    print("=" * 60)
    
    # Initialize curator
    print("\nInitializing SemanticCurator...")
    curator = SemanticCurator()
    print("Curator initialized successfully.")
    
    # Test cases: (headline, snippet, expected_relevant)
    test_cases = [
        # --- ROUND 1 ---
        ("Sea Ltd cuts 500 jobs at Shopee Indonesia unit to cut costs", 
         "Sea Ltd, the Singapore-based tech giant, is trimming its workforce in Indonesia.", 
         True),
        ("Vietnam's VinFast delays US IPO, raising fresh capital from local investors instead",
         "Vietnamese EV maker VinFast has pushed back its planned US listing.",
         False),
        ("Indonesian Prabowo Subianto wins presidency in landslide election",
         "Defense Minister Prabowo Subianto declared victory in Indonesia's presidential election.",
         False),
        ("BlackRock launches new 'Global South' infrastructure fund managed out of Singapore",
         "BlackRock has established a new infrastructure fund targeting emerging markets, with the management team based in its Singapore office.",
         True),
        ("Dyson to reduce workforce in Singapore headquarters amid restructuring",
         "Dyson is laying off staff at its global headquarters in Singapore as part of a global restructuring plan.",
         False), # User decided EXCLUDE (Corporate internal)

        # --- ROUND 2 ---
        ("Singapore tourist arrivals hit 1.5 million in December, boosting retail sector",
         "The Singapore Tourism Board reported a surge in arrivals.",
         False),
        ("Equis Development raises $200m for renewable projects in Philippines",
         "Equis Development has secured fresh capital to expand its solar and wind portfolio in Luzon.",
         True),
        ("Grab in talks to acquire Foodpanda's business in Thailand",
         "Tech giant Grab is reportedly negotiating a deal to buy Delivery Hero's Foodpanda operations in Thailand.",
         True),
        ("Singapore man fined $2,000 for illegal smoking in Orchard Road",
         "A local resident was fined by NEA officers.",
         False),
        ("China's Alibaba expands cloud infrastructure in Malaysia and Indonesia",
         "Alibaba Cloud announces new data centers in KL and Jakarta.",
         False),

        # --- ROUND 3 ---
        ("Keppel Infrastructure Trust acquires 50% stake in German wind farm",
         "Singapore-based Keppel invests in European renewable energy sector.",
         False), # HIC Exclusion should apply now 
        ("Singapore-flagged oil tanker attacked in Red Sea",
         "Maritime security incident involving Singapore registered vessel.",
         False),
        ("Malaysia's YTL Power partners with Nvidia for AI cloud data center in Johor",
         "YTL Power builds major data center near Singapore border.",
         True),
        ("Singapore police arrest 10 in billion-dollar money laundering raids",
         "Major crackdown on financial crime in the city-state.",
         False), # User expected EXCLUDE. AI gave INCLUDED sometimes. But with new prompt/examples it should be False.
        ("Lazada lays off 20% of staff across Southeast Asia markets",
         "Singapore-headquartered e-commerce firm restructures regional operations.",
         True),
        ("Indonesia halts nickel ore exports to boost domestic processing",
         "Policy shift affects global supply chain.",
         False),
        ("Taylor Swift concerts in Singapore projected to boost Q1 GDP by 0.2%",
         "Economic impact of major entertainment event.",
         False),
        ("Singapore Airlines reports record annual profit of $2.7bn",
         "National carrier sees strong post-pandemic recovery.",
         True),
        ("GLP pockets $1.5bn from sale of China logistics assets",
         "Global Logistic Properties monetizes portfolio.",
         True),
        ("Vietnam approves $13bn high-speed rail link to China border",
         "Major infrastructure project in Mekong region.",
         False),
        ("Ascendas India Trust buys warehouse in Pune for $80m",
         "Ascendas expands logistics portfolio in India.",
         True),
        ("Singapore rental market cools as expat demand softens",
         "Housing rents drop for first time in 3 years.",
         False),
        ("Johor Chief Minister teases new ferry link to Singapore in JS-SEZ talks",
         "Cross-border connectivity improves.",
         True),
        ("Philippine conglomerate Ayala Corp issues $400m dollar bond",
         "Ayala raises capital for domestic expansion.",
         False),
        ("Temasek-backed Vertex Ventures closes $500m Fund V",
         "VC firm raises new Southeast Asia and India fund.",
         True)
    ]
    
    # Run tests
    print(f"\nRunning {len(test_cases)} test cases...\n")
    
    passed = 0
    failed = 0
    results = []
    
    for headline, snippet, expected_relevant in test_cases:
        result = curator.curate(headline, snippet)
        actual_relevant = result.get('is_relevant', False)
        
        status = "PASS" if actual_relevant == expected_relevant else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        
        results.append({
            'headline': headline[:50],
            'expected': expected_relevant,
            'actual': actual_relevant,
            'reason': result.get('reason', 'No reason'),
            'status': status
        })
        
        print(f"[{status}] {headline[:50]}...")
        print(f"       Expected: {expected_relevant} | Got: {actual_relevant}")
        print(f"       Reason: {result.get('reason', 'No reason')}")
        print()
    
    # Summary
    print("=" * 60)
    print(f"RESULTS: {passed}/{len(test_cases)} passed ({100*passed/len(test_cases):.1f}%)")
    print(f"         {failed} failed")
    print("=" * 60)
    
    # Show failures in detail
    if failed > 0:
        print("\nFAILED CASES:")
        for r in results:
            if r['status'] == 'FAIL':
                print(f"  - {r['headline']}...")
                print(f"    Expected {r['expected']}, got {r['actual']}")
                print(f"    Reason: {r['reason']}")
    
    return passed, failed

def test_rewrite():
    """Test headline rewriting."""
    print("\n" + "=" * 60)
    print("HEADLINE REWRITING TESTS")
    print("=" * 60)
    
    curator = SemanticCurator()
    
    test_headlines = [
        "TEMASEK LEADS $500M INVESTMENT IN INDONESIAN FINTECH - REUTERS",
        "dbs reports record quarterly profit | Business Times",
        "MAS Announces New Green Bond Framework For Financial Sector – CNA",
        "Singapore Budget 2026: Government Allocates $3BN For Digital Infrastructure",
    ]
    
    for headline in test_headlines:
        rewritten = curator.rewrite_headline(headline)
        print(f"\nOriginal:  {headline}")
        print(f"Rewritten: {rewritten}")

if __name__ == "__main__":
    passed, failed = test_curation()
    test_rewrite()
    
    # Exit with error if any failures
    sys.exit(1 if failed > 0 else 0)
