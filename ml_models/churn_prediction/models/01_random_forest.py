"""
Model 1: Random Forest Classifier with Hyperparameter Tuning
Uses GridSearchCV to find optimal parameters.

Expected Performance: 75-78% accuracy
Training Time: ~5-10 minutes
"""

import sys
from pathlib import Path
import time
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ml_models.churn_prediction.utils.data_loader import DataLoader
from ml_models.churn_prediction.utils.evaluation import ModelEvaluator


def train_random_forest():
    """Train Random Forest with hyperparameter tuning"""
    
    print("="*70)
    print("🌲 MODEL 1: RANDOM FOREST CLASSIFIER")
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
        'n_estimators': [100, 200, 300],           # Number of trees
        'max_depth': [10, 20, 30, None],           # Tree depth
        'min_samples_split': [2, 5, 10],           # Min samples to split
        'min_samples_leaf': [1, 2, 4],             # Min samples in leaf
        'max_features': ['sqrt', 'log2'],          # Features per split
        'bootstrap': [True],                        # Use bootstrap samples
        'class_weight': ['balanced', None]         # Handle class imbalance
    }
    
    total_combinations = (
        len(param_grid['n_estimators']) *
        len(param_grid['max_depth']) *
        len(param_grid['min_samples_split']) *
        len(param_grid['min_samples_leaf']) *
        len(param_grid['max_features']) *
        len(param_grid['class_weight'])
    )
    
    print(f"   Total hyperparameter combinations: {total_combinations}")
    print(f"   Using 5-fold cross-validation")
    print(f"   Expected search time: ~5-10 minutes")
    
    # ========================================
    # STEP 3: Hyperparameter tuning
    # ========================================
    print("\n🔍 STEP 3: Hyperparameter Tuning (GridSearchCV)...")
    print("   This may take several minutes...")
    
    # Base model
    rf_base = RandomForestClassifier(
        random_state=42,
        n_jobs=-1,  # Use all CPU cores
        verbose=0
    )
    
    # Grid search with cross-validation
    grid_search = GridSearchCV(
        estimator=rf_base,
        param_grid=param_grid,
        cv=5,                      # 5-fold cross-validation
        scoring='f1',              # Optimize F1-score (balance precision/recall)
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
    evaluator = ModelEvaluator('random_forest')
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
    model_path = model_dir / "random_forest_v1.pkl"
    
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
    # STEP 8: Final summary
    # ========================================
    print("\n" + "="*70)
    print("🎉 RANDOM FOREST TRAINING COMPLETE!")
    print("="*70)
    print(f"\n📈 Final Metrics:")
    print(f"   Accuracy:  {results['accuracy']*100:.2f}%")
    print(f"   Precision: {results['precision']:.4f}")
    print(f"   Recall:    {results['recall']:.4f}")
    print(f"   F1-Score:  {results['f1_score']:.4f}")
    print(f"   ROC-AUC:   {results['roc_auc']:.4f}")
    
    print(f"\n💾 Outputs:")
    print(f"   Model: {model_path}")
    print(f"   Results: ml-models/churn_prediction/results/random_forest_results.json")
    print(f"   Confusion Matrix: ml-models/churn_prediction/results/random_forest_confusion_matrix.png")
    
    print("\n✅ Ready for deployment!")
    print("="*70 + "\n")
    
    return best_model, results


if __name__ == "__main__":
    model, results = train_random_forest()
