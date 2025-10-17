"""
Database manager for PostgreSQL operations using SQLAlchemy.
Handles connections, schema setup, and CRUD operations.
"""

# Add these lines BEFORE other imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from config.config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manager for PostgreSQL database operations using SQLAlchemy"""
    
    def __init__(self):
        """Initialize database manager with connection pool"""
        self.engine: Optional[Engine] = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Create SQLAlchemy engine with connection pool"""
        try:
            # Build connection string with password (psycopg2 requires it in connection string)
            connection_string = (
                f"postgresql://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}"
                f"@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
            )
            
            self.engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Verify connections before using
                echo=False  # Set to True for SQL debug logging
            )
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("Database engine created successfully")
        except Exception as e:
            logger.error(f"Error creating database engine: {e}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool"""
        try:
            return self.engine.connect()
        except Exception as e:
            logger.error(f"Error getting connection: {e}")
            raise
    
    def execute_schema(self, schema_file: str) -> bool:
        """
        Execute SQL schema file.
        
        Args:
            schema_file: Path to SQL file
            
        Returns:
            True if successful
        """
        try:
            # Read SQL file
            schema_path = Path(schema_file)
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_file}")
            
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Execute using SQLAlchemy
            with self.engine.begin() as conn:
                # Split and execute each statement
                statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
                for statement in statements:
                    conn.execute(text(statement))
            
            logger.info(f"Schema executed successfully: {schema_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing schema: {e}")
            return False
    
    def execute_query(
        self, 
        query: str, 
        params: dict = None,
        fetch: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters as dict
            fetch: Whether to fetch results
            
        Returns:
            List of dictionaries for SELECT queries, None for others
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                
                if fetch:
                    # Convert to list of dicts
                    rows = result.fetchall()
                    if rows:
                        columns = result.keys()
                        return [dict(zip(columns, row)) for row in rows]
                    return []
                else:
                    conn.commit()
                    return None
                    
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return None
    
    def execute_many(
        self,
        query: str,
        params_list: List[dict]
    ) -> bool:
        """
        Execute query with multiple parameter sets (batch insert/update).
        
        Args:
            query: SQL query with named parameters
            params_list: List of parameter dictionaries
            
        Returns:
            True if successful
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(text(query), params_list)
            return True
        except Exception as e:
            logger.error(f"Error executing batch query: {e}")
            return False
    
    def close(self):
        """Dispose of the engine and close all connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine disposed")


if __name__ == "__main__":
    # Test database connection and schema setup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("🗄️  DATABASE SETUP TEST")
    print("="*60)
    
    try:
        # Initialize manager
        db = DatabaseManager()
        print("✓ Connected to PostgreSQL")
        
        # Execute schema
        schema_file = Path(__file__).parent / "schemas" / "create_tables.sql"
        success = db.execute_schema(str(schema_file))
        
        if success:
            print("✓ Schema created successfully")
        
        # Test query
        tables = db.execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        if tables:
            print(f"\n📋 Created tables ({len(tables)}):")
            for table in tables:
                print(f"  - {table['table_name']}")
        
        # Test a simple insert/select
        print("\n🧪 Testing insert/select operations...")
        
        # Insert test data
        db.execute_query("""
            INSERT INTO system_metrics (timestamp, metric_name, metric_value, metric_unit)
            VALUES (NOW(), 'test_metric', 42.0, 'count')
            ON CONFLICT DO NOTHING
        """, fetch=False)
        
        # Query it back
        metrics = db.execute_query("""
            SELECT * FROM system_metrics 
            WHERE metric_name = 'test_metric'
            LIMIT 1
        """)
        
        if metrics:
            print(f"✓ Insert/Select working: {metrics[0]['metric_name']} = {metrics[0]['metric_value']}")
        
        db.close()
        
        print("\n" + "="*60)
        print("✅ DATABASE SETUP COMPLETED")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
