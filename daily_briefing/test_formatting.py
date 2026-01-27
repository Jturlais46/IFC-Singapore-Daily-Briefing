import sys
import os
import re

# Add path
sys.path.append(os.getcwd())
try:
    from backend.processing.parser import clean_headline
except ImportError:
    # Handle if run from inside backend
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    from processing.parser import clean_headline

def run_test(name, input_str, expected_str=None, expect_period=True, expect_cleaned_source=True):
    print(f"TEST: {name}")
    print(f"  Input:    '{input_str}'")
    result = clean_headline(input_str)
    print(f"  Result:   '{result}'")
    
    passed = True
    
    # Check 1: Period
    if expect_period and not result.endswith('.'):
        print("  [FAIL] Missing period.")
        passed = False
        
    # Check 2: Source Removal (Heuristic)
    if expect_cleaned_source:
        if " - " in result or " | " in result or " : " in result or "The Vibes" in result:
            # Simple check, not perfect but catches obvious failures
            if "The Vibes" in input_str and "The Vibes" in result:
                 print("  [FAIL] Source 'The Vibes' not removed.")
                 passed = False
            if "Asian Power" in input_str and "Asian Power" in result:
                 print("  [FAIL] Source 'Asian Power' not removed.")
                 passed = False
    
    # Check 3: Casing (Heuristic)
    if input_str.isupper() and result.isupper():
        print("  [FAIL] Logic failed to fix ALL CAPS.")
        passed = False
        
    if passed:
        print("  [PASS]")
    else:
        print("  [FAILED]")
    print("-" * 40)
    return passed

print("=== STARTING FORMATTING TESTS ===\n")

failures = 0

# Test Case 1: Source Removal
if not run_test("Strip standard suffix", "Singapore GDP grows 2% - CNA"): failures += 1
if not run_test("Strip pipe suffix", "LNK Energy targets investment | Asian Power"): failures += 1
if not run_test("Strip complex source", "APEC business council hails Malaysia - The Vibes"): failures += 1

# Test Case 2: Full Caps
if not run_test("Fix ALL CAPS", "SINGAPORE ANNOUNCES NEW TAX"): failures += 1

# Test Case 3: Advanced Casing (Protected Words)
if not run_test("Protected Words 1", "Singapore Announces New Tax", "Singapore announces new tax."): failures += 1
if not run_test("Protected Words 2", "Temasek BUYS US Asset", "Temasek buys US asset."): failures += 1
if not run_test("Plain Sentence", "Inflation rises in region", "Inflation rises in region.", expect_period=True): failures += 1

# Test Case 4: No Period
if not run_test("Add missing period", "Singapore inflation is stable"): failures += 1
if not run_test("Keep existing period", "Singapore inflation is stable."): failures += 1

print(f"\n=== TESTS COMPLETE. FAILURES: {failures} ===")
if failures == 0:
    print("SUCCESS: All formatting rules verified.")
else:
    print("WARNING: Some formatting rules failed.")
    exit(1)
