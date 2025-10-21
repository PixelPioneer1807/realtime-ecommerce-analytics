"""
Database connector utility for the Streamlit dashboard.
Provides connection management and query methods for real-time data fetching.

ENHANCEMENTS:
- Dynamic prediction counts (not hardcoded)
- Business impact calculations
- Time-range filtering
- Intervention effectiveness tracking
"""

import logging
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import streamlit as st
from typing import Optional, Dict, List, Any
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.config import config

logger = logging.getLogger(__name__)

class DatabaseConnector:
    """Database connection and query utility for dashboard"""
    
    def __init__(self):
        self.connection_params = {
            'host': config.POSTGRES_HOST,
            'port': config.POSTGRES_PORT,
            'database': config.POSTGRES_DB,
            'user': config.POSTGRES_USER,
            'password': config.POSTGRES_PASSWORD
        }
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute query and return pandas DataFrame"""
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                return df
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return pd.DataFrame()
    
    def get_all_predictions_in_timerange(self, hours: int = 1) -> pd.DataFrame:
        """Get ALL predictions (not limited to 50) within time range"""
        query = """
        SELECT 
            p.prediction_id,
            p.session_id,
            p.prediction_timestamp,
            p.abandonment_probability,
            p.predicted_abandoned,
            p.risk_level,
            p.intervention_triggered,
            p.intervention_type,
            p.prediction_latency_ms,
            s.cart_value,
            s.page_views,
            s.cart_additions,
            s.device_type,
            s.persona,
            s.is_converted
        FROM ml_predictions p
        LEFT JOIN user_sessions s ON p.session_id = s.session_id
        WHERE p.prediction_timestamp >= NOW() - INTERVAL '%s hours'
        ORDER BY p.prediction_timestamp DESC
        """
        return self.execute_query(query, (hours,))
    
    def get_live_predictions(self, limit: int = 100) -> pd.DataFrame:
        """Get recent ML predictions with session details (for backwards compatibility)"""
        query = """
        SELECT 
            p.session_id,
            p.prediction_timestamp,
            p.abandonment_probability,
            p.predicted_abandoned,
            p.risk_level,
            p.intervention_triggered,
            p.intervention_type,
            p.prediction_latency_ms,
            s.cart_value,
            s.page_views,
            s.cart_additions,
            s.device_type,
            s.persona,
            s.is_converted
        FROM ml_predictions p
        LEFT JOIN user_sessions s ON p.session_id = s.session_id
        WHERE p.prediction_timestamp >= NOW() - INTERVAL '1 hour'
        ORDER BY p.prediction_timestamp DESC
        LIMIT %s
        """
        return self.execute_query(query, (limit,))
    
    def get_risk_distribution(self, hours: int = 1) -> pd.DataFrame:
        """Get risk level distribution for specified time range"""
        query = """
        SELECT 
            risk_level,
            COUNT(*) as count,
            ROUND(AVG(abandonment_probability), 4) as avg_probability
        FROM ml_predictions 
        WHERE prediction_timestamp >= NOW() - INTERVAL '%s hours'
        GROUP BY risk_level
        ORDER BY 
            CASE risk_level 
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
            END
        """
        return self.execute_query(query, (hours,))
    
    def get_hourly_predictions(self, hours: int = 24) -> pd.DataFrame:
        """Get predictions grouped by hour"""
        query = """
        SELECT 
            DATE_TRUNC('hour', prediction_timestamp) as hour,
            COUNT(*) as total_predictions,
            COUNT(CASE WHEN risk_level IN ('HIGH', 'CRITICAL') THEN 1 END) as high_risk_count,
            AVG(abandonment_probability) as avg_probability,
            COUNT(CASE WHEN intervention_triggered THEN 1 END) as interventions_triggered
        FROM ml_predictions 
        WHERE prediction_timestamp >= NOW() - INTERVAL '%s hours'
        GROUP BY DATE_TRUNC('hour', prediction_timestamp)
        ORDER BY hour ASC
        """
        return self.execute_query(query, (hours,))
    
    def get_session_metrics(self) -> Dict[str, Any]:
        """Get real-time session metrics (last hour)"""
        query = """
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(CASE WHEN is_converted THEN 1 END) as converted_sessions,
            COUNT(CASE WHEN cart_value > 0 AND NOT is_converted THEN 1 END) as abandoned_sessions,
            ROUND(AVG(cart_value), 2) as avg_cart_value,
            ROUND(AVG(session_duration_seconds), 0) as avg_duration,
            AVG(page_views) as avg_page_views
        FROM user_sessions
        WHERE updated_at >= NOW() - INTERVAL '1 hour'
        """
        df = self.execute_query(query)
        if not df.empty:
            return df.iloc[0].to_dict()
        return {}
    
    def get_intervention_effectiveness(self, hours: int = 24) -> pd.DataFrame:
        """Get intervention effectiveness metrics with conversion tracking"""
        query = """
        SELECT 
            p.risk_level,
            p.intervention_type,
            COUNT(*) as total_interventions,
            COUNT(CASE WHEN s.is_converted THEN 1 END) as successful_conversions,
            ROUND(
                COUNT(CASE WHEN s.is_converted THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 
                2
            ) as conversion_rate
        FROM ml_predictions p
        LEFT JOIN user_sessions s ON p.session_id = s.session_id
        WHERE p.intervention_triggered = true
        AND p.prediction_timestamp >= NOW() - INTERVAL '%s hours'
        GROUP BY p.risk_level, p.intervention_type
        HAVING COUNT(*) >= 3
        ORDER BY conversion_rate DESC
        """
        return self.execute_query(query, (hours,))
    
    def get_model_performance_metrics(self, hours: int = 1) -> Dict[str, Any]:
        """Get model performance statistics for specified time range"""
        query = """
        SELECT 
            COUNT(*) as total_predictions,
            AVG(prediction_latency_ms) as avg_latency_ms,
            MIN(prediction_latency_ms) as min_latency_ms,
            MAX(prediction_latency_ms) as max_latency_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY prediction_latency_ms) as p95_latency_ms
        FROM ml_predictions
        WHERE prediction_timestamp >= NOW() - INTERVAL '%s hours'
        """
        df = self.execute_query(query, (hours,))
        if not df.empty:
            return df.iloc[0].to_dict()
        return {}
    
    def get_business_impact_metrics(self, hours: int = 1) -> Dict[str, Any]:
        """Calculate business impact of ML predictions"""
        query = """
        SELECT 
            COUNT(CASE WHEN p.risk_level IN ('HIGH', 'CRITICAL') THEN 1 END) as high_risk_predictions,
            COUNT(CASE WHEN p.intervention_triggered THEN 1 END) as interventions_triggered,
            SUM(CASE WHEN p.risk_level IN ('HIGH', 'CRITICAL') THEN s.cart_value ELSE 0 END) as total_at_risk_value,
            AVG(CASE WHEN p.risk_level IN ('HIGH', 'CRITICAL') THEN s.cart_value END) as avg_at_risk_cart_value,
            COUNT(CASE WHEN p.intervention_triggered AND s.is_converted THEN 1 END) as recovered_carts,
            SUM(CASE WHEN p.intervention_triggered AND s.is_converted THEN s.purchase_value ELSE 0 END) as recovered_revenue
        FROM ml_predictions p
        LEFT JOIN user_sessions s ON p.session_id = s.session_id
        WHERE p.prediction_timestamp >= NOW() - INTERVAL '%s hours'
        """
        df = self.execute_query(query, (hours,))
        if not df.empty:
            return df.iloc[0].to_dict()
        return {}
    
    def get_persona_performance(self, hours: int = 1) -> pd.DataFrame:
        """Get performance metrics by user persona for specified time range"""
        query = """
        SELECT 
            s.persona,
            COUNT(*) as sessions,
            COUNT(CASE WHEN s.is_converted THEN 1 END) as conversions,
            ROUND(AVG(p.abandonment_probability), 4) as avg_abandon_prob,
            COUNT(CASE WHEN p.risk_level IN ('HIGH', 'CRITICAL') THEN 1 END) as high_risk_count,
            ROUND(AVG(s.cart_value), 2) as avg_cart_value
        FROM user_sessions s
        LEFT JOIN ml_predictions p ON s.session_id = p.session_id
        WHERE s.updated_at >= NOW() - INTERVAL '%s hours'
        AND s.persona IS NOT NULL
        AND p.prediction_timestamp IS NOT NULL
        GROUP BY s.persona
        ORDER BY sessions DESC
        """
        return self.execute_query(query, (hours,))
    
    def get_abandonment_by_device(self, hours: int = 24) -> pd.DataFrame:
        """Get abandonment rates by device type"""
        query = """
        SELECT 
            s.device_type,
            COUNT(*) as total_sessions,
            COUNT(CASE WHEN p.risk_level IN ('HIGH', 'CRITICAL') THEN 1 END) as high_risk_sessions,
            ROUND(
                COUNT(CASE WHEN p.risk_level IN ('HIGH', 'CRITICAL') THEN 1 END) * 100.0 / COUNT(*),
                2
            ) as high_risk_rate,
            AVG(s.cart_value) as avg_cart_value
        FROM user_sessions s
        LEFT JOIN ml_predictions p ON s.session_id = p.session_id
        WHERE s.updated_at >= NOW() - INTERVAL '%s hours'
        AND p.prediction_timestamp IS NOT NULL
        GROUP BY s.device_type
        ORDER BY high_risk_rate DESC
        """
        return self.execute_query(query, (hours,))
    
    def get_conversion_funnel(self, hours: int = 24) -> pd.DataFrame:
        """Get conversion funnel metrics"""
        query = """
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(CASE WHEN page_views > 0 THEN 1 END) as with_pageviews,
            COUNT(CASE WHEN products_viewed > 0 THEN 1 END) as viewed_products,
            COUNT(CASE WHEN cart_additions > 0 THEN 1 END) as added_to_cart,
            COUNT(CASE WHEN checkout_initiated THEN 1 END) as initiated_checkout,
            COUNT(CASE WHEN is_converted THEN 1 END) as purchased,
            ROUND(COUNT(CASE WHEN is_converted THEN 1 END) * 100.0 / 
                  NULLIF(COUNT(CASE WHEN cart_additions > 0 THEN 1 END), 0), 2) as cart_to_purchase_rate
        FROM user_sessions
        WHERE updated_at >= NOW() - INTERVAL '%s hours'
        """
        df = self.execute_query(query, (hours,))
        if not df.empty:
            return df.iloc[0].to_dict()
        return {}
    
    def get_model_accuracy_metrics(self) -> Dict[str, Any]:
        """Get model accuracy based on actual outcomes (if available)"""
        query = """
        SELECT 
            COUNT(*) as total_predictions,
            COUNT(CASE WHEN was_prediction_correct THEN 1 END) as correct_predictions,
            ROUND(
                COUNT(CASE WHEN was_prediction_correct THEN 1 END) * 100.0 / 
                NULLIF(COUNT(CASE WHEN was_prediction_correct IS NOT NULL THEN 1 END), 0),
                2
            ) as accuracy_rate,
            COUNT(CASE WHEN predicted_abandoned = true AND was_prediction_correct = true THEN 1 END) as true_positives,
            COUNT(CASE WHEN predicted_abandoned = true AND was_prediction_correct = false THEN 1 END) as false_positives,
            COUNT(CASE WHEN predicted_abandoned = false AND was_prediction_correct = false THEN 1 END) as false_negatives
        FROM ml_predictions
        WHERE was_prediction_correct IS NOT NULL
        AND prediction_timestamp >= NOW() - INTERVAL '24 hours'
        """
        df = self.execute_query(query)
        if not df.empty:
            metrics = df.iloc[0].to_dict()
            # Calculate precision and recall
            tp = metrics.get('true_positives', 0)
            fp = metrics.get('false_positives', 0)
            fn = metrics.get('false_negatives', 0)
            
            metrics['precision'] = round(tp * 100.0 / (tp + fp), 2) if (tp + fp) > 0 else 0
            metrics['recall'] = round(tp * 100.0 / (tp + fn), 2) if (tp + fn) > 0 else 0
            
            return metrics
        return {}

# Global instance for dashboard use
@st.cache_resource
def get_db_connector():
    """Get cached database connector instance"""
    return DatabaseConnector()