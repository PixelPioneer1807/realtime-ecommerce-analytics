"""
Event simulator for generating realistic e-commerce user behavior.
Simulates users browsing, adding to cart, purchasing, and abandoning carts.
This creates the real-time event stream that mimics production traffic.
"""

import logging
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    """Represents an active user session"""
    session_id: str
    user_id: int
    start_time: datetime
    last_activity: datetime
    page_views: int = 0
    products_viewed: List[int] = field(default_factory=list)
    cart_items: List[Dict[str, Any]] = field(default_factory=list)
    device_type: str = "desktop"
    is_active: bool = True
    converted: bool = False
    
    def calculate_session_duration(self) -> int:
        """Calculate session duration in seconds"""
        return int((self.last_activity - self.start_time).total_seconds())
    
    def get_cart_value(self) -> float:
        """Calculate total cart value"""
        return sum(item['price'] * item['quantity'] for item in self.cart_items)


class EventSimulator:
    """
    Simulates realistic e-commerce user behavior patterns.
    Generates various event types with realistic probabilities.
    """
    
    # Event type probabilities
    EVENT_WEIGHTS = {
        'page_view': 40,
        'product_view': 25,
        'add_to_cart': 15,
        'remove_from_cart': 5,
        'purchase': 8,
        'search': 7
    }
    
    # Device type distribution
    DEVICE_TYPES = ['desktop', 'mobile', 'tablet']
    DEVICE_WEIGHTS = [50, 40, 10]  # Desktop, Mobile, Tablet percentages
    
    # Categories (matching Fake Store API)
    CATEGORIES = ['electronics', 'jewelery', "men's clothing", "women's clothing"]
    
    # Browser types
    BROWSERS = ['Chrome', 'Firefox', 'Safari', 'Edge', 'Opera']
    
    def __init__(
        self, 
        num_users: int = 10, 
        products: List[Dict[str, Any]] = None
    ):
        """
        Initialize event simulator.
        
        Args:
            num_users: Number of simulated users
            products: List of product dictionaries from API
        """
        self.num_users = num_users
        self.products = products or []
        self.active_sessions: Dict[str, UserSession] = {}
        self.all_events: List[Dict[str, Any]] = []
        
        logger.info(f"Event simulator initialized with {num_users} users and {len(products)} products")
    
    def create_session(self, user_id: int) -> UserSession:
        """
        Create a new user session.
        
        Args:
            user_id: User ID
            
        Returns:
            UserSession object
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        device_type = random.choices(self.DEVICE_TYPES, weights=self.DEVICE_WEIGHTS)[0]
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            device_type=device_type
        )
        
        self.active_sessions[session_id] = session
        
        # Generate session start event
        event = self._create_event('session_start', session)
        
        logger.debug(f"Created session {session_id} for user {user_id}")
        return session
    
    def _create_event(
        self, 
        event_type: str, 
        session: UserSession,
        product: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a user event.
        
        Args:
            event_type: Type of event
            session: UserSession object
            product: Optional product dictionary
            **kwargs: Additional event data
            
        Returns:
            Event dictionary
        """
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_id": session.user_id,
            "session_id": session.session_id,
            "event_type": event_type,
            "device_type": session.device_type,
            "browser": random.choice(self.BROWSERS)
        }
        
        # Add product-specific data
        if product:
            event.update({
                "product_id": product.get('id'),
                "category": product.get('category'),
                "price": product.get('price')
            })
        
        # Add any additional data
        event.update(kwargs)
        
        self.all_events.append(event)
        return event
    
    def simulate_page_view(self, session: UserSession) -> Dict[str, Any]:
        """Simulate a page view event"""
        session.page_views += 1
        session.last_activity = datetime.utcnow()
        
        pages = [
            '/home', '/products', '/about', '/cart', 
            '/checkout', '/account', '/deals'
        ]
        
        event = self._create_event(
            'page_view',
            session,
            page_url=random.choice(pages),
            referrer='/home' if session.page_views > 1 else 'google.com',
            time_on_page=random.randint(5, 120)
        )
        
        return event
    
    def simulate_product_view(self, session: UserSession) -> Dict[str, Any]:
        """Simulate a product view event"""
        if not self.products:
            return self.simulate_page_view(session)
        
        product = random.choice(self.products)
        session.products_viewed.append(product['id'])
        session.last_activity = datetime.utcnow()
        
        event = self._create_event(
            'product_view',
            session,
            product=product,
            time_on_page=random.randint(10, 180)
        )
        
        return event
    
    def simulate_add_to_cart(self, session: UserSession) -> Dict[str, Any]:
        """Simulate adding product to cart"""
        if not self.products:
            return self.simulate_page_view(session)
        
        # Higher probability to add recently viewed products
        if session.products_viewed and random.random() < 0.7:
            product_id = random.choice(session.products_viewed[-5:])
            product = next((p for p in self.products if p['id'] == product_id), random.choice(self.products))
        else:
            product = random.choice(self.products)
        
        quantity = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
        
        # Add to session cart
        cart_item = {
            'product_id': product['id'],
            'price': product['price'],
            'quantity': quantity
        }
        session.cart_items.append(cart_item)
        session.last_activity = datetime.utcnow()
        
        event = self._create_event(
            'add_to_cart',
            session,
            product=product,
            quantity=quantity
        )
        
        return event
    
    def simulate_remove_from_cart(self, session: UserSession) -> Dict[str, Any]:
        """Simulate removing product from cart"""
        if not session.cart_items:
            return self.simulate_page_view(session)
        
        # Remove random item from cart
        removed_item = session.cart_items.pop(random.randint(0, len(session.cart_items) - 1))
        session.last_activity = datetime.utcnow()
        
        # Find product details
        product = next((p for p in self.products if p['id'] == removed_item['product_id']), None)
        
        event = self._create_event(
            'remove_from_cart',
            session,
            product=product,
            quantity=removed_item['quantity']
        )
        
        return event
    
    def simulate_purchase(self, session: UserSession) -> Dict[str, Any]:
        """Simulate a purchase event"""
        if not session.cart_items:
            # Add some items first
            for _ in range(random.randint(1, 3)):
                self.simulate_add_to_cart(session)
        
        total_value = session.get_cart_value()
        session.converted = True
        session.last_activity = datetime.utcnow()
        
        event = self._create_event(
            'purchase',
            session,
            quantity=len(session.cart_items),
            cart_value=total_value,
            payment_method=random.choice(['credit_card', 'debit_card', 'paypal', 'apple_pay'])
        )
        
        # Clear cart after purchase
        session.cart_items = []
        
        return event
    
    def simulate_search(self, session: UserSession) -> Dict[str, Any]:
        """Simulate a search event"""
        search_queries = [
            'laptop', 'phone', 'headphones', 'backpack', 'watch',
            'shoes', 'jacket', 'dress', 'ring', 'necklace', 'shirt'
        ]
        
        session.last_activity = datetime.utcnow()
        
        event = self._create_event(
            'search',
            session,
            search_query=random.choice(search_queries),
            results_count=random.randint(5, 50)
        )
        
        return event
    
    def should_end_session(self, session: UserSession) -> bool:
        """
        Determine if session should end based on inactivity or conversion.
        
        Args:
            session: UserSession object
            
        Returns:
            True if session should end
        """
        session_duration = session.calculate_session_duration()
        
        # End session if:
        # 1. Converted (purchased) - 80% chance to end
        # 2. Session > 30 minutes - higher probability to end
        # 3. Random abandonment
        
        if session.converted and random.random() < 0.8:
            return True
        
        if session_duration > 1800:  # 30 minutes
            return random.random() < 0.7
        
        if session_duration > 900:  # 15 minutes
            return random.random() < 0.3
        
        return random.random() < 0.05  # 5% random abandonment
    
    def end_session(self, session: UserSession) -> Dict[str, Any]:
        """End a user session"""
        session.is_active = False
        
        event = self._create_event(
            'session_end',
            session,
            total_page_views=session.page_views,
            session_duration=session.calculate_session_duration(),
            converted=session.converted,
            cart_abandoned=len(session.cart_items) > 0 and not session.converted
        )
        
        # Remove from active sessions
        if session.session_id in self.active_sessions:
            del self.active_sessions[session.session_id]
        
        logger.debug(
            f"Session {session.session_id} ended. "
            f"Duration: {session.calculate_session_duration()}s, "
            f"Converted: {session.converted}"
        )
        
        return event
    
    def generate_event(self) -> Dict[str, Any]:
        """
        Generate a single random event.
        
        Returns:
            Event dictionary
        """
        # Create new session if needed
        if len(self.active_sessions) < self.num_users * 0.3:  # Maintain 30% concurrent sessions
            user_id = random.randint(1, self.num_users)
            session = self.create_session(user_id)
            return self._create_event('session_start', session)
        
        # Pick random active session
        session = random.choice(list(self.active_sessions.values()))
        
        # Check if session should end
        if self.should_end_session(session):
            return self.end_session(session)
        
        # Generate event based on weights
        event_type = random.choices(
            list(self.EVENT_WEIGHTS.keys()),
            weights=list(self.EVENT_WEIGHTS.values())
        )[0]
        
        # Generate appropriate event
        if event_type == 'page_view':
            return self.simulate_page_view(session)
        elif event_type == 'product_view':
            return self.simulate_product_view(session)
        elif event_type == 'add_to_cart':
            return self.simulate_add_to_cart(session)
        elif event_type == 'remove_from_cart':
            return self.simulate_remove_from_cart(session)
        elif event_type == 'purchase':
            return self.simulate_purchase(session)
        elif event_type == 'search':
            return self.simulate_search(session)
        
        return self.simulate_page_view(session)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics"""
        total_events = len(self.all_events)
        
        event_counts = {}
        for event in self.all_events:
            event_type = event['event_type']
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            'total_events': total_events,
            'active_sessions': len(self.active_sessions),
            'event_breakdown': event_counts
        }


if __name__ == "__main__":
    # Test the simulator
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("🎮 EVENT SIMULATOR TEST")
    print("="*60)
    
    # Mock products for testing
    mock_products = [
        {'id': 1, 'title': 'Product 1', 'price': 29.99, 'category': 'electronics'},
        {'id': 2, 'title': 'Product 2', 'price': 49.99, 'category': 'jewelery'},
        {'id': 3, 'title': 'Product 3', 'price': 19.99, 'category': "men's clothing"},
    ]
    
    simulator = EventSimulator(num_users=5, products=mock_products)
    
    # Generate 50 events
    print("\n📊 Generating 50 sample events...\n")
    for i in range(50):
        event = simulator.generate_event()
        print(f"{i+1}. [{event['event_type']}] User {event['user_id']} - Session {event['session_id'][:8]}...")
        time.sleep(0.1)  # Small delay for readability
    
    # Show statistics
    stats = simulator.get_statistics()
    print("\n📈 Simulation Statistics:")
    print(f"Total events: {stats['total_events']}")
    print(f"Active sessions: {stats['active_sessions']}")
    print(f"\nEvent breakdown:")
    for event_type, count in stats['event_breakdown'].items():
        print(f"  {event_type}: {count}")
    
    print("\n" + "="*60)
    print("✅ EVENT SIMULATOR TEST COMPLETED")
    print("="*60 + "\n")
