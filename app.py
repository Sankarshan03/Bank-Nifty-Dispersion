from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import logging

# Import our modules
from services.data_service import DataService
from services.calculation_service import CalculationService
from config.settings import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize services
data_service = DataService()
calculation_service = CalculationService()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/dispersion-data')
def get_dispersion_data():
    """Get current dispersion trade data"""
    try:
        # Get current market data
        market_data = data_service.get_live_market_data()
        
        # Calculate dispersion metrics
        dispersion_metrics = calculation_service.calculate_dispersion_premium(market_data)
        
        return jsonify({
            'status': 'success',
            'data': dispersion_metrics,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting dispersion data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/otm-levels')
def get_otm_levels():
    """Get OTM levels data"""
    try:
        levels = request.args.get('levels', 1, type=int)
        if levels > 3:
            levels = 3
            
        market_data = data_service.get_live_market_data()
        otm_data = calculation_service.calculate_otm_dispersion(market_data, levels)
        
        return jsonify({
            'status': 'success',
            'data': otm_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting OTM data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/constituents')
def get_constituents():
    """Get BankNifty constituents data"""
    try:
        constituents = data_service.get_banknifty_constituents()
        return jsonify({
            'status': 'success',
            'data': constituents
        })
    except Exception as e:
        logger.error(f"Error getting constituents: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
