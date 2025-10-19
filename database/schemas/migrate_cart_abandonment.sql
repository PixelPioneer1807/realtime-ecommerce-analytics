-- Migration Script: Add Cart Abandonment Features
-- Safe to run multiple times (uses IF NOT EXISTS)
-- Run this BEFORE starting the new event simulator

-- ============================================================================
-- STEP 1: Add new columns to user_sessions table
-- ============================================================================

-- Cart abandonment tracking
ALTER TABLE user_sessions 
ADD COLUMN IF NOT EXISTS is_cart_abandoned BOOLEAN DEFAULT FALSE;

ALTER TABLE user_sessions 
ADD COLUMN IF NOT EXISTS abandonment_reason VARCHAR(100);

ALTER TABLE user_sessions 
ADD COLUMN IF NOT EXISTS time_in_cart_seconds INTEGER DEFAULT 0;

ALTER TABLE user_sessions 
ADD COLUMN IF NOT EXISTS checkout_initiated BOOLEAN DEFAULT FALSE;

-- User persona tracking
ALTER TABLE user_sessions 
ADD COLUMN IF NOT EXISTS persona VARCHAR(50);

-- ============================================================================
-- STEP 2: Add indexes for new columns
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_user_sessions_abandoned 
ON user_sessions(is_cart_abandoned);

CREATE INDEX IF NOT EXISTS idx_user_sessions_persona 
ON user_sessions(persona);

CREATE INDEX IF NOT EXISTS idx_user_sessions_abandonment_reason 
ON user_sessions(abandonment_reason);

-- ============================================================================
-- STEP 3: Add new columns to cart_abandonments table
-- ============================================================================

ALTER TABLE cart_abandonments 
ADD COLUMN IF NOT EXISTS abandonment_reason VARCHAR(100);

ALTER TABLE cart_abandonments 
ADD COLUMN IF NOT EXISTS time_in_cart_seconds INTEGER DEFAULT 0;

ALTER TABLE cart_abandonments 
ADD COLUMN IF NOT EXISTS device_type VARCHAR(20);

ALTER TABLE cart_abandonments 
ADD COLUMN IF NOT EXISTS checkout_initiated BOOLEAN DEFAULT FALSE;

ALTER TABLE cart_abandonments 
ADD COLUMN IF NOT EXISTS persona VARCHAR(50);

-- ============================================================================
-- STEP 4: Add indexes for cart_abandonments
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_cart_abandonments_reason 
ON cart_abandonments(abandonment_reason);

CREATE INDEX IF NOT EXISTS idx_cart_abandonments_device 
ON cart_abandonments(device_type);

CREATE INDEX IF NOT EXISTS idx_cart_abandonments_persona 
ON cart_abandonments(persona);

-- ============================================================================
-- STEP 5: Create analytical views
-- ============================================================================

-- Cart Abandonment Analysis View
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

-- Conversion Funnel View
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

-- Abandonment Reasons Summary View
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

-- ============================================================================
-- STEP 6: Migration completed
-- ============================================================================
-- New columns added:
--   - is_cart_abandoned
--   - abandonment_reason
--   - time_in_cart_seconds
--   - checkout_initiated
--   - persona
--
-- Views created:
--   - v_cart_abandonment_analysis
--   - v_conversion_funnel
--   - v_abandonment_reasons