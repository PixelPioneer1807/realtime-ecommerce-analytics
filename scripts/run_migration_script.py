"""
Database Migration Runner
Applies cart abandonment schema changes to existing database.
Safe to run multiple times.

Usage: python scripts/run_migration.py
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from database.db_manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_migration():
    """Execute the cart abandonment migration"""
    print("\n" + "="*70)
    print("🔄 DATABASE MIGRATION - Cart Abandonment Features")
    print("="*70)
    print("\nThis will add new columns and views to your database.")
    print("Safe to run multiple times (uses IF NOT EXISTS).\n")
    
    try:
        # Initialize database manager
        print("📡 Connecting to database...")
        db = DatabaseManager()
        print("✓ Connected successfully\n")
        
        # Path to migration file
        migration_file = project_root / "database" / "schemas" / "migrate_cart_abandonment.sql"
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            print("\nPlease ensure the migration SQL file is in:")
            print(f"  {migration_file}")
            return False
        
        print(f"📄 Migration file: {migration_file.name}")
        print("\n🔧 Applying migration...\n")
        
        # Execute migration
        success = db.execute_schema(str(migration_file))
        
        if success:
            print("\n✅ Migration completed successfully!\n")
            
            # Verify new columns
            print("🔍 Verifying new schema...\n")
            
            # Check user_sessions columns
            columns = db.execute_query("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'user_sessions' 
                AND column_name IN (
                    'is_cart_abandoned',
                    'abandonment_reason', 
                    'time_in_cart_seconds',
                    'checkout_initiated',
                    'persona'
                )
                ORDER BY column_name
            """)
            
            if columns:
                print("✓ New columns in user_sessions:")
                for col in columns:
                    print(f"  - {col['column_name']} ({col['data_type']})")
            else:
                print("⚠️  Could not verify new columns")
            
            # Check views
            print("\n✓ Analytical views created:")
            views = db.execute_query("""
                SELECT table_name 
                FROM information_schema.views 
                WHERE table_schema = 'public'
                AND table_name LIKE 'v_%'
                ORDER BY table_name
            """)
            
            if views:
                for view in views:
                    print(f"  - {view['table_name']}")
            
            print("\n" + "="*70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY")
            print("="*70)
            print("\n📊 You can now run the updated event simulator!")
            print("   python data_ingestion/producers/user_event_producer.py\n")
            
            return True
        else:
            print("\n❌ Migration failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'db' in locals():
            db.close()


def show_sample_queries():
    """Show sample analytical queries"""
    print("\n" + "="*70)
    print("📊 SAMPLE ANALYTICAL QUERIES")
    print("="*70)
    
    queries = [
        {
            "name": "Abandonment Rate by Persona",
            "sql": """
SELECT 
    persona,
    COUNT(*) as total_sessions,
    SUM(CASE WHEN is_cart_abandoned THEN 1 ELSE 0 END) as abandoned,
    ROUND(100.0 * SUM(CASE WHEN is_cart_abandoned THEN 1 ELSE 0 END) / COUNT(*), 2) as abandonment_rate
FROM user_sessions
WHERE persona IS NOT NULL
GROUP BY persona
ORDER BY abandonment_rate DESC;
            """
        },
        {
            "name": "Top Abandonment Reasons",
            "sql": """
SELECT * FROM v_abandonment_reasons
LIMIT 5;
            """
        },
        {
            "name": "Conversion Funnel (Today)",
            "sql": """
SELECT * FROM v_conversion_funnel
WHERE funnel_date = CURRENT_DATE;
            """
        },
        {
            "name": "High-Value Abandoned Carts",
            "sql": """
SELECT 
    session_id,
    user_id,
    cart_value,
    abandonment_reason,
    device_type,
    time_in_cart_seconds
FROM v_cart_abandonment_analysis
WHERE cart_value > 100
ORDER BY cart_value DESC
LIMIT 10;
            """
        }
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{i}. {query['name']}:")
        print("-" * 70)
        print(query['sql'].strip())
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    print("\n🚀 Starting migration process...")
    
    success = run_migration()
    
    if success:
        show_sample_queries()
        sys.exit(0)
    else:
        print("\n⚠️  Migration failed. Please check the errors above.")
        sys.exit(1)