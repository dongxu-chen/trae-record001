import pandas as pd
import numpy as np
from scipy import signal
from datetime import datetime, timedelta
from collections import defaultdict
from config import STATIONS


class FlowAnalyzer:
    def __init__(self):
        self.stations = STATIONS

    def detect_flow_anomalies(self, historical_data, predictions, station, hours=24):
        station_data = historical_data[historical_data['station'] == station].copy()
        station_data = station_data.sort_values('timestamp').tail(hours * 2)
        
        anomalies = []
        
        for idx, row in station_data.iterrows():
            timestamp = row['timestamp']
            actual_in = row['in_flow']
            actual_out = row['out_flow']
            
            if station in predictions:
                pred_data = predictions[station]
                timestamps = pred_data['in_flow']['timestamps']
                if timestamp.strftime('%Y-%m-%d %H:%M:%S') in timestamps:
                    t_idx = timestamps.index(timestamp.strftime('%Y-%m-%d %H:%M:%S'))
                    upper_in = pred_data['in_flow']['upper_bound'][t_idx]
                    upper_out = pred_data['out_flow']['upper_bound'][t_idx]
                    lower_in = pred_data['in_flow']['lower_bound'][t_idx]
                    lower_out = pred_data['out_flow']['lower_bound'][t_idx]
                    
                    in_anomaly = actual_in > upper_in * 1.1 or actual_in < lower_in * 0.9
                    out_anomaly = actual_out > upper_out * 1.1 or actual_out < lower_out * 0.9
                    
                    if in_anomaly or out_anomaly:
                        anomalies.append({
                            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'station': station,
                            'type': 'in_flow' if in_anomaly else 'out_flow',
                            'actual': actual_in if in_anomaly else actual_out,
                            'expected_upper': upper_in if in_anomaly else upper_out,
                            'expected_lower': lower_in if in_anomaly else lower_out,
                            'deviation_pct': round(
                                ((actual_in - upper_in) / upper_in * 100) if in_anomaly 
                                else ((actual_out - upper_out) / upper_out * 100), 2
                            ),
                            'severity': 'high' if abs(actual_in - upper_in if in_anomaly else actual_out - upper_out) > upper_in * 0.3 else 'medium'
                        })
        
        return anomalies

    def check_real_time_alerts(self, current_flow, predictions, station):
        alerts = []
        
        if station not in predictions:
            return alerts
        
        pred_in = predictions[station]['in_flow']
        pred_out = predictions[station]['out_flow']
        
        for i in range(len(pred_in['prediction'])):
            current_in = current_flow.get('in_flow', 0)
            current_out = current_flow.get('out_flow', 0)
            
            upper_in = pred_in['upper_bound'][i]
            upper_out = pred_out['upper_bound'][i]
            
            if current_in > upper_in * 1.05:
                alerts.append({
                    'type': 'warning',
                    'station': station,
                    'flow_type': 'in_flow',
                    'message': f'进站客流超过预警阈值！当前: {current_in}, 阈值: {int(upper_in)}',
                    'timestamp': pred_in['timestamps'][i],
                    'level': 'high' if current_in > upper_in * 1.2 else 'medium'
                })
            
            if current_out > upper_out * 1.05:
                alerts.append({
                    'type': 'warning',
                    'station': station,
                    'flow_type': 'out_flow',
                    'message': f'出站客流超过预警阈值！当前: {current_out}, 阈值: {int(upper_out)}',
                    'timestamp': pred_out['timestamps'][i],
                    'level': 'high' if current_out > upper_out * 1.2 else 'medium'
                })
        
        return alerts

    def trend_decomposition(self, historical_data, station, window_size=24):
        station_data = historical_data[historical_data['station'] == station].copy()
        station_data = station_data.sort_values('timestamp')
        
        in_flow = station_data['in_flow'].values
        out_flow = station_data['out_flow'].values
        
        def moving_average(data, window):
            return np.convolve(data, np.ones(window), 'valid') / window
        
        in_trend = moving_average(in_flow, window_size)
        out_trend = moving_average(out_flow, window_size)
        
        pad_length = len(in_flow) - len(in_trend)
        in_trend_padded = np.pad(in_trend, (pad_length // 2, pad_length - pad_length // 2), mode='edge')
        out_trend_padded = np.pad(out_trend, (pad_length // 2, pad_length - pad_length // 2), mode='edge')
        
        in_short_term = in_flow - in_trend_padded
        out_short_term = out_flow - out_trend_padded
        
        in_std = np.std(in_short_term)
        out_std = np.std(out_short_term)
        
        in_anomalies = np.where(np.abs(in_short_term) > 2 * in_std)[0]
        out_anomalies = np.where(np.abs(out_short_term) > 2 * out_std)[0]
        
        anomaly_nodes = []
        for idx in in_anomalies:
            anomaly_nodes.append({
                'timestamp': station_data.iloc[idx]['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'in_flow',
                'value': float(in_flow[idx]),
                'trend': float(in_trend_padded[idx]),
                'deviation': float(in_short_term[idx]),
                'z_score': round(in_short_term[idx] / in_std, 2)
            })
        
        for idx in out_anomalies:
            anomaly_nodes.append({
                'timestamp': station_data.iloc[idx]['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'out_flow',
                'value': float(out_flow[idx]),
                'trend': float(out_trend_padded[idx]),
                'deviation': float(out_short_term[idx]),
                'z_score': round(out_short_term[idx] / out_std, 2)
            })
        
        return {
            'timestamps': station_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'in_flow': {
                'original': in_flow.tolist(),
                'trend': in_trend_padded.tolist(),
                'short_term': in_short_term.tolist()
            },
            'out_flow': {
                'original': out_flow.tolist(),
                'trend': out_trend_padded.tolist(),
                'short_term': out_short_term.tolist()
            },
            'anomaly_nodes': anomaly_nodes
        }

    def fast_slow_line_analysis(self, historical_data, station):
        decomposition = self.trend_decomposition(historical_data, station)
        
        short_term_volatility = np.std(decomposition['in_flow']['short_term'])
        trend_stability = np.std(decomposition['in_flow']['trend'])
        
        volatility_score = min(100, short_term_volatility / 20 * 100)
        stability_score = max(0, 100 - trend_stability / 50 * 100)
        
        peak_hours = self._find_peak_hours(decomposition)
        
        return {
            'station': station,
            'volatility_score': round(volatility_score, 2),
            'stability_score': round(stability_score, 2),
            'peak_hours': peak_hours,
            'classification': '快线模式' if volatility_score > 50 else '慢线模式',
            'decomposition': decomposition
        }

    def _find_peak_hours(self, decomposition):
        flows = np.array(decomposition['in_flow']['original'])
        timestamps = decomposition['timestamps']
        
        hour_counts = defaultdict(list)
        for i, ts in enumerate(timestamps):
            hour = ts.split(' ')[1].split(':')[0]
            hour_counts[hour].append(flows[i])
        
        hour_avg = {h: np.mean(v) for h, v in hour_counts.items()}
        sorted_hours = sorted(hour_avg.items(), key=lambda x: x[1], reverse=True)
        
        return [f"{hour}:00" for hour, _ in sorted_hours[:3]]

    def generate_dispatch_recommendations(self, od_matrix, predictions):
        stations = self.stations
        n = len(stations)
        
        od_array = np.array(od_matrix)
        
        total_flow = od_array.sum(axis=1) + od_array.sum(axis=0)
        station_ranking = sorted(enumerate(total_flow), key=lambda x: x[1], reverse=True)
        
        top_stations = [stations[idx] for idx, _ in station_ranking[:5]]
        
        route_flows = []
        for i in range(n):
            for j in range(n):
                if i != j and od_array[i, j] > 0:
                    route_flows.append({
                        'from': stations[i],
                        'to': stations[j],
                        'from_idx': i,
                        'to_idx': j,
                        'flow': int(od_array[i, j])
                    })
        
        route_flows.sort(key=lambda x: x['flow'], reverse=True)
        
        express_routes = []
        for route in route_flows[:5]:
            if route['flow'] > 15:
                express_routes.append({
                    'route': f"{route['from']} → {route['to']}",
                    'flow': route['flow'],
                    'recommendation': '建议加开区间车' if route['flow'] > 25 else '建议关注'
                })
        
        peak_flow = max(total_flow) if len(total_flow) > 0 else 0
        baseline_interval = 6
        
        if peak_flow > 600:
            interval = 2
            suggestion = '客流高峰，建议加密班次'
        elif peak_flow > 400:
            interval = 3
            suggestion = '客流较大，建议适当缩短间隔'
        elif peak_flow > 200:
            interval = 4
            suggestion = '正常客流，保持当前间隔'
        else:
            interval = 8
            suggestion = '客流较低，可适当延长间隔'
        
        return {
            'top_stations': top_stations,
            'hot_routes': route_flows[:10],
            'express_recommendations': express_routes,
            'interval_recommendation': {
                'peak_interval': interval,
                'baseline_interval': baseline_interval,
                'suggestion': suggestion,
                'peak_flow': int(peak_flow)
            },
            'line_adjustments': self._generate_line_adjustments(route_flows)
        }

    def _generate_line_adjustments(self, route_flows):
        adjustments = []
        
        if len(route_flows) >= 3:
            high_flow_routes = [r for r in route_flows if r['flow'] > 20]
            
            if len(high_flow_routes) >= 2:
                route1, route2 = high_flow_routes[0], high_flow_routes[1]
                if abs(route1['from_idx'] - route2['from_idx']) <= 2 and abs(route1['to_idx'] - route2['to_idx']) <= 2:
                    adjustments.append({
                        'type': '区间车',
                        'stations': f"{route1['from']} - {route1['to']}",
                        'reason': f'该区间客流集中，单向客流达 {route1["flow"]} 人次/小时',
                        'priority': '高'
                    })
        
        congested_stations = set()
        for route in route_flows[:10]:
            congested_stations.add(route['from'])
            congested_stations.add(route['to'])
        
        if len(congested_stations) >= 3:
            adjustments.append({
                'type': '大站快车',
                'stations': ', '.join(sorted(congested_stations)[:5]),
                'reason': '多站客流集中，建议开行大站快车',
                'priority': '中'
            })
        
        return adjustments

    def get_all_stations_alerts(self, historical_data, predictions, threshold=1.1):
        all_alerts = []
        
        for station in self.stations:
            station_data = historical_data[historical_data['station'] == station].tail(1)
            if len(station_data) > 0:
                current_in = station_data.iloc[-1]['in_flow']
                current_out = station_data.iloc[-1]['out_flow']
                
                alerts = self.check_real_time_alerts(
                    {'in_flow': current_in, 'out_flow': current_out},
                    predictions,
                    station
                )
                all_alerts.extend(alerts)
        
        all_alerts.sort(key=lambda x: 0 if x['level'] == 'high' else 1)
        return all_alerts
