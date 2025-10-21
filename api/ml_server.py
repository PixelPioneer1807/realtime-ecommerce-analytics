"""
Cart Abandonment Prediction API
Serves the trained Random Forest model (93.92% accuracy) for real-time predictions.

Endpoints:
- POST /predict: Get abandonment prediction for a session
- GET /health: Health check
- GET /stats: Model performance statistics

Author: PixelPioneer1807
Date: October 21, 2025
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
import joblib
import pandas as pd
from pathlib import Path
from typing import Optional
import logging
from datetime import datetime
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Cart Abandonment Prediction API",
    description="Real-time ML predictions using Random Forest (93.92% accuracy)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# MODEL LOADING
# ============================================

MODEL_PATH = Path(__file__).parent.parent / "ml_models" / "churn_prediction" / "trained_models" / "random_forest_v1.pkl"

try:
    model = joblib.load(MODEL_PATH)
    logger.info(f"✅ Model loaded successfully from {MODEL_PATH}")
    MODEL_LOADED = True
except Exception as e:
    logger.error(f"❌ Failed to load model: {e}")
    MODEL_LOADED = False
    model = None

# Track predictions
prediction_count = 0
high_risk_count = 0
app_start_time = time.time()

# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class SessionFeatures(BaseModel):
    """Input features for prediction"""
    model_config = ConfigDict(protected_namespaces=())
    
    session_id: str = Field(..., description="Unique session identifier")
    
    # Behavioral metrics
    page_views: int = Field(..., ge=0, description="Number of pages viewed")
    products_viewed: int = Field(..., ge=0, description="Number of products viewed")
    unique_products_viewed: int = Field(..., ge=0, description="Unique products viewed")
    searches: int = Field(..., ge=0, description="Number of searches")
    
    # Cart metrics
    cart_additions: int = Field(..., ge=0, description="Items added to cart")
    cart_removals: int = Field(..., ge=0, description="Items removed from cart")
    cart_value: float = Field(..., ge=0, description="Total cart value in USD")
    
    # Engagement metrics
    session_duration_seconds: int = Field(..., ge=0, description="Session duration")
    avg_time_per_page: float = Field(..., ge=0, description="Average time per page (seconds)")
    engagement_score: float = Field(..., ge=0, le=1, description="Engagement score (0-1)")
    
    # Engineered features
    cart_engagement: int = Field(..., description="Cart adds - removes")
    time_per_product: float = Field(..., ge=0, description="Time per product viewed")
    cart_to_checkout_rate: float = Field(..., ge=0, le=1, description="Checkout conversion rate")
    pages_per_minute: float = Field(..., ge=0, description="Page views per minute")
    unique_product_ratio: float = Field(..., ge=0, le=1, description="Unique/total products ratio")
    
    # Categorical features
    device_type: str = Field(..., description="Device: mobile, desktop, or tablet")
    browser: str = Field(..., description="Browser: chrome, firefox, safari, edge, opera")
    persona: str = Field(..., description="User persona: window_shopper, intent_buyer, cart_abandoner")
    
    # Binary features
    bounce: bool = Field(..., description="True if single page session")
    checkout_initiated: bool = Field(..., description="True if reached checkout")


class PredictionResponse(BaseModel):
    """Prediction output"""
    model_config = ConfigDict(protected_namespaces=())
    
    session_id: str
    abandonment_probability: float = Field(..., description="Probability of abandonment (0-1)")
    will_abandon: bool = Field(..., description="True if probability > 0.5")
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH, CRITICAL")
    confidence: str = Field(..., description="Model confidence level")
    recommended_intervention: str = Field(..., description="Suggested action")
    model_version: str = Field(default="random_forest_v1", description="Model identifier")
    prediction_time_ms: float = Field(..., description="Prediction latency in milliseconds")


class HealthResponse(BaseModel):
    """Health check response"""
    model_config = ConfigDict(protected_namespaces=())
    
    status: str
    model_loaded: bool
    model_version: str
    predictions_served: int
    high_risk_sessions: int


class StatsResponse(BaseModel):
    """API statistics"""
    model_config = ConfigDict(protected_namespaces=())
    
    total_predictions: int
    high_risk_count: int
    high_risk_percentage: float
    model_accuracy: str
    model_precision: str
    uptime_seconds: float


# ============================================
# HELPER FUNCTIONS
# ============================================

def encode_device(device: str) -> int:
    """Encode device type to integer"""
    mapping = {"desktop": 0, "mobile": 1, "tablet": 2}
    return mapping.get(device.lower(), 0)


def encode_browser(browser: str) -> int:
    """Encode browser to integer"""
    mapping = {"chrome": 0, "firefox": 1, "safari": 2, "edge": 3, "opera": 4}
    return mapping.get(browser.lower(), 0)


def encode_persona(persona: str) -> int:
    """Encode user persona to integer"""
    mapping = {"window_shopper": 0, "intent_buyer": 1, "cart_abandoner": 2}
    return mapping.get(persona.lower(), 0)


def get_risk_level(probability: float) -> tuple:
    """Determine risk level and intervention"""
    if probability >= 0.85:
        return ("CRITICAL", "Very High", "🚨 URGENT: Show 15% discount popup + free shipping immediately")
    elif probability >= 0.70:
        return ("HIGH", "High", "⚠️ Display exit-intent popup with 10% discount code")
    elif probability >= 0.50:
        return ("MEDIUM", "Moderate", "📧 Queue cart reminder email for 30 minutes")
    else:
        return ("LOW", "Low", "✅ Monitor session - no intervention needed")


# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
def root():
    """API root"""
    return {
        "service": "Cart Abandonment Prediction API",
        "status": "running" if MODEL_LOADED else "degraded",
        "model": "Random Forest v1",
        "accuracy": "93.92%",
        "precision": "98.28%",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint"""
    global prediction_count, high_risk_count
    
    return HealthResponse(
        status="healthy" if MODEL_LOADED else "unhealthy",
        model_loaded=MODEL_LOADED,
        model_version="random_forest_v1",
        predictions_served=prediction_count,
        high_risk_sessions=high_risk_count
    )


@app.get("/stats", response_model=StatsResponse)
def get_statistics():
    """Get API statistics"""
    global prediction_count, high_risk_count, app_start_time
    
    high_risk_pct = (high_risk_count / prediction_count * 100) if prediction_count > 0 else 0
    uptime = time.time() - app_start_time
    
    return StatsResponse(
        total_predictions=prediction_count,
        high_risk_count=high_risk_count,
        high_risk_percentage=round(high_risk_pct, 2),
        model_accuracy="93.92%",
        model_precision="98.28%",
        uptime_seconds=round(uptime, 2)
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict_abandonment(features: SessionFeatures, background_tasks: BackgroundTasks):
    """Main prediction endpoint"""
    global prediction_count, high_risk_count
    
    if not MODEL_LOADED:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    start_time = time.time()
    
    try:
        # Prepare features
        feature_dict = {
            'page_views': features.page_views,
            'products_viewed': features.products_viewed,
            'unique_products_viewed': features.unique_products_viewed,
            'searches': features.searches,
            'cart_additions': features.cart_additions,
            'cart_removals': features.cart_removals,
            'cart_value': features.cart_value,
            'session_duration_seconds': features.session_duration_seconds,
            'avg_time_per_page': features.avg_time_per_page,
            'engagement_score': features.engagement_score,
            'cart_engagement': features.cart_engagement,
            'time_per_product': features.time_per_product,
            'cart_to_checkout_rate': features.cart_to_checkout_rate,
            'pages_per_minute': features.pages_per_minute,
            'unique_product_ratio': features.unique_product_ratio,
            'device_type': encode_device(features.device_type),
            'browser': encode_browser(features.browser),
            'persona': encode_persona(features.persona),
            'bounce': int(features.bounce),
            'checkout_initiated': int(features.checkout_initiated)
        }
        
        X = pd.DataFrame([feature_dict])
        
        # Make prediction
        probability = float(model.predict_proba(X)[0][1])
        prediction = bool(probability > 0.5)
        
        # Determine risk level
        risk_level, confidence, intervention = get_risk_level(probability)
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Update counters
        prediction_count += 1
        if risk_level in ['HIGH', 'CRITICAL']:
            high_risk_count += 1
        
        logger.info(f"Prediction: {features.session_id} | Prob: {probability:.4f} | Risk: {risk_level}")
        
        return PredictionResponse(
            session_id=features.session_id,
            abandonment_probability=round(probability, 4),
            will_abandon=prediction,
            risk_level=risk_level,
            confidence=confidence,
            recommended_intervention=intervention,
            prediction_time_ms=round(latency_ms, 2)
        )
    
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# STARTUP
# ============================================

@app.on_event("startup")
async def startup_event():
    """Run on API startup"""
    logger.info("=" * 60)
    logger.info("🚀 CART ABANDONMENT PREDICTION API")
    logger.info("=" * 60)
    logger.info(f"Model: Random Forest v1")
    logger.info(f"Accuracy: 93.92%")
    logger.info(f"Precision: 98.28%")
    logger.info(f"Model loaded: {MODEL_LOADED}")
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 60)
    print("🚀 Starting Cart Abandonment Prediction API")
    print("=" * 60)
    print("\nEndpoints:")
    print("  • Health: http://localhost:8000/health")
    print("  • Predict: POST http://localhost:8000/predict")
    print("  • Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
