import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta

DTC_DATABASE = {
    'P0101': {'description': '质量空气流量（MAF）传感器电路范围/性能', 'severity': 'high', 'fuel_impact_pct': 15, 'category': 'sensor', 'symptoms': ['动力不足', '怠速不稳', '油耗增加10-20%']},
    'P0102': {'description': '质量空气流量（MAF）传感器电路电压低', 'severity': 'medium', 'fuel_impact_pct': 12, 'category': 'sensor', 'symptoms': ['启动困难', '油耗增加8-15%']},
    'P0113': {'description': '进气温度（IAT）传感器电路电压高', 'severity': 'medium', 'fuel_impact_pct': 8, 'category': 'sensor', 'symptoms': ['冷启动困难', '油耗增加5-10%']},
    'P0120': {'description': '节气门位置传感器A电路', 'severity': 'high', 'fuel_impact_pct': 20, 'category': 'sensor', 'symptoms': ['加速无力', '油耗增加15-25%']},
    'P0171': {'description': '燃油系统过稀（Bank 1）', 'severity': 'high', 'fuel_impact_pct': 18, 'category': 'fuel', 'symptoms': ['怠速抖动', '油耗增加12-20%']},
    'P0174': {'description': '燃油系统过稀（Bank 2）', 'severity': 'high', 'fuel_impact_pct': 18, 'category': 'fuel', 'symptoms': ['怠速抖动', '油耗增加12-20%']},
    'P0172': {'description': '燃油系统过浓（Bank 1）', 'severity': 'high', 'fuel_impact_pct': 22, 'category': 'fuel', 'symptoms': ['冒黑烟', '油耗增加15-25%']},
    'P0201': {'description': '喷油器1电路故障', 'severity': 'high', 'fuel_impact_pct': 25, 'category': 'fuel', 'symptoms': ['缺缸', '油耗增加20-30%']},
    'P0300': {'description': '检测到随机/多缸失火', 'severity': 'high', 'fuel_impact_pct': 30, 'category': 'ignition', 'symptoms': ['发动机抖动', '油耗增加20-35%']},
    'P0301': {'description': '检测到1缸失火', 'severity': 'high', 'fuel_impact_pct': 25, 'category': 'ignition', 'symptoms': ['怠速抖动', '油耗增加18-28%']},
    'P0340': {'description': '凸轮轴位置传感器电路', 'severity': 'high', 'fuel_impact_pct': 20, 'category': 'sensor', 'symptoms': ['启动困难', '油耗增加15-25%']},
    'P0351': {'description': '点火线圈A主/次电路', 'severity': 'high', 'fuel_impact_pct': 22, 'category': 'ignition', 'symptoms': ['缺缸', '油耗增加18-25%']},
    'P0401': {'description': '废气再循环（EGR）流量不足', 'severity': 'medium', 'fuel_impact_pct': 10, 'category': 'emission', 'symptoms': ['动力下降', '油耗增加8-12%']},
    'P0420': {'description': '催化转化器系统效率低于阈值（Bank 1）', 'severity': 'medium', 'fuel_impact_pct': 15, 'category': 'emission', 'symptoms': ['排放超标', '油耗增加10-18%']},
    'P0455': {'description': '蒸发排放系统检测到大泄漏', 'severity': 'medium', 'fuel_impact_pct': 5, 'category': 'emission', 'symptoms': ['燃油气味', '油耗增加3-7%']},
    'P0500': {'description': '车速传感器（VSS）故障', 'severity': 'medium', 'fuel_impact_pct': 12, 'category': 'sensor', 'symptoms': ['换挡异常', '油耗增加8-15%']},
    'P0505': {'description': '怠速空气控制（IAC）阀电路', 'severity': 'medium', 'fuel_impact_pct': 10, 'category': 'sensor', 'symptoms': ['怠速不稳', '油耗增加6-12%']},
    'P0650': {'description': '故障指示灯（MIL）控制电路', 'severity': 'low', 'fuel_impact_pct': 3, 'category': 'electrical', 'symptoms': ['故障灯异常', '油耗影响小']},
    'P0700': {'description': '变速箱控制系统故障', 'severity': 'high', 'fuel_impact_pct': 20, 'category': 'transmission', 'symptoms': ['换挡顿挫', '油耗增加15-25%']},
    'P2181': {'description': '冷却系统故障（冷却液恒温器/传感器）', 'severity': 'medium', 'fuel_impact_pct': 12, 'category': 'cooling', 'symptoms': ['过热警告', '油耗增加8-15%']},
    'P2195': {'description': '空燃比不平衡', 'severity': 'high', 'fuel_impact_pct': 18, 'category': 'fuel', 'symptoms': ['油耗飙升', '油耗增加15-20%']}
}

SEVERITY_COLORS = {
    'low': '#10b981',
    'medium': '#f59e0b',
    'high': '#ef4444'
}

SEVERITY_LABELS = {
    'low': '轻微',
    'medium': '中等',
    'high': '严重'
}

CATEGORIES = {
    'sensor': '传感器',
    'fuel': '燃油系统',
    'ignition': '点火系统',
    'emission': '排放系统',
    'electrical': '电气系统',
    'transmission': '变速箱',
    'cooling': '冷却系统'
}


class VehicleHealthAnalyzer:
    def __init__(self, data_dir='user_data'):
        self.data_dir = data_dir
        self.dtc_file = os.path.join(data_dir, 'dtc_records.csv')
        self.vehicle_file = os.path.join(data_dir, 'vehicle_profile.json')
        
    def lookup_dtc(self, dtc_code):
        code = dtc_code.upper().strip()
        if code in DTC_DATABASE:
            return DTC_DATABASE[code]
        return None
    
    def add_dtc(self, dtc_code, notes=''):
        dtcs = pd.read_csv(self.dtc_file, encoding='utf-8-sig')
        dtc_info = self.lookup_dtc(dtc_code)
        
        dtc_id = f"DTC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        new_dtc = {
            'dtc_id': dtc_id,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'dtc_code': dtc_code.upper(),
            'description': dtc_info['description'] if dtc_info else '未知故障码',
            'severity': dtc_info['severity'] if dtc_info else 'medium',
            'status': 'active',
            'cleared_date': '',
            'fuel_impact_estimate': dtc_info['fuel_impact_pct'] if dtc_info else 5,
            'notes': notes
        }
        
        dtcs = pd.concat([dtcs, pd.DataFrame([new_dtc])], ignore_index=True)
        dtcs.to_csv(self.dtc_file, index=False, encoding='utf-8-sig')
        
        return dtc_id, dtc_info
    
    def clear_dtc(self, dtc_id):
        dtcs = pd.read_csv(self.dtc_file, encoding='utf-8-sig')
        if dtc_id in dtcs['dtc_id'].values:
            dtcs.loc[dtcs['dtc_id'] == dtc_id, 'status'] = 'cleared'
            dtcs.loc[dtcs['dtc_id'] == dtc_id, 'cleared_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            dtcs.to_csv(self.dtc_file, index=False, encoding='utf-8-sig')
            return True
        return False
    
    def get_active_dtcs(self):
        dtcs = pd.read_csv(self.dtc_file, encoding='utf-8-sig')
        return dtcs[dtcs['status'] == 'active'].sort_values('date', ascending=False)
    
    def get_all_dtcs(self):
        return pd.read_csv(self.dtc_file, encoding='utf-8-sig').sort_values('date', ascending=False)
    
    def get_total_fuel_impact(self):
        active = self.get_active_dtcs()
        if len(active) == 0:
            return 0, []
        
        impacts = []
        total_impact = 1.0
        
        for _, row in active.iterrows():
            dtc_info = self.lookup_dtc(row['dtc_code'])
            if dtc_info:
                impact_pct = dtc_info['fuel_impact_pct']
                impact_factor = 1 + (impact_pct / 100)
                impacts.append({
                    'code': row['dtc_code'],
                    'description': row['description'],
                    'severity': row['severity'],
                    'impact_pct': impact_pct
                })
                total_impact *= impact_factor
        
        return (total_impact - 1) * 100, impacts
    
    def generate_health_report(self):
        active_dtcs = self.get_active_dtcs()
        total_impact, impacts = self.get_total_fuel_impact()
        
        report = {
            'active_dtc_count': len(active_dtcs),
            'total_fuel_impact_pct': total_impact,
            'high_severity_count': len(active_dtcs[active_dtcs['severity'] == 'high']),
            'medium_severity_count': len(active_dtcs[active_dtcs['severity'] == 'medium']),
            'low_severity_count': len(active_dtcs[active_dtcs['severity'] == 'low']),
            'dtc_details': impacts
        }
        
        if len(active_dtcs) == 0:
            report['health_status'] = 'good'
            report['health_score'] = 100
        elif report['high_severity_count'] > 0:
            report['health_status'] = 'critical'
            report['health_score'] = max(30, 100 - total_impact * 2)
        elif report['medium_severity_count'] > 2:
            report['health_status'] = 'warning'
            report['health_score'] = max(50, 100 - total_impact * 1.5)
        else:
            report['health_status'] = 'fair'
            report['health_score'] = max(70, 100 - total_impact)
        
        return report
    
    def get_maintenance_recommendations(self):
        active = self.get_active_dtcs()
        recommendations = []
        
        for _, row in active.iterrows():
            dtc_info = self.lookup_dtc(row['dtc_code'])
            if dtc_info:
                rec = {
                    'code': row['dtc_code'],
                    'description': row['description'],
                    'severity': row['severity'],
                    'priority': '紧急' if row['severity'] == 'high' else '建议' if row['severity'] == 'medium' else '关注',
                    'action': self._get_recommendation_action(row['dtc_code'], dtc_info),
                    'fuel_savings_estimate': dtc_info['fuel_impact_pct']
                }
                recommendations.append(rec)
        
        return sorted(recommendations, key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['severity']])
    
    def _get_recommendation_action(self, dtc_code, dtc_info):
        category = dtc_info.get('category', 'general')
        
        recommendations_map = {
            'sensor': '请检查相关传感器连接，清洁或更换传感器',
            'fuel': '请检查喷油嘴、燃油滤清器和氧传感器，必要时清洗或更换',
            'ignition': '请检查火花塞、点火线圈，必要时更换',
            'emission': '请检查催化转化器、EGR阀或碳罐系统',
            'electrical': '请检查相关电路连接和保险丝',
            'transmission': '请立即到专业维修店检查变速箱',
            'cooling': '请检查冷却液液位、节温器和水泵',
            'general': '请尽快到专业维修店进行诊断和维修'
        }
        
        return recommendations_map.get(category, recommendations_map['general'])
    
    def search_dtc_by_keyword(self, keyword):
        results = []
        for code, info in DTC_DATABASE.items():
            if keyword.lower() in code.lower() or keyword in info['description']:
                results.append({
                    'code': code,
                    'description': info['description'],
                    'severity': info['severity'],
                    'fuel_impact_pct': info['fuel_impact_pct'],
                    'category': info['category'],
                    'symptoms': info['symptoms']
                })
        return results
