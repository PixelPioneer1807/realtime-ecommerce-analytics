"""
Script to set up all Kafka topics for the project.
Run this before starting producers: python scripts/setup_kafka_topics.py
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from streaming.kafka_utils.kafka_config import KafkaManager, DEFAULT_TOPICS
from config.config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def setup_topics():
    """Set up all Kafka topics"""
    print("\n" + "="*70)
    print("🚀 KAFKA TOPICS SETUP")
    print("="*70)
    
    print(f"\n📡 Connecting to Kafka: {config.KAFKA_BOOTSTRAP_SERVERS}")
    
    manager = KafkaManager()
    
    # Create topics
    print("\n📋 Creating topics...")
    for topic_config in DEFAULT_TOPICS:
        print(f"  - {topic_config['name']} (partitions: {topic_config['partitions']})")
    
    success = manager.create_topics(DEFAULT_TOPICS)
    
    if success:
        print("\n✅ Topics created/verified successfully")
    else:
        print("\n❌ Error creating topics")
        return False
    
    # List all topics
    print("\n📝 All available topics:")
    topics = manager.list_topics()
    for topic in sorted(topics):
        if not topic.startswith('__'):  # Skip internal Kafka topics
            print(f"  ✓ {topic}")
    
    print("\n" + "="*70)
    print("✅ KAFKA SETUP COMPLETED")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    success = setup_topics()
    sys.exit(0 if success else 1)
