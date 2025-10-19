"""
Kafka producer for user behavior events.
Continuously generates and streams realistic user events to Kafka.
This simulates real-time e-commerce traffic.
"""

import logging
import time
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from confluent_kafka import Producer
from config.config import config
from data_ingestion.api_clients.fake_store_client import FakeStoreClient
from data_ingestion.producers.event_simulator import EventSimulator
from streaming.kafka_utils.kafka_config import KafkaManager

logger = logging.getLogger(__name__)


class UserEventProducer:
    """Producer for streaming user behavior events to Kafka"""
    
    def __init__(
        self, 
        num_users: int = 50,
        events_per_second: int = 10
    ):
        """
        Initialize user event producer.
        
        Args:
            num_users: Number of simulated concurrent users
            events_per_second: Target event generation rate
        """
        self.kafka_manager = KafkaManager()
        self.producer = self.kafka_manager.create_producer()
        self.topic = config.KAFKA_TOPIC_USER_EVENTS
        self.events_per_second = events_per_second
        
        # Fetch real products from API
        logger.info("Fetching products from Fake Store API...")
        api_client = FakeStoreClient()
        products = api_client.get_all_products()
        api_client.close()
        
        # Initialize event simulator
        self.simulator = EventSimulator(
            num_users=num_users,
            products=products
        )
        
        self.total_events_sent = 0
        self.running = False
        
        logger.info(
            f"User event producer initialized: "
            f"{num_users} users, {events_per_second} events/sec"
        )
    
    def send_event(self, event: dict) -> bool:
        """
        Send a single event to Kafka.
        
        Args:
            event: Event dictionary
            
        Returns:
            True if successful
        """
        try:
            success = self.kafka_manager.send_message(
                self.producer,
                self.topic,
                event,
                key=event['session_id']  # Use session_id for partitioning
            )
            
            if success:
                self.total_events_sent += 1
                
                # Log every 100 events
                if self.total_events_sent % 100 == 0:
                    stats = self.simulator.get_statistics()
                    logger.info(
                        f"Sent {self.total_events_sent} events. "
                        f"Active sessions: {stats['active_sessions']}"
                    )
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending event: {e}")
            return False
    
    def start_streaming(self, duration_seconds: int = None):
        """
        Start streaming events to Kafka.
        
        Args:
            duration_seconds: How long to run (None = infinite)
        """
        self.running = True
        start_time = time.time()
        
        logger.info(
            f"🚀 Starting event stream: {self.events_per_second} events/sec"
        )
        
        try:
            event_count = 0
            while self.running:
                loop_start = time.time()
                
                # Generate and send events for this second
                for _ in range(self.events_per_second):
                    event = self.simulator.generate_event()
                    self.send_event(event)
                    event_count += 1
                
                # Flush producer periodically
                if event_count % 50 == 0:
                    self.producer.flush()
                
                # Check if duration expired
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    logger.info(f"Duration of {duration_seconds}s reached. Stopping...")
                    break
                
                # Sleep to maintain target rate
                elapsed = time.time() - loop_start
                sleep_time = max(0, 1.0 - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("\nStopping event stream (Ctrl+C pressed)...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the producer and show statistics"""
        self.running = False
        
        # Flush remaining messages
        logger.info("Flushing remaining messages...")
        self.producer.flush()
        
        # Show statistics
        stats = self.simulator.get_statistics()
        
        print("\n" + "="*60)
        print("📊 STREAMING STATISTICS")
        print("="*60)
        print(f"Total events sent: {self.total_events_sent}")
        print(f"Active sessions: {stats['active_sessions']}")
        print(f"\nEvent breakdown:")
        for event_type, count in stats['event_breakdown'].items():
            percentage = (count / stats['total_events']) * 100
            print(f"  {event_type:20s}: {count:5d} ({percentage:5.1f}%)")
        print("="*60 + "\n")
        
        logger.info("User event producer stopped")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("🎬 USER EVENT STREAMING - REAL-TIME SIMULATION")
    print("="*60)
    print("\nThis will stream realistic e-commerce events to Kafka.")
    print("Press Ctrl+C to stop.\n")
    
    # Create producer
    producer = UserEventProducer(
        num_users=400,  # Simulate 50 concurrent users
        events_per_second=40  # Generate 10 events per second
    )
    
    # Start streaming for 60 seconds (or press Ctrl+C to stop)
    producer.start_streaming(duration_seconds=1500)
    
    print("\n✅ Streaming completed!")