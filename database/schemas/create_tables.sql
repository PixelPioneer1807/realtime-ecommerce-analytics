-- Real-Time E-commerce Analytics Database Schema
-- This database stores processed streaming data for ML and dashboards

-- ============================================================================
-- USER SESSION METRICS
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    last_activity TIMESTAMP NOT NULL,
    device_type VARCHAR(20),
    browser VARCHAR(50),
    
    -- Behavioral metrics
    page_views INTEGER DEFAULT 0,
    products_viewed INTEGER DEFAULT 0,
    unique_products_viewed INTEGER DEFAULT 0,
    searches INTEGER DEFAULT 0,
    
    -- Cart metrics  
    cart_additions INTEGER DEFAULT 0,
    cart_removals INTEGER DEFAULT 0,
    cart_value DECIMAL(10, 2) DEFAULT 0.00,
    
    -- Conversion metrics
    is_converted BOOLEAN DEFAULT FALSE,
    purchase_value DECIMAL(10, 2) DEFAULT 0.00,
    
    -- NEW: Cart abandonment tracking
    is_cart_abandoned BOOLEAN DEFAULT FALSE,
    abandonment_reason VARCHAR(100),
    time_in_cart_seconds INTEGER DEFAULT 0,
    checkout_initiated BOOLEAN DEFAULT FALSE,
    
    -- NEW: User persona tracking
    persona VARCHAR(50),
    
    -- Session quality indicators
    session_duration_seconds INTEGER DEFAULT 0,
    avg_time_per_page DECIMAL(10, 2) DEFAULT 0.00,
    bounce BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_start_time ON user_sessions(start_time);
CREATE INDEX idx_user_sessions_converted ON user_sessions(is_converted);
-- NEW: Indexes for cart abandonment analysis
CREATE INDEX idx_user_sessions_abandoned ON user_sessions(is_cart_abandoned);
CREATE INDEX idx_user_sessions_persona ON user_sessions(persona);
CREATE INDEX idx_user_sessions_abandonment_reason ON user_sessions(abandonment_reason);

-- ============================================================================
-- USER PROFILES (Aggregated behavior)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INTEGER PRIMARY KEY,
    
    -- Lifetime metrics
    total_sessions INTEGER DEFAULT 0,
    total_page_views INTEGER DEFAULT 0,
    total_products_viewed INTEGER DEFAULT 0,
    
    -- Purchase behavior
    total_purchases INTEGER DEFAULT 0,
    total_revenue DECIMAL(10, 2) DEFAULT 0.00,
    avg_order_value DECIMAL(10, 2) DEFAULT 0.00,
    
    -- Engagement metrics
    avg_session_duration DECIMAL(10, 2) DEFAULT 0.00,
    total_time_on_site INTEGER DEFAULT 0,
    
    -- Cart behavior
    total_cart_additions INTEGER DEFAULT 0,
    total_cart_abandonments INTEGER DEFAULT 0,
    cart_abandonment_rate DECIMAL(5, 2) DEFAULT 0.00,
    
    -- Recency, Frequency, Monetary (RFM) for ML
    days_since_last_visit INTEGER,
    days_since_last_purchase INTEGER,
    purchase_frequency DECIMAL(10, 2) DEFAULT 0.00,
    
    -- Preferences
    favorite_category VARCHAR(50),
    device_preference VARCHAR(20),
    
    -- Risk indicators
    churn_risk_score DECIMAL(5, 2) DEFAULT 0.00,
    
    -- Timestamps
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_profiles_churn_risk ON user_profiles(churn_risk_score);
CREATE INDEX idx_user_profiles_last_seen ON user_profiles(last_seen);

-- ============================================================================
-- PRODUCT METRICS (Real-time popularity)
-- ============================================================================
CREATE TABLE IF NOT EXISTS product_metrics (
    product_id INTEGER PRIMARY KEY,
    title VARCHAR(255),
    category VARCHAR(50),
    price DECIMAL(10, 2),
    
    -- View metrics
    total_views INTEGER DEFAULT 0,
    views_last_hour INTEGER DEFAULT 0,
    views_last_day INTEGER DEFAULT 0,
    
    -- Cart metrics
    total_cart_additions INTEGER DEFAULT 0,
    cart_additions_last_hour INTEGER DEFAULT 0,
    
    -- Purchase metrics
    total_purchases INTEGER DEFAULT 0,
    purchases_last_hour INTEGER DEFAULT 0,
    total_revenue DECIMAL(10, 2) DEFAULT 0.00,
    
    -- Conversion funnel
    view_to_cart_rate DECIMAL(5, 2) DEFAULT 0.00,
    cart_to_purchase_rate DECIMAL(5, 2) DEFAULT 0.00,
    overall_conversion_rate DECIMAL(5, 2) DEFAULT 0.00,
    
    -- Velocity indicators (for trending)
    trending_score DECIMAL(10, 2) DEFAULT 0.00,
    
    -- Stock (simulated)
    stock_quantity INTEGER DEFAULT 100,
    
    -- Timestamps
    last_viewed TIMESTAMP,
    last_purchased TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_product_metrics_category ON product_metrics(category);
CREATE INDEX idx_product_metrics_trending ON product_metrics(trending_score DESC);
CREATE INDEX idx_product_metrics_conversion ON product_metrics(overall_conversion_rate DESC);

-- ============================================================================
-- CART ABANDONMENT EVENTS (For churn prediction)
-- ENHANCED: Now captures abandonment reasons and context
-- ============================================================================
CREATE TABLE IF NOT EXISTS cart_abandonments (
    abandonment_id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    user_id INTEGER NOT NULL,
    
    -- Cart details
    cart_value DECIMAL(10, 2) NOT NULL,
    item_count INTEGER NOT NULL,
    
    -- Abandonment context
    abandonment_time TIMESTAMP NOT NULL,
    session_duration INTEGER NOT NULL,
    pages_viewed INTEGER NOT NULL,
    
    -- NEW: Enhanced abandonment tracking
    abandonment_reason VARCHAR(100),
    time_in_cart_seconds INTEGER DEFAULT 0,
    device_type VARCHAR(20),
    checkout_initiated BOOLEAN DEFAULT FALSE,
    persona VARCHAR(50),
    
    -- Predicted by ML
    churn_probability DECIMAL(5, 2),
    intervention_triggered BOOLEAN DEFAULT FALSE,
    intervention_type VARCHAR(50),
    
    -- Recovery tracking
    recovered BOOLEAN DEFAULT FALSE,
    recovery_time TIMESTAMP,
    recovery_value DECIMAL(10, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cart_abandonments_user ON cart_abandonments(user_id);
CREATE INDEX idx_cart_abandonments_time ON cart_abandonments(abandonment_time);
CREATE INDEX idx_cart_abandonments_recovered ON cart_abandonments(recovered);
-- NEW: Indexes for abandonment analysis
CREATE INDEX idx_cart_abandonments_reason ON cart_abandonments(abandonment_reason);
CREATE INDEX idx_cart_abandonments_device ON cart_abandonments(device_type);
CREATE INDEX idx_cart_abandonments_persona ON cart_abandonments(persona);

-- ============================================================================
-- REAL-TIME EVENTS LOG (Recent events for dashboard)
-- ============================================================================
CREATE TABLE IF NOT EXISTS recent_events (
    event_id VARCHAR(50) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(50) NOT NULL,
    
    -- Event details
    product_id INTEGER,
    category VARCHAR(50),
    event_value DECIMAL(10, 2),
    
    -- Context
    device_type VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Partition by day for efficient cleanup (optional optimization)
CREATE INDEX idx_recent_events_timestamp ON recent_events(timestamp DESC);
CREATE INDEX idx_recent_events_type ON recent_events(event_type);

-- Auto-cleanup old events (keep last 7 days)
-- This would be run by a scheduled job
-- DELETE FROM recent_events WHERE timestamp < NOW() - INTERVAL '7 days';

-- ============================================================================
-- CATEGORY PERFORMANCE (For demand forecasting)
-- ============================================================================
CREATE TABLE IF NOT EXISTS category_metrics (
    category VARCHAR(50) PRIMARY KEY,
    
    -- Current metrics
    total_views INTEGER DEFAULT 0,
    total_purchases INTEGER DEFAULT 0,
    total_revenue DECIMAL(10, 2) DEFAULT 0.00,
    
    -- Hourly metrics (for short-term forecasting)
    views_last_hour INTEGER DEFAULT 0,
    purchases_last_hour INTEGER DEFAULT 0,
    revenue_last_hour DECIMAL(10, 2) DEFAULT 0.00,
    
    -- Conversion
    conversion_rate DECIMAL(5, 2) DEFAULT 0.00,
    avg_order_value DECIMAL(10, 2) DEFAULT 0.00,
    
    -- Trending
    momentum_score DECIMAL(10, 2) DEFAULT 0.00,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SYSTEM METRICS (For monitoring)
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_metrics (
    metric_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10, 2) NOT NULL,
    metric_unit VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_metrics_timestamp ON system_metrics(timestamp DESC);
CREATE INDEX idx_system_metrics_name ON system_metrics(metric_name);

-- ============================================================================
-- NEW: CART ABANDONMENT ANALYTICS VIEW (For easy querying)
-- ============================================================================
CREATE OR REPLACE VIEW v_cart_abandonment_analysis AS
SELECT 
    -- Time dimensions
    DATE(s.start_time) as abandonment_date,
    EXTRACT(HOUR FROM s.start_time) as abandonment_hour,
    EXTRACT(DOW FROM s.start_time) as day_of_week,
    
    -- Session details
    s.session_id,
    s.user_id,
    s.persona,
    s.device_type,
    
    -- Cart metrics
    s.cart_value,
    s.cart_additions as items_in_cart,
    s.abandonment_reason,
    s.time_in_cart_seconds,
    s.checkout_initiated,
    
    -- Session context
    s.page_views,
    s.session_duration_seconds,
    s.products_viewed,
    
    -- Timestamps
    s.start_time,
    s.last_activity
    
FROM user_sessions s
WHERE s.is_cart_abandoned = TRUE
ORDER BY s.start_time DESC;

-- ============================================================================
-- NEW: CONVERSION FUNNEL VIEW
-- ============================================================================
CREATE OR REPLACE VIEW v_conversion_funnel AS
SELECT 
    DATE(start_time) as funnel_date,
    persona,
    device_type,
    
    -- Funnel stages
    COUNT(*) as total_sessions,
    SUM(CASE WHEN page_views > 0 THEN 1 ELSE 0 END) as browsing_sessions,
    SUM(CASE WHEN products_viewed > 0 THEN 1 ELSE 0 END) as product_viewed_sessions,
    SUM(CASE WHEN cart_additions > 0 THEN 1 ELSE 0 END) as cart_active_sessions,
    SUM(CASE WHEN checkout_initiated THEN 1 ELSE 0 END) as checkout_sessions,
    SUM(CASE WHEN is_converted THEN 1 ELSE 0 END) as purchased_sessions,
    
    -- Abandonment
    SUM(CASE WHEN is_cart_abandoned THEN 1 ELSE 0 END) as abandoned_sessions,
    
    -- Values
    SUM(cart_value) as total_cart_value,
    SUM(purchase_value) as total_purchase_value,
    AVG(cart_value) as avg_cart_value,
    AVG(purchase_value) as avg_purchase_value,
    
    -- Rates
    ROUND(
        100.0 * SUM(CASE WHEN is_converted THEN 1 ELSE 0 END) / 
        NULLIF(SUM(CASE WHEN cart_additions > 0 THEN 1 ELSE 0 END), 0), 
        2
    ) as conversion_rate,
    ROUND(
        100.0 * SUM(CASE WHEN is_cart_abandoned THEN 1 ELSE 0 END) / 
        NULLIF(SUM(CASE WHEN cart_additions > 0 THEN 1 ELSE 0 END), 0), 
        2
    ) as abandonment_rate

FROM user_sessions
GROUP BY DATE(start_time), persona, device_type
ORDER BY funnel_date DESC, persona;

-- ============================================================================
-- NEW: ABANDONMENT REASONS SUMMARY VIEW
-- ============================================================================
CREATE OR REPLACE VIEW v_abandonment_reasons AS
SELECT 
    abandonment_reason,
    COUNT(*) as total_abandonments,
    AVG(cart_value) as avg_cart_value,
    SUM(cart_value) as total_lost_value,
    AVG(time_in_cart_seconds) as avg_time_in_cart,
    AVG(page_views) as avg_page_views,
    
    -- By device
    SUM(CASE WHEN device_type = 'mobile' THEN 1 ELSE 0 END) as mobile_count,
    SUM(CASE WHEN device_type = 'desktop' THEN 1 ELSE 0 END) as desktop_count,
    SUM(CASE WHEN device_type = 'tablet' THEN 1 ELSE 0 END) as tablet_count,
    
    -- By persona
    SUM(CASE WHEN persona = 'window_shopper' THEN 1 ELSE 0 END) as window_shopper_count,
    SUM(CASE WHEN persona = 'intent_buyer' THEN 1 ELSE 0 END) as intent_buyer_count,
    SUM(CASE WHEN persona = 'cart_abandoner' THEN 1 ELSE 0 END) as cart_abandoner_count

FROM user_sessions
WHERE is_cart_abandoned = TRUE
GROUP BY abandonment_reason
ORDER BY total_abandonments DESC;