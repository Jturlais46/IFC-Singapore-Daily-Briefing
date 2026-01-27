# IFC Singapore Daily Briefing

> An enterprise-grade intelligence platform that continuously aggregates, filters, and synthesizes global financial news. Features autonomous multi-vector search (RSS & Google), LLM-driven semantic relevance scoring, and a self-healing 'Super Guardrail' architecture to ensure zero-downtime delivery of high-precision insights for IFC Singapore.

## Features
- **Multi-Source Ingestion**: Automatically scrapes and aggregates news from RSS feeds and Google Search.
- **AI Curation**: Uses advanced NLP to categorize, filter, and score news based on relevance to IFC directives.
- **Smart Rewriting**: Automatically rewrites titles and summaries for executive brevity and impact.
- **Self-Healing Architecture**: "Super Guardrail" system monitors server health and strictly enforces uptime.
- **Interactive UI**: Web-based dashboard for reviewing and managing the daily briefing.

## Prerequisites
- **Python 3.10+**
- **Git**
- **Google Cloud Console Project** (for OAuth2 credentials)

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Jturlais46/IFC-Singapore-Daily-Briefing.git
    cd IFC-Singapore-Daily-Briefing
    ```

2.  **Install Dependencies**:
    Navigate to the inner directory and install requirements:
    ```bash
    cd daily_briefing
    pip install -r requirements.txt
    ```

## Configuration

### Credentials
To access Google APIs (if applicable) or other protected resources, you must create a `credentials.json` file. This file is git-ignored for security.

1.  Obtain an OAuth 2.0 Client ID JSON from your Google Cloud Console.
2.  Save it as:
    `daily_briefing/credentials/credentials.json`

**Expected Structure**:
```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

## Usage

### Starting the Application
The easiest way to run the full stack (backend + frontend) is using the provided PowerShell script:

```powershell
./daily_briefing/start_app.ps1
```

Alternatively, you can run the backend server manually:

```bash
cd daily_briefing
uvicorn backend.main:app --reload
```

Access the dashboard at `http://127.0.0.1:8000`.

## Architecture
- **Backend**: FastAPI
- **AI/NLP**: Gemini / Custom Models
- **Frontend**: HTML/JS (served by FastAPI)
