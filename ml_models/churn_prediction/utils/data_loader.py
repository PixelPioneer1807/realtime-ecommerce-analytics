"""
Data Loader and Preprocessing Utilities
Shared across all models for consistency.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
import warnings
warnings.filterwarnings('ignore')

class DataLoader:
    """
    Load and preprocess training data for ML models.
    Handles feature engineering and train/test split.
    """
    
    def __init__(self, data_path: str = None):
        """
        Initialize data loader.
        
        Args:
            data_path: Path to training_data_latest.csv
        """
        if data_path is None:
            # Default path
            project_root = Path(__file__).parent.parent.parent.parent
            data_path = project_root / "ml_models" / "churn_prediction" / "data" / "training_data_latest.csv"
        
        self.data_path = Path(data_path)
        self.label_encoders = {}
        self.scaler = StandardScaler()
        
    def load_data(self):
        """Load CSV data"""
        print(f"📂 Loading data from: {self.data_path}")
        df = pd.read_csv(self.data_path)
        print(f"✅ Loaded {len(df):,} sessions")
        return df
    
    def engineer_features(self, df):
        """
        Create additional features for better predictions.
        
        Args:
            df: Raw dataframe
            
        Returns:
            df with new features
        """
        print("🔧 Engineering features...")
        
        # 1. Calculate abandonment target (our main prediction target)
        df['abandoned'] = (df['cart_value'] > 0) & (~df['is_converted'])
        
        # 2. Engagement score (composite metric)
        df['engagement_score'] = (
            df['page_views'] * 0.3 +
            df['products_viewed'] * 0.4 +
            df['searches'] * 0.3
        )
        
        # 3. Cart engagement
        df['cart_engagement'] = df['cart_additions'] - df['cart_removals']
        
        # 4. Time efficiency
        df['time_per_product'] = df['session_duration_seconds'] / (df['products_viewed'] + 1)
        
        # 5. Cart conversion likelihood
        df['cart_to_checkout_rate'] = (
            df['checkout_initiated'].astype(int) / (df['cart_additions'] + 1)
        )
        
        # 6. Browsing intensity
        df['pages_per_minute'] = df['page_views'] / (df['session_duration_seconds'] / 60 + 1)
        
        # 7. Product interest depth
        df['unique_product_ratio'] = df['unique_products_viewed'] / (df['products_viewed'] + 1)
        
        print(f"✅ Created 7 new features")
        return df
    
    def preprocess_features(self, df, fit=True):
        """
        Preprocess features for ML models.
        
        Args:
            df: Dataframe with features
            fit: If True, fit encoders/scalers. If False, use existing.
            
        Returns:
            X (features), y (target)
        """
        print("⚙️  Preprocessing features...")
        
        # Select features
        numerical_features = [
            'page_views',
            'products_viewed',
            'unique_products_viewed',
            'searches',
            'cart_additions',
            'cart_removals',
            'cart_value',
            'session_duration_seconds',
            'avg_time_per_page',
            'engagement_score',
            'cart_engagement',
            'time_per_product',
            'cart_to_checkout_rate',
            'pages_per_minute',
            'unique_product_ratio'
        ]
        
        categorical_features = [
            'device_type',
            'browser',
            'persona'
        ]
        
        binary_features = [
            'bounce',
            'checkout_initiated'
        ]
        
        # Handle categorical encoding
        df_encoded = df.copy()
        
        for col in categorical_features:
            if fit:
                self.label_encoders[col] = LabelEncoder()
                df_encoded[col] = self.label_encoders[col].fit_transform(df[col].astype(str))
            else:
                df_encoded[col] = self.label_encoders[col].transform(df[col].astype(str))
        
        # Combine all features
        feature_columns = numerical_features + categorical_features + binary_features
        X = df_encoded[feature_columns]
        
        # Scale numerical features
        if fit:
            X[numerical_features] = self.scaler.fit_transform(X[numerical_features])
        else:
            X[numerical_features] = self.scaler.transform(X[numerical_features])
        
        # Target variable
        y = df_encoded['abandoned'].astype(int)
        
        print(f"✅ Preprocessed {len(feature_columns)} features")
        print(f"   - Numerical: {len(numerical_features)}")
        print(f"   - Categorical: {len(categorical_features)}")
        print(f"   - Binary: {len(binary_features)}")
        
        return X, y, feature_columns
    
    def get_train_test_split(self, test_size=0.2, random_state=42):
        """
        Load, preprocess, and split data.
        
        Args:
            test_size: Proportion for test set
            random_state: Random seed for reproducibility
            
        Returns:
            X_train, X_test, y_train, y_test, feature_names
        """
        # Load data
        df = self.load_data()
        
        # Engineer features
        df = self.engineer_features(df)
        
        # Preprocess
        X, y, feature_names = self.preprocess_features(df, fit=True)
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        print(f"\n📊 Dataset Split:")
        print(f"   Training: {len(X_train):,} samples ({y_train.sum():,} abandoned)")
        print(f"   Testing: {len(X_test):,} samples ({y_test.sum():,} abandoned)")
        print(f"   Abandonment rate: {y.mean()*100:.1f}%")
        
        return X_train, X_test, y_train, y_test, feature_names


# Test if run directly
if __name__ == "__main__":
    loader = DataLoader()
    X_train, X_test, y_train, y_test, features = loader.get_train_test_split()
    print(f"\n✅ Data loaded successfully!")
    print(f"   X_train shape: {X_train.shape}")
    print(f"   Feature names: {features[:5]} ... ({len(features)} total)")
