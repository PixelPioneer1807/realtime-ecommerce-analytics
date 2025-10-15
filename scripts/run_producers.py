"""
Master script to run all Kafka producers.
This starts the complete data ingestion pipeline.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import time
from threading import Thread
from data_ingestion.producers.product_producer import ProductProducer
from data_ingestion.producers.user_event_producer import UserEventProducer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_product_producer():
    """Run product producer in background"""
    logger.info("Starting product producer...")
    producer = ProductProducer()
    
    # Publish products every 5 minutes
    while True:
        try:
            producer.publish_all_products()
            time.sleep(300)  # 5 minutes
        except KeyboardInterrupt:
            producer.close()
            break
        except Exception as e:
            logger.error(f"Product producer error: {e}")
            time.sleep(60)


def run_user_event_producer():
    """Run user event producer"""
    logger.info("Starting user event producer...")
    producer = UserEventProducer(
        num_users=100,  # 100 concurrent users
        events_per_second=20  # 20 events/second
    )
    
    try:
        producer.start_streaming()  # Run indefinitely
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 REAL-TIME E-COMMERCE DATA PIPELINE")
    print("="*70)
    print("\nStarting all producers...")
    print("  • Product Catalog Producer (updates every 5 min)")
    print("  • User Event Stream (100 users, 20 events/sec)")
    print("\nPress Ctrl+C to stop all producers.\n")
    print("="*70 + "\n")
    
    # Start product producer in background thread
    product_thread = Thread(target=run_product_producer, daemon=True)
    product_thread.start()
    
    # Give it time to publish initial products
    time.sleep(5)
    
    # Run user event producer in main thread (so Ctrl+C works)
    run_user_event_producer()
    
    print("\n✅ All producers stopped")
