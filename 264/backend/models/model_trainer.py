import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from data.data_loader import ODDataLoader
from utils.feature_extractor import SpatialTemporalFeatureExtractor
from models.od_predictor import SimpleODPredictor, train_model, predict
from models.meta_learner import MetaLearner, MetaLoss

class ODPredictorTrainer:
    def __init__(self, use_meta_learning=True):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.grid_size = Config.GRID_SIZE
        self.num_grids = self.grid_size * self.grid_size
        self.use_meta_learning = use_meta_learning
        
        self.data_loader = ODDataLoader()
        self.feature_extractor = SpatialTemporalFeatureExtractor()
        
        self.model = None
        self.model_path = Config.MODEL_PATH
        self.meta_model_path = os.path.join(os.path.dirname(Config.MODEL_PATH), 'meta_predictor.pth')
        
    def prepare_training_data(self):
        print("Preparing training data...")
        self.data_loader.load_data()
        
        start_date = datetime(2024, 1, 1)
        dates = [(start_date + timedelta(days=d)).strftime('%Y-%m-%d') 
                 for d in range(Config.HISTORY_DAYS)]
        
        features_list = []
        targets_list = []
        
        for date in dates:
            for hour in range(Config.TIME_SLOTS):
                history_matrices = []
                for h in range(max(0, hour - 3), hour):
                    try:
                        hist_matrix = self.data_loader.get_od_matrix(date, h)
                        history_matrices.append(hist_matrix)
                    except:
                        pass
                
                features = self.feature_extractor.create_model_input(
                    history_matrices, date, hour
                )
                
                target_matrix = self.data_loader.get_flattened_od(date, hour)
                
                features_list.append(features)
                targets_list.append(target_matrix)
        
        features_array = np.array(features_list)
        targets_array = np.array(targets_list)
        
        print(f"Prepared {len(features_list)} training samples")
        print(f"Features shape: {features_array.shape}")
        print(f"Targets shape: {targets_array.shape}")
        
        return features_array, targets_array
    
    def train(self, epochs=Config.EPOCHS, lr=Config.LEARNING_RATE):
        print(f"Training on device: {self.device}")
        print(f"Using meta-learning: {self.use_meta_learning}")
        
        features, targets = self.prepare_training_data()
        
        feature_dim = features.shape[-1]
        
        if self.use_meta_learning:
            self.model = MetaLearner(grid_size=self.grid_size, feature_dim=feature_dim).to(self.device)
            base_criterion = nn.MSELoss()
            criterion = MetaLoss(base_criterion, proto_loss_weight=0.1)
        else:
            self.model = SimpleODPredictor(grid_size=self.grid_size, feature_dim=feature_dim).to(self.device)
            criterion = nn.MSELoss()
        
        optimizer = optim.Adam(self.model.parameters(), lr=lr)
        
        class ODDataset(torch.utils.data.Dataset):
            def __init__(self, features, targets):
                self.features = torch.FloatTensor(features)
                self.targets = torch.FloatTensor(targets)
            
            def __len__(self):
                return len(self.features)
            
            def __getitem__(self, idx):
                return self.features[idx], self.targets[idx]
        
        dataset = ODDataset(features, targets)
        train_loader = torch.utils.data.DataLoader(dataset, batch_size=Config.BATCH_SIZE, shuffle=True)
        
        print("Starting training...")
        for epoch in range(epochs):
            loss = train_model(self.model, train_loader, optimizer, criterion, self.device)
            if (epoch + 1) % 5 == 0:
                print(f"Epoch {epoch+1}/{epochs}, Loss: {loss:.4f}")
        
        save_path = self.meta_model_path if self.use_meta_learning else self.model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        torch.save(self.model.state_dict(), save_path)
        print(f"Model saved to {save_path}")
        
        return self.model
    
    def load_model(self):
        feature_dim = 22
        
        if self.use_meta_learning and os.path.exists(self.meta_model_path):
            self.model = MetaLearner(grid_size=self.grid_size, feature_dim=feature_dim).to(self.device)
            self.model.load_state_dict(torch.load(self.meta_model_path, map_location=self.device))
            print(f"Meta model loaded from {self.meta_model_path}")
        elif os.path.exists(self.model_path):
            self.model = SimpleODPredictor(grid_size=self.grid_size, feature_dim=feature_dim).to(self.device)
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            print(f"Model loaded from {self.model_path}")
        else:
            print("No pre-trained model found. Training new model...")
            self.train()
        
        return self.model
    
    def predict_od(self, date, hour, history_matrices=[]):
        if self.model is None:
            self.load_model()
        
        features = self.feature_extractor.create_model_input(history_matrices, date, hour)
        features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
        
        prediction = predict(self.model, features_tensor, self.device)
        
        prediction = np.maximum(0, prediction)
        
        return prediction
    
    def predict_fine_grained(self, date, hour, granularity='5min'):
        if self.model is None:
            self.load_model()
        
        if granularity == '1h':
            pred = self.predict_od(date, hour, [])
            return {
                'time_points': [f"{hour:02d}:00"],
                'predictions': [pred]
            }
        
        interval_minutes = 5 if granularity == '5min' else 15
        num_points = 60 // interval_minutes
        
        base_pred = self.predict_od(date, hour, [])
        
        time_points = []
        predictions = []
        
        for i in range(num_points):
            minute = i * interval_minutes
            time_str = f"{hour:02d}:{minute:02d}"
            
            factor = 1.0
            if granularity == '5min':
                if 7 <= hour <= 9:
                    peak_offset = (hour - 7) * 12 + minute // 5
                    factor = 0.8 + 0.4 * np.sin(peak_offset / 24 * np.pi)
                elif 17 <= hour <= 19:
                    peak_offset = (hour - 17) * 12 + minute // 5
                    factor = 0.8 + 0.4 * np.sin(peak_offset / 24 * np.pi)
            
            pred = base_pred * factor
            time_points.append(time_str)
            predictions.append(pred)
        
        return {
            'time_points': time_points,
            'predictions': predictions
        }
    
    def predict_trend(self, date, start_hour, hours=24, granularity='1h'):
        if self.model is None:
            self.load_model()
        
        predictions = []
        history_matrices = []
        
        if granularity == '1h':
            for h in range(hours):
                hour = (start_hour + h) % 24
                pred = self.predict_od(date, hour, history_matrices)
                
                predictions.append({
                    'time': f"{hour:02d}:00",
                    'hour': hour,
                    'minute': 0,
                    'total_demand': float(np.sum(pred)),
                    'peak_origin': int(np.argmax(np.sum(pred, axis=1))),
                    'peak_dest': int(np.argmax(np.sum(pred, axis=0)))
                })
                
                pred_4d = pred.reshape(self.grid_size, self.grid_size, self.grid_size, self.grid_size)
                history_matrices.append(pred_4d)
                if len(history_matrices) > 6:
                    history_matrices.pop(0)
        else:
            interval_minutes = 5 if granularity == '5min' else 15
            total_points = hours * 60 // interval_minutes
            
            for p in range(total_points):
                total_minutes = start_hour * 60 + p * interval_minutes
                hour = (total_minutes // 60) % 24
                minute = total_minutes % 60
                
                pred = self.predict_od(date, hour, history_matrices)
                
                factor = 1.0
                if granularity == '5min':
                    if 7 <= hour <= 9:
                        peak_minute = (hour - 7) * 60 + minute
                        factor = 0.8 + 0.4 * np.sin(peak_minute / 180 * np.pi)
                    elif 17 <= hour <= 19:
                        peak_minute = (hour - 17) * 60 + minute
                        factor = 0.8 + 0.4 * np.sin(peak_minute / 180 * np.pi)
                
                pred = pred * factor
                
                predictions.append({
                    'time': f"{hour:02d}:{minute:02d}",
                    'hour': hour,
                    'minute': minute,
                    'total_demand': float(np.sum(pred)),
                    'peak_origin': int(np.argmax(np.sum(pred, axis=1))),
                    'peak_dest': int(np.argmax(np.sum(pred, axis=0)))
                })
                
                if minute == 0:
                    pred_4d = pred.reshape(self.grid_size, self.grid_size, self.grid_size, self.grid_size)
                    history_matrices.append(pred_4d)
                    if len(history_matrices) > 6:
                        history_matrices.pop(0)
        
        return predictions
    
    def get_similar_grids_info(self, grid_idx):
        if self.model is None:
            self.load_model()
        
        if hasattr(self.model, 'get_knowledge_transfer_weights'):
            weights = self.model.get_knowledge_transfer_weights()
            if weights is not None:
                sim_scores = weights[grid_idx]
                top_indices = np.argsort(sim_scores)[::-1][1:6]
                return {
                    'grid_idx': grid_idx,
                    'similar_grids': [
                        {'grid_idx': int(idx), 'similarity': float(sim_scores[idx])}
                        for idx in top_indices
                    ]
                }
        
        return {'grid_idx': grid_idx, 'similar_grids': []}

def get_or_train_model(use_meta_learning=True):
    trainer = ODPredictorTrainer(use_meta_learning=use_meta_learning)
    
    meta_path = os.path.join(os.path.dirname(Config.MODEL_PATH), 'meta_predictor.pth')
    if use_meta_learning and os.path.exists(meta_path):
        trainer.load_model()
    elif os.path.exists(Config.MODEL_PATH):
        trainer.use_meta_learning = False
        trainer.load_model()
    else:
        trainer.train()
    
    return trainer
