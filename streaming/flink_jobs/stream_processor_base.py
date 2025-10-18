"""
Base stream processor framework for real-time analytics.
Implements windowing, aggregation, and stateful processing.
This is a custom implementation that replaces PyFlink for Python 3.12 compatibility.
"""

import logging
import json
import time
import threading
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import execute_batch
import redis
from config.config import config

logger = logging.getLogger(__name__)


class Window:
    """Time window for stream aggregation"""
    
    def __init__(self, duration_seconds: int = 300, slide_seconds: int = 60):
        """
        Initialize window.
        
        Args:
            duration_seconds: Window duration (default: 5 minutes)
            slide_seconds: Window slide interval (default: 1 minute)
        """
        self.duration = duration_seconds
        self.slide = slide_seconds
        self.data: Dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()
    
    def add_event(self, key: str, event: dict):
        """Add event to window"""
        with self.lock:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            self.data[key].append({
                'event': event,
                'timestamp': now
            })
            # Remove expired events
            self._cleanup_expired(key, now)
    
    def _cleanup_expired(self, key: str, now: datetime):
        """Remove events older than window duration"""
        cutoff = now - timedelta(seconds=self.duration)
        while self.data[key] and self.data[key][0]['timestamp'] < cutoff:
            self.data[key].popleft()
    
    def get_window_data(self, key: str) -> List[dict]:
        """Get all events in current window for key"""
        with self.lock:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            self._cleanup_expired(key, now)
            return [item['event'] for item in self.data[key]]
    
    def get_all_keys(self) -> List[str]:
        """Get all active keys in window"""
        with self.lock:
            return list(self.data.keys())


class StateStore:
    """In-memory state store for stateful processing"""
    
    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.lock = threading.Lock()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get state value"""
        with self.lock:
            return self.state.get(key, default)
    
    def put(self, key: str, value: Any):
        """Put state value"""
        with self.lock:
            self.state[key] = value
    
    def update(self, key: str, update_fn: Callable):
        """Update state with function"""
        with self.lock:
            current = self.state.get(key)
            self.state[key] = update_fn(current)
    
    def delete(self, key: str):
        """Delete state key"""
        with self.lock:
            self.state.pop(key, None)


class StreamProcessor(ABC):
    """Base class for stream processing jobs"""
    
    def __init__(
        self,
        job_name: str,
        input_topics: List[str],
        parallelism: int = 2
    ):
        """
        Initialize stream processor.
        
        Args:
            job_name: Name of the processing job
            input_topics: List of Kafka topics to consume
            parallelism: Number of parallel consumers
        """
        self.job_name = job_name
        self.input_topics = input_topics
        self.parallelism = parallelism
        
        # State management
        self.window = Window()
        self.state_store = StateStore()
        
        # Database connections
        self.pg_conn = None
        self.redis_client = None
        
        # Control flags
        self.running = False
        self.threads: List[threading.Thread] = []
        
        logger.info(
            f"Stream processor '{job_name}' initialized: "
            f"topics={input_topics}, parallelism={parallelism}"
        )
    
    def _create_kafka_consumer(self, consumer_id: int) -> KafkaConsumer:
        """Create Kafka consumer instance"""
        return KafkaConsumer(
            *self.input_topics,
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=f'{self.job_name}-consumer-group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=1000  # 1 second timeout for graceful shutdown
        )
    
    def _init_postgres(self):
        """Initialize PostgreSQL connection"""
        try:
            self.pg_conn = psycopg2.connect(
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT,
                database=config.POSTGRES_DB,
                user=config.POSTGRES_USER,
                password=config.POSTGRES_PASSWORD
            )
            self.pg_conn.autocommit = False
            logger.info("PostgreSQL connection established")
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            raise
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            raise
    
    @abstractmethod
    def process_event(self, event: dict) -> Optional[dict]:
        """
        Process a single event.
        Must be implemented by subclasses.
        
        Args:
            event: Event dictionary from Kafka
            
        Returns:
            Processed result or None
        """
        pass
    
    @abstractmethod
    def process_window(self, key: str, events: List[dict]) -> Optional[dict]:
        """
        Process windowed events.
        Must be implemented by subclasses.
        
        Args:
            key: Window key
            events: List of events in window
            
        Returns:
            Aggregated result or None
        """
        pass
    
    def sink_to_postgres(self, table: str, data: List[dict]):
        """
        Batch insert data to PostgreSQL.
        
        Args:
            table: Target table name
            data: List of dictionaries to insert
        """
        if not data:
            return
        
        try:
            cursor = self.pg_conn.cursor()
            
            # Build INSERT query from first record
            columns = list(data[0].keys())
            placeholders = ','.join(['%s'] * len(columns))
            query = f"""
                INSERT INTO {table} ({','.join(columns)})
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            
            # Prepare values
            values = [tuple(record[col] for col in columns) for record in data]
            
            # Batch insert
            execute_batch(cursor, query, values, page_size=100)
            self.pg_conn.commit()
            cursor.close()
            
            logger.debug(f"Inserted {len(data)} records to {table}")
            
        except Exception as e:
            logger.error(f"Error inserting to PostgreSQL: {e}")
            self.pg_conn.rollback()
    
    def sink_to_redis(self, key: str, value: Any, expire_seconds: int = 3600):
        """
        Write data to Redis.
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized)
            expire_seconds: TTL in seconds
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            self.redis_client.setex(key, expire_seconds, value)
            logger.debug(f"Wrote to Redis: {key}")
            
        except Exception as e:
            logger.error(f"Error writing to Redis: {e}")
    
    def _consumer_loop(self, consumer_id: int):
        """Main consumer loop for processing events"""
        consumer = self._create_kafka_consumer(consumer_id)
        
        logger.info(f"Consumer {consumer_id} started")
        
        try:
            while self.running:
                try:
                    # Poll for messages
                    messages = consumer.poll(timeout_ms=1000)
                    
                    for topic_partition, records in messages.items():
                        for record in records:
                            try:
                                # Process single event
                                result = self.process_event(record.value)
                                
                                if result:
                                    # Add to window for aggregation
                                    key = self._extract_key(record.value)
                                    self.window.add_event(key, record.value)
                                
                            except Exception as e:
                                logger.error(f"Error processing event: {e}")
                    
                except Exception as e:
                    if self.running:  # Only log if not shutting down
                        logger.error(f"Consumer {consumer_id} error: {e}")
                        time.sleep(1)
                
        finally:
            consumer.close()
            logger.info(f"Consumer {consumer_id} stopped")
    
    def _aggregation_loop(self):
        """Periodic aggregation of windowed data"""
        logger.info("Aggregation loop started")
        
        while self.running:
            try:
                # Process all active windows
                for key in self.window.get_all_keys():
                    events = self.window.get_window_data(key)
                    
                    if events:
                        result = self.process_window(key, events)
                        
                        if result:
                            logger.debug(f"Aggregated {len(events)} events for key: {key}")
                
                # Sleep for slide interval
                time.sleep(self.window.slide)
                
            except Exception as e:
                logger.error(f"Aggregation error: {e}")
                time.sleep(1)
        
        logger.info("Aggregation loop stopped")
    
    def _extract_key(self, event: dict) -> str:
        """
        Extract key from event for windowing.
        Default implementation uses session_id or user_id.
        Override in subclasses for custom logic.
        
        Args:
            event: Event dictionary
            
        Returns:
            Key string
        """
        return event.get('session_id') or str(event.get('user_id', 'unknown'))
    
    def start(self):
        """Start the stream processor"""
        if self.running:
            logger.warning("Processor already running")
            return
        
        logger.info(f"Starting stream processor: {self.job_name}")
        
        # Initialize connections
        self._init_postgres()
        self._init_redis()
        
        self.running = True
        
        # Start consumer threads
        for i in range(self.parallelism):
            thread = threading.Thread(
                target=self._consumer_loop,
                args=(i,),
                name=f"{self.job_name}-consumer-{i}"
            )
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
        
        # Start aggregation thread
        agg_thread = threading.Thread(
            target=self._aggregation_loop,
            name=f"{self.job_name}-aggregator"
        )
        agg_thread.daemon = True
        agg_thread.start()
        self.threads.append(agg_thread)
        
        logger.info(f"Stream processor started with {len(self.threads)} threads")
    
    def stop(self):
        """Stop the stream processor"""
        logger.info(f"Stopping stream processor: {self.job_name}")
        
        self.running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=5)
        
        # Close connections
        if self.pg_conn:
            self.pg_conn.close()
        
        if self.redis_client:
            self.redis_client.close()
        
        logger.info("Stream processor stopped")
    
    def run(self, duration_seconds: Optional[int] = None):
        """
        Run the processor.
        
        Args:
            duration_seconds: Run duration (None = infinite)
        """
        self.start()
        
        try:
            if duration_seconds:
                logger.info(f"Running for {duration_seconds} seconds...")
                time.sleep(duration_seconds)
            else:
                logger.info("Running indefinitely (Ctrl+C to stop)...")
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()


if __name__ == "__main__":
    # Test the base processor
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("🔧 STREAM PROCESSOR FRAMEWORK TEST")
    print("="*60)
    
    # Test Window
    print("\n1. Testing Window...")
    window = Window(duration_seconds=10, slide_seconds=2)
    window.add_event("session_1", {"event": "test", "value": 1})
    window.add_event("session_1", {"event": "test", "value": 2})
    events = window.get_window_data("session_1")
    print(f"   ✓ Window contains {len(events)} events")
    
    # Test StateStore
    print("\n2. Testing StateStore...")
    state = StateStore()
    state.put("counter", 0)
    state.update("counter", lambda x: (x or 0) + 1)
    value = state.get("counter")
    print(f"   ✓ State value: {value}")
    
    print("\n" + "="*60)
    print("✅ STREAM PROCESSOR FRAMEWORK TEST COMPLETED")
    print("="*60 + "\n")
