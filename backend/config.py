"""
AutoMech AI - Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Application
    APP_NAME = "AutoMech AI"
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
    
    # Admin Panel
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "automech2024")
    ADMIN_TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")
    DEFAULT_BASE_SALARY = int(os.environ.get("DEFAULT_BASE_SALARY", "15000"))
    EMPLOYEE_OF_YEAR_BONUS = int(os.environ.get("EMPLOYEE_OF_YEAR_BONUS", "5000"))

config = Config()
