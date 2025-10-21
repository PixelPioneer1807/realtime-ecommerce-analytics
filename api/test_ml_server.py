"""
Test script for ML API server.
Tests prediction endpoints with realistic session data.

Usage:
    python api/test_ml_server.py
"""

import requests
import json
import time

API_URL = "http://localhost:8000"

# Sample test sessions (realistic patterns from your training data)
TEST_SESSIONS = [
    {
        "name": "High-Risk Cart Abandoner",
        "data": {
            "session_id": "test_high_risk_001",
            "page_views": 12,
            "products_viewed": 8,
            "unique_products_viewed": 6,
            "searches": 3,
            "cart_additions": 4,
            "cart_removals": 2,
            "cart_value": 125.50,
            "session_duration_seconds": 890,
            "avg_time_per_page": 74.17,
            "engagement_score": 0.65,
            "cart_engagement": 2,
            "time_per_product": 111.25,
            "cart_to_checkout_rate": 0.25,
            "pages_per_minute": 0.81,
            "unique_product_ratio": 0.75,
            "device_type": "mobile",
            "browser": "chrome",
            "persona": "cart_abandoner",
            "bounce": False,
            "checkout_initiated": False
        },
        "expected": "HIGH or CRITICAL risk"
    },
    {
        "name": "Intent Buyer (Low Risk)",
        "data": {
            "session_id": "test_low_risk_002",
            "page_views": 6,
            "products_viewed": 4,
            "unique_products_viewed": 3,
            "searches": 1,
            "cart_additions": 2,
            "cart_removals": 0,
            "cart_value": 65.00,
            "session_duration_seconds": 320,
            "avg_time_per_page": 53.33,
            "engagement_score": 0.85,
            "cart_engagement": 2,
            "time_per_product": 80.0,
            "cart_to_checkout_rate": 1.0,
            "pages_per_minute": 1.13,
            "unique_product_ratio": 0.75,
            "device_type": "desktop",
            "browser": "firefox",
            "persona": "intent_buyer",
            "bounce": False,
            "checkout_initiated": True
        },
        "expected": "LOW or MEDIUM risk"
    },
    {
        "name": "Window Shopper (Medium Risk)",
        "data": {
            "session_id": "test_medium_risk_003",
            "page_views": 15,
            "products_viewed": 10,
            "unique_products_viewed": 8,
            "searches": 4,
            "cart_additions": 1,
            "cart_removals": 0,
            "cart_value": 35.99,
            "session_duration_seconds": 1200,
            "avg_time_per_page": 80.0,
            "engagement_score": 0.45,
            "cart_engagement": 1,
            "time_per_product": 120.0,
            "cart_to_checkout_rate": 0.0,
            "pages_per_minute": 0.75,
            "unique_product_ratio": 0.8,
            "device_type": "tablet",
            "browser": "safari",
            "persona": "window_shopper",
            "bounce": False,
            "checkout_initiated": False
        },
        "expected": "MEDIUM risk"
    }
]


def print_banner(text: str):
    """Print formatted banner"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def test_health():
    """Test health endpoint"""
    print("\n🏥 Testing Health Endpoint...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed")
            print(f"   Status: {data['status']}")
            print(f"   Model loaded: {data['model_loaded']}")
            print(f"   Predictions served: {data['predictions_served']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_prediction(session):
    """Test prediction endpoint"""
    print(f"\n🎯 Testing: {session['name']}")
    print(f"   Session ID: {session['data']['session_id']}")
    print(f"   Cart Value: ${session['data']['cart_value']:.2f}")
    print(f"   Persona: {session['data']['persona']}")
    print(f"   Expected: {session['expected']}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_URL}/predict",
            json=session['data'],
            timeout=5
        )
        latency = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n   📊 Results:")
            print(f"      Probability: {result['abandonment_probability']:.4f} ({result['abandonment_probability']*100:.2f}%)")
            print(f"      Will Abandon: {result['will_abandon']}")
            print(f"      Risk Level: {result['risk_level']}")
            print(f"      Confidence: {result['confidence']}")
            print(f"      Latency: {result['prediction_time_ms']:.2f}ms (total: {latency:.2f}ms)")
            print(f"\n   💡 Intervention:")
            print(f"      {result['recommended_intervention']}")
            
            return True
        else:
            print(f"   ❌ Prediction failed: {response.status_code}")
            print(f"      {response.text}")
            return False
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_stats():
    """Test statistics endpoint"""
    print("\n📈 Testing Statistics Endpoint...")
    try:
        response = requests.get(f"{API_URL}/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Statistics retrieved")
            print(f"   Total predictions: {data['total_predictions']}")
            print(f"   High-risk sessions: {data['high_risk_count']} ({data['high_risk_percentage']:.1f}%)")
            print(f"   Model accuracy: {data['model_accuracy']}")
            print(f"   Uptime: {data['uptime_seconds']:.1f}s")
            return True
        else:
            print(f"❌ Stats failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return False


def main():
    """Run all tests"""
    print_banner("🧪 ML API TEST SUITE")
    
    print("\nAPI URL:", API_URL)
    print("Tests: 3 sessions + health + stats")
    
    # Wait for API
    print("\n⏳ Waiting for API to be ready...")
    max_retries = 5
    for i in range(max_retries):
        try:
            response = requests.get(f"{API_URL}/health", timeout=2)
            if response.status_code == 200:
                print("✅ API is ready!")
                break
        except:
            if i < max_retries - 1:
                print(f"   Retry {i+1}/{max_retries}...")
                time.sleep(2)
            else:
                print("\n❌ API not responding. Start it first:")
                print("   python api/ml_server.py")
                return
    
    # Run tests
    results = []
    results.append(("Health Check", test_health()))
    
    for session in TEST_SESSIONS:
        results.append((session['name'], test_prediction(session)))
    
    results.append(("Statistics", test_stats()))
    
    # Summary
    print_banner("📋 TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed\n")
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
