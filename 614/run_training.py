import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
import os

os.makedirs('models', exist_ok=True)

df = pd.read_csv('data/fuel_consumption_data.csv', encoding='utf-8-sig')
print(f"Data loaded: {len(df)} records")

label_encoders = {}
categorical_cols = ['车型', '发动机类型', '燃油类型', '变速箱类型', '路况类型', 
                   '交通状况', '天气状况', '驾驶风格']

for col in categorical_cols:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    label_encoders[col] = le

df['功率重量比'] = df['马力(hp)'] / df['整备质量(kg)']
df['排量马力比'] = df['排量(L)'] / df['马力(hp)']
df['负荷指数'] = (df['乘客人数'] * 70 + df['行李重量(kg)']) / df['整备质量(kg)']
df['路况复杂度'] = df['交通状况'] * 2 + df['路况类型']
df['驾驶激进度'] = df['加速强度'] * 0.4 + df['刹车频率'] * 0.4 - df['定速巡航占比'] * 0.2
df['温度影响'] = np.abs(df['环境温度(℃)'] - 25)
df['胎压异常'] = ((df['胎压(bar)'] < 2.2) | (df['胎压(bar)'] > 2.8)).astype(int)

numerical_cols = ['排量(L)', '整备质量(kg)', '马力(hp)', '环境温度(℃)', '平均车速(km/h)',
                 '车速波动', '加速强度', '刹车频率', '定速巡航占比', '海拔变化(m)',
                 '胎压(bar)', '乘客人数', '行李重量(kg)', '功率重量比', '排量马力比',
                 '负荷指数', '路况复杂度', '驾驶激进度', '温度影响', '胎压异常']

scaler = StandardScaler()
df[numerical_cols] = scaler.fit_transform(df[numerical_cols])

feature_names = categorical_cols + numerical_cols
X = df[feature_names]
y = df['百公里油耗(L)']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Train: {len(X_train)}, Test: {len(X_test)}")

model = xgb.XGBRegressor(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=20)

y_pred = model.predict(X_test)
from sklearn.metrics import r2_score, mean_squared_error
print(f"R2: {r2_score(y_test, y_pred):.4f}")
print(f"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.4f}")

joblib.dump(model, 'models/fuel_model.pkl')
joblib.dump({
    'label_encoders': label_encoders,
    'scaler': scaler,
    'feature_names': feature_names
}, 'models/feature_engineer.pkl')

print("Training completed!")
