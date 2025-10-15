"""
Event schemas for Kafka messages.
Defines the structure of all events in the system.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class EventType(str, Enum):
    """Types of user events"""
    PAGE_VIEW = "page_view"
    PRODUCT_VIEW = "product_view"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    PURCHASE = "purchase"
    SEARCH = "search"
    FILTER = "filter"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


class ProductEvent(BaseModel):
    """Schema for product-related events from Fake Store API"""
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    product_id: int
    title: str
    price: float
    category: str
    description: Optional[str] = None
    image: Optional[str] = None
    rating_rate: Optional[float] = None
    rating_count: Optional[int] = None
    stock_quantity: int = Field(default=100, description="Simulated stock level")
    
    class Config:
        schema_extra = {
            "example": {
                "event_id": "prod_123_456",
                "timestamp": "2025-10-15T09:30:00.000Z",
                "product_id": 1,
                "title": "Fjallraven Backpack",
                "price": 109.95,
                "category": "men's clothing",
                "rating_rate": 3.9,
                "rating_count": 120,
                "stock_quantity": 45
            }
        }


class UserEvent(BaseModel):
    """Schema for user behavior events"""
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    user_id: int
    session_id: str
    event_type: EventType
    product_id: Optional[int] = None
    category: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = 1
    search_query: Optional[str] = None
    page_url: Optional[str] = None
    referrer: Optional[str] = None
    device_type: str = Field(default="desktop", description="desktop, mobile, tablet")
    browser: Optional[str] = None
    time_on_page: Optional[int] = Field(None, description="Time spent in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "event_id": "evt_789_012",
                "timestamp": "2025-10-15T09:35:00.000Z",
                "user_id": 42,
                "session_id": "sess_abc123",
                "event_type": "add_to_cart",
                "product_id": 5,
                "category": "electronics",
                "price": 299.99,
                "quantity": 1,
                "device_type": "mobile"
            }
        }


class WeatherEvent(BaseModel):
    """Schema for weather data events"""
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    location: str = Field(default="New York", description="City name")
    temperature: float = Field(..., description="Temperature in Celsius")
    feels_like: float
    humidity: int
    weather_condition: str = Field(..., description="Clear, Rain, Snow, etc.")
    weather_description: str
    wind_speed: float
    
    class Config:
        schema_extra = {
            "example": {
                "event_id": "weather_345",
                "timestamp": "2025-10-15T09:00:00.000Z",
                "location": "New York",
                "temperature": 22.5,
                "feels_like": 21.0,
                "humidity": 65,
                "weather_condition": "Clear",
                "weather_description": "clear sky",
                "wind_speed": 3.5
            }
        }


class FinanceEvent(BaseModel):
    """Schema for financial/economic indicator events"""
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    symbol: str = Field(..., description="Stock ticker or index symbol")
    current_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    market_cap: Optional[float] = None
    change_percent: Optional[float] = None
    
    class Config:
        schema_extra = {
            "example": {
                "event_id": "fin_567",
                "timestamp": "2025-10-15T09:00:00.000Z",
                "symbol": "SPY",
                "current_price": 445.50,
                "open_price": 443.20,
                "high_price": 446.00,
                "low_price": 442.80,
                "volume": 50000000,
                "change_percent": 0.52
            }
        }


class CartState(BaseModel):
    """Schema for shopping cart state"""
    user_id: int
    session_id: str
    items: list[Dict[str, Any]] = Field(default_factory=list)
    total_value: float = 0.0
    item_count: int = 0
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 42,
                "session_id": "sess_abc123",
                "items": [
                    {"product_id": 5, "quantity": 1, "price": 299.99},
                    {"product_id": 12, "quantity": 2, "price": 49.99}
                ],
                "total_value": 399.97,
                "item_count": 3,
                "last_updated": "2025-10-15T09:40:00.000Z"
            }
        }


class SessionMetrics(BaseModel):
    """Schema for session-level metrics"""
    session_id: str
    user_id: int
    start_time: str
    last_activity: str
    page_views: int = 0
    products_viewed: int = 0
    cart_additions: int = 0
    cart_removals: int = 0
    searches: int = 0
    total_time_seconds: int = 0
    is_active: bool = True
    converted: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "user_id": 42,
                "start_time": "2025-10-15T09:30:00.000Z",
                "last_activity": "2025-10-15T09:45:00.000Z",
                "page_views": 12,
                "products_viewed": 8,
                "cart_additions": 3,
                "cart_removals": 1,
                "searches": 2,
                "total_time_seconds": 900,
                "is_active": True,
                "converted": False
            }
        }
