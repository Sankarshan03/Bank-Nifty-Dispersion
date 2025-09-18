import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Zerodha API Configuration
    ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
    API_KEY = os.getenv('API_KEY')
    API_SECRET = os.getenv('API_SECRET')
    API_BASE_URL = "https://api.kite.trade"
    
    # Trading Configuration
    REFERENCE_PORTFOLIO_VALUE = 60000000  # 6 crores
    MONITORING_DAYS_TO_EXPIRY = 45
    POLLING_INTERVAL = 4  # seconds
    
    # BankNifty Configuration
    BANKNIFTY_SYMBOL = "NIFTY BANK"
    
    # WebSocket Configuration
    WS_RECONNECT_ATTEMPTS = 5
    WS_RECONNECT_DELAY = 5  # seconds
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        if not cls.ACCESS_TOKEN or cls.ACCESS_TOKEN == 'your_zerodha_access_token_here':
            logger = __import__('logging').getLogger(__name__)
            logger.warning("ACCESS_TOKEN not configured - using mock data")
        if not cls.API_KEY or cls.API_KEY == 'your_zerodha_api_key_here':
            logger = __import__('logging').getLogger(__name__)
            logger.warning("API_KEY not configured - using mock data")
        return True
