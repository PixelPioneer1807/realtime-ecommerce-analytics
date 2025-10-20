"""
Model 4: LightGBM Classifier with Hyperparameter Tuning
Faster and often more accurate than XGBoost.

Expected Performance: 93-95% accuracy
Training Time: ~3-5 minutes
"""

import sys
from pathlib import Path
import time
import joblib
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import GridSearchCV
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ml_models.churn_prediction.utils.data_loader import DataLoader
from ml_models.churn_prediction.utils.evaluation import ModelEvaluator


def train_lightgbm():
    """Train LightGBM with hyperparameter tuning"""
    
    print("="*70)
    print("⚡ MODEL 4: LIGHTGBM CLASSIFIER")
    print("="*70)
    
    # ========================================
    # STEP 1: Load and prepare data
    # ========================================
    print("\n📂 STEP 1: Loading Data...")
    loader = DataLoader()
    X_train, X_test, y_train, y_test, feature_names = loader.get_train_test_split()
    
    # ========================================
    # STEP 2: Define hyperparameter grid
    # ========================================
    print("\n⚙️  STEP 2: Setting up Hyperparameter Grid...")
    
    # Optimized grid for speed and performance
    param_grid = {
        'n_estimators': [200, 300],
        'max_depth': [7, 10, 15],
        'learning_rate': [0.05, 0.1],
        'num_leaves': [31, 63],
        'min_child_samples': [20, 30],
        'subsample': [0.8, 0.9],
        'colsample_bytree': [0.8, 0.9],
        'reg_alpha': [0, 0.1],
        'reg_lambda': [0, 0.1]
    }
    
    total_combinations = (
        len(param_grid['n_estimators']) *
        len(param_grid['max_depth']) *
        len(param_grid['learning_rate']) *
        len(param_grid['num_leaves']) *
        len(param_grid['min_child_samples']) *
        len(param_grid['subsample']) *
        len(param_grid['colsample_bytree']) *
        len(param_grid['reg_alpha']) *
        len(param_grid['reg_lambda'])
    )
    
    print(f"   Total hyperparameter combinations: {total_combinations}")
    print(f"   Using 3-fold cross-validation")
    print(f"   Expected search time: ~3-5 minutes ⚡")
    
    # ========================================
    # STEP 3: Hyperparameter tuning
    # ========================================
    print("\n🔍 STEP 3: Hyperparameter Tuning (GridSearchCV)...")
    
    # Base LightGBM model
    lgb_base = lgb.LGBMClassifier(
        objective='binary',
        metric='binary_logloss',
        boosting_type='gbdt',
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )
    
    # Grid search
    grid_search = GridSearchCV(
        estimator=lgb_base,
        param_grid=param_grid,
        cv=3,
        scoring='f1',
        n_jobs=-1,
        verbose=2,
        return_train_score=True
    )
    
    start_time = time.time()
    grid_search.fit(X_train, y_train)
    training_time = time.time() - start_time
    
    print(f"\n✅ Hyperparameter tuning complete!")
    print(f"   Time taken: {training_time/60:.2f} minutes ⚡")
    
    # ========================================
    # STEP 4: Best model results
    # ========================================
    print("\n🏆 STEP 4: Best Hyperparameters Found:")
    best_params = grid_search.best_params_
    for param, value in best_params.items():
        print(f"   {param}: {value}")
    
    print(f"\n   Best CV F1-Score: {grid_search.best_score_:.4f}")
    
    best_model = grid_search.best_estimator_
    
    # ========================================
    # STEP 5: Evaluate on test set
    # ========================================
    print("\n📊 STEP 5: Evaluating on Test Set...")
    
    y_pred = best_model.predict(X_test)
    y_pred_proba = best_model.predict_proba(X_test)[:, 1]
    
    evaluator = ModelEvaluator('lightgbm')
    results = evaluator.evaluate(y_test, y_pred, y_pred_proba)
    
    # ========================================
    # STEP 6: Feature importance
    # ========================================
    print("\n🔍 STEP 6: Top 10 Feature Importances:")
    
    feature_importance = best_model.feature_importances_
    feature_importance_dict = dict(zip(feature_names, feature_importance))
    sorted_features = sorted(feature_importance_dict.items(), key=lambda x: x[1], reverse=True)
    
    for i, (feature, importance) in enumerate(sorted_features[:10], 1):
        print(f"   {i:2d}. {feature:30s}: {importance:.0f}")
    
    # ========================================
    # STEP 7: Save model and results
    # ========================================
    print("\n💾 STEP 7: Saving Model and Results...")
    
    model_dir = Path(__file__).parent.parent / "trained_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "lightgbm_v1.pkl"
    
    joblib.dump(best_model, model_path)
    print(f"   Model saved to: {model_path}")
    
    additional_info = {
        'best_params': best_params,
        'cv_f1_score': float(grid_search.best_score_),
        'training_time_seconds': float(training_time),
        'n_features': len(feature_names),
        'feature_names': feature_names,
        'top_10_features': dict(sorted_features[:10])
    }
    
    evaluator.save_results(additional_info)
    evaluator.plot_confusion_matrix(y_test, y_pred)
    
    # ========================================
    # STEP 8: Comparison with all models
    # ========================================
    print("\n📊 STEP 8: Comparing with All Models...")
    
    try:
        import json
        results_dir = Path(__file__).parent.parent / "results"
        
        print(f"\n   {'Model':<20} {'Accuracy':<12} {'F1-Score':<12} {'Time(min)':<12}")
        print(f"   {'-'*56}")
        
        models_to_compare = ['random_forest', 'xgboost', 'lightgbm']
        for model_name in models_to_compare:
            result_file = results_dir / f"{model_name}_results.json"
            if result_file.exists():
                with open(result_file, 'r') as f:
                    model_results = json.load(f)
                
                train_time = model_results.get('training_time_seconds', 0) / 60
                print(f"   {model_name:<20} "
                      f"{model_results['accuracy']:<12.4f} "
                      f"{model_results['f1_score']:<12.4f} "
                      f"{train_time:<12.2f}")
    except Exception as e:
        print(f"   Could not load previous results: {e}")
    
    # ========================================
    # STEP 9: Final summary
    # ========================================
    print("\n" + "="*70)
    print("🎉 LIGHTGBM TRAINING COMPLETE!")
    print("="*70)
    print(f"\n📈 Final Metrics:")
    print(f"   Accuracy:  {results['accuracy']*100:.2f}%")
    print(f"   Precision: {results['precision']:.4f}")
    print(f"   Recall:    {results['recall']:.4f}")
    print(f"   F1-Score:  {results['f1_score']:.4f}")
    print(f"   ROC-AUC:   {results['roc_auc']:.4f}")
    
    print(f"\n⚡ Speed Advantage:")
    print(f"   Training Time: {training_time/60:.2f} minutes")
    print(f"   Fastest gradient boosting!")
    
    print(f"\n💾 Outputs:")
    print(f"   Model: {model_path}")
    print(f"   Results: ml-models/churn_prediction/results/lightgbm_results.json")
    
    print("\n✅ Ready for deployment!")
    print("="*70 + "\n")
    
    return best_model, results


if __name__ == "__main__":
    model, results = train_lightgbm()
