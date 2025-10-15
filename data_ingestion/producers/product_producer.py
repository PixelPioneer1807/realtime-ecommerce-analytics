"""
Kafka producer for product events.
Fetches products from Fake Store API and publishes to Kafka.
"""

import logging
import time
from typing import Optional
import schedule
from confluent_kafka import Producer

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.config import config
from data_ingestion.api_clients.fake_store_client import FakeStoreClient
from streaming.kafka_utils.kafka_config import KafkaManager

logger = logging.getLogger(__name__)


class ProductProducer:
    """Producer for product catalog events"""
    
    def __init__(self):
        """Initialize product producer"""
        self.kafka_manager = KafkaManager()
        self.producer = self.kafka_manager.create_producer()
        self.api_client = FakeStoreClient()
        self.topic = config.KAFKA_TOPIC_PRODUCTS
        
        logger.info("Product producer initialized")
    
    def publish_all_products(self) -> int:
        """
        Fetch all products and publish to Kafka.
        
        Returns:
            Number of products published
        """
        try:
            products = self.api_client.get_all_products()
            
            if not products:
                logger.warning("No products fetched from API")
                return 0
            
            published_count = 0
            
            for product in products:
                # Enrich product data with event schema
                event = self.api_client.enrich_product_event(product)
                
                # Send to Kafka
                success = self.kafka_manager.send_message(
                    self.producer,
                    self.topic,
                    event,
                    key=str(product['id'])  # Use product ID as key for partitioning
                )
                
                if success:
                    published_count += 1
            
            # Wait for all messages to be delivered
            self.producer.flush()
            
            logger.info(f"Published {published_count} products to Kafka")
            return published_count
            
        except Exception as e:
            logger.error(f"Error publishing products: {e}")
            return 0
    
    def publish_products_by_category(self, category: str) -> int:
        """
        Fetch and publish products from specific category.
        
        Args:
            category: Category name
            
        Returns:
            Number of products published
        """
        try:
            products = self.api_client.get_products_by_category(category)
            
            published_count = 0
            
            for product in products:
                event = self.api_client.enrich_product_event(product)
                
                success = self.kafka_manager.send_message(
                    self.producer,
                    self.topic,
                    event,
                    key=str(product['id'])
                )
                
                if success:
                    published_count += 1
            
            # Wait for all messages to be delivered
            self.producer.flush()
            
            logger.info(f"Published {published_count} products from category '{category}'")
            return published_count
            
        except Exception as e:
            logger.error(f"Error publishing category '{category}': {e}")
            return 0
    
    def start_scheduled_publishing(self, interval_minutes: int = 30):
        """
        Start publishing products on a schedule.
        
        Args:
            interval_minutes: How often to publish (default: every 30 minutes)
        """
        logger.info(f"Starting scheduled publishing every {interval_minutes} minutes")
        
        # Publish immediately on start
        self.publish_all_products()
        
        # Schedule periodic publishing
        schedule.every(interval_minutes).minutes.do(self.publish_all_products)
        
        # Run scheduler
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            self.close()
    
    def close(self):
        """Close producer and client connections"""
        self.producer.flush()  # Wait for all messages to be delivered
        self.api_client.close()
        logger.info("Product producer closed")


if __name__ == "__main__":
    # Test the producer
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("📦 PRODUCT PRODUCER TEST")
    print("="*60)
    
    try:
        producer = ProductProducer()
        
        # Publish all products
        count = producer.publish_all_products()
        print(f"\n✅ Published {count} products to Kafka topic: {config.KAFKA_TOPIC_PRODUCTS}")
        
        # Test category publishing
        print("\n📋 Testing category publishing...")
        count = producer.publish_products_by_category("electronics")
        print(f"✅ Published {count} electronics products")
        
        producer.close()
        
        print("\n" + "="*60)
        print("✅ PRODUCT PRODUCER TEST COMPLETED")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
