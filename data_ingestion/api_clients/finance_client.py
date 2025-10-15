"""
Client for Yahoo Finance data using yfinance library.
Tracks economic indicators to correlate with spending patterns.

Economic indicators help predict:
- Market up → Luxury goods sales increase
- Market down → Budget items sales increase
- High volatility → Delayed purchases
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class FinanceClient:
    """
    Client to fetch financial market data.
    Uses yfinance library (wrapper around Yahoo Finance API - Free)
    """
    
    def __init__(self):
        """Initialize finance client"""
        try:
            import yfinance as yf
            self.yf = yf
            logger.info("yfinance library loaded successfully")
        except ImportError:
            logger.warning("yfinance not installed. Using mock data.")
            self.yf = None
    
    def get_market_data(self, symbol: str = "SPY") -> Optional[Dict[str, Any]]:
        """
        Fetch current market data for a symbol.
        
        Args:
            symbol: Stock ticker symbol (default: SPY = S&P 500 ETF)
            
        Returns:
            Market data dictionary or None if error
        """
        if not self.yf:
            logger.info("Using mock financial data")
            return self._get_mock_market_data(symbol)
        
        try:
            ticker = self.yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1d")
            
            if hist.empty:
                logger.warning(f"No data for {symbol}, using mock data")
                return self._get_mock_market_data(symbol)
            
            latest = hist.iloc[-1]
            
            market_data = {
                "symbol": symbol,
                "current_price": float(latest['Close']),
                "open_price": float(latest['Open']),
                "high_price": float(latest['High']),
                "low_price": float(latest['Low']),
                "volume": int(latest['Volume']),
                "market_cap": info.get("marketCap"),
                "change_percent": (
                    (float(latest['Close']) - float(latest['Open'])) / 
                    float(latest['Open']) * 100
                )
            }
            
            logger.info(f"Successfully fetched market data for {symbol}")
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return self._get_mock_market_data(symbol)
    
    def _get_mock_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Generate mock market data for testing.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Mock market data dictionary
        """
        import random
        
        # Simulate realistic market data
        base_prices = {
            "SPY": 450.0,    # S&P 500 ETF
            "QQQ": 380.0,    # NASDAQ ETF
            "DIA": 350.0,    # Dow Jones ETF
            "VTI": 230.0     # Total Market ETF
        }
        
        base_price = base_prices.get(symbol, 100.0)
        open_price = base_price + random.uniform(-5, 5)
        change = random.uniform(-2, 2)  # -2% to +2% daily change
        current_price = open_price * (1 + change/100)
        
        mock_data = {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "open_price": round(open_price, 2),
            "high_price": round(max(open_price, current_price) * 1.01, 2),
            "low_price": round(min(open_price, current_price) * 0.99, 2),
            "volume": random.randint(50000000, 100000000),
            "market_cap": random.randint(400000000000, 500000000000),
            "change_percent": round(change, 2)
        }
        
        return mock_data
    
    def enrich_finance_event(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw market data into standardized event schema.
        
        Args:
            market_data: Raw market data
            
        Returns:
            Enriched finance event dictionary
        """
        event = {
            "event_id": f"fin_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "symbol": market_data.get("symbol"),
            "current_price": market_data.get("current_price"),
            "open_price": market_data.get("open_price"),
            "high_price": market_data.get("high_price"),
            "low_price": market_data.get("low_price"),
            "volume": market_data.get("volume"),
            "market_cap": market_data.get("market_cap"),
            "change_percent": market_data.get("change_percent")
        }
        
        return event


if __name__ == "__main__":
    # Test the client
    logging.basicConfig(level=logging.INFO)
    
    client = FinanceClient()
    
    # Test multiple market indices
    symbols = ["SPY", "QQQ", "DIA", "VTI"]
    
    print("\n💹 FINANCIAL DATA TEST\n" + "="*50)
    
    for symbol in symbols:
        market_data = client.get_market_data(symbol)
        if market_data:
            print(f"\n📊 {symbol}:")
            print(f"   Current Price: ${market_data['current_price']}")
            print(f"   Change: {market_data['change_percent']:+.2f}%")
            print(f"   Volume: {market_data['volume']:,}")
            
            # Test enrichment
            enriched = client.enrich_finance_event(market_data)
            print(f"   Event ID: {enriched['event_id']}")
