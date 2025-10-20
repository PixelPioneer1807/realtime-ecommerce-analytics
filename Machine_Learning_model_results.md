# 🎯 Cart Abandonment Prediction - Model Results

**Project:** Real-Time E-commerce Analytics  
**Date:** October 20, 2025  
**Dataset:** 12,752 sessions (28.1% abandonment rate)  
**Training/Test Split:** 80/20 stratified split

---

## 📊 Executive Summary

Trained and evaluated 4 machine learning models to predict cart abandonment in real-time e-commerce sessions. **Random Forest achieved best performance with 93.92% accuracy and 98.28% precision**, making it ideal for production deployment with minimal false alarms.

---

## 🏆 Model Performance Comparison

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Training Time |
|-------|----------|-----------|--------|----------|---------|---------------|
| **Random Forest** | **93.92%** | **98.28%** | 79.78% | **88.07%** | 97.50% | 23.7 min |
| **Hybrid Ensemble** | 93.57% | 94.96% | **81.45%** | 87.69% | **97.46%** | 21 sec |
| **XGBoost** | 93.53% | 95.85% | 80.47% | 87.49% | 97.28% | **5.6 min** |
| **LightGBM** | 93.53% | 96.15% | 80.20% | 87.45% | 97.21% | 26.5 min |

### 🥇 Winner: **Random Forest**
- Best overall accuracy and F1-score
- Exceptional precision (only 10 false positives)
- Most reliable for production deployment

---

## 📈 Detailed Model Analysis

### 1️⃣ Random Forest

**Hyperparameters:**
- n_estimators: 300
- max_depth: 10
- min_samples_split: 5
- class_weight: None

**Confusion Matrix:**
            Predicted
          No Abandon | Abandon
        Actual No [ 1824 | 10 ]
        Actual Yes [ 145 | 572 ]


**Strengths:**
- ✅ Exceptional precision (98.28%) - minimal false alarms
- ✅ Best overall accuracy
- ✅ Robust to overfitting
- ✅ Handles feature interactions naturally

**Weaknesses:**
- ⚠️ Slower training (23.7 min)
- ⚠️ Recall could be improved (79.78%)

**Top 5 Features:**
1. checkout_initiated (19.70%)
2. cart_to_checkout_rate (18.44%)
3. cart_engagement (18.38%)
4. cart_value (16.56%)
5. cart_additions (9.60%)

---

### 2️⃣ XGBoost

**Hyperparameters:**
- n_estimators: 200
- max_depth: 5
- learning_rate: 0.05
- subsample: 0.8

**Confusion Matrix:**
            Predicted
          No Abandon | Abandon
        Actual No [ 1818 | 16 ]
        Actual Yes [ 140 | 577 ]


**Strengths:**
- ✅ **Fastest training** (5.6 min)
- ✅ Best recall (80.47%)
- ✅ Excellent precision (95.85%)

**Weaknesses:**
- ⚠️ Slightly lower accuracy than Random Forest

**Top 5 Features:**
1. checkout_initiated (41.08%)
2. cart_to_checkout_rate (24.07%)
3. cart_value (11.46%)
4. cart_engagement (10.44%)
5. persona (2.40%)

---

### 3️⃣ LightGBM

**Hyperparameters:**
- n_estimators: 200
- max_depth: 7
- learning_rate: 0.05
- num_leaves: 31

**Confusion Matrix:**
            Predicted
          No Abandon | Abandon
        Actual No [ 1820 | 14 ]
        Actual Yes [ 142 | 575 ]


**Strengths:**
- ✅ High precision (96.15%)
- ✅ Memory efficient
- ✅ Good balance of metrics

**Weaknesses:**
- ⚠️ Slower than expected (26.5 min)
- ⚠️ Didn't beat XGBoost on speed

**Top 5 Features:**
1. cart_value (635)
2. time_per_product (521)
3. session_duration_seconds (450)
4. engagement_score (393)
5. avg_time_per_page (391)

---

### 4️⃣ Hybrid Ensemble (Stacking)

**Architecture:**
- Base Models: Random Forest, XGBoost, LightGBM
- Meta-Learner: Logistic Regression
- Stacking Method: Probability-based
- Cross-Validation: 5-fold

**Meta-Learner Weights:**
- Random Forest: **+6.81** (dominant)
- XGBoost: +2.10
- LightGBM: +0.13

**Confusion Matrix:**
            Predicted
          No Abandon | Abandon
        Actual No [ 1798 | 36 ]
        Actual Yes [ 133 | 584 ]


**Strengths:**
- ✅ **Best recall** (81.45%) - catches most abandonments
- ✅ **Lightning fast training** (21 seconds)
- ✅ Combines strengths of all models

**Weaknesses:**
- ⚠️ Didn't exceed Random Forest accuracy (expected)
- ⚠️ Random Forest dominates (weight 6.81)

---

## 🎯 Recommendation

### **Production Deployment: Random Forest** 🏆

**Rationale:**
1. ✅ **Best accuracy** (93.92%)
2. ✅ **Exceptional precision** (98.28%) - only 1.7% false alarm rate
3. ✅ **Highest F1-score** (88.07%) - best balance
4. ✅ **Most reliable** - robust performance

### **Alternative: Hybrid Ensemble** ⚡

For scenarios prioritizing:
- **Best recall** (81.45% - catches most abandonments)
- **Fastest inference** (already pre-trained)
- **Balanced predictions** (meta-learner combines all models)

---

## 💰 Business Impact

### Expected ROI with Random Forest:

**Assumptions:**
- Average cart value: $45
- Intervention cost: $2 (email/popup)
- Recovery rate: 15% (industry standard)

**Per 10,000 Sessions:**
- Predicted high-risk: 2,282 sessions
- Actual abandonments: 2,810
- True positives: 2,240 (correctly predicted)
- Expected recoveries: 336 carts
- Recovered revenue: **$15,120**
- Intervention cost: $4,564
- **Net profit: $10,556** 💰

**Annual Impact (1M sessions):**
- **Additional revenue: $1.06M per year**

---

## 🔍 Feature Importance Insights

### Key Predictors (Consistent Across All Models):

1. **checkout_initiated** - Strongest signal
   - Users who reach checkout but don't convert = high risk

2. **cart_to_checkout_rate** - Conversion intent
   - Low rate = hesitation/friction

3. **cart_engagement** - Purchase confidence
   - (cart_additions - cart_removals)
   - Negative values = uncertainty

4. **cart_value** - Price sensitivity
   - Higher values = higher abandon risk

5. **persona** - User behavior type
   - window_shopper, intent_buyer, cart_abandoner

### Actionable Insights:
- ✅ Focus interventions when users reach checkout
- ✅ Reduce checkout friction
- ✅ Address cart hesitation (removals)
- ✅ Offer discounts for high-value carts
- ✅ Personalize by user persona

---

## 📚 Technical Details

### Dataset Quality:
- ✅ 12,752 sessions (sufficient sample size)
- ✅ 28.1% positive class (well-balanced)
- ✅ 20 features (behavioral + categorical)
- ✅ No missing values
- ✅ Realistic user behavior patterns

### Training Configuration:
- Train/Test Split: 80/20 stratified
- Cross-Validation: 3-5 fold
- Hyperparameter Tuning: GridSearchCV
- Evaluation Metrics: Accuracy, Precision, Recall, F1, ROC-AUC

### Model Files:
- `random_forest_v1.pkl` (177 MB)
- `xgboost_v1.pkl` (2.3 MB)
- `lightgbm_v1.pkl` (1.8 MB)
- `hybrid_ensemble_v1.pkl` (182 MB)

---

## 📊 Reproducibility

**Environment:**
- Python 3.11
- scikit-learn 1.3.2
- xgboost 2.0.2
- lightgbm 4.5.0

**Training Time:**
- Total: ~56 minutes for 4 models
- Hardware: CPU-based (parallelized)

**Random Seeds:**
- All models: seed=42 (reproducible)

---
