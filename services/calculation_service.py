import logging
from typing import Dict, List
import math

from config.settings import Config
from data.banknifty_constituents import get_constituents, get_banknifty_config
from .data_service import DataService
logger = logging.getLogger(__name__)

class CalculationService:
    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self.constituents = get_constituents()
        self.banknifty_config = get_banknifty_config()
        self.reference_portfolio = Config.REFERENCE_PORTFOLIO_VALUE
        
    def calculate_dispersion_premium(self, market_data: Dict) -> Dict:
        """Calculate the net dispersion premium"""
        try:
            banknifty_data = market_data.get('banknifty', {})
            constituents_data = market_data.get('constituents', {})
            
            logger.info(f"Calculating dispersion with BankNifty spot: {banknifty_data.get('spot_price', 'N/A')}")
            logger.info(f"Constituents count: {len(constituents_data)}")
            
            if not banknifty_data or not constituents_data:
                raise ValueError("Incomplete market data")
            
            # Calculate normalized lot sizes
            normalized_lots = self._calculate_normalized_lots(constituents_data, banknifty_data)
            
            # Calculate BankNifty position (Buy straddle)
            banknifty_premium = self._calculate_banknifty_position(banknifty_data, normalized_lots['banknifty'])
            
            # Calculate constituents positions (Sell straddles)
            constituents_premium = self._calculate_constituents_positions(constituents_data, normalized_lots)
            
            # Calculate net premium
            net_premium = banknifty_premium - constituents_premium['total_premium']
            
            return {
                'net_premium': net_premium,
                'banknifty_position': {
                    'premium': banknifty_premium,
                    'lots': normalized_lots['banknifty'],
                    'strike': banknifty_data.get('atm_strike'),
                    'straddle_price': banknifty_data.get('straddle_premium'),
                    'spot_price': banknifty_data.get('spot_price')
                },
                'constituents_positions': constituents_premium,
                'normalized_lots': normalized_lots,
                'portfolio_value': self._calculate_portfolio_value(constituents_data, normalized_lots),
                'timestamp': market_data.get('timestamp')
            }
            
        except Exception as e:
            logger.error(f"Error calculating dispersion premium: {str(e)}")
            raise
    
    def calculate_otm_dispersion(self, market_data: Dict, levels: int = 1) -> Dict:
        """Calculate dispersion for OTM levels"""
        try:
            results = {}
            
            for level in range(1, levels + 1):
                # Calculate OTM strikes and get option data
                otm_market_data = self._get_otm_market_data(market_data, level)
                
                # Calculate dispersion for this OTM level using the same logic as ATM
                otm_dispersion = self._calculate_otm_level_dispersion(otm_market_data, level)
                
                results[f'otm_level_{level}'] = otm_dispersion
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating OTM dispersion: {str(e)}")
            raise
    
    def _calculate_normalized_lots(self, constituents_data: Dict, banknifty_data: Dict) -> Dict:
        """Calculate normalized lot sizes based on reference portfolio"""
        try:
            # Calculate total portfolio value at current prices
            total_value = 0
            constituent_values = {}
            
            for symbol, data in constituents_data.items():
                if 'error' in data:
                    continue
                    
                spot_price = data.get('spot_price', 0)
                lot_size = data.get('lot_size', 0)
                weight = data.get('weight', 0)
                
                # Calculate value for one lot
                lot_value = spot_price * lot_size
                constituent_values[symbol] = {
                    'lot_value': lot_value,
                    'weight': weight,
                    'lot_size': lot_size
                }
                total_value += lot_value * (weight / 100)
            
            # Calculate scaling factor to reach reference portfolio
            if total_value > 0:
                scaling_factor = self.reference_portfolio / total_value
            else:
                scaling_factor = 1
            
            # Calculate normalized lots for each constituent
            normalized_lots = {}
            
            for symbol, values in constituent_values.items():
                weight_ratio = values['weight'] / 100
                target_value = self.reference_portfolio * weight_ratio
                lots_needed = target_value / values['lot_value']
                
                # Round to nearest integer (can be fractional initially)
                normalized_lots[symbol] = max(1, round(lots_needed))
            
            # Calculate BankNifty lots
            banknifty_spot = banknifty_data.get('spot_price', 0)
            banknifty_lot_size = self.banknifty_config['lot_size']
            
            if banknifty_spot > 0:
                banknifty_lot_value = banknifty_spot * banknifty_lot_size
                banknifty_lots = max(1, round(self.reference_portfolio / banknifty_lot_value))
            else:
                banknifty_lots = 1
            
            normalized_lots['banknifty'] = banknifty_lots
            
            return normalized_lots
            
        except Exception as e:
            logger.error(f"Error calculating normalized lots: {str(e)}")
            return {}
    
    def _calculate_banknifty_position(self, banknifty_data: Dict, lots: int) -> float:
        """Calculate BankNifty position premium (Buy straddle)"""
        try:
            straddle_premium = banknifty_data.get('straddle_premium', 0)
            lot_size = self.banknifty_config['lot_size']
            
            # Premium paid for buying straddle (positive outflow)
            total_premium = straddle_premium * lot_size * lots
            
            return total_premium
            
        except Exception as e:
            logger.error(f"Error calculating BankNifty position: {str(e)}")
            return 0
    
    def _calculate_constituents_positions(self, constituents_data: Dict, normalized_lots: Dict) -> Dict:
        """Calculate constituents positions premium (Sell straddles)"""
        try:
            positions = {}
            total_premium = 0
            
            for symbol, data in constituents_data.items():
                if 'error' in data or symbol not in normalized_lots:
                    continue
                
                straddle_premium = data.get('straddle_premium', 0)
                lot_size = data.get('lot_size', 0)
                lots = normalized_lots.get(symbol, 0)
                weight = data.get('weight', 0)
                
                # Premium received for selling straddle (positive inflow)
                position_premium = straddle_premium * lot_size * lots
                
                positions[symbol] = {
                    'premium': position_premium,
                    'lots': lots,
                    'straddle_price': straddle_premium,
                    'lot_size': lot_size,
                    'weight': weight,
                    'strike': data.get('atm_strike'),
                    'spot_price': data.get('spot_price', 0)
                }
                
                total_premium += position_premium
            
            return {
                'positions': positions,
                'total_premium': total_premium
            }
            
        except Exception as e:
            logger.error(f"Error calculating constituents positions: {str(e)}")
            return {'positions': {}, 'total_premium': 0}
    
    def _calculate_portfolio_value(self, constituents_data: Dict, normalized_lots: Dict) -> Dict:
        """Calculate total portfolio value"""
        try:
            total_value = 0
            breakdown = {}
            
            for symbol, data in constituents_data.items():
                if 'error' in data or symbol not in normalized_lots:
                    continue
                
                spot_price = data.get('spot_price', 0)
                lot_size = data.get('lot_size', 0)
                lots = normalized_lots.get(symbol, 0)
                
                position_value = spot_price * lot_size * lots
                breakdown[symbol] = position_value
                total_value += position_value
            
            return {
                'total_value': total_value,
                'breakdown': breakdown,
                'target_value': self.reference_portfolio
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio value: {str(e)}")
            return {'total_value': 0, 'breakdown': {}, 'target_value': self.reference_portfolio}
    
    def _calculate_atm_strike(self, spot_price: float) -> float:
        """Calculate ATM strike price"""
        # Round to nearest 100 for BankNifty, nearest 50 for stocks
        if spot_price > 10000:  # Likely BankNifty
            return round(spot_price / 100) * 100
        else:  # Individual stocks
            return round(spot_price / 50) * 50
    
    def _calculate_otm_strikes(self, market_data: Dict, level: int) -> Dict:
        """Calculate OTM strikes for given level"""
        try:
            otm_data = {
                'banknifty': {},
                'constituents': {}
            }
            
            # BankNifty OTM
            banknifty_data = market_data.get('banknifty', {})
            spot_price = banknifty_data.get('spot_price', 0)
            
            if spot_price > 0:
                strike_interval = 100  # BankNifty strike interval
                otm_call_strike = spot_price + (level * strike_interval)
                otm_put_strike = spot_price - (level * strike_interval)
                
                otm_data['banknifty'] = {
                    'call_strike': round(otm_call_strike / strike_interval) * strike_interval,
                    'put_strike': round(otm_put_strike / strike_interval) * strike_interval,
                    'spot_price': spot_price
                }
            
            # Constituents OTM
            constituents_data = market_data.get('constituents', {})
            for symbol, data in constituents_data.items():
                if 'error' in data:
                    continue
                
                spot_price = data.get('spot_price', 0)
                if spot_price > 0:
                    strike_interval = 50  # Individual stock strike interval
                    otm_call_strike = spot_price + (level * strike_interval)
                    otm_put_strike = spot_price - (level * strike_interval)
                    
                    otm_data['constituents'][symbol] = {
                        'call_strike': round(otm_call_strike / strike_interval) * strike_interval,
                        'put_strike': round(otm_put_strike / strike_interval) * strike_interval,
                        'spot_price': spot_price,
                        'weight': data.get('weight'),
                        'lot_size': data.get('lot_size')
                    }
            
            return otm_data
            
        except Exception as e:
            logger.error(f"Error calculating OTM strikes: {str(e)}")
            return {}
    
    def _get_otm_market_data(self, market_data: Dict, level: int) -> Dict:
        """Get market data with OTM strikes and option prices"""
        try:
            otm_market_data = {
                'banknifty': {},
                'constituents': {},
                'timestamp': market_data.get('timestamp')
            }
            
            # BankNifty OTM data
            banknifty_data = market_data.get('banknifty', {})
            spot_price = banknifty_data.get('spot_price', 0)
            
            if spot_price > 0:
                strike_interval = 100  # BankNifty strike interval
                
                # Calculate OTM call and put strikes
                atm_strike = self._calculate_atm_strike(spot_price)
                otm_call_strike = atm_strike + (level * strike_interval)
                otm_put_strike = atm_strike - (level * strike_interval)
                
                # Get OTM option data (using real api response data, with proper structure)
                call_data = self._get_otm_option_data('BANKNIFTY', otm_call_strike, 'CE', level)
                put_data = self._get_otm_option_data('BANKNIFTY', otm_put_strike, 'PE', level)
                
                otm_market_data['banknifty'] = {
                    'spot_price': spot_price,
                    'atm_strike': atm_strike,
                    'call_strike': otm_call_strike,
                    'put_strike': otm_put_strike,
                    'expiry_date': banknifty_data.get('expiry_date'),
                    'call': call_data,
                    'put': put_data,
                    'straddle_premium': (call_data.get('ltp', 0) + put_data.get('ltp', 0))
                }
            
            # Constituents OTM data
            constituents_data = market_data.get('constituents', {})
            for symbol, data in constituents_data.items():
                if 'error' in data:
                    continue
                
                spot_price = data.get('spot_price', 0)
                if spot_price > 0:
                    strike_interval = 50  # Individual stock strike interval
                    
                    # Calculate OTM strikes
                    atm_strike = self._calculate_atm_strike(spot_price)
                    otm_call_strike = atm_strike + (level * strike_interval)
                    otm_put_strike = atm_strike - (level * strike_interval)
                    
                    # Get OTM option data
                    call_data = self._get_otm_option_data(symbol, otm_call_strike, 'CE', level)
                    put_data = self._get_otm_option_data(symbol, otm_put_strike, 'PE', level)
                    
                    otm_market_data['constituents'][symbol] = {
                        'spot_price': spot_price,
                        'atm_strike': atm_strike,
                        'call_strike': otm_call_strike,
                        'put_strike': otm_put_strike,
                        'expiry_date': data.get('expiry_date'),
                        'call': call_data,
                        'put': put_data,
                        'straddle_premium': (call_data.get('ltp', 0) + put_data.get('ltp', 0)),
                        'weight': data.get('weight'),
                        'lot_size': data.get('lot_size')
                    }
            
            return otm_market_data
            
        except Exception as e:
            logger.error(f"Error getting OTM market data for level {level}: {str(e)}")
            return {}
    
    def _get_otm_option_data(self, symbol: str, strike: float, option_type: str, level: int) -> Dict:
        """Get OTM option data using real API through data_service"""
        if not self.data_service:
            logger.warning("No data_service available, using mock data for OTM options")
            return self._get_mock_otm_option_data(symbol, strike, option_type, level)
        
        try:
            # Get expiry date (same logic as data_service)
            expiry = self.data_service._get_next_monthly_expiry()
            
            # Use data_service._get_option_data for real API call
            option_data = self.data_service._get_option_data(symbol, strike, option_type, expiry)
            
            logger.info(f"Got real OTM option data for {symbol} {strike} {option_type}: LTP={option_data.get('ltp', 'N/A')}")
            return option_data
            
        except Exception as e:
            logger.error(f"Error getting real OTM option data for {symbol}: {str(e)}")
            # Fallback to mock data
            return self._get_mock_otm_option_data(symbol, strike, option_type, level)
    
    def _get_mock_otm_option_data(self, symbol: str, strike: float, option_type: str, level: int) -> Dict:
        """Mock OTM option data as fallback"""
        import random
        
        # Base premium calculation for OTM options (lower than ATM)
        base_premium = strike * 0.01 * (1 / level)  # Decreasing premium for higher OTM levels
        
        # Add some variation
        variation = random.uniform(-0.15, 0.15)  # ±15% variation
        ltp = max(0.05, base_premium * (1 + variation))  # Minimum 0.05 premium
        
        return {
            'ltp': round(ltp, 2),
            'bid': round(ltp * 0.95, 2),
            'ask': round(ltp * 1.05, 2),
            'volume': random.randint(100, 1000),
            'oi': random.randint(1000, 5000)
        }
    
    def _calculate_otm_level_dispersion(self, otm_market_data: Dict, level: int) -> Dict:
        """Calculate dispersion for specific OTM level using the same logic as ATM"""
        try:
            # Use the same calculation logic as ATM dispersion
            banknifty_data = otm_market_data.get('banknifty', {})
            constituents_data = otm_market_data.get('constituents', {})
            
            if not banknifty_data or not constituents_data:
                return {
                    'level': level,
                    'net_premium': 0,
                    'banknifty_position': {},
                    'constituents_positions': {},
                    'note': f'Insufficient data for OTM level {level}'
                }
            
            # Calculate normalized lot sizes (same as ATM)
            normalized_lots = self._calculate_normalized_lots(constituents_data, banknifty_data)
            
            # Calculate BankNifty OTM position (Buy strangle/straddle)
            banknifty_premium = self._calculate_banknifty_position(banknifty_data, normalized_lots['banknifty'])
            
            # Calculate constituents OTM positions (Sell strangles/straddles)
            constituents_premium = self._calculate_constituents_positions(constituents_data, normalized_lots)
            
            # Calculate net premium
            net_premium = banknifty_premium - constituents_premium['total_premium']
            
            return {
                'level': level,
                'net_premium': net_premium,
                'banknifty_position': {
                    'premium': banknifty_premium,
                    'lots': normalized_lots['banknifty'],
                    'call_strike': banknifty_data.get('call_strike'),
                    'put_strike': banknifty_data.get('put_strike'),
                    'straddle_price': banknifty_data.get('straddle_premium'),
                    'spot_price': banknifty_data.get('spot_price')
                },
                'constituents_positions': constituents_premium,
                'normalized_lots': normalized_lots,
                'portfolio_value': self._calculate_portfolio_value(constituents_data, normalized_lots),
                'note': f'OTM Level {level} - Call: {banknifty_data.get("call_strike", 0)}, Put: {banknifty_data.get("put_strike", 0)}'
            }
            
        except Exception as e:
            logger.error(f"Error calculating OTM level {level} dispersion: {str(e)}")
            return {
                'level': level,
                'net_premium': 0,
                'banknifty_position': {},
                'constituents_positions': {},
                'note': f'Error calculating OTM level {level}: {str(e)}'
            }
