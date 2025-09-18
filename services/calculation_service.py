import logging
from typing import Dict, List
import math

from config.settings import Config
from data.banknifty_constituents import get_constituents, get_banknifty_config

logger = logging.getLogger(__name__)

class CalculationService:
    def __init__(self):
        self.constituents = get_constituents()
        self.banknifty_config = get_banknifty_config()
        self.reference_portfolio = Config.REFERENCE_PORTFOLIO_VALUE
        
    def calculate_dispersion_premium(self, market_data: Dict) -> Dict:
        """Calculate the net dispersion premium"""
        try:
            banknifty_data = market_data.get('banknifty', {})
            constituents_data = market_data.get('constituents', {})
            
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
                    'straddle_price': banknifty_data.get('straddle_premium')
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
                # Calculate OTM strikes
                otm_data = self._calculate_otm_strikes(market_data, level)
                
                # Calculate dispersion for this OTM level
                otm_dispersion = self._calculate_otm_level_dispersion(otm_data, level)
                
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
                    'strike': data.get('atm_strike')
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
    
    def _calculate_otm_level_dispersion(self, otm_data: Dict, level: int) -> Dict:
        """Calculate dispersion for specific OTM level"""
        try:
            # This would involve fetching OTM option prices and calculating dispersion
            # For now, return a placeholder structure
            return {
                'level': level,
                'net_premium': 0,  # Placeholder
                'banknifty_position': otm_data.get('banknifty', {}),
                'constituents_positions': otm_data.get('constituents', {}),
                'note': 'OTM calculation placeholder - requires additional option price fetching'
            }
            
        except Exception as e:
            logger.error(f"Error calculating OTM level {level} dispersion: {str(e)}")
            return {}
