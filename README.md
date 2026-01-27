# IFC Singapore Daily Briefing 🌏📈

> **Automated Market Intelligence & Curation Platform**
> *An AI-powered engine designed to autonomously aggregate, analyze, and synthesize critical financial developments for the IFC Singapore office.*

---

## 🎯 Initial Intent & Core Directives

### The Mission
The IFC Singapore Daily Briefing tool was conceived to solve a specific problem: **Information Overload**. 
Investment officers and executives spend too much time sifting through noise to find signals relevant to:
*   **Region**: Southeast Asia & Pacific.
*   **Sectors**: Infrastructure, Green Finance, Fintech, Manufacturing, and Agribusiness.
*   **Action**: Investment opportunities, policy shifts, and competitor movements.

### Core Directives
The system is governed by strict "Directives" that dictate what is considered "curated news":
1.  **Relevance**: Must impact IFC's strategic interests in Singapore and the region.
2.  **Timeliness**: Only the last 24-48 hours of news.
3.  **Accuracy**: Prioritize reputable sources (CNA, Reuters, specialized industry feeds).
4.  **Brevity**: Titles and summaries must be rewritten for executive consumption (bottom-line up front).

---

## 🚀 Evolution & Iterations

The project has evolved through several distinct phases of development to reach its current state of maturity.

### Phase 1: The Aggregator (Legacy)
*   **Goal**: Simple RSS feed collection.
*   **Mechanism**: Python scripts using `feedparser` to dump raw headlines.
*   **Limitation**: Too much noise, no filtering, poor formatting.

### Phase 2: Semantic Intelligence
*   **Goal**: Understand *what* the news is about.
*   **Upgrade**: Integrated **Google Gemini** (LLM) to read headlines and snippets.
*   **Feature**: Added **Relevance Scoring** (0-100) and **Categorization** (e.g., "Market Intelligence" vs. "Irrelevant").

### Phase 3: Active Research Agent
*   **Goal**: Go beyond provided feeds.
*   **Upgrade**: Implemented a **Google Search Agent** that actively searches for keywords based on IFC directives (e.g., "IFC investment Indonesia").
*   **Challenge**: Handling Google's date filtering and anti-bot measures.
*   **Solution**: Smart scraper with strict time-window parameters (`tbs=qdr:d`).

### Phase 4: The "Super Guardrail" (Current State)
*   **Goal**: Enterprise-grade reliability.
*   **Problem**: Server crashes, hanging processes, and API timeouts.
*   **Solution**: A self-healing architecture that:
    *   Monitors the backend process 24/7.
    *   Auto-kills zombie processes on Port 8000.
    *   Restarts the server automatically upon failure.
    *   Guards against "Uncategorized" data leaks.

---

## ⚡ Key Features

### 1. Multi-Vector Ingestion
- **RSS Feeds**: Monitors a curated list of high-value RSS streams.
- **Active Search**:  AI agents actively query Google News for specific topics missed by RSS.

### 2. AI-Driven Curation Pipeline
- **Categorization**: Automatically sorts articles into IFC-defined buckets.
- **Rewriting Engine**: Rephrases clickbait titles into professional, descriptive headlines.
- **Deduplication**: Identifies and merges coverage of the same event from multiple sources.

### 3. Interactive Web Dashboard
- **Review Mode**: A "Tinder-style" curation interface to quickly Accept/Reject/Edit articles.
- **Visual Feedback**: Real-time progress bars and status updates during the scraping process.
- **Newsletter Generation**: One-click export of the final curated list into a formatted HTML/Text briefing.

### 4. Stability & Security
- **Self-Healing**: The `start_app.ps1` script launches a watchdog that ensures uptime.
- **Local Execution**: Data processing happens locally, ensuring sensitive directives stay secure.

---

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.10+**
- **Git**
- **Google Cloud API Key** (for Gemini & Search)

### Quick Start
1.  **Clone the Repo**:
    ```bash
    git clone https://github.com/Jturlais46/IFC-Singapore-Daily-Briefing.git
    ```
2.  **Install Dependencies**:
    ```bash
    cd IFC-Singapore-Daily-Briefing/daily_briefing
    pip install -r requirements.txt
    ```
3.  **Setup Credentials**:
    Place your `credentials.json` (OAuth2) in `daily_briefing/credentials/`.
4.  **Launch**:
    Double-click `start_app.ps1` or run:
    ```powershell
    ./daily_briefing/start_app.ps1
    ```

---

## ❓ Troubleshooting

### "Port 8000 is already in use"
*   **Cause**: A previous instance of the server didn't close properly.
*   **Fix**: The "Super Guardrail" should handle this automatically on next launch. If not, run `daily_briefing/restart_server.bat` to force-kill the process.

### "Google Search returning old news"
*   **Cause**: Google's algorithmic search sometimes ignores the time filter.
*   **Fix**: The scraper has a strict validator that checks the date metadata in the HTML. If no date is found, it defaults to rejecting the article to be safe.

### "Authentication Error" or "403 Forbidden"
*   **Cause**: `credentials.json` is missing, expired, or has incorrect scopes.
*   **Fix**: Re-download the JSON from Google Cloud Console and ensure the "Generative Language API" is enabled for your project.

### "Stuck on 'Estimating Remaning Time'..."
*   **Cause**: The AI agent is processing a large batch of articles.
*   **Fix**: Check the terminal output. If it is moving, just wait. If it is frozen for >5 minutes, restart the server.

---
*Built with ❤️ by the IFC Singapore Tech Team*
