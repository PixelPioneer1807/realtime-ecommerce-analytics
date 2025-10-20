"""
Model 2: XGBoost Classifier with Hyperparameter Tuning
Gradient Boosting optimized for tabular data.

Expected Performance: 78-82% accuracy (may beat Random Forest!)
Training Time: ~10-15 minutes
"""

import sys
from pathlib import Path
import time
import joblib
import numpy as np
import xgboost as xgb
from sklearn.model_selection import GridSearchCV
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ml_models.churn_prediction.utils.data_loader import DataLoader
from ml_models.churn_prediction.utils.evaluation import ModelEvaluator


def train_xgboost():
    """Train XGBoost with hyperparameter tuning"""
    
    print("="*70)
    print("🚀 MODEL 2: XGBOOST CLASSIFIER")
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
    
    param_grid = {
        'n_estimators': [100, 200, 300],              # Number of boosting rounds
        'max_depth': [3, 5, 7, 10],                   # Tree depth
        'learning_rate': [0.01, 0.05, 0.1, 0.2],      # Step size (eta)
        'subsample': [0.7, 0.8, 0.9, 1.0],            # Sample fraction per tree
        'colsample_bytree': [0.7, 0.8, 0.9, 1.0],     # Feature fraction per tree
        'min_child_weight': [1, 3, 5],                # Minimum sum of weights
        'gamma': [0, 0.1, 0.2],                       # Minimum loss reduction
        'reg_alpha': [0, 0.1, 1],                     # L1 regularization
        'reg_lambda': [1, 1.5, 2]                     # L2 regularization
    }
    
    # For faster training, use reduced grid
    param_grid_reduced = {
        'n_estimators': [200, 300],
        'max_depth': [5, 7, 10],
        'learning_rate': [0.05, 0.1],
        'subsample': [0.8, 0.9],
        'colsample_bytree': [0.8, 0.9],
        'min_child_weight': [1, 3],
        'gamma': [0, 0.1],
        'reg_alpha': [0, 0.1],
        'reg_lambda': [1, 1.5]
    }
    
    total_combinations = (
        len(param_grid_reduced['n_estimators']) *
        len(param_grid_reduced['max_depth']) *
        len(param_grid_reduced['learning_rate']) *
        len(param_grid_reduced['subsample']) *
        len(param_grid_reduced['colsample_bytree']) *
        len(param_grid_reduced['min_child_weight']) *
        len(param_grid_reduced['gamma']) *
        len(param_grid_reduced['reg_alpha']) *
        len(param_grid_reduced['reg_lambda'])
    )
    
    print(f"   Total hyperparameter combinations: {total_combinations}")
    print(f"   Using 3-fold cross-validation (for speed)")
    print(f"   Expected search time: ~10-15 minutes")
    
    # ========================================
    # STEP 3: Hyperparameter tuning
    # ========================================
    print("\n🔍 STEP 3: Hyperparameter Tuning (GridSearchCV)...")
    print("   This may take several minutes...")
    
    # Base XGBoost model
    xgb_base = xgb.XGBClassifier(
        objective='binary:logistic',
        eval_metric='auc',
        use_label_encoder=False,
        random_state=42,
        n_jobs=-1,
        tree_method='hist',  # Faster training
        verbosity=0
    )
    
    # Grid search with cross-validation
    grid_search = GridSearchCV(
        estimator=xgb_base,
        param_grid=param_grid_reduced,
        cv=3,                      # 3-fold CV (faster)
        scoring='f1',              # Optimize F1-score
        n_jobs=-1,                 # Parallel processing
        verbose=2,                 # Show progress
        return_train_score=True
    )
    
    # Start timer
    start_time = time.time()
    
    # Fit grid search
    grid_search.fit(X_train, y_train)
    
    # End timer
    training_time = time.time() - start_time
    
    print(f"\n✅ Hyperparameter tuning complete!")
    print(f"   Time taken: {training_time/60:.2f} minutes")
    
    # ========================================
    # STEP 4: Best model results
    # ========================================
    print("\n🏆 STEP 4: Best Hyperparameters Found:")
    best_params = grid_search.best_params_
    for param, value in best_params.items():
        print(f"   {param}: {value}")
    
    print(f"\n   Best CV F1-Score: {grid_search.best_score_:.4f}")
    
    # Get best model
    best_model = grid_search.best_estimator_
    
    # ========================================
    # STEP 5: Evaluate on test set
    # ========================================
    print("\n📊 STEP 5: Evaluating on Test Set...")
    
    # Predictions
    y_pred = best_model.predict(X_test)
    y_pred_proba = best_model.predict_proba(X_test)[:, 1]
    
    # Evaluate
    evaluator = ModelEvaluator('xgboost')
    results = evaluator.evaluate(y_test, y_pred, y_pred_proba)
    
    # ========================================
    # STEP 6: Feature importance
    # ========================================
    print("\n🔍 STEP 6: Top 10 Feature Importances:")
    
    feature_importance = best_model.feature_importances_
    feature_importance_dict = dict(zip(feature_names, feature_importance))
    sorted_features = sorted(feature_importance_dict.items(), key=lambda x: x[1], reverse=True)
    
    for i, (feature, importance) in enumerate(sorted_features[:10], 1):
        print(f"   {i:2d}. {feature:30s}: {importance:.4f}")
    
    # ========================================
    # STEP 7: Save model and results
    # ========================================
    print("\n💾 STEP 7: Saving Model and Results...")
    
    # Save model
    model_dir = Path(__file__).parent.parent / "trained_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "xgboost_v1.pkl"
    
    joblib.dump(best_model, model_path)
    print(f"   Model saved to: {model_path}")
    
    # Save results with additional info
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
    # STEP 8: Comparison with Random Forest
    # ========================================
    print("\n📊 STEP 8: Comparing with Random Forest...")
    
    try:
        # Load Random Forest results
        rf_results_path = Path(__file__).parent.parent / "results" / "random_forest_results.json"
        if rf_results_path.exists():
            import json
            with open(rf_results_path, 'r') as f:
                rf_results = json.load(f)
            
            print(f"\n   Comparison:")
            print(f"   {'Metric':<15} {'Random Forest':<15} {'XGBoost':<15} {'Winner':<15}")
            print(f"   {'-'*60}")
            
            metrics = ['accuracy', 'precision', 'recall', 'f1_score', 'roc_auc']
            for metric in metrics:
                rf_val = rf_results.get(metric, 0)
                xgb_val = results.get(metric, 0)
                winner = "XGBoost 🚀" if xgb_val > rf_val else "Random Forest 🌲" if rf_val > xgb_val else "Tie 🤝"
                print(f"   {metric:<15} {rf_val:<15.4f} {xgb_val:<15.4f} {winner:<15}")
    except Exception as e:
        print(f"   Could not load Random Forest results: {e}")
    
    # ========================================
    # STEP 9: Final summary
    # ========================================
    print("\n" + "="*70)
    print("🎉 XGBOOST TRAINING COMPLETE!")
    print("="*70)
    print(f"\n📈 Final Metrics:")
    print(f"   Accuracy:  {results['accuracy']*100:.2f}%")
    print(f"   Precision: {results['precision']:.4f}")
    print(f"   Recall:    {results['recall']:.4f}")
    print(f"   F1-Score:  {results['f1_score']:.4f}")
    print(f"   ROC-AUC:   {results['roc_auc']:.4f}")
    
    print(f"\n💾 Outputs:")
    print(f"   Model: {model_path}")
    print(f"   Results: ml-models/churn_prediction/results/xgboost_results.json")
    print(f"   Confusion Matrix: ml-models/churn_prediction/results/xgboost_confusion_matrix.png")
    
    print("\n✅ Ready for deployment!")
    print("="*70 + "\n")
    
    return best_model, results


if __name__ == "__main__":
    model, results = train_xgboost()
