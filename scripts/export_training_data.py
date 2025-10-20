# scripts/export_training_data.py

"""
Export user_sessions data to CSV for ML training.
Saves to ml-models/churn_prediction/data/training_data.csv
"""

import psycopg2
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import config

def export_to_csv():
    """Export user_sessions table to CSV"""
    
    print("\n" + "="*60)
    print("📤 EXPORTING TRAINING DATA TO CSV")
    print("="*60)
    
    try:
        # Connect to database
        print("\n🔗 Connecting to database...")
        conn = psycopg2.connect(
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            database=config.POSTGRES_DB,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD
        )
        
        # Query all sessions
        print("📊 Loading sessions from database...")
        query = """
            SELECT 
                session_id,
                user_id,
                start_time,
                end_time,
                last_activity,
                device_type,
                browser,
                page_views,
                products_viewed,
                unique_products_viewed,
                searches,
                cart_additions,
                cart_removals,
                cart_value,
                is_converted,
                purchase_value,
                is_cart_abandoned,
                abandonment_reason,
                time_in_cart_seconds,
                checkout_initiated,
                persona,
                session_duration_seconds,
                avg_time_per_page,
                bounce,
                created_at,
                updated_at
            FROM user_sessions
            ORDER BY start_time
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        # FIX: Calculate actual abandonment (cart but no purchase)
        df['abandoned'] = (df['cart_value'] > 0) & (~df['is_converted'])
        
        # Print statistics
        print(f"\n✅ Loaded {len(df):,} sessions")
        print(f"\n📈 Dataset Statistics:")
        print(f"  Total Sessions: {len(df):,}")
        print(f"  Purchased: {df['is_converted'].sum():,} ({df['is_converted'].mean()*100:.1f}%)")
        print(f"  Abandoned (cart > 0, not purchased): {df['abandoned'].sum():,} ({df['abandoned'].mean()*100:.1f}%)")
        print(f"  With Cart: {(df['cart_value'] > 0).sum():,}")
        print(f"  Just Browsing: {((df['cart_value'] == 0) & (~df['is_converted'])).sum():,}")
        
        # Breakdown by persona
        print(f"\n👥 By Persona:")
        persona_stats = df.groupby('persona').agg({
            'session_id': 'count',
            'is_converted': 'sum',
            'abandoned': 'sum'
        }).rename(columns={'session_id': 'total'})
        print(persona_stats.to_string())
        
        # Create output directory
        output_dir = project_root / "ml-models" / "churn_prediction" / "data"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"training_data_{timestamp}.csv"
        
        # Save to CSV
        print(f"\n💾 Saving to: {output_file}")
        df.to_csv(output_file, index=False)
        
        # Also save as latest
        latest_file = output_dir / "training_data_latest.csv"
        df.to_csv(latest_file, index=False)
        
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        
        print(f"✅ Export complete!")
        print(f"  File size: {file_size_mb:.2f} MB")
        print(f"  Location: {output_file}")
        print(f"  Also saved as: {latest_file}")
        
        # Show preview
        print(f"\n📋 Data Preview (first 5 rows):")
        preview_cols = ['session_id', 'persona', 'device_type', 'page_views', 
                       'cart_value', 'is_converted', 'abandoned', 'session_duration_seconds']
        print(df[preview_cols].head().to_string(index=False))
        
        # Show distribution
        print(f"\n📊 Target Distribution:")
        print(f"  Purchased: {df['is_converted'].sum():,} ({df['is_converted'].mean()*100:.1f}%)")
        print(f"  Abandoned: {df['abandoned'].sum():,} ({df['abandoned'].mean()*100:.1f}%)")
        print(f"  Browsing: {((~df['is_converted']) & (~df['abandoned'])).sum():,} ({((~df['is_converted']) & (~df['abandoned'])).mean()*100:.1f}%)")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    export_to_csv()
