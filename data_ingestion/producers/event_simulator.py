"""
Event simulator for generating realistic e-commerce user behavior.
Simulates users browsing, adding to cart, purchasing, and abandoning carts.
This creates the real-time event stream that mimics production traffic.

PORTFOLIO FEATURES:
- User personas with different behavior patterns
- Realistic event sequences (can't buy without adding to cart)
- Cart abandonment detection (15-20 min inactivity)
- Variable timing between events
- Abandonment reasons tracking
"""

import logging
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class UserPersona(Enum):
    """Different types of user behavior patterns"""
    WINDOW_SHOPPER = "window_shopper"      # Browse heavily, rarely buy (60%)
    INTENT_BUYER = "intent_buyer"          # Direct path to purchase (25%)
    CART_ABANDONER = "cart_abandoner"      # Add to cart, then abandon (15%)


class SessionState(Enum):
    """User session progression states"""
    BROWSING = "browsing"
    INTERESTED = "interested"              # Viewed multiple products
    CART_ACTIVE = "cart_active"            # Has items in cart
    CHECKOUT_INITIATED = "checkout_initiated"
    PURCHASED = "purchased"
    ABANDONED = "abandoned"


@dataclass
class UserSession:
    """Represents an active user session with state tracking"""
    session_id: str
    user_id: int
    start_time: datetime
    last_activity: datetime
    persona: UserPersona
    state: SessionState = SessionState.BROWSING
    page_views: int = 0
    products_viewed: List[int] = field(default_factory=list)
    cart_items: List[Dict[str, Any]] = field(default_factory=list)
    device_type: str = "desktop"
    is_active: bool = True
    converted: bool = False
    
    # Cart abandonment tracking
    cart_created_at: Optional[datetime] = None
    abandonment_reason: Optional[str] = None
    
    def calculate_session_duration(self) -> int:
        """Calculate session duration in seconds"""
        return int((self.last_activity - self.start_time).total_seconds())
    
    def get_cart_value(self) -> float:
        """Calculate total cart value"""
        return sum(item['price'] * item['quantity'] for item in self.cart_items)
    
    def time_since_last_activity(self) -> int:
        """Calculate seconds since last activity"""
        return int((datetime.utcnow() - self.last_activity).total_seconds())
    
    def has_abandoned_cart(self, inactivity_threshold: int = 900) -> bool:
        """
        Check if cart should be considered abandoned (15 min default).
        
        Args:
            inactivity_threshold: Seconds of inactivity to consider abandoned
            
        Returns:
            True if cart is abandoned
        """
        return (
            len(self.cart_items) > 0 
            and not self.converted
            and self.time_since_last_activity() >= inactivity_threshold
        )


class EventSimulator:
    """
    Simulates realistic e-commerce user behavior patterns.
    Generates various event types with realistic probabilities and sequences.
    """
    
    # Persona distribution (how users are divided)
    PERSONA_WEIGHTS = {
        UserPersona.WINDOW_SHOPPER: 60,
        UserPersona.INTENT_BUYER: 25,
        UserPersona.CART_ABANDONER: 15
    }
    
    # Device type distribution
    DEVICE_TYPES = ['desktop', 'mobile', 'tablet']
    DEVICE_WEIGHTS = [50, 40, 10]
    
    # Categories (matching Fake Store API)
    CATEGORIES = ['electronics', 'jewelery', "men's clothing", "women's clothing"]
    
    # Browser types
    BROWSERS = ['Chrome', 'Firefox', 'Safari', 'Edge', 'Opera']
    
    # Cart abandonment reasons
    ABANDONMENT_REASONS = [
        'high_price',
        'unexpected_shipping_cost',
        'comparison_shopping',
        'found_better_deal',
        'just_browsing',
        'payment_concerns',
        'slow_checkout',
        'needed_more_time'
    ]
    
    # Time delays between actions (seconds) - min, max
    ACTION_DELAYS = {
        'page_view': (2, 15),
        'product_view': (10, 45),
        'add_to_cart': (5, 20),
        'checkout': (15, 60),
        'purchase': (30, 120)
    }
    
    # Cart abandonment threshold (15-20 minutes in seconds)
    CART_ABANDONMENT_THRESHOLD = random.randint(900, 1200)  # 15-20 min
    
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
        
        # Track last event time per session for realistic timing
        self.last_event_time: Dict[str, datetime] = {}
        
        logger.info(
            f"Event simulator initialized with {num_users} users and "
            f"{len(products)} products"
        )
    
    def _select_persona(self) -> UserPersona:
        """Select user persona based on distribution"""
        personas = list(self.PERSONA_WEIGHTS.keys())
        weights = list(self.PERSONA_WEIGHTS.values())
        return random.choices(personas, weights=weights)[0]
    
    def create_session(self, user_id: int) -> UserSession:
        """
        Create a new user session with persona.
        
        Args:
            user_id: User ID
            
        Returns:
            UserSession object
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        device_type = random.choices(self.DEVICE_TYPES, weights=self.DEVICE_WEIGHTS)[0]
        persona = self._select_persona()
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            device_type=device_type,
            persona=persona
        )
        
        self.active_sessions[session_id] = session
        self.last_event_time[session_id] = datetime.utcnow()
        
        # Generate session start event
        event = self._create_event('session_start', session, persona=persona.value)
        
        logger.debug(f"Created session {session_id} for user {user_id} ({persona.value})")
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
            "browser": random.choice(self.BROWSERS),
            "session_state": session.state.value
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
    
    def _should_wait_for_action(self, session_id: str, action_type: str) -> bool:
        """
        Check if we should wait before allowing next action (realistic timing).
        
        Args:
            session_id: Session ID
            action_type: Type of action to perform
            
        Returns:
            True if should wait
        """
        if session_id not in self.last_event_time:
            return False
        
        last_time = self.last_event_time[session_id]
        min_delay, max_delay = self.ACTION_DELAYS.get(action_type, (1, 5))
        
        # Random delay within range
        required_delay = random.uniform(min_delay, max_delay)
        elapsed = (datetime.utcnow() - last_time).total_seconds()
        
        return elapsed < required_delay
    
    def _update_session_state(self, session: UserSession, new_state: SessionState):
        """Update session state with logging"""
        old_state = session.state
        session.state = new_state
        logger.debug(f"Session {session.session_id} state: {old_state.value} → {new_state.value}")
    
    def simulate_page_view(self, session: UserSession) -> Dict[str, Any]:
        """Simulate a page view event"""
        session.page_views += 1
        session.last_activity = datetime.utcnow()
        self.last_event_time[session.session_id] = datetime.utcnow()
        
        # Different pages based on state
        if session.state == SessionState.CART_ACTIVE:
            pages = ['/cart', '/products', '/checkout']
        elif session.state == SessionState.INTERESTED:
            pages = ['/products', '/category', '/deals']
        else:
            pages = ['/home', '/products', '/about', '/deals', '/categories']
        
        event = self._create_event(
            'page_view',
            session,
            page_url=random.choice(pages),
            referrer='/home' if session.page_views > 1 else 'google.com',
            time_on_page=random.randint(5, 120)
        )
        
        # State transition: After 3+ page views, become interested
        if session.page_views >= 3 and session.state == SessionState.BROWSING:
            self._update_session_state(session, SessionState.INTERESTED)
        
        return event
    
    def simulate_product_view(self, session: UserSession) -> Dict[str, Any]:
        """Simulate a product view event"""
        if not self.products:
            return self.simulate_page_view(session)
        
        # Persona-based product selection
        if session.persona == UserPersona.INTENT_BUYER:
            # Intent buyers focus on specific categories
            if random.random() < 0.7:
                category = random.choice(self.CATEGORIES)
                category_products = [p for p in self.products if p.get('category') == category]
                product = random.choice(category_products) if category_products else random.choice(self.products)
            else:
                product = random.choice(self.products)
        else:
            # Window shoppers and abandoners browse randomly
            product = random.choice(self.products)
        
        session.products_viewed.append(product['id'])
        session.last_activity = datetime.utcnow()
        self.last_event_time[session.session_id] = datetime.utcnow()
        
        event = self._create_event(
            'product_view',
            session,
            product=product,
            time_on_page=random.randint(10, 180)
        )
        
        # State transition: Viewed 2+ products → interested
        if len(session.products_viewed) >= 2 and session.state == SessionState.BROWSING:
            self._update_session_state(session, SessionState.INTERESTED)
        
        return event
    
    def simulate_add_to_cart(self, session: UserSession) -> Dict[str, Any]:
        """Simulate adding product to cart - MUST have viewed products first"""
        if not self.products:
            return self.simulate_page_view(session)
        
        # REALISTIC CONSTRAINT: Must have viewed products before adding to cart
        if len(session.products_viewed) == 0:
            logger.debug(f"Session {session.session_id} tried to add to cart without viewing - showing product instead")
            return self.simulate_product_view(session)
        
        # Higher probability to add recently viewed products (70%)
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
        self.last_event_time[session.session_id] = datetime.utcnow()
        
        # Track when cart was created
        if session.cart_created_at is None:
            session.cart_created_at = datetime.utcnow()
        
        event = self._create_event(
            'add_to_cart',
            session,
            product=product,
            quantity=quantity,
            cart_value=session.get_cart_value()
        )
        
        # State transition: Has items in cart
        self._update_session_state(session, SessionState.CART_ACTIVE)
        
        return event
    
    def simulate_remove_from_cart(self, session: UserSession) -> Dict[str, Any]:
        """Simulate removing product from cart"""
        if not session.cart_items:
            return self.simulate_page_view(session)
        
        # Remove random item from cart
        removed_item = session.cart_items.pop(random.randint(0, len(session.cart_items) - 1))
        session.last_activity = datetime.utcnow()
        self.last_event_time[session.session_id] = datetime.utcnow()
        
        # Find product details
        product = next((p for p in self.products if p['id'] == removed_item['product_id']), None)
        
        event = self._create_event(
            'remove_from_cart',
            session,
            product=product,
            quantity=removed_item['quantity'],
            cart_value=session.get_cart_value()
        )
        
        # State transition: If cart now empty, back to interested
        if len(session.cart_items) == 0:
            self._update_session_state(session, SessionState.INTERESTED)
        
        return event
    
    def simulate_checkout_initiated(self, session: UserSession) -> Dict[str, Any]:
        """Simulate checkout initiation - MUST have items in cart"""
        # REALISTIC CONSTRAINT: Can't checkout empty cart
        if not session.cart_items:
            logger.debug(f"Session {session.session_id} tried to checkout empty cart - adding product first")
            return self.simulate_add_to_cart(session)
        
        session.last_activity = datetime.utcnow()
        self.last_event_time[session.session_id] = datetime.utcnow()
        
        event = self._create_event(
            'checkout_initiated',
            session,
            cart_value=session.get_cart_value(),
            items_count=len(session.cart_items)
        )
        
        # State transition
        self._update_session_state(session, SessionState.CHECKOUT_INITIATED)
        
        return event
    
    def simulate_purchase(self, session: UserSession) -> Dict[str, Any]:
        """Simulate a purchase event - MUST have gone through checkout"""
        # REALISTIC CONSTRAINT: Must have items in cart
        if not session.cart_items:
            logger.debug(f"Session {session.session_id} tried to purchase empty cart - adding items first")
            for _ in range(random.randint(1, 3)):
                self.simulate_add_to_cart(session)
        
        total_value = session.get_cart_value()
        session.converted = True
        session.last_activity = datetime.utcnow()
        self.last_event_time[session.session_id] = datetime.utcnow()
        
        event = self._create_event(
            'purchase',
            session,
            quantity=len(session.cart_items),
            cart_value=total_value,
            payment_method=random.choice(['credit_card', 'debit_card', 'paypal', 'apple_pay'])
        )
        
        # State transition
        self._update_session_state(session, SessionState.PURCHASED)
        
        # Clear cart after purchase
        session.cart_items = []
        
        return event
    
    def simulate_cart_abandoned(self, session: UserSession) -> Dict[str, Any]:
        """
        Simulate cart abandonment event.
        Called when cart has been inactive for threshold period.
        """
        if not session.cart_items:
            return None
        
        # Select abandonment reason based on cart value and persona
        cart_value = session.get_cart_value()
        
        if cart_value > 100:
            # High value carts - price-related abandonment
            reason = random.choice(['high_price', 'unexpected_shipping_cost', 'payment_concerns'])
        elif session.persona == UserPersona.CART_ABANDONER:
            reason = random.choice(['just_browsing', 'comparison_shopping', 'found_better_deal'])
        else:
            reason = random.choice(self.ABANDONMENT_REASONS)
        
        session.abandonment_reason = reason
        session.last_activity = datetime.utcnow()
        
        event = self._create_event(
            'cart_abandoned',
            session,
            cart_value=cart_value,
            items_count=len(session.cart_items),
            abandonment_reason=reason,
            time_in_cart_seconds=int((datetime.utcnow() - session.cart_created_at).total_seconds()) if session.cart_created_at else 0,
            device_type=session.device_type
        )
        
        # State transition
        self._update_session_state(session, SessionState.ABANDONED)
        
        logger.info(
            f"Cart abandoned: session {session.session_id}, "
            f"value ${cart_value:.2f}, reason: {reason}"
        )
        
        return event
    
    def simulate_search(self, session: UserSession) -> Dict[str, Any]:
        """Simulate a search event"""
        search_queries = [
            'laptop', 'phone', 'headphones', 'backpack', 'watch',
            'shoes', 'jacket', 'dress', 'ring', 'necklace', 'shirt'
        ]
        
        session.last_activity = datetime.utcnow()
        self.last_event_time[session.session_id] = datetime.utcnow()
        
        event = self._create_event(
            'search',
            session,
            search_query=random.choice(search_queries),
            results_count=random.randint(5, 50)
        )
        
        return event
    
    def should_end_session(self, session: UserSession) -> bool:
        """
        Determine if session should end based on persona and state.
        
        Args:
            session: UserSession object
            
        Returns:
            True if session should end
        """
        session_duration = session.calculate_session_duration()
        
        # End session if purchased (80% chance for intent buyers, 95% for others)
        if session.converted:
            if session.persona == UserPersona.INTENT_BUYER:
                return random.random() < 0.8
            return random.random() < 0.95
        
        # End session if cart abandoned
        if session.state == SessionState.ABANDONED:
            return random.random() < 0.9
        
        # Persona-based session duration preferences
        if session.persona == UserPersona.WINDOW_SHOPPER:
            # Window shoppers stay longer
            if session_duration > 1800:  # 30 minutes
                return random.random() < 0.5
        elif session.persona == UserPersona.INTENT_BUYER:
            # Intent buyers are quick
            if session_duration > 600:  # 10 minutes
                return random.random() < 0.6
        else:  # CART_ABANDONER
            # Cart abandoners leave after adding items
            if session.state == SessionState.CART_ACTIVE and session_duration > 300:
                return random.random() < 0.4
        
        # General timeouts
        if session_duration > 2400:  # 40 minutes
            return random.random() < 0.8
        
        return random.random() < 0.03  # 3% random session end
    
    def end_session(self, session: UserSession) -> Dict[str, Any]:
        """End a user session"""
        session.is_active = False
        
        event = self._create_event(
            'session_end',
            session,
            total_page_views=session.page_views,
            session_duration=session.calculate_session_duration(),
            converted=session.converted,
            cart_abandoned=len(session.cart_items) > 0 and not session.converted,
            abandonment_reason=session.abandonment_reason,
            persona=session.persona.value
        )
        
        # Remove from active sessions
        if session.session_id in self.active_sessions:
            del self.active_sessions[session.session_id]
        if session.session_id in self.last_event_time:
            del self.last_event_time[session.session_id]
        
        logger.debug(
            f"Session {session.session_id} ended. "
            f"Duration: {session.calculate_session_duration()}s, "
            f"Converted: {session.converted}, "
            f"Persona: {session.persona.value}"
        )
        
        return event
    
    def check_abandoned_carts(self) -> List[Dict[str, Any]]:
        """
        Check all active sessions for abandoned carts.
        Generate abandonment events for carts inactive beyond threshold.
        
        Returns:
            List of cart_abandoned events
        """
        abandoned_events = []
        
        for session_id, session in list(self.active_sessions.items()):
            # Check if cart should be marked as abandoned
            if session.has_abandoned_cart(self.CART_ABANDONMENT_THRESHOLD):
                event = self.simulate_cart_abandoned(session)
                if event:
                    abandoned_events.append(event)
        
        return abandoned_events
    
    def generate_event(self) -> Dict[str, Any]:
        """
        Generate a single realistic event following user journey logic.
        
        Returns:
            Event dictionary
        """
        # Check for abandoned carts first (every event generation cycle)
        abandoned_events = self.check_abandoned_carts()
        if abandoned_events and random.random() < 0.3:  # 30% chance to return abandoned event
            return abandoned_events[0]
        
        # Create new session if needed (maintain 20-40% concurrent sessions)
        target_sessions = int(self.num_users * random.uniform(0.2, 0.4))
        if len(self.active_sessions) < target_sessions:
            user_id = random.randint(1, self.num_users)
            session = self.create_session(user_id)
            return self._create_event('session_start', session, persona=session.persona.value)
        
        # Pick random active session
        if not self.active_sessions:
            user_id = random.randint(1, self.num_users)
            session = self.create_session(user_id)
            return self._create_event('session_start', session, persona=session.persona.value)
        
        session = random.choice(list(self.active_sessions.values()))
        
        # Check if session should end
        if self.should_end_session(session):
            return self.end_session(session)
        
        # Generate event based on PERSONA and CURRENT STATE (realistic journey)
        next_action = self._determine_next_action(session)
        
        # Execute action
        if next_action == 'page_view':
            return self.simulate_page_view(session)
        elif next_action == 'product_view':
            return self.simulate_product_view(session)
        elif next_action == 'add_to_cart':
            return self.simulate_add_to_cart(session)
        elif next_action == 'remove_from_cart':
            return self.simulate_remove_from_cart(session)
        elif next_action == 'checkout':
            return self.simulate_checkout_initiated(session)
        elif next_action == 'purchase':
            return self.simulate_purchase(session)
        elif next_action == 'search':
            return self.simulate_search(session)
        
        return self.simulate_page_view(session)
    
    def _determine_next_action(self, session: UserSession) -> str:
        """
        Determine next action based on session state and persona.
        This creates realistic user journeys.
        
        Args:
            session: UserSession object
            
        Returns:
            Action string
        """
        state = session.state
        persona = session.persona
        
        # BROWSING state
        if state == SessionState.BROWSING:
            weights = {
                'page_view': 40,
                'product_view': 35,
                'search': 25
            }
        
        # INTERESTED state (viewed multiple products)
        elif state == SessionState.INTERESTED:
            if persona == UserPersona.INTENT_BUYER:
                # Intent buyers quickly add to cart
                weights = {
                    'product_view': 30,
                    'add_to_cart': 50,
                    'page_view': 15,
                    'search': 5
                }
            elif persona == UserPersona.CART_ABANDONER:
                # Cart abandoners add to cart but then browse
                weights = {
                    'product_view': 35,
                    'add_to_cart': 40,
                    'page_view': 20,
                    'search': 5
                }
            else:  # WINDOW_SHOPPER
                # Window shoppers keep browsing
                weights = {
                    'product_view': 45,
                    'page_view': 30,
                    'add_to_cart': 15,
                    'search': 10
                }
        
        # CART_ACTIVE state
        elif state == SessionState.CART_ACTIVE:
            if persona == UserPersona.INTENT_BUYER:
                # Intent buyers go to checkout quickly
                weights = {
                    'checkout': 60,
                    'add_to_cart': 20,
                    'product_view': 10,
                    'page_view': 5,
                    'remove_from_cart': 5
                }
            elif persona == UserPersona.CART_ABANDONER:
                # Cart abandoners browse more, rarely checkout
                weights = {
                    'page_view': 35,
                    'product_view': 30,
                    'add_to_cart': 15,
                    'remove_from_cart': 15,
                    'checkout': 5
                }
            else:  # WINDOW_SHOPPER
                # Window shoppers hesitant to checkout
                weights = {
                    'page_view': 30,
                    'product_view': 25,
                    'add_to_cart': 20,
                    'checkout': 15,
                    'remove_from_cart': 10
                }
        
        # CHECKOUT_INITIATED state
        elif state == SessionState.CHECKOUT_INITIATED:
            if persona == UserPersona.INTENT_BUYER:
                # Intent buyers complete purchase
                weights = {
                    'purchase': 85,
                    'page_view': 10,
                    'remove_from_cart': 5
                }
            else:
                # Others might abandon at checkout
                weights = {
                    'purchase': 40,
                    'page_view': 30,
                    'remove_from_cart': 20,
                    'product_view': 10
                }
        
        # Default fallback
        else:
            weights = {
                'page_view': 50,
                'product_view': 30,
                'search': 20
            }
        
        # Select action based on weights
        actions = list(weights.keys())
        action_weights = list(weights.values())
        
        return random.choices(actions, weights=action_weights)[0]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics"""
        total_events = len(self.all_events)
        
        event_counts = {}
        persona_counts = {p: 0 for p in UserPersona}
        
        for event in self.all_events:
            event_type = event['event_type']
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            # Count personas from session_start events
            if event_type == 'session_start':
                persona_str = event.get('persona')
                for persona in UserPersona:
                    if persona.value == persona_str:
                        persona_counts[persona] += 1
        
        # Calculate abandonment rate
        cart_abandoned = event_counts.get('cart_abandoned', 0)
        purchases = event_counts.get('purchase', 0)
        total_cart_interactions = cart_abandoned + purchases
        abandonment_rate = (cart_abandoned / total_cart_interactions * 100) if total_cart_interactions > 0 else 0
        
        return {
            'total_events': total_events,
            'active_sessions': len(self.active_sessions),
            'event_breakdown': event_counts,
            'persona_distribution': {p.value: count for p, count in persona_counts.items()},
            'abandonment_rate': round(abandonment_rate, 2),
            'purchases': purchases,
            'cart_abandonments': cart_abandoned
        }


if __name__ == "__main__":
    # Test the simulator
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("🎮 REALISTIC EVENT SIMULATOR TEST")
    print("="*60)
    
    # Mock products for testing
    mock_products = [
        {'id': 1, 'title': 'Laptop', 'price': 999.99, 'category': 'electronics'},
        {'id': 2, 'title': 'Gold Ring', 'price': 299.99, 'category': 'jewelery'},
        {'id': 3, 'title': 'T-Shirt', 'price': 19.99, 'category': "men's clothing"},
        {'id': 4, 'title': 'Phone', 'price': 599.99, 'category': 'electronics'},
        {'id': 5, 'title': 'Dress', 'price': 49.99, 'category': "women's clothing"},
    ]
    
    simulator = EventSimulator(num_users=5, products=mock_products)
    
    # Generate 100 events to see realistic patterns
    print("\n📊 Generating 100 sample events...\n")
    print(f"{'#':<4} {'Event Type':<25} {'User':<6} {'Session':<12} {'State':<20}")
    print("-" * 80)
    
    for i in range(100):
        event = simulator.generate_event()
        event_type = event['event_type']
        user_id = event.get('user_id', 'N/A')
        session_id = event['session_id'][:8]
        state = event.get('session_state', 'unknown')
        
        # Add emoji for key events
        emoji = {
            'session_start': '🆕',
            'cart_abandoned': '🛒❌',
            'purchase': '✅💰',
            'add_to_cart': '🛒',
            'checkout_initiated': '💳'
        }.get(event_type, '  ')
        
        print(f"{i+1:<4} {emoji} {event_type:<23} {user_id:<6} {session_id:<12} {state:<20}")
        
        time.sleep(0.05)  # Small delay for readability
    
    # Show statistics
    print("\n" + "="*60)
    print("📈 SIMULATION STATISTICS")
    print("="*60)
    
    stats = simulator.get_statistics()
    
    print(f"\n🎯 Overall Metrics:")
    print(f"  Total events: {stats['total_events']}")
    print(f"  Active sessions: {stats['active_sessions']}")
    print(f"  Purchases: {stats['purchases']}")
    print(f"  Cart abandonments: {stats['cart_abandonments']}")
    print(f"  Abandonment rate: {stats['abandonment_rate']}%")
    
    print(f"\n👥 Persona Distribution:")
    for persona, count in stats['persona_distribution'].items():
        if count > 0:
            print(f"  {persona}: {count}")
    
    print(f"\n📋 Event Breakdown:")
    for event_type, count in sorted(stats['event_breakdown'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['total_events']) * 100
        print(f"  {event_type:<25}: {count:5d} ({percentage:5.1f}%)")
    
    print("\n" + "="*60)
    print("✅ REALISTIC EVENT SIMULATOR TEST COMPLETED")
    print("="*60 + "\n")