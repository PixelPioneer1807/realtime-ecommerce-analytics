import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_PRODUCTS = os.getenv("KAFKA_TOPIC_PRODUCTS", "product-events")
    KAFKA_TOPIC_USER_EVENTS = os.getenv("KAFKA_TOPIC_USER_EVENTS", "user-events")
    KAFKA_TOPIC_WEATHER = os.getenv("KAFKA_TOPIC_WEATHER", "weather-data")
    KAFKA_TOPIC_FINANCE = os.getenv("KAFKA_TOPIC_FINANCE", "finance-data")
    
    # PostgreSQL Configuration
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "ecommerce_analytics")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres123")
    
    @property
    def POSTGRES_URL(self):
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis Configuration
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    
    # InfluxDB Configuration
    INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-token")
    INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "ecommerce")
    INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "analytics")
    
    # API Keys
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
    
    # FastAPI Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_RELOAD = os.getenv("API_RELOAD", "True").lower() == "true"
    
    # Streamlit Configuration
    STREAMLIT_SERVER_PORT = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
    STREAMLIT_SERVER_ADDRESS = os.getenv("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")
    
    # Paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    LOGS_DIR = BASE_DIR / "logs"
    MODELS_DIR = BASE_DIR / "ml-models" / "models"
    
    # Create directories if they don't exist
    LOGS_DIR.mkdir(exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Create global config instance
config = Config()
