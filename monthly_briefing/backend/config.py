import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in the same directory
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_DIR = BASE_DIR / "credentials"
FRONTEND_DIR = BASE_DIR / "frontend"
os.makedirs(CREDENTIALS_DIR, exist_ok=True)

# Google / Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gmail Configuration
# Keep credentials.json in project (user-provided)
GMAIL_CREDENTIALS_PATH = CREDENTIALS_DIR / "credentials.json"
# Move token.json to LOCALAPPDATA to avoid OneDrive sync/lock issues
LOCAL_DATA_ROOT = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))) / "IFC_Monthly_Briefing"
GMAIL_TOKEN_PATH = LOCAL_DATA_ROOT / "token.json"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
ALERTS_SENDER = "googlealerts-noreply@google.com"
EXECSUM_SENDER = "news@execsum.co"

# Browser Configuration (Workaround for local admin blocks)
BROWSER_EXECUTABLE_PATH = r"C:\Program Files\WindowsApps\TheBrowserCompany.Arc_1.89.1.3_x64__ttt1ap7aakyb4\Arc.exe"
if not os.path.exists(BROWSER_EXECUTABLE_PATH):
    BROWSER_EXECUTABLE_PATH = None # Fallback to default chromium

# Source Configuration
FT_BASE_URL = "https://www.ft.com/search?sort=date&q=" # Base URL, query will be appended
DSA_BASE_URL = "https://www.dealstreetasia.com/stories/singapore"

RSS_FEEDS = {
    "The Business Times": [
        "https://www.businesstimes.com.sg/rss/companies-markets",
        "https://www.businesstimes.com.sg/rss/banking-finance",
        "https://www.businesstimes.com.sg/rss/asean-business",
        "https://www.businesstimes.com.sg/rss/startups-tech",
        "https://www.businesstimes.com.sg/rss/singapore"
    ],
    "The Straits Times": [
        "https://www.straitstimes.com/news/business/rss.xml",
        "https://www.straitstimes.com/news/singapore/rss.xml"
    ],
    "Channel News Asia": [
        "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6936",  # Business
        "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=10416" # Singapore
    ],
    # "Eco-Business": [
    #     "https://www.eco-business.com/feeds/news/topic/policy-finance/",
    #     "https://www.eco-business.com/feeds/news/topic/energy/",
    #     "https://www.eco-business.com/feeds/news/topic/cities/"
    # ],
    "Fintech News SG": ["https://fintechnews.sg/feed"],
    "The Diplomat": ["https://thediplomat.com/feed/"],
    # "East Asia Forum": ["https://www.eastasiaforum.org/feed/"]
}

# Search Keywords (for FT and other search-based sources)
SEARCH_KEYWORDS = [
    "Singapore acquisition", "Singapore banking", "Singapore cross-border", 
    "Singapore expansion", "Singapore financial regulations", "Singapore infrastructure",
    "Singapore interest rate", "Singapore M&A", "Singapore manufacturing", 
    "Singapore renewable energy", "Singapore investment", "Singapore economy",
    "Singapore private equity", "Singapore venture capital"
]

# Sections Configuration
SECTIONS = [
    "IFC Portfolio / Pipeline Highlights",
    "Macro Indicators",
    "Policy & Political Economy",
    "Financial Institutions & Capital Markets",
    "Real-Sector Deal Flow"
]

REAL_SECTOR_SUBSECTIONS = {
    "Real-Sector Deal Flow": ["INR (Infrastructure)", "MAS (Manufacturing, Agribusiness, Services)"]
}
