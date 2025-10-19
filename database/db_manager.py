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
import re
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
    
    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """
        Split SQL content into individual statements, handling complex cases.
        
        Args:
            sql_content: Full SQL file content
            
        Returns:
            List of SQL statements
        """
        # Remove SQL comments (-- style and /* */ style)
        sql_content = re.sub(r'--[^\n]*', '', sql_content)
        sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
        
        # Split by semicolon but be smart about it
        statements = []
        current_statement = []
        in_dollar_quote = False
        dollar_tag = None
        
        lines = sql_content.split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            # Check for dollar-quoted strings ($$)
            if '$$' in stripped:
                if not in_dollar_quote:
                    # Starting dollar quote
                    in_dollar_quote = True
                    # Extract the tag if any (e.g., $tag$ or just $$)
                    match = re.search(r'\$(\w*)\$', stripped)
                    if match:
                        dollar_tag = match.group(0)
                else:
                    # Check if this closes the dollar quote
                    if dollar_tag and dollar_tag in stripped:
                        in_dollar_quote = False
                        dollar_tag = None
                    elif '$$' in stripped and dollar_tag == '$$':
                        in_dollar_quote = False
                        dollar_tag = None
            
            current_statement.append(line)
            
            # If we hit a semicolon and not in dollar quote, it's end of statement
            if ';' in stripped and not in_dollar_quote:
                statement = '\n'.join(current_statement).strip()
                if statement and not statement.startswith('--'):
                    statements.append(statement)
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            statement = '\n'.join(current_statement).strip()
            if statement and not statement.startswith('--'):
                statements.append(statement)
        
        # Filter out empty statements
        return [s for s in statements if s and s.strip()]
    
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
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Split into individual statements
            statements = self._split_sql_statements(schema_sql)
            
            if not statements:
                logger.warning(f"No SQL statements found in {schema_file}")
                return True  # Not an error, just empty
            
            # Execute each statement
            with self.engine.begin() as conn:
                for i, statement in enumerate(statements, 1):
                    try:
                        conn.execute(text(statement))
                        logger.debug(f"Executed statement {i}/{len(statements)}")
                    except Exception as e:
                        logger.error(f"Error in statement {i}: {e}")
                        logger.error(f"Statement: {statement[:200]}...")
                        raise
            
            logger.info(f"Schema executed successfully: {schema_file} ({len(statements)} statements)")
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