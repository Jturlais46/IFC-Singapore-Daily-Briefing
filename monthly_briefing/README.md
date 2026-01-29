# IFC Singapore Daily Briefing Tool

A local automation tool to capture, categorize, and curate daily news for the IFC Singapore office.

## Prerequisites

- Python 3.10+
- Chrome Browser (for Financial Times access)
- A Google Cloud Project with Gmail API enabled (for email access)
- A Google Gemini API Key (for AI categorization)

## Setup

1. **Install Dependencies**
   Open PowerShell in this directory and run:
   ```powershell
   pip install -r requirements.txt
   playwright install chromium chrome
   ```

2. **Configure Environment**
   Create a `.env` file in `daily_briefing/backend/.env` (or just in the root `daily_briefing/backend` folder) with:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Gmail Credentials**
   - Go to Google Cloud Console -> APIs & Services -> Credentials.
   - Create "OAuth 2.0 Client IDs" (Desktop App).
   - Download the JSON file.
   - Rename it to `credentials.json` and place it in:
     `daily_briefing/credentials/credentials.json`

## Usage

1. **Start the App**
   Run the startup script:
   ```powershell
   .\start_app.ps1
   ```
   Or manually:
   ```powershell
   cd daily_briefing/backend
   python -m uvicorn main:app --reload
   ```

2. **Browser Access**
   Open your browser to: `http://127.0.0.1:8000`

3. **First Run**
   - The tool will open a browser window to authenticate with Gmail.
   - It will also open a Chrome window for the Financial Times and Deal Street Asia.
   - **Important**: Log in to Financial Times in the opened browser window. The tool saves your session, so you only need to do this once.

## Features

- **Date Selection**: Choose which day's news to fetch.
- **AI Categorization**: Automatically sorts news into IFC-relevant sections.
- **Editing**: Click any headline to edit it directly.
- **Rewrite**: Use the "Rewrite" button to get an AI-generated summary.
- **Export**: Click "Publish to Outlook" to copy the formatted HTML to your clipboard.

## Troubleshooting

- **Gmail Token**: If auth fails, delete `daily_briefing/credentials/token.json` and restart to re-authenticate.
- **FT Login**: If Fetch fails to find FT articles, ensure you are logged in within the browser window that Playwright opens (or run once in `headless=False` mode if you changed scripts).
