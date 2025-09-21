import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import time
import threading
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from kiteconnect import KiteConnect, KiteTicker

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
            self.kws = None
        else:
            try:
                self.kite = KiteConnect(api_key=api_key)
                self.kite.set_access_token(access_token)
                # Initialize WebSocket ticker
                self.kws = KiteTicker(api_key, access_token)
                logger.info("Zerodha KiteConnect and WebSocket initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize KiteConnect: {str(e)}")
                self.kite = None
                self.kws = None
        
        self.constituents = get_constituents()
        self.banknifty_config = get_banknifty_config()
        
        # Instrument tokens mapping (will be populated)
        self.instrument_tokens = {}
        
        # Data caching and threading
        self.data_cache = {}
        self.cache_timestamp = {}
        self.cache_lock = threading.Lock()
        self.cache_duration = 2  # Cache for 2 seconds
        
        # WebSocket data storage
        self.live_quotes = {}
        self.websocket_active = False
        self.websocket_thread = None
        
        # Polling mechanism
        self.polling_active = False
        self.polling_thread = None
        self.polling_interval = 4  # 4 seconds
        self.data_callbacks = []
        
        # Thread pool for concurrent API calls
        self.executor = ThreadPoolExecutor(max_workers=10)
        
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
        
    def get_live_market_data(self, use_cache: bool = True) -> Dict:
        """Get live market data for BankNifty and all constituents"""
        # Check cache first if requested
        if use_cache:
            with self.cache_lock:
                if 'market_data' in self.data_cache:
                    cache_age = time.time() - self.cache_timestamp.get('market_data', 0)
                    if cache_age < self.cache_duration:
                        return self.data_cache['market_data']
        
        try:
            market_data = {
                'banknifty': self._get_banknifty_data(),
                'constituents': self._get_constituents_data(),
                'timestamp': datetime.now().isoformat()
            }
            
            # Update cache
            if use_cache:
                with self.cache_lock:
                    self.data_cache['market_data'] = market_data
                    self.cache_timestamp['market_data'] = time.time()
            
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
        # Check WebSocket data first
        if self.websocket_active and self.live_quotes:
            instrument_token = self.instrument_tokens.get(symbol)
            if instrument_token and instrument_token in self.live_quotes:
                return self.live_quotes[instrument_token].get('last_price', 0)
        
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
        if not self.kite:
            return self._get_mock_option_data(symbol, strike, option_type)
        
        try:
            # Generate option instrument symbol (this needs proper formatting)
            option_symbol = f"{symbol}{expiry.replace(' ', '')}{strike}{option_type}"
            
            # Get instrument token for this option
            # This requires pre-loading option instruments or using a different approach
            instrument_token = self.instrument_tokens.get(option_symbol)
            
            if not instrument_token:
                return self._get_mock_option_data(symbol, strike, option_type)
            
            # Get quote
            quote = self.kite.quote([instrument_token])
            return quote[str(instrument_token)]
        except Exception as e:
            logger.error(f"Error getting option data for {symbol}: {str(e)}")
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
    
    # ========== WebSocket Implementation ==========
    
    def start_websocket(self, callback: Optional[Callable] = None):
        """Start WebSocket connection for real-time data"""
        if not self.kws:
            logger.warning("WebSocket not available, falling back to polling")
            self.start_polling(callback)
            return
        
        if self.websocket_active:
            logger.info("WebSocket already active")
            return
        
        try:
            # Get all instrument tokens we need to subscribe to
            tokens = list(self.instrument_tokens.values())
            if not tokens:
                logger.warning("No instrument tokens available for WebSocket")
                return
            
            # Setup WebSocket callbacks
            self.kws.on_ticks = self._on_websocket_ticks
            self.kws.on_connect = self._on_websocket_connect
            self.kws.on_close = self._on_websocket_close
            self.kws.on_error = self._on_websocket_error
            
            # Add callback if provided
            if callback:
                self.add_data_callback(callback)
            
            # Start WebSocket in separate thread
            self.websocket_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.websocket_thread.start()
            
            logger.info("WebSocket started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket: {str(e)}")
            # Fallback to polling
            self.start_polling(callback)
    
    def _run_websocket(self):
        """Run WebSocket in separate thread"""
        try:
            self.websocket_active = True
            self.kws.connect(threaded=False)
        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
            self.websocket_active = False
    
    def _on_websocket_connect(self, ws, response):
        """WebSocket connection callback"""
        logger.info("WebSocket connected successfully")
        # Subscribe to all instrument tokens
        tokens = list(self.instrument_tokens.values())
        if tokens:
            ws.subscribe(tokens)
            ws.set_mode(ws.MODE_LTP, tokens)  # Get Last Traded Price
    
    def _on_websocket_ticks(self, ws, ticks):
        """Handle incoming WebSocket ticks"""
        try:
            for tick in ticks:
                instrument_token = tick['instrument_token']
                self.live_quotes[instrument_token] = tick
            
            # Trigger callbacks with updated data
            self._trigger_data_callbacks()
            
        except Exception as e:
            logger.error(f"Error processing WebSocket ticks: {str(e)}")
    
    def _on_websocket_close(self, ws, code, reason):
        """WebSocket close callback"""
        logger.warning(f"WebSocket closed: {code} - {reason}")
        self.websocket_active = False
        # Attempt to reconnect or fallback to polling
        self.start_polling()
    
    def _on_websocket_error(self, ws, code, reason):
        """WebSocket error callback"""
        logger.error(f"WebSocket error: {code} - {reason}")
        self.websocket_active = False
    
    def stop_websocket(self):
        """Stop WebSocket connection"""
        if self.kws and self.websocket_active:
            try:
                self.kws.close()
                self.websocket_active = False
                logger.info("WebSocket stopped")
            except Exception as e:
                logger.error(f"Error stopping WebSocket: {str(e)}")
    
    # ========== Polling Implementation ==========
    
    def start_polling(self, callback: Optional[Callable] = None):
        """Start polling for live data updates"""
        if self.polling_active:
            logger.info("Polling already active")
            return
        
        if callback:
            self.add_data_callback(callback)
        
        self.polling_active = True
        self.polling_thread = threading.Thread(target=self._run_polling, daemon=True)
        self.polling_thread.start()
        logger.info(f"Started polling every {self.polling_interval} seconds")
    
    def _run_polling(self):
        """Run polling in separate thread"""
        while self.polling_active:
            try:
                # Fetch fresh data
                market_data = self.get_live_market_data(use_cache=False)
                
                # Update cache
                with self.cache_lock:
                    self.data_cache['market_data'] = market_data
                    self.cache_timestamp['market_data'] = time.time()
                
                # Trigger callbacks
                self._trigger_data_callbacks(market_data)
                
            except Exception as e:
                logger.error(f"Error in polling: {str(e)}")
            
            time.sleep(self.polling_interval)
    
    def stop_polling(self):
        """Stop polling"""
        self.polling_active = False
        if self.polling_thread:
            self.polling_thread.join(timeout=1)
        logger.info("Polling stopped")
    
    def set_polling_interval(self, seconds: int):
        """Set polling interval"""
        self.polling_interval = max(1, seconds)  # Minimum 1 second
        logger.info(f"Polling interval set to {self.polling_interval} seconds")
    
    # ========== Callback Management ==========
    
    def add_data_callback(self, callback: Callable):
        """Add callback for data updates"""
        if callback not in self.data_callbacks:
            self.data_callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable):
        """Remove callback"""
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
    
    def _trigger_data_callbacks(self, data=None):
        """Trigger all registered callbacks"""
        if not self.data_callbacks:
            return
        
        try:
            if data is None:
                data = self.get_live_market_data()
            
            for callback in self.data_callbacks:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in data callback: {str(e)}")
        except Exception as e:
            logger.error(f"Error triggering callbacks: {str(e)}")
    
    # ========== Enhanced Data Fetching ==========
    
    def get_live_market_data_cached(self) -> Dict:
        """Get cached market data if available and fresh"""
        with self.cache_lock:
            if 'market_data' in self.data_cache:
                cache_age = time.time() - self.cache_timestamp.get('market_data', 0)
                if cache_age < self.cache_duration:
                    return self.data_cache['market_data']
        
        # Cache miss or stale, fetch fresh data
        return self.get_live_market_data(use_cache=False)
    
    def get_concurrent_quotes(self, symbols: List[str]) -> Dict:
        """Get quotes for multiple symbols concurrently"""
        if not self.kite:
            return {symbol: self._get_mock_spot_price(symbol) for symbol in symbols}
        
        # Use WebSocket data if available
        if self.websocket_active and self.live_quotes:
            quotes = {}
            for symbol in symbols:
                token = self.instrument_tokens.get(symbol)
                if token and token in self.live_quotes:
                    quotes[symbol] = self.live_quotes[token].get('last_price', 0)
                else:
                    quotes[symbol] = self._get_mock_spot_price(symbol)
            return quotes
        
        # Concurrent API calls
        futures = []
        with self.executor:
            for symbol in symbols:
                future = self.executor.submit(self._get_spot_price, symbol)
                futures.append((symbol, future))
        
        quotes = {}
        for symbol, future in futures:
            try:
                quotes[symbol] = future.result(timeout=5)
            except Exception as e:
                logger.error(f"Error getting quote for {symbol}: {str(e)}")
                quotes[symbol] = self._get_mock_spot_price(symbol)
        
        return quotes
    
    # ========== Cleanup ==========
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_websocket()
        self.stop_polling()
        if self.executor:
            self.executor.shutdown(wait=True)
        logger.info("DataService cleanup completed")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass
