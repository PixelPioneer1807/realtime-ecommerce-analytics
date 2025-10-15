"""
Kafka configuration and utility functions using confluent-kafka.
Handles Kafka connection, topic creation, and producer/consumer setup.
"""

import logging
from typing import List, Optional, Dict, Any
from confluent_kafka import Producer, Consumer, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
import json
from config.config import config

logger = logging.getLogger(__name__)


class KafkaManager:
    """Manager class for Kafka operations"""
    
    def __init__(self, bootstrap_servers: Optional[str] = None):
        """
        Initialize Kafka manager.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers (uses config if not provided)
        """
        self.bootstrap_servers = bootstrap_servers or config.KAFKA_BOOTSTRAP_SERVERS
        logger.info(f"Initializing Kafka manager with servers: {self.bootstrap_servers}")
    
    def create_producer(self) -> Producer:
        """
        Create a Kafka producer.
        
        Returns:
            Configured Producer instance
        """
        try:
            producer_config = {
                'bootstrap.servers': self.bootstrap_servers,
                'client.id': 'ecommerce-producer',
                'acks': 'all',
                'retries': 3,
                'compression.type': 'gzip',
                'linger.ms': 10,
                'batch.size': 16384
            }
            
            producer = Producer(producer_config)
            logger.info("Kafka producer created successfully")
            return producer
            
        except Exception as e:
            logger.error(f"Error creating Kafka producer: {e}")
            raise
    
    def create_consumer(
        self, 
        topics: List[str], 
        group_id: str = "analytics-group"
    ) -> Consumer:
        """
        Create a Kafka consumer.
        
        Args:
            topics: List of topics to subscribe to
            group_id: Consumer group ID
            
        Returns:
            Configured Consumer instance
        """
        try:
            consumer_config = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': group_id,
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': True,
                'auto.commit.interval.ms': 1000
            }
            
            consumer = Consumer(consumer_config)
            consumer.subscribe(topics)
            logger.info(f"Kafka consumer created for topics: {topics}")
            return consumer
            
        except Exception as e:
            logger.error(f"Error creating Kafka consumer: {e}")
            raise
    
    def create_topics(self, topic_configs: List[dict]) -> bool:
        """
        Create Kafka topics if they don't exist.
        
        Args:
            topic_configs: List of topic configuration dictionaries
                          [{"name": "topic-name", "partitions": 3, "replication": 1}]
            
        Returns:
            True if successful, False otherwise
        """
        try:
            admin_config = {
                'bootstrap.servers': self.bootstrap_servers
            }
            admin_client = AdminClient(admin_config)
            
            # Create NewTopic objects
            new_topics = []
            for topic_config in topic_configs:
                new_topic = NewTopic(
                    topic_config["name"],
                    num_partitions=topic_config.get("partitions", 3),
                    replication_factor=topic_config.get("replication", 1)
                )
                new_topics.append(new_topic)
            
            # Create topics
            fs = admin_client.create_topics(new_topics)
            
            # Wait for operations to finish
            for topic_name, future in fs.items():
                try:
                    future.result()  # Block until topic is created
                    logger.info(f"Topic '{topic_name}' created successfully")
                except KafkaException as e:
                    if e.args[0].code() == 36:  # TOPIC_ALREADY_EXISTS
                        logger.info(f"Topic '{topic_name}' already exists")
                    else:
                        logger.error(f"Error creating topic '{topic_name}': {e}")
                except Exception as e:
                    logger.error(f"Unexpected error for topic '{topic_name}': {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in topic creation: {e}")
            return False
    
    def list_topics(self) -> List[str]:
        """
        List all Kafka topics.
        
        Returns:
            List of topic names
        """
        try:
            admin_config = {
                'bootstrap.servers': self.bootstrap_servers
            }
            admin_client = AdminClient(admin_config)
            
            metadata = admin_client.list_topics(timeout=10)
            topics = list(metadata.topics.keys())
            
            logger.info(f"Found {len(topics)} topics")
            return topics
            
        except Exception as e:
            logger.error(f"Error listing topics: {e}")
            return []
    
    def send_message(
        self, 
        producer: Producer, 
        topic: str, 
        message: dict,
        key: Optional[str] = None
    ) -> bool:
        """
        Send a message to Kafka topic.
        
        Args:
            producer: Producer instance
            topic: Topic name
            message: Message dictionary
            key: Optional message key for partitioning
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize message to JSON
            value = json.dumps(message).encode('utf-8')
            key_bytes = key.encode('utf-8') if key else None
            
            # Produce message
            producer.produce(
                topic,
                value=value,
                key=key_bytes,
                callback=self._delivery_callback
            )
            
            # Trigger delivery reports
            producer.poll(0)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to {topic}: {e}")
            return False
    
    @staticmethod
    def _delivery_callback(err, msg):
        """
        Callback for message delivery reports.
        
        Args:
            err: Error object (None if successful)
            msg: Message object
        """
        if err is not None:
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.debug(
                f'Message delivered to {msg.topic()} '
                f'[partition {msg.partition()}] at offset {msg.offset()}'
            )


# Default topic configurations for the project
DEFAULT_TOPICS = [
    {
        "name": config.KAFKA_TOPIC_PRODUCTS,
        "partitions": 3,
        "replication": 1
    },
    {
        "name": config.KAFKA_TOPIC_USER_EVENTS,
        "partitions": 5,  # More partitions for high-volume user events
        "replication": 1
    },
    {
        "name": config.KAFKA_TOPIC_WEATHER,
        "partitions": 1,
        "replication": 1
    },
    {
        "name": config.KAFKA_TOPIC_FINANCE,
        "partitions": 1,
        "replication": 1
    }
]


if __name__ == "__main__":
    # Test Kafka connection and topic creation
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("🔧 KAFKA SETUP TEST")
    print("="*60)
    
    manager = KafkaManager()
    
    # Create topics
    print("\n📋 Creating topics...")
    success = manager.create_topics(DEFAULT_TOPICS)
    
    if success:
        print("✅ Topics created successfully")
    else:
        print("❌ Error creating topics")
    
    # List all topics
    print("\n📝 Listing all topics:")
    topics = manager.list_topics()
    for topic in topics:
        if not topic.startswith('__'):  # Skip internal topics
            print(f"  - {topic}")
    
    # Test producer
    print("\n📤 Testing producer...")
    producer = manager.create_producer()
    
    test_message = {
        "test": "Hello Kafka!",
        "timestamp": "2025-10-15T09:50:00Z"
    }
    
    success = manager.send_message(
        producer, 
        config.KAFKA_TOPIC_PRODUCTS, 
        test_message
    )
    
    if success:
        producer.flush()  # Wait for message to be sent
        print("✅ Test message sent successfully")
    else:
        print("❌ Error sending test message")
    
    print("\n" + "="*60)
    print("✅ KAFKA SETUP TEST COMPLETED")
    print("="*60 + "\n")
