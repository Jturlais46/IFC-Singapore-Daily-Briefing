"""
Semantic Curation Engine for IFC Singapore Daily Briefing.

Uses vector embeddings to compare incoming news against curated examples
of relevant/irrelevant content, combined with keyword rules and AI reasoning.
"""
import os
import json
import logging
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception
)

# Load environment
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

class QuotaExceededError(Exception):
    """Custom error for daily quota exhaustion to stop retrying."""
    pass

def should_retry_error(exception):
    """Retry on standard errors but STOP on QuotaExceededError, Auth, or Bad Request."""
    if isinstance(exception, QuotaExceededError):
        return False
    
    # Check for authentication/bad request errors in string representation
    err_msg = str(exception)
    if "401" in err_msg or "403" in err_msg or "API key not valid" in err_msg:
        return False
    if "400" in err_msg or "InvalidArgument" in err_msg:
        return False
    if "404" in err_msg or "Not Found" in err_msg:
        return False
        
    return isinstance(exception, Exception)

def log_retry_attempt(retry_state):
    """Log retry attempts for visibility."""
    if retry_state.outcome.failed:
        exc = retry_state.outcome.exception()
        logging.getLogger(__name__).warning(f"Retrying... Attempt #{retry_state.attempt_number} due to {type(exc).__name__}: {exc}")

class SemanticCurator:
    """
    A multi-layered curation engine that combines:
    1. Hard keyword rules (always include/exclude)
    2. Semantic similarity to curated examples
    3. AI-powered final reasoning
    """
    
    def __init__(self, examples_path: str = None):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        # Initialize Gemini client
        from google import genai
        self.client = genai.Client(api_key=self.api_key)
        
        # Model configuration
        # Revert to gemini-flash-latest (Limit 20) as 2.0-flash returned Limit 0.
        # Combined with Batch Size 50, this provides 1000 items capacity.
        self.generation_model = "models/gemini-flash-latest" 
        self.fallback_model = "models/gemini-pro-latest" 
        self.embedding_model = "models/gemini-embedding-001"
        
        # Load relevance examples
        if examples_path is None:
            examples_path = os.path.join(os.path.dirname(__file__), 'relevance_examples.json')
        
        self.examples = self._load_examples(examples_path)
        self.examples_path = examples_path # Store path for saving
        
        # Pre-compute embeddings for examples (cached)
        self._relevant_embeddings = None
        self._irrelevant_embeddings = None
        
        logger.info(f"SemanticCurator initialized with {len(self.examples.get('relevant_examples', []))} relevant examples")
    
    def _load_examples(self, path: str) -> dict:
        """Load relevance examples from JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load examples: {e}")
            return {
                "relevant_examples": [],
                "irrelevant_examples": [],
                "keywords_always_relevant": ["IFC", "World Bank", "Singapore", "Temasek", "GIC"]
            }
    
    
    @retry(
        retry=retry_if_exception(should_retry_error), 
        wait=wait_random_exponential(multiplier=1, max=30),
        stop=stop_after_attempt(3)
    )
    def _report_progress(self, message: str, type: str = "log", queue=None, loop=None):
        """Helper to send progress updates back to the UI queue."""
        if queue and loop:
            try:
                import asyncio
                msg = {"type": type, "message": message}
                asyncio.run_coroutine_threadsafe(queue.put(msg), loop)
            except Exception as e:
                logger.error(f"Error reporting progress: {e}")
        logger.info(message)

    @retry(
        retry=retry_if_exception(should_retry_error), 
        wait=wait_random_exponential(multiplier=1, max=30),
        stop=stop_after_attempt(3),
        before_sleep=log_retry_attempt
    )
    def _get_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Get embeddings for a list of texts using batch API call."""
        if not texts:
            return []
            
        try:
            # The Gemini embed_content can process multiple texts at once
            # by passing a list to the contents parameter
            # Max batch size is typically 100, so chunk if needed
            
            CHUNK_SIZE = 100
            all_embeddings = []
            
            for i in range(0, len(texts), CHUNK_SIZE):
                chunk = texts[i:i + CHUNK_SIZE]
                
                # Single API call for the entire chunk
                response = self.client.models.embed_content(
                    model=self.embedding_model,
                    contents=chunk  # Pass list of strings
                )
                
                # Extract embeddings from response
                if hasattr(response, 'embeddings') and response.embeddings:
                    # Response contains multiple embeddings in order
                    for emb in response.embeddings:
                        all_embeddings.append(emb.values)
                else:
                    # Fallback - assume None for all in chunk
                    logger.warning(f"Unexpected embedding response structure for chunk of {len(chunk)} items")
                    all_embeddings.extend([None] * len(chunk))
                
            return all_embeddings
            
        except Exception as e:
            if "429" in str(e) or "Resource" in str(e) or "Quota" in str(e):
                err_msg = str(e)
                # Detect Daily Quota to stop retrying
                if "Daily" in err_msg or "RequestsPerDay" in err_msg:
                     raise QuotaExceededError(err_msg)

                logger.warning(f"Rate limit hit in batch embedding, retrying... ({e})")
                raise e
            logger.error(f"Batch embedding failed: {e}")
            return [None] * len(texts)

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Legacy single embedding wrapper (calls batch with 1 item)."""
        res = self._get_batch_embeddings([text])
        return res[0] if res else None
    
    import threading
    _embedding_lock = threading.Lock()

    def _compute_example_embeddings(self):
        """Pre-compute embeddings for all example headlines."""
        if self._relevant_embeddings is not None:
            return  # Already computed
        
        with self._embedding_lock:
            if self._relevant_embeddings is not None:
                return

            logger.info("Computing embeddings for relevance examples (Batch)...")
            
            # Batch process relevant examples
            rel_exs = self.examples.get('relevant_examples', [])
            rel_texts = [ex['headline'] for ex in rel_exs]
            rel_embs = self._get_batch_embeddings(rel_texts)
            
            self._relevant_embeddings = []
            for ex, emb in zip(rel_exs, rel_embs):
                if emb:
                    self._relevant_embeddings.append({
                        'headline': ex['headline'],
                        'reason': ex['reason'],
                        'embedding': emb
                    })
            
            # Batch process irrelevant examples
            irrel_exs = self.examples.get('irrelevant_examples', [])
            irrel_texts = [ex['headline'] for ex in irrel_exs]
            irrel_embs = self._get_batch_embeddings(irrel_texts)
            
            self._irrelevant_embeddings = []
            for ex, emb in zip(irrel_exs, irrel_embs):
                if emb:
                    self._irrelevant_embeddings.append({
                        'headline': ex['headline'],
                        'reason': ex['reason'],
                        'embedding': emb
                    })
            
            logger.info(f"Computed {len(self._relevant_embeddings)} relevant and {len(self._irrelevant_embeddings)} irrelevant embeddings")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
    
    def _check_keywords(self, headline: str) -> Tuple[bool, Optional[str]]:
        """Check if headline contains must-include keywords."""
        h_lower = headline.lower()
        
        for kw in self.examples.get('keywords_always_relevant', []):
            if kw.lower() in h_lower:
                return True, f"Contains key entity: {kw}"
        
        return False, None
    
    def _compute_semantic_score(self, headline: str) -> Tuple[float, str]:
        """
        Compute semantic relevance score.
        Returns (score, explanation) where score > 0 means relevant, < 0 means irrelevant.
        """
        # Ensure embeddings are computed
        self._compute_example_embeddings()
        
        # Get embedding for input headline
        headline_emb = self._get_embedding(headline)
        if headline_emb is None:
            return 0.0, "Embedding unavailable"
        
        # Find most similar relevant example
        best_relevant_sim = 0.0
        best_relevant_match = None
        for ex in self._relevant_embeddings:
            sim = self._cosine_similarity(headline_emb, ex['embedding'])
            if sim > best_relevant_sim:
                best_relevant_sim = sim
                best_relevant_match = ex
        
        # Find most similar irrelevant example
        best_irrelevant_sim = 0.0
        best_irrelevant_match = None
        for ex in self._irrelevant_embeddings:
            sim = self._cosine_similarity(headline_emb, ex['embedding'])
            if sim > best_irrelevant_sim:
                best_irrelevant_sim = sim
                best_irrelevant_match = ex
        
        # Compute differential score
        score = best_relevant_sim - best_irrelevant_sim
        
        if score > 0.05:  # Clearly more similar to relevant
            explanation = f"Similar to: '{best_relevant_match['headline'][:50]}...' ({best_relevant_match['reason']})"
        elif score < -0.05:  # Clearly more similar to irrelevant
            explanation = f"Rejected: Similar to irrelevant pattern ({best_irrelevant_match['reason']})"
        else:
            explanation = "Borderline - requires AI judgment"
        
        return score, explanation
    
    def _extract_text(self, response) -> str:
        """Safely extract text from Gemini response."""
        try:
            if hasattr(response, 'text') and response.text:
                return response.text
            
            # Fallback to candidates structure
            if hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
                
        except Exception:
            pass
        return ""

    @retry(
        retry=retry_if_exception(should_retry_error), 
        wait=wait_random_exponential(multiplier=2, max=60),
        stop=stop_after_attempt(5),
        before_sleep=log_retry_attempt
    )
    def _ai_final_judgment(self, headline: str, snippet: str, semantic_score: float, semantic_reason: str) -> Dict:
        """Use AI for final relevance judgment and categorization."""
        
        prompt = f"""You are the IFC Singapore Country Manager's guardrail agent. Your ONLY job is to filter news to keep those immediately relevant to IFC Singapore.

CONTEXT - "Relevant and Actionable" means ONE of the following is true:
1. Environment changer (macro/policy): Shifts IFC's operating context in Singapore (growth, inflation, rates/liquidity, regulatory, trade/geo dynamics).
2. Pipeline signal (deal/financing): Singapore-based sponsor requiring capital (>$30m), pursuing M&A/JV/LOI, or scaling into IFC sectors/geographies.
3. Market-moving capital signal: VC/PE fundraising (later stage), platform build-ups, IPOs, shifts in banking/asset management.
4. Action hook for the office: Warrants outreach, internal coordination, or "watchlist" (client engagement, partner mapping, risk flag).

CAPTURE THESE SPECIFIC ITEMS:
- Cross-border activity by Singapore sponsors (M&A, expansions, investments).
- Banking/finance shifts in Singapore affecting capital formation.
- High-impact policy/regulatory moves with business implication.
- Large financing needs from Singapore sponsors globally (rule-of-thumb: US$30m+).
- Large asset sales/disposals/acquisitions involving Singapore sponsors globally.
- IPOs in Singapore and IPOs globally where the sponsor is Singapore-based.
- Material JVs / LOIs / strategic partnerships involving Singapore sponsors.
- VC / PE / post–Series B fundraising.
- Large projects by Singapore sponsors globally (infra, energy transition, digital).

NEWS ITEM:
Headline: "{headline}"
Snippet: "{snippet if snippet else 'No snippet available'}"
Semantic Score: {semantic_score:.3f} ({semantic_reason})

OUTPUT (JSON only):
{{
    "is_relevant": true/false,
    "confidence": 0.0-1.0,
    "reason": "Cite the specific criteria matched (e.g. 'Pipeline: Singtel expansive M&A', 'Macro: MAS policy shift').",
    "section": "Category name or null if irrelevant",
    "subsection": "Specific subsection if applicable (e.g., 'M&A', 'Policy', 'Fundraising'), or null",
    "rewritten_headline": "Clean headline with period."
}}"""

        try:
            response = self.client.models.generate_content(
                model=self.generation_model,
                contents=prompt
            )
            
            text = self._extract_text(response).strip()
            
            if not text:
                raise ValueError("Empty response from AI")

            # Clean markdown code blocks
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            result = json.loads(text.strip())
            
            # Ensure subsection key exists even if model forgot it
            if 'subsection' not in result:
                result['subsection'] = None
                
            return result
            
        except Exception as e:
            if "429" in str(e) or "Resource" in str(e) or "Quota" in str(e):
                logger.warning(f"Rate limit hit in judgment, retrying... ({e})")
                raise e
            logger.warning(f"AI judgment failed: {e}")
            
            # STRICT FALLBACK LOGIC
            # If AI fails (e.g. 404 model not found, or rate limit exceeded despite retries),
            # we must only keep items that are SEMANTICALLY VERY STRONG matches.
            # Previously we kept anything with score > 0 (neutral). Now we require > 0.3 (Strong match).
            is_strong_semantic_match = semantic_score > 0.3
            
            if is_strong_semantic_match:
                reason = semantic_reason
            else:
                reason = f"AI Unavailable + Weak Semantic Match ({semantic_score:.2f}). Rejected safety."
            
            return {
                "is_relevant": is_strong_semantic_match,
                "confidence": 0.4 if is_strong_semantic_match else 0.0,
                "reason": reason,
                "section": "Uncategorized" if is_strong_semantic_match else None,
                "subsection": None,
                "rewritten_headline": headline
            }
    
    @retry(
        retry=retry_if_exception(should_retry_error), 
        wait=wait_random_exponential(multiplier=2, max=60),
        stop=stop_after_attempt(5),
        before_sleep=log_retry_attempt
    )
    def _ai_batch_judgment(self, candidates: List[Dict]) -> Dict[str, Dict]:
        """
        Judge a batch of candidates in one API call to save RPD.
        Returns a dict mapping original_headline -> result_dict
        """
        if not candidates:
            return {}

        prompt = """You are the IFC Singapore Country Manager's STRICT FILTER agent.
**YOUR DEFAULT ANSWER IS "REJECT"**. Only mark is_relevant: true if the item CLEARLY meets relevance criteria AND does NOT match ANY exclusion.

*** CRITICAL: APPLY EXCLUSION RULES FIRST - IF ANY MATCH, REJECT IMMEDIATELY ***

EXCLUSION RULES (REJECT THESE - CHECK EACH ONE):
1. HIGH INCOME COUNTRIES (HIC): REJECT investments by Singapore sponsors into High Income Countries (USA, UK, Germany, Europe, Japan, Australia, Canada, etc.). IFC ONLY focuses on Emerging Markets.
   - REJECT: "Keppel invests in German wind farm" (Germany is HIC).
   - REJECT: "VinFast IPO in US" (US is HIC).
   - ACCEPT: "Ascendas invests in India" (India is EM).
2. DOMESTIC SINGAPORE SOCIAL: REJECT domestic Singapore social/lifestyle news:
   - Demographics (fertility rates, birth rates, aging, population).
   - Education policy (SkillsFuture, universities, course funding).
   - Immigration/manpower policy (unless directly affects business investment flows).
   - General legal/tech commentary (AI liability, privacy laws) without deal context.
   - Retail, Tourism, Shopping, Dining.
   - Crime, Police Raids, Money Laundering arrests (unless Systemic Banking Crisis).
   - Local Transport, Housing, HDB, Rental market.
3. NEIGHBOR POLITICS: REJECT domestic politics of Indonesia/Malaysia/Vietnam/Thailand/India (e.g. elections, local regulations) UNLESS there is a specific, explicit Singapore treaty/trade deal mentioned.
4. PURELY FOREIGN: REJECT regional/international news with NO link to Singapore:
   - Foreign bilateral deals (Canada-India oil trade, India-EU tariffs) - no Singapore.
   - Foreign company IPOs (China company HK IPO) - no Singapore sponsor.
   - Regional bank internal strategies (Maybank AI investment) - unless deal with SG entity.
   - Regional banking risks (Vietnam debt) - unless Singapore exposure stated.
5. GENERAL COMMENTARY: REJECT general trade/economic commentary without actionable hook:
   - "RCEP needs more work" - no deal, no action.
   - "Market outlook uncertain" - no specific signal.

STRICT RELEVANCE CRITERIA (If NOT Excluded, matches ONE?):
1. Pipeline signal (deal/financing): Singapore-based sponsor requiring capital (>$30m), M&A/JV, or scaling into Emerging Markets.
   - INCLUDES: "Singapore Airlines reports record profit" (Capital Signal).
   - INCLUDES: "Dyson cuts jobs in Singapore HQ" (Major Corp Restructuring).
2. Environment changer (macro/policy): Shifts IFC's operating context in Singapore (MAS policy, Trade Agreements, JS-SEZ).
3. Market-moving capital signal: VC/PE fundraising (later stage), platform build-ups, IPOs in Singapore.
4. Action hook: High-level ministerial trade visits from Emerging Markets to Singapore.
5. JS-SEZ: Any meaningful development regarding the Johor-Singapore Special Economic Zone.

CATEGORIES (ASSIGN ONE):
- Macro Indicators
- Policy & Political Economy
- Financial Institutions & Capital Markets
- Real-Sector Deal Flow
- JS-SEZ

INPUT: List of news items with ID, Headline, Snippet, Semantic Score.

OUTPUT: A JSON Object where keys are the Item IDs and values are the decision objects.
Format:
{
    "ID_1": {
        "is_relevant": true,
        "confidence": 0.9,
        "reason": "Pipeline: Singtel expansive M&A (Targeting Thai data center)",
        "section": "Financial Institutions & Capital Markets",
        "subsection": "M&A",
        "rewritten_headline": "Singtel explores $500m data center sale in Thailand."
    },
    ...
}

CRITICAL FORMATTING RULES ("rewritten_headline"):
1. SENTENCE CASE: Only capitalize the FIRST letter AND Proper Nouns.
2. PERIOD: Every headline MUST end with a period.
3. NUMBERS & CURRENCY: Use "mn", "bn", "k". CURRENCY SYMBOL FIRST (e.g. "$1bn").
4. ATTRIBUTION: If the sponsor is Singapore-based but not globally famous (e.g. Equis, GLP, YTL Power), you MUST prefix or include "Singapore-based [Entity]" or "[Entity] (Singapore)".
5. DATA ENRICHMENT (CRITICAL): If the snippet contains specific data (Deal Size, Growth %, Profit Amount, Rate Value) missing from the headline, YOU MUST INJECT IT.
   - CAPTURE BOTH: If available, include BOTH the absolute amount AND the percentage change.
   - Example Bad: "Temasek portfolio value rises to S$382bn."
   - Example Good: "Temasek portfolio value rises 5.4% to S$382bn."
   - Example Bad: "Singapore exports slump."
   - Example Good: "Singapore exports slump 20.1% YoY."
6. CLEAN: Remove source attribution. Keep < 15 words.

ITEMS TO JUDGE:
"""
        for i, item in enumerate(candidates):
            prompt += f"""
ID: {item['id']}
Headline: {item['headline']}
Snippet: {item['snippet'][:200]}
Semantic Score: {item['semantic_score']:.3f} ({item['semantic_reason']})
---"""

        try:
            # Try generation with fallback logic for 404s
            try:
                response = self.client.models.generate_content(
                    model=self.generation_model,
                    contents=prompt
                )
            except Exception as e:
                # If model is not found (404), switch to fallback and retry once
                if "404" in str(e) or "Not Found" in str(e):
                    logger.warning(f"Model {self.generation_model} not found (404). Switching to {self.fallback_model} permanently.")
                    self.generation_model = self.fallback_model
                    response = self.client.models.generate_content(
                        model=self.generation_model,
                        contents=prompt
                    )
                else:
                    raise e
            
            text = self._extract_text(response).strip()
            if not text: 
                raise ValueError("Empty AI response")
                
            # Clean markdown
            if text.startswith("```json"): text = text[7:]
            if text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            
            results = json.loads(text.strip())
            return results
            
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "Resource" in err_msg or "Quota" in err_msg:
                # Detect Daily Quota vs RPM
                if "Daily" in err_msg or "RequestsPerDay" in err_msg:
                    logger.error(f"FATAL: Gemini Daily Quota Exceeded. ({err_msg})")
                    raise QuotaExceededError(err_msg)
                
                logger.warning(f"Rate limit hit (RPM), retrying... ({err_msg})")
                raise e
            logger.error(f"Batch judgment failed: {e}")
            return {}

    @retry(
        retry=retry_if_exception(should_retry_error), 
        wait=wait_random_exponential(multiplier=2, max=60),
        stop=stop_after_attempt(3)
    )
    def force_categorize(self, headline: str, snippet: str = "") -> Dict:
        """
        Force categorization of an item assuming it is relevant.
        Used when manually restoring a rejected item.
        """
        prompt = f"""You are the IFC Singapore Country Manager's guardrail agent.
You are being forced to CATEGORIZE an article that was previously rejected.
Assume it IS relevant and find the best fit category.

NEWS ITEM:
Headline: "{headline}"
Snippet: "{snippet if snippet else 'No snippet available'}"

CATEGORIES (ASSIGN ONE):
- IFC Portfolio / Pipeline Highlights
- Macro Indicators
- Policy & Political Economy
- Financial Institutions & Capital Markets
- Real-Sector Deal Flow

OUTPUT (JSON only):
{{
    "is_relevant": true,
    "confidence": 1.0,
    "reason": "Manual restoration by user.",
    "section": "Category name",
    "subsection": "Specific subsection if applicable",
    "rewritten_headline": "Clean headline with period (Sentence case)."
}}"""
        try:
            response = self.client.models.generate_content(
                model=self.generation_model,
                contents=prompt
            )
            text = self._extract_text(response).strip()
            
            # Clean markdown
            if text.startswith("```json"): text = text[7:]
            if text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            
            result = json.loads(text.strip())
            
             # Formatting Fixes
            if 'rewritten_headline' in result:
                rh = result['rewritten_headline']
                if not rh.strip().endswith('.'): rh = rh.strip() + '.'
                result['rewritten_headline'] = rh
            
            return result
        except Exception as e:
            logger.error(f"Force categorization failed: {e}")
            return {
                "is_relevant": True,
                "confidence": 1.0,
                "reason": "Manual restoration (AI Failed)",
                "section": "Uncategorized",
                "subsection": None,
                "rewritten_headline": headline
            }

    def curate_batch(self, items: List[Dict], queue=None, loop=None) -> Tuple[List[Dict], List[Dict]]:
        """
        Curate a list of items using batching with real-time feedback.
        Returns (relevant_items, rejected_items)
        """
        import asyncio
        
        final_items = []
        rejected_items = []
        batch_candidates = []
        
        self._report_progress("Pass 1: Screening keywords...", queue=queue, loop=loop)
        
        headlines_to_embed = []
        items_to_embed_indices = []
        
        for i, item in enumerate(items):
            headline = item['headline']
            kw_match, kw_reason = self._check_keywords(headline)
            
            if kw_match:
                item['semantic_score'] = 1.0
                item['semantic_reason'] = kw_reason
                item['id'] = str(len(final_items) + len(batch_candidates) + len(rejected_items))
                batch_candidates.append(item)
            else:
                headlines_to_embed.append(headline)
                items_to_embed_indices.append(i)

        # Pass 2: Batch Embeddings
        if headlines_to_embed:
            self._report_progress(f"Pass 2: Calculating relevance for {len(headlines_to_embed)} items...", queue=queue, loop=loop)
            
            try:
                embeddings = self._get_batch_embeddings(headlines_to_embed)
                self._compute_example_embeddings() 
            except Exception as e:
                self._report_progress(f"Warning: Semantic scoring failed ({e}). Falling back to AI only.", queue=queue, loop=loop)
                embeddings = [None] * len(headlines_to_embed)
            
            # Pass 3: Process Embeddings & Score
            for idx, emb in zip(items_to_embed_indices, embeddings):
                item = items[idx]
                headline = item['headline']
                
                if emb is None:
                    score = 0.0
                    reason = "Score unavailable"
                else:
                    best_relevant_sim = 0.0
                    for ex in self._relevant_embeddings:
                        sim = self._cosine_similarity(emb, ex['embedding'])
                        if sim > best_relevant_sim: best_relevant_sim = sim
                    
                    best_irrelevant_sim = 0.0
                    for ex in self._irrelevant_embeddings:
                        sim = self._cosine_similarity(emb, ex['embedding'])
                        if sim > best_irrelevant_sim: best_irrelevant_sim = sim
                    
                    score = best_relevant_sim - best_irrelevant_sim
                    reason = "Calculated relevance"

                item['semantic_score'] = score
                item['semantic_reason'] = reason
                
                # Assign ID temporarily for tracking
                item['id'] = str(len(final_items) + len(batch_candidates) + len(rejected_items))

                if score < -0.05:  # Tightened threshold to reject more borderline cases 
                    # Auto reject
                    item['relevance_reason'] = f"Low Semantic Score ({score:.2f})"
                    rejected_items.append(item)
                else:
                    batch_candidates.append(item)
        
        # Step 2: Batch AI Judgment
        self._report_progress(f"Step 3: AI Deep Analysis for {len(batch_candidates)} candidates...", queue=queue, loop=loop)
        
        BATCH_SIZE = 50
        quota_exhausted = False
        
        for i in range(0, len(batch_candidates), BATCH_SIZE):
            if quota_exhausted: break
            
            chunk = batch_candidates[i : i + BATCH_SIZE]
            batch_num = i//BATCH_SIZE + 1
            total_batches = (len(batch_candidates) + BATCH_SIZE - 1) // BATCH_SIZE
            
            self._report_progress(f"Analyzing batch {batch_num}/{total_batches} ({len(chunk)} items)...", queue=queue, loop=loop)
            
            try:
                id_map = {c['id']: c for c in chunk}
                decisions = self._ai_batch_judgment(chunk)
                
                # Report Progress update (UI progress bar)
                if queue and loop:
                    try:
                        completed = min((i + BATCH_SIZE), len(batch_candidates))
                        msg = {
                            "type": "progress", 
                            "completed": completed, 
                            "total": len(batch_candidates),
                            "currentItem": f"Batch {batch_num} complete"
                        }
                        asyncio.run_coroutine_threadsafe(queue.put(msg), loop)
                    except Exception: pass
                
                # Process results
                for cid, c_item in id_map.items():
                    if cid in decisions:
                        dec = decisions[cid]
                        # ONLY append if AI explicitly marked as relevant
                        if dec.get('is_relevant', False):
                            out_item = c_item.copy()
                            out_item.update(dec)
                            if 'reason' in dec: out_item['relevance_reason'] = dec['reason']
                            
                            # Formatting Fixes
                            if 'rewritten_headline' in dec:
                                rh = dec['rewritten_headline']
                                if not rh.strip().endswith('.'): rh = rh.strip() + '.'
                                out_item['rewritten_headline'] = rh
                                out_item['headline'] = rh 
                            
                            final_items.append(out_item)
                        else:
                            # Capture as rejected
                            out_item = c_item.copy()
                            out_item['relevance_reason'] = dec.get('reason', 'AI Rejected')
                            rejected_items.append(out_item)
                            logger.info(f"AI Rejected candidate: {c_item['headline'][:50]}... Reason: {dec.get('reason', 'None')}")
                    else:
                        # Missing decision? Treat as rejected safely
                        if c_item not in rejected_items: # avoid duplicates if logic weird
                             c_item['relevance_reason'] = "AI Skipped/Error"
                             rejected_items.append(c_item)

            except QuotaExceededError:
                 self._report_progress("⚠️ Batch AI limit reached. Switching to semi-automatic curation for remaining items.", queue=queue, loop=loop)
                 quota_exhausted = True
                 # Fallback for the rest of this batch and remaining batches
                 for c_item in chunk:
                     if c_item.get('semantic_score', 0) > 0.3:
                         c_item['is_relevant'] = True
                         c_item['relevance_reason'] = "Strong match (AI Quota Limit)"
                         c_item['section'] = "Financial Institutions & Capital Markets"
                         c_item['rewritten_headline'] = c_item['headline']
                         final_items.append(c_item)
                     else:
                         c_item['relevance_reason'] = "Weak match (AI Quota Limit)"
                         rejected_items.append(c_item)

            except Exception as e:
                self._report_progress(f"Batch {batch_num} failed: {e}. Recovering strong matches.", queue=queue, loop=loop)
                for c_item in chunk:
                    if c_item.get('semantic_score', 0) > 0.3:
                         c_item['is_relevant'] = True
                         c_item['relevance_reason'] = "Strong match (AI Error Recovery)"
                         c_item['section'] = "Financial Institutions & Capital Markets"
                         c_item['rewritten_headline'] = c_item['headline']
                         final_items.append(c_item)
                    else:
                         c_item['relevance_reason'] = "Weak (AI Error)"
                         rejected_items.append(c_item)
        
        # If quota was exhausted during any batch, handle remaining batches
        if quota_exhausted:
            start_idx = (i // BATCH_SIZE + 1) * BATCH_SIZE
            if start_idx < len(batch_candidates):
                remaining = batch_candidates[start_idx:]
                for c_item in remaining:
                    if c_item.get('semantic_score', 0) > 0.3:
                         c_item['is_relevant'] = True
                         c_item['relevance_reason'] = "Strong match (AI Quota Limit)"
                         c_item['section'] = "Financial Institutions & Capital Markets"
                         c_item['rewritten_headline'] = c_item['headline']
                         final_items.append(c_item)
                    else:
                         c_item['relevance_reason'] = "Weak match (AI Quota Limit)"
                         rejected_items.append(c_item)

        return final_items, rejected_items


    def curate(self, headline: str, snippet: str = "") -> Dict:
        """
        Legacy single-item curation. 
        Auto-wraps into batch logic or keeps original?
        Original logic is fine for single re-checks, but batch is needed for fetch.
        """
        # Layer 1: Keyword check (fast path)
        kw_match, kw_reason = self._check_keywords(headline)
        if kw_match:
            logger.debug(f"Keyword match: {headline[:50]}")
            # Still run AI for categorization
            # Still run AI for categorization AND validation (Don't auto-accept)
            # We now trust the AI to filter out domestic/irrelevant keyword matches (e.g. "Singapore crime")
            try:
                # Pass to AI Judgment with high score, but allow it to reject if HIC/Domestic
                result = self._ai_final_judgment(headline, snippet, 1.0, kw_reason)
                return result
            except Exception as e:
                logger.error(f"AI categorization failed for keyword match: {e}")
                # Only fallback to auto-accept if AI fails HARD
                return {
                    "is_relevant": True,
                    "confidence": 0.8,
                    "reason": f"{kw_reason} (AI Unavailable)",
                    "section": "Uncategorized",
                    "subsection": None,
                    "rewritten_headline": headline
                }
        
        # Layer 2: Semantic similarity
        semantic_score, semantic_reason = self._compute_semantic_score(headline)

        # Optimization: Auto-reject content that is semantically close to "Irrelevant" examples
        # Score < -0.1 means it is strictly more similar to irrelevant examples than relevant ones.
        # We use -0.1 as a safe buffer.
        if semantic_score < -0.1:
            logger.info(f"Auto-rejected by semantic score: {semantic_score:.3f} | {headline[:50]}...")
            return {
                "is_relevant": False,
                "confidence": 0.9,
                "reason": f"Auto-rejected (Semantic Score {semantic_score:.2f}): {semantic_reason}",
                "section": None,
                "subsection": None,
                "rewritten_headline": headline
            }
        
        # Layer 3: AI final judgment
        try:
            result = self._ai_final_judgment(headline, snippet, semantic_score, semantic_reason)
            return result
        except Exception as e:
            logger.error(f"AI final judgment failed after retries: {e}")
            return {
                "is_relevant": semantic_score > 0.05,
                "confidence": 0.5,
                "reason": f"AI unavailable. Semantic reason: {semantic_reason}",
                "section": "Uncategorized",
                "subsection": None,
                "rewritten_headline": headline
            }

    def add_example(self, headline: str, is_relevant: bool, reason: str = "User feedback"):
        """
        Add a new example to the knowledge base and update embeddings immediately.
        """
        if not headline:
            return

        new_example = {
            "headline": headline,
            "reason": reason
        }

        # Add to local dict
        if is_relevant:
            # Check for duplicates
            if any(ex['headline'] == headline for ex in self.examples.get('relevant_examples', [])):
                logger.info(f"Skipping duplicate relevant example: {headline}")
                return
            self.examples.setdefault('relevant_examples', []).append(new_example)
        else:
            if any(ex['headline'] == headline for ex in self.examples.get('irrelevant_examples', [])):
                logger.info(f"Skipping duplicate irrelevant example: {headline}")
                return
            self.examples.setdefault('irrelevant_examples', []).append(new_example)

        # Save to file
        try:
            if self.examples_path:
                with open(self.examples_path, 'w', encoding='utf-8') as f:
                    json.dump(self.examples, f, indent=4)
                logger.info(f"Saved new {'relevant' if is_relevant else 'irrelevant'} example: {headline}")
        except Exception as e:
            logger.error(f"Failed to save examples file: {e}")

        # Update embeddings immediately (Fast, single item)
        # We don't need to re-compute ALL, just append this one.
        # But for simplicity and safety, we can just compute this one and append to the list.
        try:
            embedding = self._get_embedding(headline)
            if embedding:
                example_obj = {
                    'headline': headline,
                    'reason': reason,
                    'embedding': embedding
                }
                
                with self._embedding_lock:
                    if is_relevant:
                        if self._relevant_embeddings is None: self._relevant_embeddings = []
                        self._relevant_embeddings.append(example_obj)
                    else:
                        if self._irrelevant_embeddings is None: self._irrelevant_embeddings = []
                        self._irrelevant_embeddings.append(example_obj)
                
                logger.info("Updated in-memory embeddings for new example.")
        except Exception as e:
            logger.error(f"Failed to update in-memory embeddings for new example: {e}")

    
    @retry(
        retry=retry_if_exception(should_retry_error), 
        wait=wait_random_exponential(multiplier=1, max=60),
        stop=stop_after_attempt(3)
    )
    def rewrite_headline(self, headline: str) -> str:
        """Rewrite a headline for clarity and style."""
        try:
            response = self.client.models.generate_content(
                model=self.generation_model,
                contents=f"""Rewrite this headline for a professional investment briefing.
Rules:
1. Sentence case (Capitalize only first letter and Proper Nouns like "Southeast Asia", "Esso").
2. NUMBERS & CURRENCY: Use "mn", "bn", "k". CURRENCY SYMBOL FIRST (e.g. "$1.5bn", "S$50mn"). NEVER "1.5bn USD".
3. SMART LINKING: Put brackets `[]` around the main subject entity (e.g. "[Singtel] acquires...").
4. Remove source suffixes. End with period. Concise (<15 words).

Original: "{headline}"

Return ONLY the rewritten headline."""
            )
            
            result = self._extract_text(response).strip()
            
            # Remove any quotes
            if result.startswith('"') and result.endswith('"'):
                result = result[1:-1]
            if result and not result.endswith('.'):
                result += '.'
            return result
            
        except Exception as e:
            if "429" in str(e) or "Resource" in str(e) or "Quota" in str(e):
                logger.warning(f"Rate limit hit in rewrite, retrying... ({e})")
                raise e
            logger.warning(f"Rewrite failed: {e}")
            return headline


# Singleton instance
_curator_instance = None

def get_curator() -> SemanticCurator:
    """Get or create the semantic curator singleton."""
    global _curator_instance
    if _curator_instance is None:
        _curator_instance = SemanticCurator()
    return _curator_instance
