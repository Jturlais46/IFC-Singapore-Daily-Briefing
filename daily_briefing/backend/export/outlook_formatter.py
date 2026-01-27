from typing import List, Dict
import urllib.parse
from datetime import datetime
from config import SECTIONS, REAL_SECTOR_SUBSECTIONS

def generate_html_email(categorized_items: List[Dict]) -> str:
    """
    Generates the HTML body for the daily briefing email using the Monthly Update style.
    """
    
    html = """
    <html>
    <body style="font-family: Calibri, sans-serif; font-size: 11pt; color: #1F497D;">
        <h2 style="color: #1F497D;">IFC Singapore Daily Briefing</h2>
        <p><i>Generated on {}</i></p>
        <hr>
    """.format(datetime.now().strftime("%B %d, %Y"))

    # Group items by section
    items_by_section = {section: [] for section in SECTIONS}
    
    for item in categorized_items:
        sec = item.get("section")
        if sec in items_by_section:
            items_by_section[sec].append(item)
    
    for section in SECTIONS:
        section_items = items_by_section[section]
        
        # Determine if we need to render this section (skip empty? maybe keep header for consistency?)
        # User said "consistent decision-oriented structure", implies headers should be there.
        # But if empty, maybe just show "No significant updates."
        
        html += f'<h3 style="background-color: #E0E0E0; padding: 5px; color: #002060;">{section}</h3>'
        
        if not section_items:
            html += "<p><i>No actionable updates today.</i></p>"
            continue
            
        # Special handling for Real-Sector Deal Flow subsections
        if section == "Real-Sector Deal Flow":
            # Group by subsection
            inr_items = [i for i in section_items if i.get("subsection") == "INR (Infrastructure)"]
            mas_items = [i for i in section_items if i.get("subsection") == "MAS (Manufacturing, Agribusiness, Services)"]
            others = [i for i in section_items if i not in inr_items and i not in mas_items]
            
            if inr_items:
                html += "<h4><u>INR (Infrastructure)</u></h4><ul>"
                for item in inr_items:
                    html += _render_item_li(item)
                html += "</ul>"
                
            if mas_items:
                html += "<h4><u>MAS (Manufacturing, Agribusiness, Services)</u></h4><ul>"
                for item in mas_items:
                    html += _render_item_li(item)
                html += "</ul>"
                
            if others:
                 html += "<h4><u>Other / General</u></h4><ul>"
                 for item in others:
                     html += _render_item_li(item)
                 html += "</ul>"
                 
        else:
            # Standard List
            html += "<ul>"
            for item in section_items:
                html += _render_item_li(item)
            html += "</ul>"
            
    html += "</body></html>"
    return html

def _render_item_li(item: Dict) -> str:
    """Helper to render a single list item with smart linking."""
    import re
    
    headline = item.get("rewritten_headline") or item.get("headline") or ""
    url = item.get("url", "#")
    # source = item.get("source", "") # Source hidden per user request
    
    # Smart Linking Logic
    # Check for [Bracketed Text] which indicates the Subject/Anchor
    match = re.search(r"\[(.*?)\]", headline)
    
    if match:
        # Link ONLY the content inside brackets
        anchor_text = match.group(1)
        linked_anchor = f'<a href="{url}" style="color: #1F497D; text-decoration: none;">{anchor_text}</a>'
        # Replace the full [Key Text] with the linked version
        # We need to be careful to replace only the specific match or use simple string replace if unique
        # Using string replacement on the full match `[Key Text]`
        full_match_str = match.group(0) # e.g. [Temasek]
        final_html = headline.replace(full_match_str, linked_anchor)
        
        # Remove any other brackets if multiple (unlikely, but good to clean)
        final_html = final_html.replace("[", "").replace("]", "")
        
    else:
        # Fallback: Link the first 4 words
        words = headline.split()
        if len(words) > 0:
            link_len = min(len(words), 4)
            anchor_text = " ".join(words[:link_len])
            remainder = " ".join(words[link_len:])
            
            linked_anchor = f'<a href="{url}" style="color: #1F497D; text-decoration: none;">{anchor_text}</a>'
            final_html = f"{linked_anchor} {remainder}"
        else:
             # Empty headline?
             final_html = f'<a href="{url}" style="color: #1F497D; text-decoration: none;">Link</a>'

    return f"""
    <li style="margin-bottom: 8px;">
        <span style="color: #1F497D;">{final_html}</span>
    </li>
    """

def create_mailto_link(html_body: str) -> str:
    """Creates a mailto link to open in Outlook (Subject + Body)."""
    # Note: mailto links have size limits (approx 2KB). 
    # For a full daily briefing, this will likely fail.
    # We should rely on clipboard copy for the full body.
    # But we can try to open a draft with just the subject?
    
    subject = f"IFC Singapore Daily Briefing - {datetime.now().strftime('%d %b %Y')}"
    # We won't put the body in the mailto if it's too long.
    return f"mailto:?subject={urllib.parse.quote(subject)}"

