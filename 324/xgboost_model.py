import os
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from config import XGBOOST_PARAMS, MODEL_DIR, RANDOM_SEED
from utils import calculate_rmse, calculate_mape
from data_generator import generate_historical_dramas, generate_feature_matrix, generate_single_drama_features

np.random.seed(RANDOM_SEED)

class XGBoostRatingPredictor:
    def __init__(self, params=None):
        self.params = params or XGBOOST_PARAMS
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = None
        self.model_path = os.path.join(MODEL_DIR, 'xgboost_model.pkl')
        self.scaler_path = os.path.join(MODEL_DIR, 'xgboost_scaler.pkl')
        self.feature_cols_path = os.path.join(MODEL_DIR, 'xgboost_features.pkl')
    
    def train(self, num_dramas=100, test_size=0.2):
        print(f"Generating {num_dramas} historical dramas...")
        dramas_data = generate_historical_dramas(num_dramas)
        
        print("Building feature matrix...")
        features_df, targets = generate_feature_matrix(dramas_data)
        
        self.feature_columns = features_df.columns.tolist()
        
        X = features_df.values
        y = targets
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=RANDOM_SEED
        )
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        print("Training XGBoost model...")
        self.model = xgb.XGBRegressor(**self.params)
        self.model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_test_scaled, y_test)],
            verbose=100
        )
        
        y_pred = self.model.predict(X_test_scaled)
        rmse = calculate_rmse(y_test, y_pred)
        mape = calculate_mape(y_test, y_pred)
        
        print(f"\nModel Evaluation:")
        print(f"  RMSE: {rmse:.4f}")
        print(f"  MAPE: {mape:.2f}%")
        
        self.save()
        
        return {
            'rmse': rmse,
            'mape': mape,
            'feature_importance': self.get_feature_importance(),
            'y_true': y_test,
            'y_pred': y_pred
        }
    
    def predict(self, drama_info, dates, known_ratings, social_df, episode_idx):
        if self.model is None:
            self.load()
        
        feature_row = generate_single_drama_features(
            drama_info, dates, known_ratings, social_df, episode_idx
        )
        
        features_df = pd.DataFrame([feature_row])
        
        for col in self.feature_columns:
            if col not in features_df.columns:
                features_df[col] = 0
        
        features_df = features_df[self.feature_columns]
        
        X_scaled = self.scaler.transform(features_df.values)
        
        prediction = self.model.predict(X_scaled)[0]
        return max(0.1, min(8.0, prediction))
    
    def predict_all_episodes(self, drama_info, dates, initial_ratings, social_df):
        n = len(dates)
        predictions = []
        known_ratings = list(initial_ratings)
        
        for i in range(n):
            if i < len(initial_ratings):
                pred = initial_ratings[i]
            else:
                pred = self.predict(drama_info, dates, known_ratings, social_df, i)
            
            predictions.append(pred)
            known_ratings.append(pred)
        
        return predictions
    
    def get_feature_importance(self, top_n=20):
        if self.model is None:
            return None
        
        importance = self.model.feature_importances_
        feature_imp = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        return feature_imp.head(top_n)
    
    def grid_search(self, X_train, y_train, param_grid=None):
        if param_grid is None:
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [4, 6, 8],
                'learning_rate': [0.01, 0.05, 0.1],
                'subsample': [0.7, 0.8, 0.9],
                'colsample_bytree': [0.7, 0.8, 0.9]
            }
        
        grid_search = GridSearchCV(
            estimator=xgb.XGBRegressor(random_state=RANDOM_SEED),
            param_grid=param_grid,
            cv=5,
            n_jobs=-1,
            verbose=2,
            scoring='neg_mean_squared_error'
        )
        
        grid_search.fit(X_train, y_train)
        
        print("Best parameters found:")
        print(grid_search.best_params_)
        print(f"Best cross-validation score: {-grid_search.best_score_:.4f}")
        
        self.model = grid_search.best_estimator_
        self.params = grid_search.best_params_
        
        return grid_search.best_params_
    
    def save(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        
        with open(self.scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        with open(self.feature_cols_path, 'wb') as f:
            pickle.dump(self.feature_columns, f)
        
        print(f"Model saved to {self.model_path}")
    
    def load(self):
        if not os.path.exists(self.model_path):
            print("Model not found, training a new model...")
            self.train()
            return
        
        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)
        
        with open(self.scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)
        
        with open(self.feature_cols_path, 'rb') as f:
            self.feature_columns = pickle.load(f)
        
        print(f"Model loaded from {self.model_path}")
    
    def is_trained(self):
        return self.model is not None

if __name__ == '__main__':
    predictor = XGBoostRatingPredictor()
    
    eval_results = predictor.train(num_dramas=30)
    
    print("\nTop 10 Feature Importance:")
    print(eval_results['feature_importance'].head(10))
    
    from data_generator import generate_drama_basic_info, generate_episodic_ratings, generate_social_media_data
    
    test_drama = generate_drama_basic_info('TEST001')
    dates, ratings = generate_episodic_ratings(test_drama)
    social_df = generate_social_media_data(test_drama, dates, ratings)
    
    n_known = 10
    known_ratings = ratings[:n_known]
    
    predictions = predictor.predict_all_episodes(test_drama, dates, known_ratings, social_df)
    
    print(f"\nPredictions for {test_drama['drama_name']}:")
    for i, (date, true, pred) in enumerate(zip(dates, ratings, predictions)):
        status = " (known)" if i < n_known else " (predicted)"
        print(f"  Ep{i+1:2d} ({date.strftime('%Y-%m-%d')}): True={true:.3f}, Pred={pred:.3f}{status}")
