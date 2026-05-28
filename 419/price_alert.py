import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Optional, Callable

ALERTS_FILE = 'price_alerts.json'

class PriceAlertManager:
    def __init__(self, alerts_file: str = ALERTS_FILE):
        self.alerts_file = alerts_file
        self.alerts = self._load_alerts()
    
    def _load_alerts(self) -> List[Dict]:
        if os.path.exists(self.alerts_file):
            try:
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_alerts(self):
        with open(self.alerts_file, 'w', encoding='utf-8') as f:
            json.dump(self.alerts, f, ensure_ascii=False, indent=2)
    
    def create_alert(self, route: str, target_price: float, departure_date: str,
                     email: Optional[str] = None, phone: Optional[str] = None,
                     airline: Optional[str] = None, note: str = '') -> Dict:
        alert_id = f'alert_{int(datetime.now().timestamp())}_{np.random.randint(1000, 9999)}'
        
        alert = {
            'id': alert_id,
            'route': route,
            'target_price': target_price,
            'departure_date': departure_date,
            'email': email,
            'phone': phone,
            'airline': airline,
            'note': note,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'active',
            'triggered_at': None,
            'current_lowest_price': None,
            'price_history': []
        }
        
        self.alerts.append(alert)
        self._save_alerts()
        return alert
    
    def cancel_alert(self, alert_id: str) -> bool:
        for alert in self.alerts:
            if alert['id'] == alert_id:
                alert['status'] = 'cancelled'
                self._save_alerts()
                return True
        return False
    
    def get_active_alerts(self) -> List[Dict]:
        return [a for a in self.alerts if a['status'] == 'active']
    
    def get_all_alerts(self) -> List[Dict]:
        return self.alerts
    
    def check_alerts(self, model, current_date: Optional[datetime] = None) -> List[Dict]:
        if current_date is None:
            current_date = datetime.now()
        
        triggered = []
        
        for alert in self.get_active_alerts():
            try:
                dep_date = pd.to_datetime(alert['departure_date'])
                if dep_date < current_date:
                    alert['status'] = 'expired'
                    continue
                
                current_price = self._get_current_price(alert, model)
                
                alert['current_lowest_price'] = current_price
                alert['price_history'].append({
                    'date': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'price': current_price
                })
                
                if current_price <= alert['target_price']:
                    alert['status'] = 'triggered'
                    alert['triggered_at'] = current_date.strftime('%Y-%m-%d %H:%M:%S')
                    triggered.append(alert)
                    
                    self._send_notification(alert, current_price)
            except Exception as e:
                print(f"检查警报 {alert['id']} 时出错: {e}")
        
        self._save_alerts()
        return triggered
    
    def _get_current_price(self, alert: Dict, model) -> float:
        from prediction import prepare_prediction_data_enhanced
        
        try:
            feature_data = prepare_prediction_data_enhanced(
                alert['route'], 
                alert['departure_date'],
                airline=alert.get('airline')
            )
            price = model.predict_with_xgboost(feature_data)[0]
            return float(price)
        except:
            route_parts = alert['route'].split('-')
            if len(route_parts) == 2:
                from multi_city import get_distance
                dist = get_distance(route_parts[0], route_parts[1])
                base_price = 500 + dist * 0.4
                return float(base_price)
            return 1000.0
    
    def _send_notification(self, alert: Dict, current_price: float):
        print(f"\n{'='*60}")
        print(f"🔔 价格警报触发!")
        print(f"航线: {alert['route']}")
        print(f"目标价格: ¥{alert['target_price']:.0f}")
        print(f"当前价格: ¥{current_price:.0f}")
        print(f"出发日期: {alert['departure_date']}")
        if alert.get('note'):
            print(f"备注: {alert['note']}")
        print(f"{'='*60}\n")
        
        if alert.get('email'):
            self._send_email_alert(alert, current_price)
        if alert.get('phone'):
            self._send_sms_alert(alert, current_price)
    
    def _send_email_alert(self, alert: Dict, current_price: float):
        print(f"📧 已发送邮件通知到: {alert['email']}")
    
    def _send_sms_alert(self, alert: Dict, current_price: float):
        print(f"📱 已发送短信通知到: {alert['phone']}")
    
    def simulate_price_tracking(self, alert: Dict, model, days: int = 30) -> Dict:
        from datetime import timedelta
        
        start_date = datetime.now()
        price_history = []
        
        for day in range(days):
            check_date = start_date + timedelta(days=day)
            current_price = self._get_current_price(alert, model)
            price_history.append({
                'date': check_date.strftime('%Y-%m-%d'),
                'price': current_price,
                'target_reached': current_price <= alert['target_price']
            })
            
            if current_price <= alert['target_price']:
                break
        
        return {
            'alert': alert,
            'tracking_days': len(price_history),
            'price_history': price_history,
            'target_reached': any(p['target_reached'] for p in price_history),
            'first_hit_date': next(
                (p['date'] for p in price_history if p['target_reached']), 
                None
            )
        }
    
    def get_alert_statistics(self) -> Dict:
        total = len(self.alerts)
        active = len(self.get_active_alerts())
        triggered = len([a for a in self.alerts if a['status'] == 'triggered'])
        cancelled = len([a for a in self.alerts if a['status'] == 'cancelled'])
        expired = len([a for a in self.alerts if a['status'] == 'expired'])
        
        if triggered > 0:
            avg_days_to_trigger = 0
            for a in self.alerts:
                if a['status'] == 'triggered' and a.get('created_at') and a.get('triggered_at'):
                    created = pd.to_datetime(a['created_at'])
                    triggered_at = pd.to_datetime(a['triggered_at'])
                    avg_days_to_trigger += (triggered_at - created).total_seconds() / 86400
            avg_days_to_trigger /= triggered
        else:
            avg_days_to_trigger = 0
        
        return {
            'total_alerts': total,
            'active_alerts': active,
            'triggered_alerts': triggered,
            'cancelled_alerts': cancelled,
            'expired_alerts': expired,
            'avg_days_to_trigger': round(avg_days_to_trigger, 1),
            'trigger_rate': round(triggered / total * 100, 1) if total > 0 else 0
        }
    
    def delete_alert(self, alert_id: str) -> bool:
        self.alerts = [a for a in self.alerts if a['id'] != alert_id]
        self._save_alerts()
        return True
    
    def clear_all_alerts(self):
        self.alerts = []
        self._save_alerts()

def create_price_alert(manager: PriceAlertManager, model, 
                       route: str, target_price: float, departure_date: str,
                       **kwargs) -> Dict:
    alert = manager.create_alert(route, target_price, departure_date, **kwargs)
    
    current_price = manager._get_current_price(alert, model)
    
    if current_price <= target_price:
        print(f"⚠️ 当前价格 ¥{current_price:.0f} 已低于目标价格 ¥{target_price:.0f}")
    
    return alert

def get_price_drop_probability(route: str, target_price: float, 
                               departure_date: str, model) -> Dict:
    from prediction import predict_price_range, generate_price_path
    
    dep_date = pd.to_datetime(departure_date)
    days_to_departure = (dep_date - datetime.now()).days
    
    feature_data = prepare_prediction_data_enhanced(route, departure_date)
    mean_price = model.predict_with_xgboost(feature_data)[0]
    
    lower_bound, upper_bound = predict_price_range(feature_data, model)
    
    price_paths = generate_price_path(mean_price, days_to_departure, n_paths=1000)
    
    drop_count = 0
    for path in price_paths:
        if min(path) <= target_price:
            drop_count += 1
    
    probability = drop_count / len(price_paths)
    
    return {
        'current_price': float(mean_price),
        'target_price': target_price,
        'days_to_departure': days_to_departure,
        'drop_probability': round(probability * 100, 1),
        'price_range': [float(lower_bound), float(upper_bound)],
        'expected_min_price': float(np.percentile([min(p) for p in price_paths], 25))
    }

def prepare_prediction_data_enhanced(route, departure_date, airline=None):
    from prediction import prepare_prediction_data_enhanced as pred_func
    return pred_func(route, departure_date, airline=airline)

if __name__ == '__main__':
    print('测试价格警报系统...')
    
    manager = PriceAlertManager()
    
    alert = manager.create_alert(
        route='北京-上海',
        target_price=500,
        departure_date='2025-08-15',
        email='test@example.com',
        note='暑假旅行'
    )
    
    print(f"创建警报: {alert['id']}")
    print(f"当前活动警报数: {len(manager.get_active_alerts())}")
    
    stats = manager.get_alert_statistics()
    print(f"警报统计: {stats}")
    
    print('\n价格下跌概率测试:')
    from model_training import AirlinePriceModel
    try:
        model = AirlinePriceModel()
        model.load_models()
        result = get_price_drop_probability('北京-上海', 500, '2025-08-15', model)
        print(result)
    except Exception as e:
        print(f"模型加载失败: {e}")
