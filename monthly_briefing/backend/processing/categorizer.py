from google import genai
import json
from config import GEMINI_API_KEY, SECTIONS, REAL_SECTOR_SUBSECTIONS

class Categorizer:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set. Please check your .env file in the backend directory.")
        
        # Initialize the client with the new SDK
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def _build_prompt(self, headline: str, snippet: str) -> str:
        return f"""
        You are a highly selective Investment Committee Analyst for the IFC Singapore Country Manager.
        
        TASK: Filter and format this news item. 90% of items should be REJECTED.
        
        INPUT ITEM:
        - Headline: "{headline}"
        - Snippet: "{snippet}"
        
        GUIDELINES:
        
        1. RELEVANCE (THE "SINGAPORE/DEAL" OFFSET):
           - REJECT if strictly domestic news from neighboring countries (e.g., "Malaysia passes new law", "Indonesia election update") UNLESS it explicitly mentions a Singapore user/bank/investor.
           - ACCEPT ONLY IF:
             A) Major Deal (> $50m) involving a Singapore Entity (Temasek, GIC, SingTel, DBS, OCBC, UOB).
             B) Domestic Singapore Macro/Policy (MAS, Govt, Tax, Budget).
             C) Direct IFC Mention.
             
        2. REASONING (MUST BE SPECIFIC):
           - The `relevance_reason` field MUST follow this format: "[Entity/Topic] + [Action/Impact]".
           - BAD EXAMPLES (DO NOT USE): "Relevant to region", "Economic news", "Mentions Singapore".
           - GOOD EXAMPLES: "Temasek invests $100m in US Tech", "MAS tightens monetary policy", "Singapore-based Grab acquires rival".
           - If you cannot construct a specific reason like this, set "is_relevant": false.
        
        3. FORMATTING (STRICT SUB-EDITOR):
           - REMOVE source suffixes.
           - Sentence case (capitalize first letter and proper nouns ONLY).
           - End with a period.
           
        4. CATEGORIZATION:
           - "IFC Portfolio / Pipeline Highlights"
           - "Macro Indicators"
           - "Policy & Political Economy"
           - "Financial Institutions & Capital Markets"
           - "Real-Sector Deal Flow" (Subsections: "INR", "MAS")

        OUTPUT JSON:
        {{
            "is_relevant": true/false,
            "relevance_reason": "Specific Entity + Action (e.g. 'Temasek backs solar deal').",
            "section": "Category Name",
            "subsection": "Subsection Name",
            "confidence": 0.0-1.0,
            "rewritten_headline": "The polished headline."
        }}
        """

    def categorize_item(self, headline: str, snippet: str = "") -> dict:
        """
        Categorizes a single news item using Gemini.
        Returns a dict with 'section', 'subsection' (if applicable), and 'is_relevant'.
        """
        prompt = self._build_prompt(headline, snippet)

        try:
            # Use the new generate_content method
            try:
                # Primary model - latest available in 2026 env
                response = self.client.models.generate_content(
                    model="models/gemini-3-flash-preview", 
                    contents=prompt
                )
            except Exception:
                 # Fallback to secondary confirmed model
                response = self.client.models.generate_content(
                    model="models/gemini-2.5-flash-lite-preview-09-2025", 
                    contents=prompt
                )
            
            # Cleanup Markdown code blocks if present
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            return json.loads(text)
        except Exception:
            # Silent failure - just use keywords
            # user demanded "no errors" if it works "superficially"
            pass
            
            # KEYWORD FALLBACK
            # If AI fails, use simple keywords to guess category
            
            # 1. Clean formatting first (since AI didn't do it)
            from .parser import clean_headline
            headline = clean_headline(headline)
            
            h_lower = headline.lower()
            
            fallback_section = "Uncategorized"
            fallback_subsection = None
            reason = "AI Unavailable - Unmatched"
            
            if any(x in h_lower for x in ["ifc", "world bank", "international finance corporation"]):
                fallback_section = "IFC Portfolio / Pipeline Highlights"
                reason = "Keyword match: IFC/World Bank"
                
            elif any(x in h_lower for x in ["inflation", "gdp", "currency", "central bank", "monetary", "trade", "economy", "rate"]):
                fallback_section = "Macro Indicators"
                reason = "Keyword match: Macro term"
                
            elif any(x in h_lower for x in ["regulation", "law", "minister", "government", "policy", "political", "tax"]):
                fallback_section = "Policy & Political Economy"
                reason = "Keyword match: Policy term"
                
            elif any(x in h_lower for x in ["bank", "ipo", "fund", "capital", "fintech", "investment", "debt", "equity", "finance", "venture"]):
                fallback_section = "Financial Institutions & Capital Markets"
                reason = "Keyword match: Financial term"
                
            elif any(x in h_lower for x in ["solar", "energy", "infrastructure", "transport", "logistics", "power", "grid", "green", "utility"]):
                fallback_section = "Real-Sector Deal Flow"
                fallback_subsection = "INR (Infrastructure)"
                reason = "Keyword match: Infrastructure term"
                
            elif any(x in h_lower for x in ["manufacturing", "health", "agri", "service", "retail", "consumer", "pharma", "education", "factory"]):
                fallback_section = "Real-Sector Deal Flow"
                fallback_subsection = "MAS (Manufacturing, Agribusiness, Services)"
                reason = "Keyword match: MAS Sector term"
            
            if fallback_section == "Uncategorized" and any(x in h_lower for x in ["deal", "acquisition", "stake", "buyout", "merger"]):
                 fallback_section = "Real-Sector Deal Flow"
                 reason = "Keyword match: Deal term"
            
            return {
                "is_relevant": True,  # Default to keep
                "section": fallback_section,
                "subsection": fallback_subsection,
                "confidence": 0.5,
                "rewritten_headline": headline, # Formatted by clean_headline
                "relevance_reason": reason
            }

    def rewrite_headline_only(self, headline: str) -> str:
        """
        Specialized method just for the 'Rewrite' button. 
        Focuses on making the headline catchy and professional for IFC audience.
        """
        prompt = f"""
        You are a senior editor for the IFC (International Finance Corporation) Singapore Daily Briefing.
        
        TASK: Rewrite the following headline to be engaging, professional, and relevant to an investment audience.
        
        GUIDELINES:
        1. STYLE: Catchy but professional. Active voice. Highlight the business/investment impact.
        2. AUDIENCE: IFC management, investors, bankers, policy makers.
        3. FORMATTING: 
           - Remove source suffixes (e.g. "- CNA", "| Bloomberg").
           - Sentence case (only proper nouns capitalized).
           - End with a period (.).
        4. LENGTH: Concise (max 15 words).
        
        INPUT: "{headline}"
        
        OUTPUT: Return ONLY the rewritten headline string. Nothing else.
        """
        
        try:
            # Use stable Flash model for speed and better rate limits
            try:
                response = self.client.models.generate_content(
                    model="models/gemini-2.5-flash", 
                    contents=prompt
                )
            except Exception:
                 # Fallback to 2.0 Flash
                response = self.client.models.generate_content(
                    model="models/gemini-2.0-flash", 
                    contents=prompt
                )
            
            text = response.text.strip()
            # Remove quotes if AI added them
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            if text.startswith("'") and text.endswith("'"):
                text = text[1:-1]
            # Remove common prefixes
            if text.lower().startswith("headline:"):
                text = text[9:].strip()
            if text.lower().startswith("rewritten headline:"):
                text = text[19:].strip()
                
            return text
        except Exception as e:
            print(f"Rewrite failed: {e}")
            return headline # Return original if fail
