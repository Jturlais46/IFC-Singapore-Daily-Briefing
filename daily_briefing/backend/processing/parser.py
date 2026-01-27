from datetime import datetime
from typing import List, Dict
import hashlib

def generate_id(headline: str) -> str:
    """Generates a stable ID based on headline hash."""
    return hashlib.md5(headline.encode('utf-8')).hexdigest()

import re

def clean_headline(headline: str) -> str:
    """
    Cleans source suffixes and normalizes case.
    """
    if not headline: return ""
    
    # 1. Remove common source patterns at the end
    # Matches " - Source", " | Source", " : Source", " – Source" (en dash)
    # Also handles " - The Vibes", " | Asian Power" etc.
    # We look for a separator followed by text at the end.
    # Be careful not to cut off real content. Sources usually short (< 20 chars?) or specific pattern?
    # Safer: Look for specific common delimiters and strip if matches source-like pattern
    headline = re.sub(r'\s+[-|:–]\s+(?:The\s)?[A-Z][a-zA-Z0-9\s\.]+$', '', headline)
    
    # 2. Casing Normalization
    # Convert ALL CAPS or Title Case to Sentence case
    # Heuristic: If > 40% of words start with uppercase, it's probably Title Case
    words = headline.split()
    if len(words) > 3:
        caps_count = sum(1 for w in words if w[0].isupper() and w.lower() not in ["ifc", "sg", "us", "uk", "eu", "asean", "gdp"])
        if caps_count / len(words) > 0.4: 
             # Manual Sentence Case with Protected Words
             # 1. Define protected words (Acronyms, Countries, Entities)
             protected = {
                 "Singapore", "Singapore's", "Singapores", "SG", "US", "USA", "UK", "EU", "ASEAN", "IFC", "WBG", 
                 "GIC", "Temasek", "DBS", "OCBC", "UOB", "MAS", "HDB", "CPF", "M&A", "AI", "EV", "GDP", "IPO", 
                 "Malaysia", "Indonesia", "Vietnam", "Thailand", "Philippines", "China", "India", "Japan",
                 "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
             }
             
             new_words = []
             for i, w in enumerate(words):
                 # First word always capitalized
                 if i == 0:
                     new_words.append(w.capitalize())
                     continue
                 
                 # Check if word (stripped of punctuation) is in protected list
                 check_w = w.strip(".,:;!?")
                 if check_w in protected or check_w.upper() in protected:
                     new_words.append(w) # Keep original casing (or force protected casing?)
                     # If original was "SINGAPORE", keep it. If "Singapore", keep it.
                     # But if "SINGAPORE" and we want "Singapore"?
                     # Let's trust that if it matches protected, we keep it, OR we force the specific protected spelling?
                     # Safer to leave it if it matches 'meaning', but for "Title Case", "Singapore" is already correct.
                     # For "SINGAPORE", we might want "Singapore".
                     # Let's just keep 'w' if it is in protected, otherwise lower.
                 else:
                     new_words.append(w.lower())
             
             headline = " ".join(new_words)

    # 3. Enforce Period
    headline = headline.strip()
    if headline and not headline.endswith('.'):
        headline += '.'
        
    # NOTE: We now allow brackets [] for smart linking. 
    # Do NOT strip them.
        
    return headline

def clean_and_deduplicate(items: List[Dict]) -> List[Dict]:
    """
    Cleans up news items, removes duplicates, and ensures schema consistency.
    """
    seen_ids = set()
    cleaned = []
    
    for item in items:
        # Generate ID
        raw_headline = item.get("headline", "").strip()
        if not raw_headline:
            continue
            
        # Clean headline immediately
        headline = clean_headline(raw_headline)
            
        item_id = generate_id(headline) # Use cleaned headline for ID stability? Or raw? 
        # Better to use raw for stability across runs if cleaning logic changes
        # But if we want to dedupe "Title | Source" vs "Title", use cleaned.
        # Let's use cleaned for ID.
        item_id = generate_id(headline)
        
        if item_id in seen_ids:
            continue
        
        seen_ids.add(item_id)
        
        # Ensure fields exist
        cleaned.append({
            "id": item_id,
            "headline": headline,  # Store CLEANED headline
            "snippet": item.get("snippet", "").strip(),
            "url": item.get("url", ""),
            "source": item.get("source", "Unknown"),
            "date": item.get("date", datetime.now().isoformat()),
            # These will be filled by categorizer
            "section": item.get("section", None),
            "subsection": item.get("subsection", None),
            "rewritten_headline": None, 
            "is_relevant": item.get("is_relevant", None),
            "relevance_reason": item.get("relevance_reason", None)
        })
        
    return cleaned
