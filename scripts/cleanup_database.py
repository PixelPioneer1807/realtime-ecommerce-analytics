# scripts/cleanup_database.py

"""
Clean database before generating fresh training data.
Removes all sessions and resets for fresh start.
"""

import psycopg2
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import config

def cleanup_database():
    """Delete all data from user_sessions table"""
    
    print("\n" + "="*60)
    print("🧹 DATABASE CLEANUP")
    print("="*60)
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            database=config.POSTGRES_DB,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD
        )
        cursor = conn.cursor()
        
        # Check current count
        cursor.execute("SELECT COUNT(*) FROM user_sessions")
        current_count = cursor.fetchone()[0]
        print(f"\n📊 Current sessions in database: {current_count}")
        
        if current_count == 0:
            print("✅ Database already empty!")
            return
        
        # Ask for confirmation
        response = input(f"\n⚠️  Delete {current_count} sessions? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Cleanup cancelled")
            return
        
        # Delete all data
        print("\n🗑️  Deleting all sessions...")
        cursor.execute("DELETE FROM user_sessions")
        conn.commit()
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM user_sessions")
        final_count = cursor.fetchone()[0]
        
        print(f"✅ Cleanup complete! Deleted {current_count} sessions")
        print(f"📊 Current count: {final_count}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_database()
