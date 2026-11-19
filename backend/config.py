"""
Nova AI - Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Application
    APP_NAME = "Nova AI"
    VERSION = "1.0.0"
    
    # Telegram Bot Configuration
    # Create a bot via @BotFather on Telegram to get your token
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN)
    
    # MongoDB Configuration
    MONGO_URI = os.environ.get("MONGO_URI", "")
    
    # Data directory
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    
    # Diagnosis Engine
    TFIDF_WEIGHT = 0.50        # Weight for TF-IDF similarity
    FUZZY_WEIGHT = 0.30        # Weight for fuzzy string matching
    KEYWORD_WEIGHT = 0.20      # Weight for keyword extraction
    CONFIDENCE_THRESHOLD = 0.10 # Minimum confidence to include result
    MAX_RESULTS = 5            # Maximum diagnosis results to return
    
    # Inventory
    AUTO_ORDER_ENABLED = True   # Auto-order when stock below minimum
    
    # Labour rate per hour (INR)
    LABOUR_RATE_PER_HOUR = 500
    
    # Feature Flags
    ENABLE_VIDEO_GUIDES = os.environ.get("ENABLE_VIDEO_GUIDES", "true").lower() in ("true", "1", "yes")
    ENABLE_REPAIR_GUIDES = os.environ.get("ENABLE_REPAIR_GUIDES", "true").lower() in ("true", "1", "yes")
    ENABLE_APPROVAL_WORKFLOW = os.environ.get("ENABLE_APPROVAL_WORKFLOW", "true").lower() in ("true", "1", "yes")
    
    # YouTube Data API Configuration (Feature 1 — LEGACY, replaced by Visual Repair Guides)
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
    VIDEO_CACHE_TTL_DAYS = int(os.environ.get("VIDEO_CACHE_TTL_DAYS", "7"))

    # AI-Powered Visual Repair Guidance (Feature 1 replacement)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemma-4-26b-a4b-it")
    GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY", "")
    GOOGLE_SEARCH_CX = os.environ.get("GOOGLE_SEARCH_CX", "")
    
    # Company Approval Workflow (Feature 2)
    # Comma-separated reviewer Telegram chat IDs who have authority to approve/reject
    COMPANY_REVIEWER_CHAT_IDS = [
        c.strip() for c in os.environ.get("COMPANY_REVIEWER_CHAT_IDS", "").split(",") if c.strip()
    ]
    APPROVAL_EXPIRY_HOURS = int(os.environ.get("APPROVAL_EXPIRY_HOURS", "48"))
    APPROVAL_HMAC_SECRET = os.environ.get("APPROVAL_HMAC_SECRET", "automech-unbiased-diagnostics-secret-key-2024")

    # Independent AI Diagnostic Auditor (Feature 3: Anti-Overreplacement & Auto-Greenflag)
    ENABLE_AI_AUDITOR = os.environ.get("ENABLE_AI_AUDITOR", "true").lower() in ("true", "1", "yes")
    AI_AUDITOR_AUTO_GREENFLAG = os.environ.get("AI_AUDITOR_AUTO_GREENFLAG", "true").lower() in ("true", "1", "yes")
    AI_AUDITOR_STRICTNESS = os.environ.get("AI_AUDITOR_STRICTNESS", "balanced").lower() # strict, balanced, permissive
    AI_AUDITOR_AUTO_PRUNE = os.environ.get("AI_AUDITOR_AUTO_PRUNE", "true").lower() in ("true", "1", "yes")
    AI_AUDITOR_MODEL = os.environ.get("AI_AUDITOR_MODEL", "Sentinel-Neural-4.2")
    
    # Admin Panel
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "nova2024")
    ADMIN_TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")
    DEFAULT_BASE_SALARY = int(os.environ.get("DEFAULT_BASE_SALARY", "15000"))
    EMPLOYEE_OF_YEAR_BONUS = int(os.environ.get("EMPLOYEE_OF_YEAR_BONUS", "5000"))

config = Config()
