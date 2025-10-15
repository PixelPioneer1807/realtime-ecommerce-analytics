"""
Client for OpenWeatherMap API to fetch weather data.
Free API Key: Sign up at https://openweathermap.org/api

Weather data is used to correlate purchasing patterns with weather conditions.
Example: Rain increases umbrella sales, cold weather boosts heater sales.
"""

import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from config.config import config

logger = logging.getLogger(__name__)


class WeatherClient:
    """Client to interact with OpenWeatherMap API"""
    
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize weather client.
        
        Args:
            api_key: OpenWeatherMap API key (optional, uses config if not provided)
        """
        self.api_key = api_key or config.OPENWEATHER_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RealTimeEcommerceAnalytics/1.0'
        })
    
    def get_weather_by_city(self, city: str = "New York") -> Optional[Dict[str, Any]]:
        """
        Fetch current weather data for a city.
        
        Args:
            city: City name (default: New York)
            
        Returns:
            Weather data dictionary or None if error
        """
        if not self.api_key:
            logger.warning("No API key provided. Using mock data.")
            return self._get_mock_weather(city)
        
        try:
            params = {
                "q": city,
                "appid": self.api_key,
                "units": "metric"  # Use Celsius
            }
            
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            weather_data = response.json()
            
            logger.info(f"Successfully fetched weather for {city}")
            return weather_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather for {city}: {e}")
            logger.info("Falling back to mock data")
            return self._get_mock_weather(city)
    
    def _get_mock_weather(self, city: str) -> Dict[str, Any]:
        """
        Generate mock weather data for testing without API key.
        
        Args:
            city: City name
            
        Returns:
            Mock weather data dictionary
        """
        import random
        
        conditions = ["Clear", "Clouds", "Rain", "Snow", "Mist"]
        descriptions = {
            "Clear": "clear sky",
            "Clouds": "few clouds",
            "Rain": "light rain",
            "Snow": "light snow",
            "Mist": "mist"
        }
        
        condition = random.choice(conditions)
        temp = random.uniform(0, 35)  # 0-35°C
        
        mock_data = {
            "coord": {"lon": -74.0060, "lat": 40.7128},
            "weather": [
                {
                    "id": 800,
                    "main": condition,
                    "description": descriptions[condition],
                    "icon": "01d"
                }
            ],
            "main": {
                "temp": round(temp, 2),
                "feels_like": round(temp - random.uniform(-2, 2), 2),
                "humidity": random.randint(40, 90),
                "pressure": random.randint(1000, 1020)
            },
            "wind": {
                "speed": round(random.uniform(0, 15), 2)
            },
            "name": city
        }
        
        return mock_data
    
    def enrich_weather_event(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw weather data into standardized event schema.
        
        Args:
            weather_data: Raw weather data from API
            
        Returns:
            Enriched weather event dictionary
        """
        weather_info = weather_data.get("weather", [{}])[0]
        main_data = weather_data.get("main", {})
        wind_data = weather_data.get("wind", {})
        
        event = {
            "event_id": f"weather_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.utcnow().isoformat() + "Z", # Fixed deprecation warning
            "location": weather_data.get("name", "Unknown"),
            "temperature": main_data.get("temp"),
            "feels_like": main_data.get("feels_like"),
            "humidity": main_data.get("humidity"),
            "weather_condition": weather_info.get("main"),
            "weather_description": weather_info.get("description"),
            "wind_speed": wind_data.get("speed")
        }
        
        return event
    
    def close(self):
        """Close the session"""
        self.session.close()


if __name__ == "__main__":
    # Test the client
    logging.basicConfig(level=logging.INFO)
    
    client = WeatherClient()
    
    # Test multiple cities (simulating different regions)
    cities = ["New York", "Los Angeles", "Chicago", "Miami"]
    
    print("\n🌤️  WEATHER DATA TEST\n" + "="*50)
    
    for city in cities:
        weather = client.get_weather_by_city(city)
        if weather:
            print(f"\n📍 {city}:")
            print(f"   Temperature: {weather['main']['temp']}°C")
            print(f"   Condition: {weather['weather'][0]['main']}")
            print(f"   Humidity: {weather['main']['humidity']}%")
            
            # Test enrichment
            enriched = client.enrich_weather_event(weather)
            print(f"   Event ID: {enriched['event_id']}")
    
    client.close()
