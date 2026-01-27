#!/usr/bin/env python3
"""
Diagnostic script to test Gemini API access.
This will help identify exactly why AI calls are failing.
"""
import os
import sys
import json
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("FATAL: GEMINI_API_KEY not found in .env")
    sys.exit(1)

print(f"API Key loaded: ...{api_key[-8:]}")

# Test 1: Import the library
print("\n=== Test 1: Import google-genai ===")
try:
    from google import genai
    print("SUCCESS: google-genai imported")
except ImportError as e:
    print(f"FAIL: {e}")
    sys.exit(1)

# Test 2: Create client
print("\n=== Test 2: Create Client ===")
try:
    client = genai.Client(api_key=api_key)
    print("SUCCESS: Client created")
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)

# Test 3: List available models
print("\n=== Test 3: List Models ===")
available_models = []
try:
    for m in client.models.list():
        available_models.append(m.name)
    print(f"SUCCESS: Found {len(available_models)} models")
    # Print first 10
    for m in available_models[:10]:
        print(f"  - {m}")
    if len(available_models) > 10:
        print(f"  ... and {len(available_models) - 10} more")
except Exception as e:
    print(f"FAIL: {e}")

# Test 4: Try text generation with various models
print("\n=== Test 4: Text Generation ===")
test_models = [
    "models/gemini-3-flash-preview",
    "models/gemini-2.5-flash-lite-preview-09-2025",
    "models/gemini-2.5-flash-preview-09-2025",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
]

working_model = None
for model_name in test_models:
    print(f"\nTrying: {model_name}")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'Hello World' in exactly those two words."
        )
        print(f"  SUCCESS! Response: {response.text.strip()}")
        working_model = model_name
        break
    except Exception as e:
        print(f"  FAIL: {str(e)[:100]}")

if working_model:
    print(f"\n=== CONCLUSION: Use model '{working_model}' ===")
else:
    print("\n=== CONCLUSION: No text generation models available ===")
    print("Falling back to embedding-only approach")

# Test 5: Try Embedding API
print("\n=== Test 5: Embedding API ===")
embedding_models = [m for m in available_models if 'embed' in m.lower()]
print(f"Found {len(embedding_models)} embedding models:")
for m in embedding_models[:5]:
    print(f"  - {m}")

if embedding_models:
    test_embed_model = embedding_models[0]
    print(f"\nTrying embedding with: {test_embed_model}")
    try:
        # Try the embed_content method
        response = client.models.embed_content(
            model=test_embed_model,
            contents="Singapore Temasek invests in renewable energy"
        )
        # Check if we got embeddings
        if hasattr(response, 'embeddings') and response.embeddings:
            emb_len = len(response.embeddings[0].values)
            print(f"  SUCCESS! Got embedding of dimension {emb_len}")
        elif hasattr(response, 'embedding'):
            emb_len = len(response.embedding.values)
            print(f"  SUCCESS! Got embedding of dimension {emb_len}")
        else:
            print(f"  Response structure: {dir(response)}")
    except Exception as e:
        print(f"  FAIL: {e}")

print("\n=== DIAGNOSTIC COMPLETE ===")
