#!/usr/bin/env python3
"""
Test script to verify mock data functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.data_service import DataService
from services.calculation_service import CalculationService
import json

def test_mock_data():
    """Test the application with mock data"""
    print("🧪 Testing BankNifty Dispersion Monitor with Mock Data")
    print("=" * 60)
    
    try:
        # Initialize services
        print("\n1. Initializing Data Service...")
        data_service = DataService()
        print("✅ Data Service initialized")
        
        print("\n2. Initializing Calculation Service...")
        calc_service = CalculationService()
        print("✅ Calculation Service initialized")
        
        print("\n3. Fetching market data...")
        market_data = data_service.get_live_market_data()
        print("✅ Market data fetched")
        
        print("\n4. Calculating dispersion metrics...")
        dispersion_metrics = calc_service.calculate_dispersion_premium(market_data)
        print("✅ Dispersion metrics calculated")
        
        # Display results
        print("\n" + "=" * 60)
        print("📊 DISPERSION TRADE RESULTS")
        print("=" * 60)
        
        print(f"\n💰 Net Premium: ₹{dispersion_metrics.get('net_premium', 0):,.2f}")
        
        # BankNifty position
        bn_pos = dispersion_metrics.get('banknifty_position', {})
        print(f"\n🏦 BankNifty Position:")
        print(f"   Strike: {bn_pos.get('strike', 0)}")
        print(f"   Lots: {bn_pos.get('lots', 0)}")
        print(f"   Premium Paid: ₹{bn_pos.get('premium', 0):,.2f}")
        
        # Constituents summary
        const_pos = dispersion_metrics.get('constituents_positions', {})
        print(f"\n📈 Constituents Summary:")
        print(f"   Total Stocks: {len(const_pos.get('positions', {}))}")
        print(f"   Total Premium Received: ₹{const_pos.get('total_premium', 0):,.2f}")
        
        # Portfolio value
        portfolio = dispersion_metrics.get('portfolio_value', {})
        print(f"\n💼 Portfolio:")
        print(f"   Current Value: ₹{portfolio.get('total_value', 0):,.2f}")
        print(f"   Target Value: ₹{portfolio.get('target_value', 0):,.2f}")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! The application is working with mock data.")
        print("🔧 Configure Zerodha API credentials for live data.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mock_data()
    sys.exit(0 if success else 1)
