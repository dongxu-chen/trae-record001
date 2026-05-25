import os
import time
import threading
import queue
import numpy as np
import pickle
import config


class OnlineLearningBuffer:
    def __init__(self, max_size=None):
        self.max_size = max_size or config.ONLINE_BUFFER_SIZE
        self.buffer = []
        self._lock = threading.Lock()
    
    def add(self, features, labels):
        with self._lock:
            self.buffer.append({
                'features': features,
                'labels': labels,
                'timestamp': time.time()
            })
            
            if len(self.buffer) > self.max_size:
                self.buffer.pop(0)
    
    def get_batch(self, batch_size=None):
        if batch_size is None:
            batch_size = config.ONLINE_BATCH_SIZE
        
        with self._lock:
            if len(self.buffer) == 0:
                return None
            
            batch_data = self.buffer[-batch_size:]
            return batch_data
    
    def clear_old(self, max_age_seconds=3600):
        current_time = time.time()
        with self._lock:
            self.buffer = [
                item for item in self.buffer
                if current_time - item['timestamp'] < max_age_seconds
            ]
    
    def __len__(self):
        with self._lock:
            return len(self.buffer)
    
    def clear(self):
        with self._lock:
            self.buffer.clear()


class OnlineLearningManager:
    def __init__(self, model, feature_preprocessor=None):
        self.model = model
        self.feature_preprocessor = feature_preprocessor
        self.buffer = OnlineLearningBuffer()
        self.stats = {
            'total_samples': 0,
            'total_updates': 0,
            'last_update_time': None,
            'avg_loss': 0.0,
            'recent_losses': []
        }
        
        self._update_thread = None
        self._stop_event = threading.Event()
        self._running = False
        self._lock = threading.Lock()
        
        self.stats_file = None
    
    def add_feedback(self, features, labels):
        self.buffer.add(features, labels)
        
        with self._lock:
            self.stats['total_samples'] += 1
        
        return True
    
    def add_feedback_from_dict(self, sample_dict, feedback_dict):
        if self.feature_preprocessor is None:
            raise ValueError("Feature preprocessor is required for dict input")
        
        features = self.feature_preprocessor.process_sample(sample_dict)
        labels = self._prepare_labels(feedback_dict)
        
        return self.add_feedback(features, labels)
    
    def _prepare_labels(self, feedback_dict):
        labels = []
        for target in config.MULTI_TARGET:
            labels.append(float(feedback_dict.get(target, 0)))
        return np.array(labels)
    
    def process_batch(self, batch_size=None):
        batch_data = self.buffer.get_batch(batch_size)
        
        if batch_data is None or len(batch_data) == 0:
            return None
        
        batch_features = {}
        batch_labels = []
        
        feature_keys = batch_data[0]['features'].keys()
        for key in feature_keys:
            batch_features[key] = []
        
        for item in batch_data:
            for key in feature_keys:
                batch_features[key].append(item['features'][key])
            batch_labels.append(item['labels'])
        
        for key in feature_keys:
            batch_features[key] = np.array(batch_features[key])
        
        batch_labels = np.array(batch_labels)
        
        loss = self.model.online_train_step(
            batch_features, 
            batch_labels,
            learning_rate=config.ONLINE_LEARNING_RATE
        )
        
        with self._lock:
            self.stats['total_updates'] += 1
            self.stats['last_update_time'] = time.time()
            self.stats['recent_losses'].append(float(loss))
            
            if len(self.stats['recent_losses']) > 100:
                self.stats['recent_losses'].pop(0)
            
            self.stats['avg_loss'] = np.mean(self.stats['recent_losses'])
        
        return {
            'batch_size': len(batch_data),
            'loss': float(loss),
            'avg_loss': self.stats['avg_loss']
        }
    
    def start_background_training(self, interval=None):
        if self._running:
            print("Background training already running")
            return False
        
        if interval is None:
            interval = config.ONLINE_UPDATE_INTERVAL
        
        self._stop_event.clear()
        self._running = True
        
        self._update_thread = threading.Thread(
            target=self._background_worker,
            args=(interval,),
            daemon=True
        )
        self._update_thread.start()
        
        print(f"Background online training started (interval: {interval}s)")
        return True
    
    def stop_background_training(self):
        if not self._running:
            return
        
        self._stop_event.set()
        if self._update_thread:
            self._update_thread.join(timeout=10)
        
        self._running = False
        print("Background online training stopped")
    
    def _background_worker(self, interval):
        while not self._stop_event.is_set():
            try:
                if len(self.buffer) >= config.ONLINE_BATCH_SIZE:
                    result = self.process_batch()
                    if result:
                        print(f"[Online Learning] Updated with {result['batch_size']} samples, "
                              f"loss: {result['loss']:.4f}, avg: {result['avg_loss']:.4f}")
            except Exception as e:
                print(f"[Online Learning] Error in background update: {e}")
            
            self._stop_event.wait(interval)
    
    def get_stats(self):
        with self._lock:
            return {
                'buffer_size': len(self.buffer),
                'total_samples': self.stats['total_samples'],
                'total_updates': self.stats['total_updates'],
                'last_update_time': self.stats['last_update_time'],
                'avg_recent_loss': self.stats['avg_loss'],
                'is_running': self._running
            }
    
    def save_stats(self, path):
        with self._lock:
            with open(path, 'wb') as f:
                pickle.dump(self.stats, f)
    
    def load_stats(self, path):
        if os.path.exists(path):
            with open(path, 'rb') as f:
                self.stats = pickle.load(f)
    
    def set_model(self, model):
        with self._lock:
            self.model = model
    
    def get_model(self):
        with self._lock:
            return self.model


class FeaturePreprocessor:
    def __init__(self, processors):
        self.title_processor = processors.get('title_processor')
        self.tag_processor = processors.get('tag_processor')
        self.user_processor = processors.get('user_processor')
    
    def process_sample(self, sample_dict):
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        from src.data.preprocess import preprocess_video_features, preprocess_user_features
        import pandas as pd
        
        df = pd.DataFrame([sample_dict])
        
        video_features = preprocess_video_features(
            df, self.title_processor, self.tag_processor
        )
        user_features, _ = preprocess_user_features(df, self.user_processor)
        
        features = {}
        features.update(video_features)
        features.update(user_features)
        
        return features


_global_online_manager = None


def get_online_manager(model=None, processors=None):
    global _global_online_manager
    if _global_online_manager is None:
        if model is None:
            return None
        
        feature_preprocessor = FeaturePreprocessor(processors) if processors else None
        _global_online_manager = OnlineLearningManager(model, feature_preprocessor)
    
    return _global_online_manager
