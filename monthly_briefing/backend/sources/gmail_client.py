import os
import os.path
import base64
import webbrowser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import (
    GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, SCOPES,
    ALERTS_SENDER, EXECSUM_SENDER, CREDENTIALS_DIR
)

class GmailClient:
    def __init__(self):
        self.creds = None
        self._authenticate()
        self.service = build('gmail', 'v1', credentials=self.creds)

    def _authenticate(self):
        """Authenticates with Gmail API, saving tokens locally."""
        # Ensure credentials directory exists
        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        
        print(f"[Gmail] Checking for existing token at {GMAIL_TOKEN_PATH}")
        
        if os.path.exists(GMAIL_TOKEN_PATH):
            print("[Gmail] Found existing token, loading...")
            self.creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_PATH), SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("[Gmail] Token expired, refreshing...")
                self.creds.refresh(Request())
            else:
                print("[Gmail] No valid token, starting OAuth flow...")
                if not os.path.exists(GMAIL_CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f"credentials.json not found at {GMAIL_CREDENTIALS_PATH}. "
                        "Please download it from Google Cloud Console and place it there."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(GMAIL_CREDENTIALS_PATH), SCOPES)
                
                # Manually handle the OAuth flow to ensure browser opens
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f"\n{'='*60}")
                print("GMAIL AUTHORIZATION REQUIRED")
                print(f"{'='*60}")
                print(f"\nOpening browser for authorization...")
                print(f"If browser doesn't open, please visit this URL manually:\n{auth_url}\n")
                
                # Try to open browser
                webbrowser.open(auth_url)
                
                # Run the local server to catch the callback
                self.creds = flow.run_local_server(port=0)
                print("[Gmail] Authorization successful!")
            
            # Save the credentials for the next run
            print(f"[Gmail] Saving token to {GMAIL_TOKEN_PATH}")
            os.makedirs(os.path.dirname(str(GMAIL_TOKEN_PATH)), exist_ok=True)
            with open(str(GMAIL_TOKEN_PATH), 'w') as token:
                token.write(self.creds.to_json())
            print("[Gmail] Token saved successfully!")

    def list_messages(self, sender: str, date_start: datetime, date_end: datetime) -> List[Dict]:
        """List messages from a sender within a date range."""
        date_str_after = date_start.strftime("%Y/%m/%d")
        
        # Gmail 'before' is exclusive
        date_str_before = date_end.strftime("%Y/%m/%d")
        
        query = f"from:{sender} after:{date_str_after} before:{date_str_before}"
        print(f"[Gmail] Querying: '{query}'")
        
        try:
            results = self.service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])
            print(f"[Gmail] Found {len(messages)} messages from {sender}")
            return messages
        except Exception as e:
            print(f"[Gmail] Error fetching from {sender}: {e}")
            return []

    def get_message_content(self, msg_id: str) -> Optional[Dict]:
        """Get the content of a specific message."""
        try:
            message = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            payload = message['payload']
            headers = payload.get('headers')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), "")
            
            # Get body
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/html':
                        data = part['body'].get('data')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode()
                            break
            elif payload.get('body', {}).get('data'):
                body = base64.urlsafe_b64decode(payload['body']['data']).decode()
            
            return {
                "id": msg_id,
                "subject": subject,
                "date": date_str,
                "body": body
            }
        except Exception as e:
            print(f"[Gmail] Error getting message {msg_id}: {e}")
            return None

    def parse_google_alert(self, html_content: str) -> List[Dict]:
        """Parses a Google Alert HTML email."""
        soup = BeautifulSoup(html_content, 'html.parser')
        items = []
        
        for link in soup.find_all('a'):
            href = link.get('href')
            if not href or 'google.com/url' not in href:
                continue
                
            try:
                actual_url = href.split('url=')[1].split('&')[0]
                headline = link.get_text().strip()
                
                if headline and actual_url and len(headline) > 10:
                    items.append({
                        "headline": headline,
                        "url": actual_url,
                        "snippet": "",
                        "source": "Google Alerts"
                    })
            except IndexError:
                continue
                
        return items

    def parse_execsum(self, html_content: str) -> List[Dict]:
        """Parses an ExecSum email."""
        soup = BeautifulSoup(html_content, 'html.parser')
        items = []
        
        for link in soup.find_all('a'):
            headline = link.get_text().strip()
            href = link.get('href')
            
            if href and len(headline) > 10:
                if "unsubscribe" in headline.lower() or "view in browser" in headline.lower():
                    continue
                    
                items.append({
                    "headline": headline,
                    "url": href,
                    "snippet": "",
                    "source": "ExecSum"
                })
        return items

    def fetch_news(self, date_start: datetime, date_end: datetime) -> List[Dict]:
        """Main entry point to fetch and parse emails for a specific date range."""
        all_news = []
        
        # Fetch Google Alerts
        print(f"[Gmail] Fetching Google Alerts for {date_start.date()} to {date_end.date()}...")
        msgs = self.list_messages(ALERTS_SENDER, date_start, date_end)
        for msg in msgs:
            content = self.get_message_content(msg['id'])
            if content and content['body']:
                news_items = self.parse_google_alert(content['body'])
                all_news.extend(news_items)
                print(f"[Gmail] Extracted {len(news_items)} items from Alerts email")

        # Fetch ExecSum
        print(f"[Gmail] Fetching ExecSum...")
        msgs = self.list_messages(EXECSUM_SENDER, date_start, date_end)
        for msg in msgs:
            content = self.get_message_content(msg['id'])
            if content and content['body']:
                news_items = self.parse_execsum(content['body'])
                all_news.extend(news_items)
                print(f"[Gmail] Extracted {len(news_items)} items from ExecSum email")
                
        print(f"[Gmail] Total items fetched: {len(all_news)}")
        return all_news
