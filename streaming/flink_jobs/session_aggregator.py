"""
Session Aggregator Job
Processes user events and aggregates session-level metrics in real-time.

Input: user-events Kafka topic
Output: user_sessions PostgreSQL table + Redis cache

Metrics computed:
- Page views count
- Products viewed count
- Cart additions/removals
- Session duration
- Conversion status
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streaming.flink_jobs.stream_processor_base import StreamProcessor
from config.config import config

logger = logging.getLogger(__name__)


class SessionAggregator(StreamProcessor):
    """Aggregates user session metrics from event stream"""
    
    def __init__(self):
        super().__init__(
            job_name="session-aggregator",
            input_topics=[config.KAFKA_TOPIC_USER_EVENTS],
            parallelism=2
        )
        
        # Session state tracking
        self.session_starts: Dict[str, datetime] = {}
        self.session_metrics: Dict[str, dict] = defaultdict(lambda: {
            'page_views': 0,
            'products_viewed': set(),
            'cart_additions': 0,
            'cart_removals': 0,
            'searches': 0,
            'cart_value': 0.0,
            'is_converted': False,
            'purchase_value': 0.0
        })
    
    def process_event(self, event: dict) -> Optional[dict]:
        """
        Process individual user event and update session state.
        
        Args:
            event: User event from Kafka
            
        Returns:
            Processed event (for windowing)
        """
        try:
            session_id = event.get('session_id')
            event_type = event.get('event_type')
            
            if not session_id:
                return None
            
            # Track session start time
            if event_type == 'session_start':
                timestamp_str = event.get('timestamp')
                self.session_starts[session_id] = datetime.fromisoformat(
                    timestamp_str.replace('Z', '+00:00')
                ).replace(tzinfo=None)
            
            # Update metrics based on event type
            metrics = self.session_metrics[session_id]
            
            if event_type == 'page_view':
                metrics['page_views'] += 1
            
            elif event_type == 'product_view':
                product_id = event.get('product_id')
                if product_id:
                    metrics['products_viewed'].add(product_id)
            
            elif event_type == 'add_to_cart':
                metrics['cart_additions'] += 1
                price = event.get('price', 0)
                quantity = event.get('quantity', 1)
                metrics['cart_value'] += price * quantity
            
            elif event_type == 'remove_from_cart':
                metrics['cart_removals'] += 1
                price = event.get('price', 0)
                quantity = event.get('quantity', 1)
                metrics['cart_value'] -= price * quantity
            
            elif event_type == 'search':
                metrics['searches'] += 1
            
            elif event_type == 'purchase':
                metrics['is_converted'] = True
                metrics['purchase_value'] = event.get('cart_value', 0.0)
            
            return event
            
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            return None
    
    def process_window(self, key: str, events: List[dict]) -> Optional[dict]:
        """
        Process windowed events and aggregate session metrics.
        
        Args:
            key: Session ID
            events: List of events in window
            
        Returns:
            Aggregated session data
        """
        try:
            if not events:
                return None
            
            session_id = key
            
            # Get first and last event
            first_event = events[0]
            last_event = events[-1]
            
            user_id = first_event.get('user_id')
            device_type = first_event.get('device_type', 'desktop')
            browser = first_event.get('browser', 'Unknown')
            
            # Get metrics from state
            metrics = self.session_metrics.get(session_id, {})
            
            # Calculate session duration
            start_time = self.session_starts.get(session_id)
            if not start_time:
                start_time = datetime.now(timezone.utc).replace(tzinfo=None)
                self.session_starts[session_id] = start_time
            
            last_activity = datetime.fromisoformat(
                last_event.get('timestamp', '').replace('Z', '+00:00')
            ).replace(tzinfo=None)
            
            duration_seconds = int((last_activity - start_time).total_seconds())
            
            # Calculate average time per page
            page_views = metrics.get('page_views', 0)
            avg_time_per_page = duration_seconds / page_views if page_views > 0 else 0
            
            # Determine if bounce (single page view, < 30 seconds)
            is_bounce = page_views <= 1 and duration_seconds < 30
            
            # Build aggregated record
            session_record = {
                'session_id': session_id,
                'user_id': user_id,
                'start_time': start_time.isoformat(),
                'end_time': None,
                'last_activity': last_activity.isoformat(),
                'device_type': device_type,
                'browser': browser,
                'page_views': page_views,
                'products_viewed': len(metrics.get('products_viewed', set())),
                'unique_products_viewed': len(metrics.get('products_viewed', set())),
                'searches': metrics.get('searches', 0),
                'cart_additions': metrics.get('cart_additions', 0),
                'cart_removals': metrics.get('cart_removals', 0),
                'cart_value': round(metrics.get('cart_value', 0.0), 2),
                'is_converted': metrics.get('is_converted', False),
                'purchase_value': round(metrics.get('purchase_value', 0.0), 2),
                'session_duration_seconds': duration_seconds,
                'avg_time_per_page': round(avg_time_per_page, 2),
                'bounce': is_bounce,
                'updated_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            }
            
            # Write to PostgreSQL
            self.sink_to_postgres('user_sessions', [session_record])
            
            # Cache in Redis for fast lookup (1 hour TTL)
            redis_key = f"session:{session_id}"
            self.sink_to_redis(redis_key, session_record, expire_seconds=3600)
            
            logger.info(
                f"Aggregated session {session_id}: "
                f"{page_views} page views, "
                f"{metrics.get('cart_additions', 0)} cart additions, "
                f"converted={metrics.get('is_converted', False)}"
            )
            
            return session_record
            
        except Exception as e:
            logger.error(f"Error processing window for session {key}: {e}")
            return None
    
    def _extract_key(self, event: dict) -> str:
        """Extract session_id as the key for windowing"""
        return event.get('session_id', 'unknown')


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("🚀 SESSION AGGREGATOR JOB")
    print("="*60)
    print("\nThis job processes user events and aggregates session metrics.")
    print("It reads from Kafka 'user-events' topic and writes to PostgreSQL.")
    print("\nMake sure the following are running:")
    print("  1. Docker Compose (Kafka, PostgreSQL, Redis)")
    print("  2. User event producer")
    print("\nPress Ctrl+C to stop.\n")
    print("="*60 + "\n")
    
    try:
        aggregator = SessionAggregator()
        aggregator.run()
        
    except KeyboardInterrupt:
        print("\n\n✅ Session aggregator stopped by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
