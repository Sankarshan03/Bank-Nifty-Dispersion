# BankNifty Dispersion Trade Monitor

A real-time monitoring tool for BankNifty dispersion trades that tracks the net premium capturable by buying BankNifty ATM straddles and selling constituent stock ATM straddles.

## Features

- **Real-time Market Data**: Live monitoring of BankNifty and constituent stock prices
- **Dispersion Premium Calculation**: Automatic calculation of net premium based on normalized lot sizes
- **Portfolio Optimization**: 6 crore reference portfolio with normalized lot allocation
- **OTM Analysis**: Support for up to 3 levels of Out-of-The-Money options
- **Auto Refresh**: Configurable auto-refresh every 4 seconds
- **Export Functionality**: Export data to CSV for analysis
- **Responsive Dashboard**: Modern web interface with real-time updates

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Bank-Nifty-Dispersion
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.template .env
   ```
   Edit `.env` and add your Zerodha API credentials (API_KEY, API_SECRET, ACCESS_TOKEN)

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Access the dashboard**:
   Open http://localhost:5000 in your browser

## Configuration

### Environment Variables

- `API_KEY`: Your Zerodha API key (required)
- `API_SECRET`: Your Zerodha API secret (required)
- `ACCESS_TOKEN`: Your Zerodha access token (required)
- `REFERENCE_PORTFOLIO_VALUE`: Target portfolio value in rupees (default: 6 crores)
- `MONITORING_DAYS_TO_EXPIRY`: Start monitoring X days before expiry (default: 45)
- `POLLING_INTERVAL`: Data refresh interval in seconds (default: 4)

### BankNifty Constituents

The tool monitors the following BankNifty constituents with their respective weights (updated):

- HDFCBANK (28.61%)
- ICICIBANK (26.05%)
- SBIN (9.11%)
- KOTAKBANK (8.10%)
- AXISBANK (7.82%)
- INDUSINDBK (3.37%)
- FEDERALBNK (3.25%)
- IDFCFIRSTB (3.11%)
- BANDHANBNK (2.98%)
- AUBANK (2.79%)

## Trade Strategy

### Dispersion Trade Logic

1. **Buy BankNifty ATM Straddle**: Purchase call and put options at ATM strike
2. **Sell Constituent ATM Straddles**: Sell call and put options for each constituent stock
3. **Lot Normalization**: Normalize lot sizes based on 6 crore reference portfolio
4. **Net Premium Monitoring**: Track the net premium capturable from the trade

### Position Sizing

- Portfolio normalized to 6 crore reference value
- Lot sizes calculated based on constituent weights
- Fractional lots allowed initially, rounded to nearest integer
- Minimum 1 lot per constituent to maintain liquidity

## API Endpoints

- `GET /`: Main dashboard
- `GET /api/dispersion-data`: Current dispersion trade data
- `GET /api/otm-levels?levels=N`: OTM levels analysis (N=1,2,3)
- `GET /api/constituents`: BankNifty constituents information

## Usage

1. **Monitor Net Premium**: The main dashboard shows the current net premium capturable
2. **Set Alert Levels**: Manually determine healthy premium levels for trade entry
3. **OTM Analysis**: Use the OTM selector to analyze different strike levels
4. **Export Data**: Download current data for offline analysis
5. **Auto Refresh**: Enable/disable automatic data updates

## Technical Details

### Architecture

- **Backend**: Flask (Python)
- **Frontend**: HTML5, Bootstrap 5, Vanilla JavaScript
- **Data Source**: Zerodha Kite Connect API
- **Real-time Updates**: Polling every 4 seconds
- **Responsive Design**: Mobile-friendly interface

### Data Flow

1. Market data fetched from Zerodha Kite Connect API
2. ATM strikes calculated based on current spot prices
3. Option premiums retrieved for straddles
4. Lot sizes normalized based on reference portfolio
5. Net premium calculated and displayed
6. Frontend updates every 4 seconds

## Limitations

- Requires valid Zerodha API credentials
- Market data subject to API rate limits
- Option chain data availability depends on market hours
- Mock data used for development when API is unavailable

## Support

For issues or questions, please check the logs in the console or contact the development team.

## Disclaimer

This tool is for educational and monitoring purposes only. Trading decisions should be made based on thorough analysis and risk management. The developers are not responsible for any trading losses.
