import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
from kiteconnect import KiteConnect

from config.settings import Config
from data.banknifty_constituents import get_constituents, get_banknifty_config

logger = logging.getLogger(__name__)

class DataService:
    def __init__(self):
        self.config = Config()
        self.config.validate_config()
        
        # Initialize Kite Connect with cleaned tokens
        api_key = Config.API_KEY.strip() if Config.API_KEY else None
        access_token = Config.ACCESS_TOKEN.strip() if Config.ACCESS_TOKEN else None
        
        if not api_key or not access_token:
            logger.warning("Zerodha API credentials not configured, using mock data")
            self.kite = None
        else:
            try:
                self.kite = KiteConnect(api_key=api_key)
                self.kite.set_access_token(access_token)
                logger.info("Zerodha KiteConnect initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize KiteConnect: {str(e)}")
                self.kite = None
        
        self.constituents = get_constituents()
        self.banknifty_config = get_banknifty_config()
        
        # Instrument tokens mapping (will be populated)
        self.instrument_tokens = {}
        self._load_instruments()
    
    def _load_instruments(self):
        """Load instrument tokens for faster API calls"""
        if not self.kite:
            logger.info("KiteConnect not available, using mock instrument tokens")
            self._load_mock_instruments()
            return
            
        try:
            # Get all instruments
            instruments = self.kite.instruments()
            
            # Create mapping for quick lookup
            for instrument in instruments:
                symbol = instrument['tradingsymbol']
                if instrument['exchange'] == 'NSE':
                    if symbol in self.constituents or symbol == 'NIFTY BANK':
                        self.instrument_tokens[symbol] = instrument['instrument_token']
                        
            logger.info(f"Loaded {len(self.instrument_tokens)} instrument tokens")
            
        except Exception as e:
            logger.error(f"Error loading instruments: {str(e)}")
            # Use mock data if instruments can't be loaded
            self._load_mock_instruments()
    
    def _load_mock_instruments(self):
        """Load mock instrument tokens for development"""
        mock_tokens = {
            'NIFTY BANK': 260105,
            'HDFCBANK': 341249,
            'ICICIBANK': 1270529,
            'SBIN': 779521,
            'KOTAKBANK': 492033,
            'AXISBANK': 54273,
            'INDUSINDBK': 1346049,
            'FEDERALBNK': 1023553,
            'IDFCFIRSTB': 7712001,
            'BANDHANBNK': 2263297,
            'AUBANK': 4708097
        }
        self.instrument_tokens = mock_tokens
        
    def get_live_market_data(self) -> Dict:
        """Get live market data for BankNifty and all constituents"""
        try:
            market_data = {
                'banknifty': self._get_banknifty_data(),
                'constituents': self._get_constituents_data(),
                'timestamp': datetime.now().isoformat()
            }
            return market_data
        except Exception as e:
            logger.error(f"Error fetching live market data: {str(e)}")
            raise
    
    def _get_banknifty_data(self) -> Dict:
        """Get BankNifty options data"""
        try:
            # Get current BankNifty spot price
            spot_price = self._get_spot_price("NIFTY BANK")
            
            # Calculate ATM strike
            atm_strike = self._calculate_atm_strike(spot_price)
            
            # Get expiry date (next monthly expiry)
            expiry_date = self._get_next_monthly_expiry()
            
            # Get options data for ATM straddle
            call_data = self._get_option_data("BANKNIFTY", atm_strike, "CE", expiry_date)
            put_data = self._get_option_data("BANKNIFTY", atm_strike, "PE", expiry_date)
            
            return {
                'spot_price': spot_price,
                'atm_strike': atm_strike,
                'expiry_date': expiry_date,
                'call': call_data,
                'put': put_data,
                'straddle_premium': (call_data.get('ltp', 0) + put_data.get('ltp', 0)) if call_data and put_data else 0
            }
        except Exception as e:
            logger.error(f"Error getting BankNifty data: {str(e)}")
            return {}
    
    def _get_constituents_data(self) -> Dict:
        """Get options data for all BankNifty constituents"""
        constituents_data = {}
        
        for symbol, info in self.constituents.items():
            try:
                # Get spot price
                spot_price = self._get_spot_price(symbol)
                
                # Calculate ATM strike
                atm_strike = self._calculate_atm_strike(spot_price)
                
                # Get expiry date (next monthly expiry)
                expiry_date = self._get_next_monthly_expiry()
                
                # Get options data
                call_data = self._get_option_data(symbol, atm_strike, "CE", expiry_date)
                put_data = self._get_option_data(symbol, atm_strike, "PE", expiry_date)
                
                constituents_data[symbol] = {
                    'spot_price': spot_price,
                    'atm_strike': atm_strike,
                    'expiry_date': expiry_date,
                    'call': call_data,
                    'put': put_data,
                    'straddle_premium': (call_data.get('ltp', 0) + put_data.get('ltp', 0)) if call_data and put_data else 0,
                    'weight': info['weight'],
                    'lot_size': info['lot_size']
                }
            except Exception as e:
                logger.error(f"Error getting data for {symbol}: {str(e)}")
                constituents_data[symbol] = {
                    'error': str(e),
                    'weight': info['weight'],
                    'lot_size': info['lot_size']
                }
        
        return constituents_data
    
    def _get_spot_price(self, symbol: str) -> float:
        """Get current spot price for an instrument"""
        # If KiteConnect is not available, use mock data
        if not self.kite:
            return self._get_mock_spot_price(symbol)
            
        try:
            # Get instrument token
            instrument_token = self.instrument_tokens.get(symbol)
            if not instrument_token:
                logger.warning(f"Instrument token not found for {symbol}, using mock data")
                return self._get_mock_spot_price(symbol)
            
            # Get quote from Kite API
            quote = self.kite.quote([instrument_token])
            
            if quote and str(instrument_token) in quote:
                return quote[str(instrument_token)]['last_price']
            else:
                logger.warning(f"No quote data for {symbol}, using mock data")
                return self._get_mock_spot_price(symbol)
                
        except Exception as e:
            logger.error(f"Error getting spot price for {symbol}: {str(e)}")
            # Return mock data for development
            return self._get_mock_spot_price(symbol)
    
    def _get_option_data(self, symbol: str, strike: float, option_type: str, expiry: str) -> Dict:
        """Get option data for specific strike and expiry"""
        # For now, using mock data for options as real-time option chain data 
        # requires complex instrument token mapping and subscription
        # This can be enhanced later with proper option chain integration
        return self._get_mock_option_data(symbol, strike, option_type)
    
    
    def _calculate_atm_strike(self, spot_price: float) -> float:
        """Calculate ATM strike price"""
        # Round to nearest 100 for BankNifty, nearest 50 for stocks
        if spot_price > 10000:  # Likely BankNifty
            return round(spot_price / 100) * 100
        else:  # Individual stocks
            return round(spot_price / 50) * 50
    
    def _get_next_monthly_expiry(self) -> str:
        """Get next monthly expiry date"""
        # This is a simplified calculation
        # In practice, you'd need to get actual expiry dates from the exchange
        today = datetime.now()
        
        # Find last Thursday of current month
        year = today.year
        month = today.month
        
        # If we're past the monthly expiry, move to next month
        last_thursday = self._get_last_thursday(year, month)
        if today > last_thursday:
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
            last_thursday = self._get_last_thursday(year, month)
        
        return last_thursday.strftime("%d%b%Y").upper()
    
    def _get_last_thursday(self, year: int, month: int) -> datetime:
        """Get last Thursday of the month"""
        # Find last day of month
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        
        last_day = next_month - timedelta(days=1)
        
        # Find last Thursday
        days_back = (last_day.weekday() - 3) % 7
        if days_back == 0 and last_day.weekday() != 3:
            days_back = 7
        
        last_thursday = last_day - timedelta(days=days_back)
        return last_thursday
    
    def _get_mock_spot_price(self, symbol: str) -> float:
        """Mock spot prices for development"""
        mock_prices = {
            "NIFTY BANK": 45000.0,
            "HDFCBANK": 1650.0,
            "ICICIBANK": 950.0,
            "AXISBANK": 1100.0,
            "KOTAKBANK": 1800.0,
            "SBIN": 600.0,
            "INDUSINDBK": 1400.0,
            "AUBANK": 700.0,
            "BANDHANBNK": 250.0,
            "FEDERALBNK": 150.0,
            "IDFCFIRSTB": 80.0
        }
        return mock_prices.get(symbol, 100.0)
    
    def _get_mock_option_data(self, symbol: str, strike: float, option_type: str) -> Dict:
        """Mock option data for development"""
        # Simple mock based on moneyness
        base_premium = strike * 0.02  # 2% of strike as base premium
        return {
            'ltp': base_premium,
            'bid': base_premium * 0.98,
            'ask': base_premium * 1.02,
            'volume': 1000,
            'oi': 5000
        }
    
    def get_banknifty_constituents(self) -> Dict:
        """Get BankNifty constituents information"""
        return self.constituents
