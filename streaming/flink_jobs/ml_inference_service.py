import logging
import requests
from datetime import datetime, timezone
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

class MLInferenceService:
    def __init__(self, pg_conn, model_url: str = "http://localhost:8000/predict"):
        self.pg_conn = pg_conn
        self.model_url = model_url

    def call_ml_api(self, session_record: dict):
        """Call ML API and get abandonment prediction."""
        try:
            if session_record.get("cart_value", 0) <= 0:
                return None

            resp = requests.post(self.model_url, json=session_record, timeout=3)
            if resp.status_code != 200:
                logger.error(f"ML API returned {resp.status_code}")
                return None

            return resp.json()

        except Exception as exc:
            logger.error(f"ML API call failed: {exc}")
            return None

    def log_prediction(self, record: dict, result: dict, latency_ms: float):
        """Log prediction result into ml_predictions table."""
        if self.pg_conn is None:
            logger.error("Postgres connection is None, cannot log prediction")
            return

        try:
            cursor = self.pg_conn.cursor()
            query = """
                INSERT INTO ml_predictions (
                    session_id, user_id, prediction_timestamp,
                    abandonment_probability, predicted_abandoned,
                    risk_level, intervention_triggered,
                    intervention_type, model_version,
                    prediction_latency_ms
                )
                VALUES %s
                ON CONFLICT DO NOTHING
            """
            data = [(
                record.get("session_id"),
                record.get("user_id"),
                datetime.now(timezone.utc),
                result.get("abandonment_probability"),
                result.get("will_abandon", True),
                result.get("risk_level"),
                True if result.get("risk_level") in ["HIGH", "CRITICAL"] else False,
                result.get("recommended_intervention"),
                result.get("model_version", "random_forest_v1"),
                int(latency_ms)
            )]
            execute_values(cursor, query, data)
            self.pg_conn.commit()
            cursor.close()
            logger.info(f"🧠 Prediction logged: {record.get('session_id')} → {result.get('risk_level')} ({result.get('abandonment_probability')*100:.1f}%)")

        except Exception as exc:
            try:
                if self.pg_conn is not None:
                    self.pg_conn.rollback()
            except Exception as rollback_exc:
                logger.error(f"Rollback failed: {rollback_exc}")
            logger.error(f"Database insert failed: {exc}")
