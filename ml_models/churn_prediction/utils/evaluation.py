"""
Model Evaluation Utilities
Common metrics and reporting functions for all models.
"""

import json
import numpy as np
from pathlib import Path
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)
import matplotlib.pyplot as plt
import seaborn as sns


def convert_to_python_types(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, dict):
        return {key: convert_to_python_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_python_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


class ModelEvaluator:
    """Evaluate and save model results"""
    
    def __init__(self, model_name: str):
        """
        Initialize evaluator.
        
        Args:
            model_name: Name of the model (e.g., 'random_forest')
        """
        self.model_name = model_name
        self.results = {}
        
        # Create results directory
        self.results_dir = Path(__file__).parent.parent / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def evaluate(self, y_true, y_pred, y_pred_proba=None):
        """
        Calculate all metrics.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_pred_proba: Predicted probabilities (optional)
            
        Returns:
            Dictionary of metrics
        """
        print(f"\n📊 Evaluating {self.model_name}...")
        
        # Calculate metrics
        self.results = {
            'model_name': self.model_name,
            'accuracy': float(accuracy_score(y_true, y_pred)),
            'precision': float(precision_score(y_true, y_pred)),
            'recall': float(recall_score(y_true, y_pred)),
            'f1_score': float(f1_score(y_true, y_pred)),
            'confusion_matrix': confusion_matrix(y_true, y_pred).tolist()
        }
        
        # ROC AUC if probabilities provided
        if y_pred_proba is not None:
            self.results['roc_auc'] = float(roc_auc_score(y_true, y_pred_proba))
        
        # Print results
        print(f"✅ Results:")
        print(f"   Accuracy:  {self.results['accuracy']:.4f} ({self.results['accuracy']*100:.2f}%)")
        print(f"   Precision: {self.results['precision']:.4f}")
        print(f"   Recall:    {self.results['recall']:.4f}")
        print(f"   F1-Score:  {self.results['f1_score']:.4f}")
        if 'roc_auc' in self.results:
            print(f"   ROC-AUC:   {self.results['roc_auc']:.4f}")
        
        return self.results
    
    def save_results(self, additional_info=None):
        """
        Save results to JSON file.
        
        Args:
            additional_info: Dictionary of extra info (hyperparameters, etc.)
        """
        if additional_info:
            self.results.update(additional_info)
        
        # Convert all numpy types to Python types
        serializable_results = convert_to_python_types(self.results)
        
        # Save to JSON
        json_path = self.results_dir / f"{self.model_name}_results.json"
        with open(json_path, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        print(f"💾 Results saved to: {json_path}")
        
    def plot_confusion_matrix(self, y_true, y_pred):
        """Plot and save confusion matrix"""
        cm = confusion_matrix(y_true, y_pred)
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title(f'Confusion Matrix - {self.model_name}')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        
        # Save plot
        plot_path = self.results_dir / f"{self.model_name}_confusion_matrix.png"
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"📊 Confusion matrix saved to: {plot_path}")
