# BankNifty constituents with their weights and lot sizes
# Data based on latest weightage information

BANKNIFTY_CONSTITUENTS = {
    "HDFCBANK": {
        "weight": 28.61,
        "lot_size": 550,
        "symbol": "HDFCBANK"
    },
    "ICICIBANK": {
        "weight": 26.05,
        "lot_size": 1375,
        "symbol": "ICICIBANK"
    },
    "SBIN": {
        "weight": 9.11,
        "lot_size": 1500,
        "symbol": "SBIN"
    },
    "KOTAKBANK": {
        "weight": 8.10,
        "lot_size": 400,
        "symbol": "KOTAKBANK"
    },
    "AXISBANK": {
        "weight": 7.82,
        "lot_size": 1200,
        "symbol": "AXISBANK"
    },
    "INDUSINDBK": {
        "weight": 3.37,
        "lot_size": 900,
        "symbol": "INDUSINDBK"
    },
    "FEDERALBNK": {
        "weight": 3.25,
        "lot_size": 10000,
        "symbol": "FEDERALBNK"
    },
    "IDFCFIRSTB": {
        "weight": 3.11,
        "lot_size": 10000,
        "symbol": "IDFCFIRSTB"
    },
    "BANDHANBNK": {
        "weight": 2.98,
        "lot_size": 1800,
        "symbol": "BANDHANBNK"
    },
    "AUBANK": {
        "weight": 2.79,
        "lot_size": 1200,
        "symbol": "AUBANK"
    }
}

# BankNifty index configuration
BANKNIFTY_CONFIG = {
    "symbol": "BANKNIFTY",
    "lot_size": 15,  # BankNifty lot size
    "expiry_format": "%d%b%Y"  # Format for expiry dates
}

def get_constituents():
    """Get all BankNifty constituents"""
    return BANKNIFTY_CONSTITUENTS

def get_banknifty_config():
    """Get BankNifty configuration"""
    return BANKNIFTY_CONFIG

def get_total_weight():
    """Get total weight of all constituents"""
    return sum(constituent["weight"] for constituent in BANKNIFTY_CONSTITUENTS.values())
