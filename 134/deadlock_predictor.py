import json
import pickle
import os
from datetime import datetime, timedelta
from collections import defaultdict
from config import Config

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("警告: scikit-learn 未安装，机器学习功能将受限")

class DeadlockPredictor:
    def __init__(self):
        self.model_path = Config.ML_MODEL_PATH
        self.model = None
        self.scaler = None
        self.feature_names = [
            'hour_of_day',
            'day_of_week',
            'recent_deadlock_count_1h',
            'recent_deadlock_count_6h',
            'recent_deadlock_count_24h',
            'avg_transaction_per_minute',
            'lock_contention_score',
            'high_risk_table_count',
            'update_delete_ratio'
        ]
        self.training_data = []
        self._load_model()
    
    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data.get('model')
                    self.scaler = data.get('scaler')
                    self.training_data = data.get('training_data', [])
                print(f"模型已加载: {self.model_path}")
            except Exception as e:
                print(f"加载模型失败: {e}")
    
    def _save_model(self):
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'scaler': self.scaler,
                    'training_data': self.training_data
                }, f)
            print(f"模型已保存: {self.model_path}")
        except Exception as e:
            print(f"保存模型失败: {e}")
    
    def extract_features_from_history(self, deadlock_history, target_time=None):
        if target_time is None:
            target_time = datetime.now()
        
        features = {}
        
        features['hour_of_day'] = target_time.hour
        features['day_of_week'] = target_time.weekday()
        
        one_hour_ago = target_time - timedelta(hours=1)
        six_hours_ago = target_time - timedelta(hours=6)
        twenty_four_hours_ago = target_time - timedelta(hours=24)
        
        count_1h = 0
        count_6h = 0
        count_24h = 0
        
        table_counts = defaultdict(int)
        query_types = {'UPDATE': 0, 'DELETE': 0, 'SELECT': 0, 'INSERT': 0}
        
        for deadlock in deadlock_history:
            try:
                deadlock_time = datetime.fromisoformat(deadlock.get('timestamp'))
            except:
                continue
            
            if deadlock_time <= target_time:
                if deadlock_time > one_hour_ago:
                    count_1h += 1
                if deadlock_time > six_hours_ago:
                    count_6h += 1
                if deadlock_time > twenty_four_hours_ago:
                    count_24h += 1
                
                for txn in deadlock.get('transactions', []):
                    for hold in txn.get('holds', []):
                        table = hold.get('table')
                        if table and table != 'UNKNOWN':
                            table_counts[table] += 1
                    
                    for sql in txn.get('queries', []):
                        sql_upper = sql.strip().upper()
                        if sql_upper.startswith('UPDATE'):
                            query_types['UPDATE'] += 1
                        elif sql_upper.startswith('DELETE'):
                            query_types['DELETE'] += 1
                        elif sql_upper.startswith('SELECT'):
                            query_types['SELECT'] += 1
                        elif sql_upper.startswith('INSERT'):
                            query_types['INSERT'] += 1
        
        features['recent_deadlock_count_1h'] = count_1h
        features['recent_deadlock_count_6h'] = count_6h
        features['recent_deadlock_count_24h'] = count_24h
        
        total_queries = sum(query_types.values()) or 1
        features['avg_transaction_per_minute'] = count_24h / (24 * 60) if count_24h > 0 else 0
        features['lock_contention_score'] = min(count_6h / 6, 10)
        features['high_risk_table_count'] = sum(1 for cnt in table_counts.values() if cnt > 3)
        
        total_update_delete = query_types['UPDATE'] + query_types['DELETE'] or 1
        features['update_delete_ratio'] = total_update_delete / total_queries
        
        return features
    
    def prepare_training_data(self, deadlock_history):
        X = []
        y = []
        
        for i, deadlock in enumerate(deadlock_history):
            try:
                deadlock_time = datetime.fromisoformat(deadlock.get('timestamp'))
            except:
                continue
            
            previous_history = deadlock_history[:i]
            features = self.extract_features_from_history(previous_history, deadlock_time)
            
            feature_vector = [features[name] for name in self.feature_names]
            X.append(feature_vector)
            
            next_deadlocks = sum(1 for d in deadlock_history[i+1:i+6] 
                                if datetime.fromisoformat(d.get('timestamp')) - deadlock_time < timedelta(hours=1))
            y.append(1 if next_deadlocks > 0 else 0)
        
        return X, y
    
    def train_model(self, deadlock_history):
        if not SKLEARN_AVAILABLE:
            print("scikit-learn 未安装，无法训练模型")
            return None
        
        if len(deadlock_history) < 10:
            print("历史数据不足，需要至少10条死锁记录才能训练")
            return None
        
        X, y = self.prepare_training_data(deadlock_history)
        
        if len(X) < 10:
            print("有效训练样本不足")
            return None
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
        self.model.fit(X_train_scaled, y_train)
        
        y_pred = self.model.predict(X_test_scaled)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'training_samples': len(X_train),
            'test_samples': len(X_test)
        }
        
        self.training_data = deadlock_history
        self._save_model()
        
        return metrics
    
    def predict(self, deadlock_history):
        if not SKLEARN_AVAILABLE or self.model is None:
            return self._rule_based_prediction(deadlock_history)
        
        features = self.extract_features_from_history(deadlock_history)
        feature_vector = [[features[name] for name in self.feature_names]]
        
        try:
            feature_vector_scaled = self.scaler.transform(feature_vector)
            probability = self.model.predict_proba(feature_vector_scaled)[0][1]
            
            risk_level = 'low'
            if probability >= Config.ML_PREDICTION_THRESHOLD:
                risk_level = 'high'
            elif probability >= 0.4:
                risk_level = 'medium'
            
            return {
                'probability': float(probability),
                'risk_level': risk_level,
                'features': features,
                'method': 'ml_model'
            }
        except Exception as e:
            print(f"机器学习预测失败，回退到规则预测: {e}")
            return self._rule_based_prediction(deadlock_history)
    
    def _rule_based_prediction(self, deadlock_history):
        features = self.extract_features_from_history(deadlock_history)
        
        score = 0
        
        if features['recent_deadlock_count_1h'] >= 2:
            score += 30
        elif features['recent_deadlock_count_1h'] >= 1:
            score += 15
        
        if features['recent_deadlock_count_6h'] >= 5:
            score += 25
        elif features['recent_deadlock_count_6h'] >= 3:
            score += 15
        
        if features['recent_deadlock_count_24h'] >= 10:
            score += 20
        elif features['recent_deadlock_count_24h'] >= 5:
            score += 10
        
        if features['high_risk_table_count'] >= 2:
            score += 15
        
        if features['update_delete_ratio'] > 0.5:
            score += 10
        
        if 9 <= features['hour_of_day'] <= 17:
            score += 10
        
        probability = min(score / 100, 1.0)
        
        risk_level = 'low'
        if probability >= Config.ML_PREDICTION_THRESHOLD:
            risk_level = 'high'
        elif probability >= 0.4:
            risk_level = 'medium'
        
        return {
            'probability': probability,
            'risk_level': risk_level,
            'features': features,
            'method': 'rule_based'
        }
    
    def get_prediction_explanation(self, prediction):
        features = prediction.get('features', {})
        explanations = []
        
        if features.get('recent_deadlock_count_1h', 0) > 0:
            explanations.append(f"过去1小时内发生 {features['recent_deadlock_count_1h']} 次死锁")
        
        if features.get('recent_deadlock_count_6h', 0) > 0:
            explanations.append(f"过去6小时内发生 {features['recent_deadlock_count_6h']} 次死锁")
        
        if features.get('high_risk_table_count', 0) > 0:
            explanations.append(f"有 {features['high_risk_table_count']} 个高风险表")
        
        if features.get('update_delete_ratio', 0) > 0.5:
            explanations.append("写操作比例较高（UPDATE/DELETE > 50%）")
        
        hour = features.get('hour_of_day', 0)
        if 9 <= hour <= 17:
            explanations.append("当前是业务高峰时段")
        
        if not explanations:
            explanations.append("当前风险因素较低")
        
        return explanations
    
    def generate_prediction_report(self, deadlock_history):
        prediction = self.predict(deadlock_history)
        explanations = self.get_prediction_explanation(prediction)
        
        risk_colors = {
            'low': '#48bb78',
            'medium': '#ed8936',
            'high': '#f56565'
        }
        
        suggestions = self._generate_suggestions(prediction['risk_level'], prediction['features'])
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>死锁预测报告</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 15px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
        .risk-indicator {{ text-align: center; padding: 40px; }}
        .risk-circle {{ width: 200px; height: 200px; border-radius: 50%; margin: 0 auto; display: flex; flex-direction: column; justify-content: center; align-items: center; color: white; font-size: 48px; font-weight: bold; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
        .risk-label {{ font-size: 24px; margin-top: 10px; }}
        .section {{ padding: 30px; border-top: 1px solid #e9ecef; }}
        h2 {{ color: #2d3748; margin-bottom: 20px; }}
        .feature-list {{ display: grid; gap: 10px; }}
        .feature-item {{ display: flex; justify-content: space-between; padding: 10px; background: #f8f9fa; border-radius: 8px; }}
        .suggestion-item {{ background: #f7fafc; border-left: 4px solid #4299e1; padding: 15px; margin: 10px 0; border-radius: 0 8px 8px 0; }}
        .method-badge {{ display: inline-block; padding: 5px 15px; border-radius: 20px; font-size: 14px; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔮 死锁预测报告</h1>
            <p>预测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p class="method-badge" style="background: #4299e1;">预测方法: {prediction['method']}</p>
        </div>
        
        <div class="risk-indicator">
            <div class="risk-circle" style="background: {risk_colors[prediction['risk_level']]}">
                {int(prediction['probability'] * 100)}%
                <div class="risk-label">{prediction['risk_level'].upper()} 风险</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 风险因素分析</h2>
            <div class="feature-list">
                {"".join(f"<div class='feature-item'><span>{k.replace('_', ' ').title()}</span><strong>{v:.2f if isinstance(v, float) else v}</strong></div>" for k, v in prediction['features'].items())}
            </div>
        </div>
        
        <div class="section">
            <h2>💡 风险说明</h2>
            <ul>
                {"".join(f"<li>{exp}</li>" for exp in explanations)}
            </ul>
        </div>
        
        <div class="section">
            <h2>🛡️ 预防建议</h2>
            {"".join(f"<div class='suggestion-item'>{s}</div>" for s in suggestions)}
        </div>
    </div>
</body>
</html>
        """
        
        with open('deadlock_prediction_report.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return 'deadlock_prediction_report.html'
    
    def _generate_suggestions(self, risk_level, features):
        suggestions = []
        
        if risk_level == 'high':
            suggestions.append("⚠️ 高风险预警！建议立即监控数据库锁等待情况")
            suggestions.append("考虑暂停或降低高风险表的写操作")
            suggestions.append("检查长事务，及时提交或回滚")
            suggestions.append("准备DBA人工介入")
        elif risk_level == 'medium':
            suggestions.append("建议增加监控频率，关注锁等待指标")
            suggestions.append("检查慢查询日志，优化高频写操作")
        else:
            suggestions.append("当前风险较低，继续保持常规监控即可")
        
        if features.get('high_risk_table_count', 0) > 1:
            suggestions.append("多表存在高风险，建议考虑应用层面的限流或分批处理")
        
        if features.get('update_delete_ratio', 0) > 0.6:
            suggestions.append("写操作比例过高，建议优化写操作SQL，考虑使用读写分离")
        
        suggestions.append("定期执行死锁趋势分析，提前发现风险模式")
        
        return suggestions
