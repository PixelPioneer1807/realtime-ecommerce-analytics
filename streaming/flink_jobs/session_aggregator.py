import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

# Add the project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streaming.flink_jobs.stream_processor_base import StreamProcessor
from config.config import config
from streaming.flink_jobs.ml_inference_service import MLInferenceService

logger = logging.getLogger(__name__)

class SessionAggregator(StreamProcessor):
    def __init__(self):
        super().__init__(
            job_name="session-aggregator",
            input_topics=[config.KAFKA_TOPIC_USER_EVENTS],
            parallelism=2
        )
        self.session_starts: Dict[str, datetime] = {}
        self.session_metrics: Dict[str, dict] = defaultdict(lambda: {
            'page_views': 0,
            'products_viewed': set(),
            'cart_additions': 0,
            'cart_removals': 0,
            'searches': 0,
            'cart_value': 0.0,
            'is_converted': False,
            'purchase_value': 0.0,
            'is_cart_abandoned': False,
            'abandonment_reason': None,
            'time_in_cart_seconds': 0,
            'checkout_initiated': False,
            'persona': None
        })
        # ML service will be initialized after DB connection is established
        self.ml_service = None

    def start(self):
        """Override start to initialize ML service after DB connection"""
        # Call parent start (this creates pg_conn)
        super().start()
        
        # NOW initialize ML service with the established connection
        if self.pg_conn:
            self.ml_service = MLInferenceService(self.pg_conn)
            logger.info("✅ ML Inference Service initialized with database connection")
        else:
            logger.warning("⚠️ ML Inference Service could not be initialized - no DB connection")

    def process_event(self, event: dict) -> Optional[dict]:
        try:
            session_id = event.get('session_id')
            event_type = event.get('event_type')
            if not session_id:
                return None
            
            if event_type == 'session_start':
                timestamp_str = event.get('timestamp')
                self.session_starts[session_id] = datetime.fromisoformat(
                    timestamp_str.replace('Z', '+00:00')
                ).replace(tzinfo=None)
                persona = event.get('persona')
                if persona:
                    self.session_metrics[session_id]['persona'] = persona
            
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
                metrics['cart_value'] = max(0, metrics['cart_value'])
            elif event_type == 'search':
                metrics['searches'] += 1
            elif event_type == 'checkout_initiated':
                metrics['checkout_initiated'] = True
            elif event_type == 'purchase':
                metrics['is_converted'] = True
                metrics['purchase_value'] = event.get('cart_value', 0.0)
            elif event_type == 'cart_abandoned':
                metrics['is_cart_abandoned'] = True
                metrics['abandonment_reason'] = event.get('abandonment_reason')
                metrics['time_in_cart_seconds'] = event.get('time_in_cart_seconds', 0)
                logger.info(f"Cart abandoned detected: session {session_id}, reason: {metrics['abandonment_reason']}, value: ${event.get('cart_value', 0):.2f}")
            return event
        
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            return None

    def process_window(self, key: str, events: List[dict]) -> Optional[dict]:
        try:
            if not events:
                return None
            session_id = key
            first_event = events[0]
            last_event = events[-1]
            user_id = first_event.get('user_id')
            device_type = first_event.get('device_type', 'desktop')
            browser = first_event.get('browser', 'Unknown')
            metrics = self.session_metrics.get(session_id, {})
            start_time = self.session_starts.get(session_id)
            if not start_time:
                start_time = datetime.now(timezone.utc).replace(tzinfo=None)
                self.session_starts[session_id] = start_time
            last_activity = datetime.fromisoformat(last_event.get('timestamp', '').replace('Z', '+00:00')).replace(tzinfo=None)
            duration_seconds = int((last_activity - start_time).total_seconds())
            page_views = metrics.get('page_views', 0)
            avg_time_per_page = duration_seconds / page_views if page_views > 0 else 0
            is_bounce = page_views <= 1 and duration_seconds < 30
            is_cart_abandoned = metrics.get('is_cart_abandoned', False)
            abandonment_reason = metrics.get('abandonment_reason')
            time_in_cart = metrics.get('time_in_cart_seconds', 0)
            products_viewed = len(metrics.get('products_viewed', set()))
            unique_products_viewed = products_viewed
            cart_additions = metrics.get('cart_additions', 0)
            cart_removals = metrics.get('cart_removals', 0)
            cart_value = round(metrics.get('cart_value', 0.0), 2)
            checkout_initiated = metrics.get('checkout_initiated', False)
            searches = metrics.get('searches', 0)
            bounce = is_bounce

            def safe_div(a, b):
                return float(a) / float(b) if b else 0.0

            cart_engagement = cart_additions - cart_removals
            time_per_product = safe_div(duration_seconds, products_viewed)
            cart_to_checkout_rate = safe_div(int(checkout_initiated), cart_additions)
            pages_per_minute = safe_div(page_views, float(duration_seconds) / 60.0)
            unique_product_ratio = safe_div(unique_products_viewed, products_viewed)

            engagement_score = min(
                1.0,
                (0.35 * safe_div(products_viewed, page_views)) +
                (0.20 * cart_additions) +
                (0.20 * safe_div(cart_value, max(1, cart_additions) * 40.0)) +
                (0.15 * pages_per_minute) +
                (0.10 * (not bounce))
            )

            ml_payload = {
                "session_id": str(session_id),
                "user_id": int(user_id) if user_id else 0,
                "page_views": int(page_views),
                "products_viewed": int(products_viewed),
                "unique_products_viewed": int(unique_products_viewed),
                "searches": int(searches),
                "cart_additions": int(cart_additions),
                "cart_removals": int(cart_removals),
                "cart_value": float(cart_value),
                "session_duration_seconds": int(duration_seconds),
                "avg_time_per_page": float(avg_time_per_page),
                "engagement_score": round(float(engagement_score), 4),
                "cart_engagement": int(cart_engagement),
                "time_per_product": round(float(time_per_product), 2),
                "cart_to_checkout_rate": round(float(cart_to_checkout_rate), 2),
                "pages_per_minute": round(float(pages_per_minute), 2),
                "unique_product_ratio": round(float(unique_product_ratio), 2),
                "device_type": str(device_type),
                "browser": str(browser),
                "persona": str(metrics.get('persona') or "window_shopper"),
                "bounce": bool(bounce),
                "checkout_initiated": bool(checkout_initiated)
            }

            # Call ML API only if ML service is initialized
            prediction = None
            if self.ml_service:
                start_time_predict = time.time()
                prediction = self.ml_service.call_ml_api(ml_payload)

                if prediction:
                    latency_ms = (time.time() - start_time_predict) * 1000
                    self.ml_service.log_prediction(ml_payload, prediction, latency_ms)

                    if prediction.get('risk_level') in ['HIGH', 'CRITICAL']:
                        logger.warning(
                            f"⚠️ HIGH RISK ABANDONMENT: session {session_id} "
                            f"(probability: {prediction.get('abandonment_probability')*100:.2f}%) "
                            f"recommended: {prediction.get('recommended_intervention')}"
                        )
            else:
                logger.debug("ML service not initialized, skipping prediction")

            session_record = {
                'session_id': session_id,
                'user_id': user_id,
                'start_time': start_time.isoformat(),
                'end_time': None,
                'last_activity': last_activity.isoformat(),
                'device_type': device_type,
                'browser': browser,
                'page_views': page_views,
                'products_viewed': products_viewed,
                'unique_products_viewed': unique_products_viewed,
                'searches': searches,
                'cart_additions': cart_additions,
                'cart_removals': cart_removals,
                'cart_value': cart_value,
                'is_converted': metrics.get('is_converted', False),
                'purchase_value': round(metrics.get('purchase_value', 0.0), 2),
                'session_duration_seconds': duration_seconds,
                'avg_time_per_page': round(avg_time_per_page, 2),
                'bounce': bounce,
                'is_cart_abandoned': is_cart_abandoned,
                'abandonment_reason': abandonment_reason,
                'time_in_cart_seconds': time_in_cart,
                'checkout_initiated': checkout_initiated,
                'persona': metrics.get('persona'),
                'updated_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            }

            self.sink_to_postgres('user_sessions', [session_record])
            redis_key = f"session:{session_id}"
            self.sink_to_redis(redis_key, session_record, expire_seconds=3600)

            log_msg = f"Aggregated session {session_id}: {page_views} page views, {cart_additions} cart additions"
            if is_cart_abandoned:
                log_msg += f", ABANDONED (reason: {abandonment_reason})"
            elif metrics.get('is_converted', False):
                log_msg += f", CONVERTED (${metrics.get('purchase_value', 0):.2f})"
            logger.info(log_msg)

            return session_record

        except Exception as e:
            logger.error(f"Error processing window for session {key}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_key(self, event: dict) -> str:
        return event.get('session_id', 'unknown')

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    print("\n" + "=" * 60)
    print("🚀 SESSION AGGREGATOR JOB (Enhanced with ML prediction)")
    print("=" * 60)
    print("\nThis job processes user events and aggregates session metrics.")
    print("It reads from Kafka 'user-events' topic and writes to PostgreSQL.")
    print("\n✨ NEW FEATURES:")
    print("  - Real-time ML abandonment prediction and logging")
    print("  - Cart abandonment reasons and persona tracking")
    print("\nMake sure the following are running:")
    print(" 1. Docker Compose (Kafka, PostgreSQL, Redis)")
    print(" 2. User event producer")
    print(" 3. ML API server (FastAPI)")
    print("\nPress Ctrl+C to stop.\n")
    print("=" * 60 + "\n")

    try:
        aggregator = SessionAggregator()
        aggregator.run()
    except KeyboardInterrupt:
        print("\n\n✅ Session aggregator stopped by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()