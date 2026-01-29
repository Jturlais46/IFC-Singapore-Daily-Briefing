
import os
import sys

# Add backend to sys path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from processing.categorizer import Categorizer

def test_rewrite():
    print("Initializing Categorizer...")
    try:
        cat = Categorizer()
    except Exception as e:
        print(f"Failed to initialize Categorizer: {e}")
        return

    test_headline = "Singapore's Temasek Holdings invests $50 million in new AI startup - CNA"
    print(f"\nOriginal Headline: {test_headline}")
    
    print("Testing rewrite_headline_only...")
    try:
        rewritten = cat.rewrite_headline_only(test_headline)
        print(f"Rewritten Headline: {rewritten}")
        
        if not rewritten:
            print("FAILED: Returned empty string")
        elif rewritten == test_headline:
            print("FAILED: Returned original headline (rewrite failed silently)")
        else:
            print("SUCCESS: Headline rewritten")
            
    except Exception as e:
        print(f"FAILED with error: {e}")

if __name__ == "__main__":
    test_rewrite()
