from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import logging
import atexit

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

# Start live data updates (WebSocket preferred, polling fallback)
def data_update_callback(market_data):
    """Callback for live data updates"""
    logger.info(f"Received live data update at {market_data.get('timestamp', 'unknown')}")

# Start WebSocket or polling for live updates
data_service.start_websocket(data_update_callback)

# Ensure cleanup on app shutdown
def cleanup_services():
    """Cleanup services on shutdown"""
    logger.info("Shutting down services...")
    data_service.cleanup()

atexit.register(cleanup_services)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/dispersion-data')
def get_dispersion_data():
    """Get current dispersion trade data"""
    try:
        # Get current market data (use cached if available)
        market_data = data_service.get_live_market_data_cached()
        
        # Calculate dispersion metrics
        dispersion_metrics = calculation_service.calculate_dispersion_premium(market_data)
        
        return jsonify({
            'status': 'success',
            'data': dispersion_metrics,
            'timestamp': datetime.now().isoformat(),
            'data_source': 'websocket' if data_service.websocket_active else 'polling' if data_service.polling_active else 'api'
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
            
        market_data = data_service.get_live_market_data_cached()
        otm_data = calculation_service.calculate_otm_dispersion(market_data, levels)
        
        return jsonify({
            'status': 'success',
            'data': otm_data,
            'timestamp': datetime.now().isoformat(),
            'data_source': 'websocket' if data_service.websocket_active else 'polling' if data_service.polling_active else 'api'
        })
    except Exception as e:
        logger.error(f"Error getting OTM data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/data-source')
def get_data_source():
    """Get current data source information"""
    return jsonify({
        'websocket_active': data_service.websocket_active,
        'polling_active': data_service.polling_active,
        'polling_interval': data_service.polling_interval,
        'cache_duration': data_service.cache_duration,
        'data_source': 'websocket' if data_service.websocket_active else 'polling' if data_service.polling_active else 'api'
    })

@app.route('/api/control/polling', methods=['POST'])
def control_polling():
    """Control polling settings"""
    try:
        data = request.get_json()
        action = data.get('action')
        
        if action == 'start':
            interval = data.get('interval', 4)
            data_service.set_polling_interval(interval)
            data_service.start_polling()
            return jsonify({'status': 'success', 'message': 'Polling started'})
        elif action == 'stop':
            data_service.stop_polling()
            return jsonify({'status': 'success', 'message': 'Polling stopped'})
        elif action == 'set_interval':
            interval = data.get('interval', 4)
            data_service.set_polling_interval(interval)
            return jsonify({'status': 'success', 'message': f'Polling interval set to {interval} seconds'})
        else:
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
            
    except Exception as e:
        logger.error(f"Error controlling polling: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/control/websocket', methods=['POST'])
def control_websocket():
    """Control WebSocket connection"""
    try:
        data = request.get_json()
        action = data.get('action')
        
        if action == 'start':
            data_service.start_websocket()
            return jsonify({'status': 'success', 'message': 'WebSocket started'})
        elif action == 'stop':
            data_service.stop_websocket()
            return jsonify({'status': 'success', 'message': 'WebSocket stopped'})
        else:
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
            
    except Exception as e:
        logger.error(f"Error controlling WebSocket: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        cleanup_services()
