import os
import json
import logging
from datetime import datetime
from typing import List
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type
)

# Load environment
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

class KeywordsAgent:
    """
    ai agent that devises keywords to fetch relevant articles based on IFC directives.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        # Initialize Gemini client
        from google import genai
        self.client = genai.Client(api_key=self.api_key)
        self.model = "models/gemini-flash-latest"

    @retry(
        retry=retry_if_exception_type(Exception), 
        wait=wait_random_exponential(multiplier=1, max=60),
        stop=stop_after_attempt(3)
    )
    def generate_search_queries(self, date: datetime) -> List[str]:
        """
        Generate a list of Google Search queries based on the date and directives.
        """
        date_str = date.strftime("%Y-%m-%d")
        
        prompt = f"""
You are an expert Research Analyst for the IFC (International Finance Corporation) Singapore office.
Your task is to generate targeted Google Search queries to find news from {date_str} that matches specific strategic directives.

CONTEXT - "Relevant and Actionable" news means:
1. Environment changer (macro/policy): Shifts IFC's operating context in Singapore.
2. Pipeline signal (deal/financing): Singapore-based sponsor requiring capital (>$30m), pursuing M&A/JV/LOI.
3. Market-moving capital signal: VC/PE fundraising, platform build-ups, IPOs.
4. Action hook: Warrants outreach or watchlist.

SPECIFIC THEMES TO CAPTURE:
- Cross-border activity by Singapore sponsors (M&A, expansions).
- Banking/finance shifts in Singapore affecting capital formation.
- High-impact policy/regulatory moves.
- Large financing needs from Singapore sponsors globally (US$30m+).
- Large asset sales/disposals/acquisitions involving Singapore sponsors.
- IPOs in Singapore and globally by Singapore-based sponsors.
- Material JVs / LOIs / strategic partnerships.
- VC / PE / post–Series B fundraising.
- Large projects globally by Singapore sponsors (infra, energy transition, digital).

TASK:
Generate 15 highly specific Google Search queries to find this news for the date {date_str}.
Mix broad terms with specific financial keywords.
Do NOT include the date in the query strings themselves (the scraper will handle date filtering).
Focus on "Singapore" combined with deal terms.

OUTPUT:
Return ONLY a JSON array of strings. Example: ["Singapore M&A", "Temasek holdings investment", "Singtel acquisition"]
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            text = response.text
            # Clean markdown
            if text.startswith("```json"): text = text[7:]
            if text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            
            queries = json.loads(text.strip())
            
            # Sanity check
            if not isinstance(queries, list):
                logger.warning("Agent returned non-list. customized fallback.")
                return self._get_fallback_queries()
                
            return queries[:15] # Limit to 15
            
        except Exception as e:
            logger.error(f"Keywords generation failed: {e}")
            return self._get_fallback_queries()

    def _get_fallback_queries(self):
        return [
            "Singapore M&A news",
            "Singapore large acquisition",
            "Singapore fundraising series B",
            "Singapore IPO news",
            "Temasek investment news",
            "GIC investment news",
            "Singapore infrastructure project",
            "Singapore energy transition deal",
            "Singapore banking regulation change",
            "Singapore cross-border investment"
        ]
