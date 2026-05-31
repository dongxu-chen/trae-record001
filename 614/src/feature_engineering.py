import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib

class FeatureEngineer:
    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_names = []
        
    def fit_transform(self, df):
        df_processed = df.copy()
        
        categorical_cols = ['车型', '发动机类型', '燃油类型', '变速箱类型', '路况类型', 
                           '交通状况', '天气状况', '驾驶风格']
        
        for col in categorical_cols:
            le = LabelEncoder()
            df_processed[col] = le.fit_transform(df_processed[col])
            self.label_encoders[col] = le
        
        df_processed['功率重量比'] = df_processed['马力(hp)'] / df_processed['整备质量(kg)']
        df_processed['排量马力比'] = df_processed['排量(L)'] / df_processed['马力(hp)']
        df_processed['负荷指数'] = (df_processed['乘客人数'] * 70 + df_processed['行李重量(kg)']) / df_processed['整备质量(kg)']
        df_processed['路况复杂度'] = df_processed['交通状况'] * 2 + df_processed['路况类型']
        df_processed['驾驶激进度'] = df_processed['加速强度'] * 0.4 + df_processed['刹车频率'] * 0.4 - df_processed['定速巡航占比'] * 0.2
        df_processed['温度影响'] = np.abs(df_processed['环境温度(℃)'] - 25)
        df_processed['胎压异常'] = (df_processed['胎压(bar)'] < 2.2) | (df_processed['胎压(bar)'] > 2.8)
        df_processed['胎压异常'] = df_processed['胎压异常'].astype(int)
        
        df_processed['加速度能量'] = df_processed['纵向加速度均值(m/s²)'] ** 2 + df_processed['横向加速度均值(m/s²)'] ** 2
        df_processed['驾驶平稳性指数'] = 1 / (1 + df_processed['纵向加速度标准差(m/s²)'] + df_processed['横向加速度标准差(m/s²)'])
        df_processed['激进驾驶指数'] = (df_processed['急加速事件次数'] * 0.4 + 
                                       df_processed['急刹车事件次数'] * 0.35 + 
                                       df_processed['急变道事件次数'] * 0.25)
        df_processed['经济驾驶指数'] = df_processed['定速巡航占比'] * 0.4 + df_processed['驾驶平稳性指数'] * 0.6
        df_processed['加减速能耗指数'] = df_processed['加减速切换频率(次/小时)'] * df_processed['纵向加速度均值(m/s²)']
        df_processed['怠速损失指数'] = df_processed['怠速时间占比'] * df_processed['平均车速(km/h)'].clip(lower=1)
        df_processed['加速度冲击指数'] = df_processed['加速度变化率均值(m/s³)'] * df_processed['纵向加速度均值(m/s²)']
        df_processed['总激烈事件'] = df_processed['急加速事件次数'] + df_processed['急刹车事件次数'] + df_processed['急变道事件次数']
        df_processed['油门效率'] = 1 / (1 + df_processed['大油门持续占比'])
        df_processed['三维加速度模'] = np.sqrt(
            df_processed['纵向加速度均值(m/s²)'] ** 2 + 
            df_processed['横向加速度均值(m/s²)'] ** 2 + 
            9.8 ** 2
        )
        
        sensor_cols = ['纵向加速度均值(m/s²)', '纵向加速度标准差(m/s²)', 
                      '横向加速度均值(m/s²)', '横向加速度标准差(m/s²)',
                      '急加速事件次数', '急刹车事件次数', '急变道事件次数',
                      '加减速切换频率(次/小时)', '怠速时间占比', '大油门持续占比',
                      '加速度变化率均值(m/s³)']
        
        derived_sensor_cols = ['加速度能量', '驾驶平稳性指数', '激进驾驶指数', '经济驾驶指数',
                               '加减速能耗指数', '怠速损失指数', '加速度冲击指数', 
                               '总激烈事件', '油门效率', '三维加速度模']
        
        numerical_cols = ['排量(L)', '整备质量(kg)', '马力(hp)', '环境温度(℃)', '平均车速(km/h)',
                         '车速波动', '加速强度', '刹车频率', '定速巡航占比', '海拔变化(m)',
                         '胎压(bar)', '乘客人数', '行李重量(kg)', '功率重量比', '排量马力比',
                         '负荷指数', '路况复杂度', '驾驶激进度', '温度影响', '胎压异常'] + sensor_cols + derived_sensor_cols
        
        df_processed[numerical_cols] = self.scaler.fit_transform(df_processed[numerical_cols])
        
        self.feature_names = categorical_cols + numerical_cols
        
        X = df_processed[self.feature_names]
        y = df['百公里油耗(L)'] if '百公里油耗(L)' in df.columns else None
        
        return X, y
    
    def transform(self, df):
        df_processed = df.copy()
        
        categorical_cols = ['车型', '发动机类型', '燃油类型', '变速箱类型', '路况类型', 
                           '交通状况', '天气状况', '驾驶风格']
        
        for col in categorical_cols:
            if col in self.label_encoders:
                le = self.label_encoders[col]
                df_processed[col] = df_processed[col].map(
                    lambda x: le.transform([x])[0] if x in le.classes_ else 0
                )
        
        df_processed['功率重量比'] = df_processed['马力(hp)'] / df_processed['整备质量(kg)']
        df_processed['排量马力比'] = df_processed['排量(L)'] / df_processed['马力(hp)']
        df_processed['负荷指数'] = (df_processed['乘客人数'] * 70 + df_processed['行李重量(kg)']) / df_processed['整备质量(kg)']
        df_processed['路况复杂度'] = df_processed['交通状况'] * 2 + df_processed['路况类型']
        df_processed['驾驶激进度'] = df_processed['加速强度'] * 0.4 + df_processed['刹车频率'] * 0.4 - df_processed['定速巡航占比'] * 0.2
        df_processed['温度影响'] = np.abs(df_processed['环境温度(℃)'] - 25)
        df_processed['胎压异常'] = (df_processed['胎压(bar)'] < 2.2) | (df_processed['胎压(bar)'] > 2.8)
        df_processed['胎压异常'] = df_processed['胎压异常'].astype(int)
        
        df_processed['加速度能量'] = df_processed['纵向加速度均值(m/s²)'] ** 2 + df_processed['横向加速度均值(m/s²)'] ** 2
        df_processed['驾驶平稳性指数'] = 1 / (1 + df_processed['纵向加速度标准差(m/s²)'] + df_processed['横向加速度标准差(m/s²)'])
        df_processed['激进驾驶指数'] = (df_processed['急加速事件次数'] * 0.4 + 
                                       df_processed['急刹车事件次数'] * 0.35 + 
                                       df_processed['急变道事件次数'] * 0.25)
        df_processed['经济驾驶指数'] = df_processed['定速巡航占比'] * 0.4 + df_processed['驾驶平稳性指数'] * 0.6
        df_processed['加减速能耗指数'] = df_processed['加减速切换频率(次/小时)'] * df_processed['纵向加速度均值(m/s²)']
        df_processed['怠速损失指数'] = df_processed['怠速时间占比'] * df_processed['平均车速(km/h)'].clip(lower=1)
        df_processed['加速度冲击指数'] = df_processed['加速度变化率均值(m/s³)'] * df_processed['纵向加速度均值(m/s²)']
        df_processed['总激烈事件'] = df_processed['急加速事件次数'] + df_processed['急刹车事件次数'] + df_processed['急变道事件次数']
        df_processed['油门效率'] = 1 / (1 + df_processed['大油门持续占比'])
        df_processed['三维加速度模'] = np.sqrt(
            df_processed['纵向加速度均值(m/s²)'] ** 2 + 
            df_processed['横向加速度均值(m/s²)'] ** 2 + 
            9.8 ** 2
        )
        
        sensor_cols = ['纵向加速度均值(m/s²)', '纵向加速度标准差(m/s²)', 
                      '横向加速度均值(m/s²)', '横向加速度标准差(m/s²)',
                      '急加速事件次数', '急刹车事件次数', '急变道事件次数',
                      '加减速切换频率(次/小时)', '怠速时间占比', '大油门持续占比',
                      '加速度变化率均值(m/s³)']
        
        derived_sensor_cols = ['加速度能量', '驾驶平稳性指数', '激进驾驶指数', '经济驾驶指数',
                               '加减速能耗指数', '怠速损失指数', '加速度冲击指数', 
                               '总激烈事件', '油门效率', '三维加速度模']
        
        numerical_cols = ['排量(L)', '整备质量(kg)', '马力(hp)', '环境温度(℃)', '平均车速(km/h)',
                         '车速波动', '加速强度', '刹车频率', '定速巡航占比', '海拔变化(m)',
                         '胎压(bar)', '乘客人数', '行李重量(kg)', '功率重量比', '排量马力比',
                         '负荷指数', '路况复杂度', '驾驶激进度', '温度影响', '胎压异常'] + sensor_cols + derived_sensor_cols
        
        df_processed[numerical_cols] = self.scaler.transform(df_processed[numerical_cols])
        
        X = df_processed[self.feature_names]
        
        return X
    
    def save(self, path):
        joblib.dump({
            'label_encoders': self.label_encoders,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }, path)
    
    @classmethod
    def load(cls, path):
        data = joblib.load(path)
        fe = cls()
        fe.label_encoders = data['label_encoders']
        fe.scaler = data['scaler']
        fe.feature_names = data['feature_names']
        return fe
