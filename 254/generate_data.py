import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta

np.random.seed(42)
random.seed(42)


def generate_phone_number():
    prefixes = ['138', '139', '158', '159', '188', '189', '136', '137', '150', '151']
    return f"{random.choice(prefixes)}{random.randint(1000, 9999):04d}{random.randint(1000, 9999):04d}"


def generate_address():
    cities = ['北京市', '上海市', '广州市', '深圳市', '杭州市', '成都市', '武汉市', 
              '南京市', '苏州市', '西安市', '重庆市', '天津市', '长沙市', '郑州市']
    districts = ['朝阳区', '海淀区', '浦东新区', '南山区', '福田区', '西湖区', 
                 '武侯区', '洪山区', '鼓楼区', '天河区', '渝中区', '和平区']
    streets = ['中山路', '人民路', '解放路', '建设路', '文化路', '科技路', 
               '长江路', '黄河路', '珠江路', '松花江路']
    return f"{random.choice(cities)}{random.choice(districts)}{random.choice(streets)}{random.randint(1, 999)}号"


def generate_hospital():
    hospitals = [
        '北京协和医院', '解放军总医院', '上海瑞金医院', '广州中山医院', 
        '华西医院', '湘雅医院', '同济医院', '宣武医院', '瑞金医院',
        '第一人民医院', '中心医院', '人民医院', '中医院', '附属医院'
    ]
    return random.choice(hospitals)


def generate_bank_account():
    banks = ['6222', '6227', '6217', '6216', '6228', '6225', '6226', '6221']
    return f"{random.choice(banks)}{random.randint(1000, 9999):04d}{random.randint(1000, 9999):04d}{random.randint(1000, 9999):04d}"


def generate_name():
    surnames = ['张', '李', '王', '刘', '陈', '杨', '黄', '赵', '周', '吴', '徐', '孙', '马', '朱', '胡']
    names = ['伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋', '勇', '艳', '杰', '娟', '涛', '明', '超', '秀英', '霞', '平']
    return f"{random.choice(surnames)}{random.choice(names)}{random.choice(names) if random.random() > 0.5 else ''}"


def generate_insurance_claims(n_samples=10000, fraud_ratio=0.08, fraud_group_ratio=0.3):
    print(f"Generating {n_samples} insurance claims with {fraud_ratio*100:.1f}% fraud rate...")
    
    n_fraud = int(n_samples * fraud_ratio)
    n_normal = n_samples - n_fraud
    
    n_fraud_groups = int(n_fraud * fraud_group_ratio // 5)
    print(f"Creating {n_fraud_groups} fraud groups with shared identifiers...")
    
    fraud_groups = []
    for g in range(n_fraud_groups):
        group_size = random.randint(3, 8)
        shared_phone = generate_phone_number()
        shared_address = generate_address()
        shared_hospital = generate_hospital()
        shared_bank = generate_bank_account()
        share_type = random.choice(['phone', 'address', 'hospital', 'bank', 'all'])
        fraud_groups.append({
            'group_id': f'FRAUD_GROUP_{g+1:03d}',
            'size': group_size,
            'shared_phone': shared_phone,
            'shared_address': shared_address,
            'shared_hospital': shared_hospital,
            'shared_bank': shared_bank,
            'share_type': share_type,
            'assigned': 0
        })
    
    data = []
    
    accident_types = ['单 vehicle 事故', '多 vehicle 事故', '行人事故', '追尾事故', '侧面碰撞', 
                      '翻滚事故', '盗窃', '火灾', '自然灾害', '其他']
    occupations = ['办公室职员', '技术工人', '服务业', '自由职业', '学生', '退休人员', 
                   '企业高管', '医疗工作者', '教育工作者', '其他']
    regions = ['华东', '华南', '华北', '华中', '西南', '西北', '东北']
    seasons = ['春', '夏', '秋', '冬']
    time_of_day = ['早高峰', '日间', '晚高峰', '夜间']
    weather = ['晴', '雨', '雪', '雾', '冰雹']
    vehicle_types = ['轿车', 'SUV', '货车', '客车', '摩托车', '新能源汽车']
    coverage_types = ['交强险', '商业险-基本', '商业险-全险', '综合险']
    
    fraud_idx = 0
    
    for i in range(n_samples):
        is_fraud = 1 if i < n_fraud else 0
        
        age = int(np.random.normal(40, 15))
        age = max(18, min(85, age))
        
        gender = random.choice(['男', '女'])
        name = generate_name()
        
        occupation = random.choice(occupations)
        region = random.choice(regions)
        marital_status = random.choice(['未婚', '已婚', '离异', '丧偶'])
        driving_years = max(0, age - 18 - int(np.random.normal(5, 3)))
        annual_income = int(np.random.normal(150000, 80000))
        annual_income = max(30000, annual_income)
        
        phone = generate_phone_number()
        address = generate_address()
        bank_account = generate_bank_account()
        
        hospital = generate_hospital()
        
        group_id = None
        
        if is_fraud and fraud_idx < len(fraud_groups) * 5:
            group_idx = fraud_idx // 5
            if group_idx < len(fraud_groups) and fraud_groups[group_idx]['assigned'] < fraud_groups[group_idx]['size']:
                group = fraud_groups[group_idx]
                group_id = group['group_id']
                group['assigned'] += 1
                
                share_type = group['share_type']
                if share_type in ['phone', 'all']:
                    phone = group['shared_phone']
                if share_type in ['address', 'all']:
                    address = group['shared_address']
                if share_type in ['hospital', 'all']:
                    hospital = group['shared_hospital']
                if share_type in ['bank', 'all']:
                    bank_account = group['shared_bank']
        
        accident_type = random.choice(accident_types)
        accident_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 364))
        accident_season = seasons[(accident_date.month - 1) // 3]
        accident_time = random.choice(time_of_day)
        accident_weather = random.choice(weather)
        
        vehicle_age = int(np.random.normal(5, 3))
        vehicle_age = max(0, min(20, vehicle_age))
        vehicle_type = random.choice(vehicle_types)
        vehicle_value = int(np.random.normal(200000, 100000))
        vehicle_value = max(50000, min(1000000, vehicle_value))
        
        coverage_type = random.choice(coverage_types)
        policy_premium = int(vehicle_value * np.random.uniform(0.02, 0.08))
        policy_duration = random.choice([1, 2, 3])
        
        past_claims_count = np.random.poisson(1)
        past_claims_total = past_claims_count * int(np.random.normal(8000, 5000))
        past_fraud_count = 0
        
        if is_fraud:
            past_fraud_count = np.random.binomial(past_claims_count, 0.3)
            fraud_idx += 1
        
        medical_expense = int(np.random.normal(5000, 3000))
        medical_expense = max(0, medical_expense)
        
        vehicle_repair_cost = int(np.random.normal(15000, 10000))
        vehicle_repair_cost = max(0, vehicle_repair_cost)
        
        third_party_injury = random.choice([0, 1])
        third_party_medical = int(third_party_injury * np.random.normal(8000, 5000))
        third_party_medical = max(0, third_party_medical)
        
        third_party_property_damage = int(np.random.normal(5000, 3000))
        third_party_property_damage = max(0, third_party_property_damage)
        
        total_claim_amount = medical_expense + vehicle_repair_cost + third_party_medical + third_party_property_damage
        
        deductible = random.choice([0, 500, 1000, 2000, 5000])
        claim_amount = max(0, total_claim_amount - deductible)
        
        hospital_days = int(np.random.normal(3, 5))
        hospital_days = max(0, hospital_days)
        
        disability_level = random.choice([0, 1, 2, 3, 4, 5])
        disability_level = disability_level if hospital_days > 0 else 0
        
        police_report = random.choice([0, 1])
        witness_present = random.choice([0, 1])
        photos_provided = random.choice([0, 1])
        repair_invoice = random.choice([0, 1])
        medical_invoice = random.choice([0, 1])
        
        claim_processing_days = random.randint(1, 60)
        
        if is_fraud:
            medical_expense = int(medical_expense * np.random.uniform(1.5, 3.0))
            vehicle_repair_cost = int(vehicle_repair_cost * np.random.uniform(1.3, 2.5))
            total_claim_amount = medical_expense + vehicle_repair_cost + third_party_medical + third_party_property_damage
            claim_amount = max(0, total_claim_amount - deductible)
            
            police_report = random.choice([0, 1])
            witness_present = random.choice([0, 1])
            photos_provided = random.choice([0, 1])
            
            past_claims_count = int(past_claims_count * np.random.uniform(1.5, 3.0))
            past_fraud_count = np.random.binomial(past_claims_count, 0.4)
        
        claim_ratio = claim_amount / policy_premium if policy_premium > 0 else 0
        expense_to_value_ratio = total_claim_amount / vehicle_value if vehicle_value > 0 else 0
        
        same_day_claim = 1 if claim_processing_days <= 1 else 0
        high_value_ratio = 1 if expense_to_value_ratio > 0.5 else 0
        
        suspicious_time = 1 if accident_time in ['夜间', '晚高峰'] and accident_weather in ['晴', '阴'] else 0
        
        fraud_indicators = 0
        if past_fraud_count > 0:
            fraud_indicators += 1
        if not police_report:
            fraud_indicators += 1
        if not witness_present:
            fraud_indicators += 1
        if same_day_claim:
            fraud_indicators += 1
        if high_value_ratio:
            fraud_indicators += 1
        if suspicious_time:
            fraud_indicators += 1
        
        data.append({
            'claim_id': f'CLAIM{i+1:08d}',
            'is_fraud': is_fraud,
            'group_id': group_id,
            
            'name': name,
            'phone': phone,
            'address': address,
            'bank_account': bank_account,
            'hospital': hospital,
            
            'age': age,
            'gender': gender,
            'occupation': occupation,
            'region': region,
            'marital_status': marital_status,
            'driving_years': driving_years,
            'annual_income': annual_income,
            
            'accident_type': accident_type,
            'accident_date': accident_date.strftime('%Y-%m-%d'),
            'accident_season': accident_season,
            'accident_time': accident_time,
            'accident_weather': accident_weather,
            
            'vehicle_age': vehicle_age,
            'vehicle_type': vehicle_type,
            'vehicle_value': vehicle_value,
            
            'coverage_type': coverage_type,
            'policy_premium': policy_premium,
            'policy_duration': policy_duration,
            
            'past_claims_count': past_claims_count,
            'past_claims_total': past_claims_total,
            'past_fraud_count': past_fraud_count,
            
            'medical_expense': medical_expense,
            'vehicle_repair_cost': vehicle_repair_cost,
            'third_party_injury': third_party_injury,
            'third_party_medical': third_party_medical,
            'third_party_property_damage': third_party_property_damage,
            'total_claim_amount': total_claim_amount,
            'deductible': deductible,
            'claim_amount': claim_amount,
            'hospital_days': hospital_days,
            'disability_level': disability_level,
            
            'police_report': police_report,
            'witness_present': witness_present,
            'photos_provided': photos_provided,
            'repair_invoice': repair_invoice,
            'medical_invoice': medical_invoice,
            'claim_processing_days': claim_processing_days,
            
            'claim_ratio': claim_ratio,
            'expense_to_value_ratio': expense_to_value_ratio,
            'same_day_claim': same_day_claim,
            'high_value_ratio': high_value_ratio,
            'suspicious_time': suspicious_time,
            'fraud_indicators': fraud_indicators
        })
    
    df = pd.DataFrame(data)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    n_groups = df['group_id'].notna().sum()
    print(f"Generated {len(df)} claims: {df['is_fraud'].sum()} fraud ({df['is_fraud'].mean()*100:.2f}%)")
    print(f"  - {n_groups} claims in fraud groups with shared identifiers")
    
    return df


def save_data(df, train_path='data/train.csv', test_path='data/test.csv', full_path='data/claims_full.csv', test_size=0.2):
    import os
    os.makedirs('data', exist_ok=True)
    
    from sklearn.model_selection import train_test_split
    
    df.to_csv(full_path, index=False, encoding='utf-8-sig')
    
    train_df, test_df = train_test_split(df, test_size=test_size, random_state=42, stratify=df['is_fraud'])
    
    train_df.to_csv(train_path, index=False, encoding='utf-8-sig')
    test_df.to_csv(test_path, index=False, encoding='utf-8-sig')
    
    print(f"Full data: {len(df)} samples saved to {full_path}")
    print(f"Training data: {len(train_df)} samples saved to {train_path}")
    print(f"Test data: {len(test_df)} samples saved to {test_path}")
    
    return train_df, test_df


if __name__ == '__main__':
    df = generate_insurance_claims(n_samples=10000, fraud_ratio=0.08, fraud_group_ratio=0.3)
    train_df, test_df = save_data(df)
    
    print("\nSample data:")
    print(df[['claim_id', 'is_fraud', 'group_id', 'name', 'phone', 'hospital']].head())
    print("\nData columns:")
    print(df.columns.tolist())
