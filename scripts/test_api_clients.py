"""
Test script for all API clients.
Run from project root: python scripts/test_api_clients.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from data_ingestion.api_clients.fake_store_client import FakeStoreClient
from data_ingestion.api_clients.json_placeholder_client import JSONPlaceholderClient
from data_ingestion.api_clients.weather_client import WeatherClient
from data_ingestion.api_clients.finance_client import FinanceClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_fake_store():
    """Test Fake Store API client"""
    print("\n" + "="*60)
    print("🛍️  TESTING FAKE STORE API CLIENT")
    print("="*60)
    
    client = FakeStoreClient()
    
    # Test fetching products
    products = client.get_all_products()
    print(f"\n✓ Fetched {len(products)} products")
    
    # Test categories
    categories = client.get_all_categories()
    print(f"✓ Found {len(categories)} categories: {categories}")
    
    # Test single product and enrichment
    if products:
        product = products[0]
        enriched = client.enrich_product_event(product)
        print(f"\n✓ Sample enriched event:")
        print(f"  Event ID: {enriched['event_id']}")
        print(f"  Product: {enriched['title'][:50]}...")
        print(f"  Price: ${enriched['price']}")
        print(f"  Stock: {enriched['stock_quantity']}")
    
    client.close()
    print("\n✅ Fake Store API test completed")


def test_json_placeholder():
    """Test JSONPlaceholder API client"""
    print("\n" + "="*60)
    print("👥 TESTING JSON PLACEHOLDER API CLIENT")
    print("="*60)
    
    client = JSONPlaceholderClient()
    
    # Test fetching users
    users = client.get_all_users()
    print(f"\n✓ Fetched {len(users)} users")
    
    # Test single user
    if users:
        user = users[0]
        print(f"\n✓ Sample user:")
        print(f"  ID: {user['id']}")
        print(f"  Name: {user['name']}")
        print(f"  Email: {user['email']}")
        print(f"  City: {user['address']['city']}")
        
        # Test user posts
        posts = client.get_user_posts(user['id'])
        print(f"  Posts: {len(posts)}")
    
    client.close()
    print("\n✅ JSONPlaceholder API test completed")


def test_weather():
    """Test Weather API client"""
    print("\n" + "="*60)
    print("🌤️  TESTING WEATHER API CLIENT")
    print("="*60)
    
    client = WeatherClient()
    
    cities = ["New York", "Los Angeles", "Chicago"]
    
    for city in cities:
        weather = client.get_weather_by_city(city)
        if weather:
            enriched = client.enrich_weather_event(weather)
            print(f"\n✓ {city}:")
            print(f"  Temperature: {enriched['temperature']}°C")
            print(f"  Condition: {enriched['weather_condition']}")
            print(f"  Humidity: {enriched['humidity']}%")
            print(f"  Event ID: {enriched['event_id']}")
    
    client.close()
    print("\n✅ Weather API test completed")


def test_finance():
    """Test Finance API client"""
    print("\n" + "="*60)
    print("💹 TESTING FINANCE API CLIENT")
    print("="*60)
    
    client = FinanceClient()
    
    symbols = ["SPY", "QQQ"]
    
    for symbol in symbols:
        market_data = client.get_market_data(symbol)
        if market_data:
            enriched = client.enrich_finance_event(market_data)
            print(f"\n✓ {symbol}:")
            print(f"  Current Price: ${enriched['current_price']}")
            print(f"  Change: {enriched['change_percent']:+.2f}%")
            print(f"  Volume: {enriched['volume']:,}")
            print(f"  Event ID: {enriched['event_id']}")
    
    print("\n✅ Finance API test completed")


if __name__ == "__main__":
    print("\n🚀 TESTING ALL API CLIENTS\n")
    
    test_fake_store()
    test_json_placeholder()
    test_weather()
    test_finance()
    
    print("\n" + "="*60)
    print("✅ ALL API CLIENT TESTS COMPLETED SUCCESSFULLY!")
    print("="*60 + "\n")
