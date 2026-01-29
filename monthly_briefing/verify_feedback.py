import asyncio
import json
import os
import sys
import tempfile

# Add project root to path
sys.path.append(os.getcwd())

from backend.processing.semantic_curator import SemanticCurator

# Use absolute paths or correct relative paths based on CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Write test file to SYSTEM TEMP directory to avoid OneDrive permission issues
TEST_EXAMPLES_PATH = os.path.join(tempfile.gettempdir(), "ifc_briefing_test_examples.json")
ORIGINAL_PATH = os.path.join(BASE_DIR, "backend", "processing", "relevance_examples.json")

async def test_feedback_loop():
    print(f"CWD: {os.getcwd()}")
    print("Creating fresh test examples file...")
    
    initial_data = {
        "relevant_examples": [],
        "irrelevant_examples": [],
        "keywords_always_relevant": ["TestKeyword"]
    }
    
    # Create the file directly
    with open(TEST_EXAMPLES_PATH, 'w', encoding='utf-8') as f:
        json.dump(initial_data, f)
        
    print(f"Created {TEST_EXAMPLES_PATH}")

    try:
        curator = SemanticCurator(examples_path=TEST_EXAMPLES_PATH)
        
        # Test 1: Restore (Add Back) -> Should Learn
        headline_restore = "Test Item Restored by User"
        print(f"\n[Test 1] Simulating RESTORE of: '{headline_restore}'")
        curator.add_example(headline_restore, is_relevant=True, reason="User Restore")
        
        # Verify JSON
        with open(TEST_EXAMPLES_PATH, 'r') as f:
            data = json.load(f)
            found = any(ex['headline'] == headline_restore for ex in data.get('relevant_examples', []))
            print(f"  -> Saved to JSON (Relevant)? {found}")
            if not found: raise Exception("Failed to save restored item to JSON")

        # Test 2: Remove with Learn=True -> Should Learn
        headline_remove = "Test Item Removed by User"
        print(f"\n[Test 2] Simulating REMOVE (Learn=True) of: '{headline_remove}'")
        curator.add_example(headline_remove, is_relevant=False, reason="User Remove")
        
        # Verify JSON
        with open(TEST_EXAMPLES_PATH, 'r') as f:
            data = json.load(f)
            found = any(ex['headline'] == headline_remove for ex in data.get('irrelevant_examples', []))
            print(f"  -> Saved to JSON (Irrelevant)? {found}")
            if not found: raise Exception("Failed to save removed item to JSON")
            
        print("\nSUCCESS: Feedback loop logic verified.")

    except Exception as e:
        print(f"Test failed: {e}")
        raise e
    finally:
        # Cleanup
        if os.path.exists(TEST_EXAMPLES_PATH):
            try:
                os.remove(TEST_EXAMPLES_PATH)
                print("Cleanup complete.")
            except:
                print("Cleanup failed (file might be locked or gone).")

if __name__ == "__main__":
    asyncio.run(test_feedback_loop())
