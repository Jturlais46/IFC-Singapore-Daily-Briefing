from fastapi import FastAPI, HTTPException

# Reload Test Comment
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import uvicorn
import os
import asyncio

from config import BASE_DIR, CREDENTIALS_DIR, GEMINI_API_KEY, RSS_FEEDS, FRONTEND_DIR
from sources.gmail_client import GmailClient
from sources.ft_scraper import FTScraper, USER_DATA_DIR as FT_ISOLATION_DIR
from sources.dsa_scraper import DSAScraper, DSA_USER_DATA_DIR as DSA_ISOLATION_DIR
from sources.rss_scraper import get_rss_news
from processing.parser import clean_and_deduplicate
from processing.semantic_curator import get_curator
from processing.keywords_agent import KeywordsAgent
from sources.google_scraper import GoogleSearchScraper

from export.outlook_formatter import generate_html_email

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.on_event("startup")
async def startup_event():
    print(f"\n{'='*60}")
    print(f"--- APPLICATION STARTUP (VERSION: 2.1 - LOCAL PATHS) ---")
    print(f"{'='*60}")
    print(f"Project Base: {BASE_DIR}")
    
    # Force create directories using os.makedirs (more reliable on OneDrive)
    from config import GMAIL_TOKEN_PATH, LOCAL_DATA_ROOT
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)
    os.makedirs(FT_ISOLATION_DIR, exist_ok=True)
    os.makedirs(DSA_ISOLATION_DIR, exist_ok=True)
    os.makedirs(LOCAL_DATA_ROOT, exist_ok=True)
    
    print(f"Data storage locations:")
    print(f"  Project Credentials: {CREDENTIALS_DIR}")
    print(f"  Local Data Root:    {LOCAL_DATA_ROOT}")
    print(f"  Gmail Token:        {GMAIL_TOKEN_PATH}")
    print(f"  FT Browser Data:    {FT_ISOLATION_DIR}")
    print(f"  DSA Browser Data:   {DSA_ISOLATION_DIR}")
    
    # Warm up AI curator (compute embeddings sequentially in bg)
    # Use create_task so we don't block server startup (rendering/static files)
    try:
        print("Starting Semantic Curator warm-up in background...")
        async def warmup():
            try:
                print("Warmup: Acquiring lock...")
                await asyncio.to_thread(curator._compute_example_embeddings)
                print("Warmup: Semantic Curator ready.")
            except Exception as e:
                print(f"Warmup failed: {e}")
        
        asyncio.create_task(warmup())
        
    except Exception as e:
        print(f"Warning: Curator warm-up init failed: {e}")

    if not GEMINI_API_KEY:
        print("WARNING: Gemini API Key not found in environment!")
    print(f"{'='*60}\n")


# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for the current session's news
# In a real app, use a DB. Here, simpler is better for local tool.
current_news_db: List[dict] = []
current_rejected_db: List[dict] = []

# Services
curator = get_curator()
keywords_agent = KeywordsAgent()
google_scraper = GoogleSearchScraper()

class FetchRequest(BaseModel):
    date_from: datetime
    sources: Optional[List[str]] = ["gmail", "ft", "dsa", "rss", "google"] # Default to all

class UpdateItemRequest(BaseModel):
    id: str
    headline: str

class RewriteRequest(BaseModel):
    id: str

# Helper functions to run sync code in thread pool
def _fetch_gmail(date_from):
    gmail = GmailClient()
    return gmail.fetch_news(date_from)

def _fetch_ft(date_from):
    ft = FTScraper()
    return ft.scrape(date_from)

def _fetch_dsa(date_from):
    dsa = DSAScraper()
    return dsa.scrape(date_from)

def _fetch_google(date_from):
    # 1. Devise keywords using agent
    queries = keywords_agent.generate_search_queries(date_from)
    # 2. Scrape Google Research
    return google_scraper.scrape(queries, date_from)
    
def _fetch_rss(date_from, target_sources=None):
    # Filter RSS_FEEDS based on target_sources (if provided)
    if target_sources:
        # Filter config to only include keys that are in target_sources
        # We also keep "rss" as a catch-all if someone sends it
        feed_config = {k: v for k, v in RSS_FEEDS.items() if k in target_sources or "rss" in target_sources}
    else:
        feed_config = RSS_FEEDS

    if not feed_config:
        print("No matching RSS feeds found for selection.")
        return []

    return get_rss_news(feed_config, date_from=date_from)

from fastapi.responses import StreamingResponse
import json

# ... (imports remain)

@app.post("/api/fetch")
async def fetch_news(request: FetchRequest):
    # Create a queue to communicate between the background worker and the response stream
    queue = asyncio.Queue()

    async def event_generator():
        while True:
            # excessive wait time to ensure we don't kill the connection if processing hangs briefly
            data = await queue.get()
            if data is None: # Sentinel for end of stream
                break
            # Yield JSON line
            def json_serial(obj):
                """JSON serializer for objects not serializable by default json code"""
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                raise TypeError (f"Type {type(obj)} not serializable")
                
            yield json.dumps(data, default=json_serial) + "\n"

    # Start the heavy lifting in background
    asyncio.create_task(run_fetch_pipeline(request, queue))

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

async def run_fetch_pipeline(request: FetchRequest, queue: asyncio.Queue):
    global current_news_db, current_rejected_db
    
    try:
        date_from = request.date_from
        # Normalize to start of day (00:00:00) to capture all news from that date
        date_from = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Determine actual sources list to use
        req_sources = request.sources or ["gmail", "ft", "dsa", "rss", "google"] 
        # Clean sources list (remove empty strings if any)
        sources = [s for s in req_sources if s]

        raw_items = []
        
        await queue.put({"type": "log", "message": f"Initializing search for {date_from.date()}..."})
        
        # 1. Fetch from sources
        # We can run these in parallel or sequence. Parallel is better for speed, but let's keep it simple and safe for now,
        # or use asyncio.gather for the fetches if they are thread-safe.
        
        # GMAIL
        if "gmail" in sources:
            await queue.put({"type": "log", "message": "Scanning Google Alerts..."})
            try:
                # Run in thread
                gmail_items = await asyncio.to_thread(_fetch_gmail, date_from)
                await queue.put({"type": "log", "message": f"Found {len(gmail_items)} items from Gmail."})
                raw_items.extend(gmail_items)
            except Exception as e:
                await queue.put({"type": "log", "message": f"Error scanning Gmail: {e}"})
        
        # DSA
        if "dsa" in sources:
            await queue.put({"type": "log", "message": "Scanning DealStreetAsia..."})
            try:
                dsa_items = await asyncio.to_thread(_fetch_dsa, date_from)
                await queue.put({"type": "log", "message": f"Found {len(dsa_items)} items from DSA."})
                raw_items.extend(dsa_items)
            except Exception as e:
                await queue.put({"type": "log", "message": f"Error scanning DSA: {e}"})

        # GOOGLE RESEARCH
        if "google" in sources:
            await queue.put({"type": "log", "message": "Conducting AI-driven Google Research..."})
            try:
                google_items = await asyncio.to_thread(_fetch_google, date_from)
                await queue.put({"type": "log", "message": f"Found {len(google_items)} items from Google Research."})
                raw_items.extend(google_items)
            except Exception as e:
                await queue.put({"type": "log", "message": f"Error during Google Research: {e}"})
                
        # RSS (Handles multiple feeds inside)
        rss_keys = list(RSS_FEEDS.keys()) + ["rss"]
        has_rss_request = any(s in sources for s in rss_keys)
        if has_rss_request:
            await queue.put({"type": "log", "message": "Scanning RSS Feeds..."})
            try:
                rss_items = await asyncio.to_thread(_fetch_rss, date_from, sources)
                await queue.put({"type": "log", "message": f"Found {len(rss_items)} items from RSS."})
                raw_items.extend(rss_items)
            except Exception as e:
                await queue.put({"type": "log", "message": f"Error scanning RSS: {e}"})

        # 2. Clean & Dedup
        await queue.put({"type": "log", "message": f"Cleaning and deduplicating {len(raw_items)} raw items..."})
        cleaned_items = clean_and_deduplicate(raw_items)
        await queue.put({"type": "log", "message": f"Analysis pending for {len(cleaned_items)} unique items."})

        # 3. AI Categorize
        if not cleaned_items:
            await queue.put({"type": "result", "data": []})
            await queue.put(None)
            return

        await queue.put({"type": "log", "message": "Starting AI Curation..."})
        
        # 3. AI Categorize (Using SemanticCurator in BATCH mode for Rate Limit Compliance)
        await queue.put({"type": "log", "message": f"Curating {len(cleaned_items)} items using Batch Processing..."})
        
        # We must run this in a thread because it does blocking IO (embeddings mostly)
        # But batching reduces the number of trips significantly.
        loop = asyncio.get_running_loop()
        final_items, rejected_items = await asyncio.to_thread(curator.curate_batch, cleaned_items, queue, loop)
        
        await queue.put({"type": "log", "message": f"Batch curation complete. {len(final_items)} relevant, {len(rejected_items)} rejected."})
        
        current_news_db = final_items
        current_rejected_db = rejected_items
        
        await queue.put({"type": "log", "message": "Curation complete."})
        await queue.put({"type": "result", "relevant": final_items, "rejected": rejected_items})

    except Exception as e:
        import traceback
        traceback.print_exc()
        await queue.put({"type": "error", "message": str(e)})
    finally:
        await queue.put(None) # End stream

@app.get("/api/news")
async def get_news():
    return {"relevant": current_news_db, "rejected": current_rejected_db}

@app.post("/api/news/rejected/{item_id}/restore")
async def restore_item(item_id: str):
    global current_news_db, current_rejected_db
    
    # Find item in rejected list
    item_to_restore = None
    for item in current_rejected_db:
        if item['id'] == item_id:
            item_to_restore = item
            break
    
    if not item_to_restore:
        raise HTTPException(status_code=404, detail="Item not found in rejected list")
        
    # Remove from rejected
    current_rejected_db = [i for i in current_rejected_db if i['id'] != item_id]
    
    # Force categorize (run in thread to avoid blocking)
    updated_item = await asyncio.to_thread(curator.force_categorize, item_to_restore['headline'], item_to_restore.get('snippet', ''))
    
    # Learn from this restoration (Self-reinforcing loop)
    # Run in background to not block UI response
    asyncio.create_task(asyncio.to_thread(
        curator.add_example, 
        headline=item_to_restore['headline'], 
        is_relevant=True, 
        reason="User manually restored (Feedback Loop)"
    ))
    
    # update item with new details
    item_to_restore.update(updated_item)
    
    # Add to relevant
    current_news_db.append(item_to_restore)
    
    return item_to_restore

@app.post("/api/news/{item_id}/update")
async def update_item(item_id: str, req: UpdateItemRequest):
    for item in current_news_db:
        if item['id'] == item_id:
            item['headline'] = req.headline
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/api/news/{item_id}/rewrite")
async def rewrite_item(item_id: str):
    for item in current_news_db:
        if item['id'] == item_id:
            # Re-run specialized rewrite
            # Updates the MAIN headline to the perfected version (Sentence case, No sources, Period)
            new_headline = curator.rewrite_headline(item['headline'])
            
            # Update both fields to be safe
            item['headline'] = new_headline
            item['rewritten_headline'] = new_headline 
            
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/api/news/{item_id}")
async def delete_item(item_id: str, learn: bool = False):
    global current_news_db
    
    # Find item before deleting to get headline for learning
    item_to_delete = None
    for item in current_news_db:
        if item['id'] == item_id:
            item_to_delete = item
            break
            
    if item_to_delete and learn:
         # Learn from this removal (Self-reinforcing loop)
        asyncio.create_task(asyncio.to_thread(
            curator.add_example, 
            headline=item_to_delete['headline'], 
            is_relevant=False, 
            reason="User manually removed (Feedback Loop)"
        ))

    current_news_db = [i for i in current_news_db if i['id'] != item_id]
    return {"status": "success"}

@app.get("/api/export")
async def export_news():
    # Filter only relevant items
    relevant_items = [i for i in current_news_db if i.get('is_relevant') and i.get('section') != 'Not Relevant']
    html = generate_html_email(relevant_items)
    return {"html": html}

# Serve Frontend
# Must be last
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
