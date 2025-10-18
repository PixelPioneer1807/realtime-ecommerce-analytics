"""
Script to run the Session Aggregator job.
This is a convenient entry point for starting the job.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from streaming.flink_jobs.session_aggregator import SessionAggregator

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/session_aggregator.log')
        ]
    )
    
    print("\n" + "="*70)
    print(" "*20 + "SESSION AGGREGATOR JOB")
    print("="*70)
    print("\n📊 Real-Time Session Analytics Pipeline")
    print("\n🔄 Processing Flow:")
    print("   Kafka (user-events) → Session Aggregation → PostgreSQL + Redis")
    print("\n✅ Prerequisites:")
    print("   • Docker Compose running (Kafka, PostgreSQL, Redis)")
    print("   • User event producer generating events")
    print("\nPress Ctrl+C to stop the job.\n")
    print("="*70 + "\n")
    
    try:
        aggregator = SessionAggregator()
        aggregator.run()
        
    except KeyboardInterrupt:
        print("\n" + "="*70)
        print("🛑 Session Aggregator stopped by user")
        print("="*70 + "\n")
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
