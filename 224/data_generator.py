import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_hr_data(num_samples=2000, random_seed=42):
    np.random.seed(random_seed)
    
    data = {}
    
    data['EmployeeID'] = np.arange(1, num_samples + 1)
    
    data['Age'] = np.random.randint(22, 60, num_samples)
    data['Gender'] = np.random.choice(['Male', 'Female'], num_samples, p=[0.55, 0.45])
    data['MaritalStatus'] = np.random.choice(['Single', 'Married', 'Divorced'], num_samples, p=[0.4, 0.5, 0.1])
    
    data['Department'] = np.random.choice(
        ['IT', 'Sales', 'HR', 'Finance', 'Operations', 'Marketing', 'R&D'],
        num_samples,
        p=[0.2, 0.18, 0.08, 0.12, 0.18, 0.12, 0.12]
    )
    
    data['JobLevel'] = np.random.choice(
        ['Entry', 'Junior', 'Mid', 'Senior', 'Executive'],
        num_samples,
        p=[0.25, 0.3, 0.25, 0.15, 0.05]
    )
    
    data['YearsAtCompany'] = np.random.exponential(scale=5, size=num_samples).astype(int)
    data['YearsAtCompany'] = np.clip(data['YearsAtCompany'], 0, 25)
    
    data['YearsInCurrentRole'] = np.random.exponential(scale=3, size=num_samples).astype(int)
    data['YearsInCurrentRole'] = np.clip(data['YearsInCurrentRole'], 0, 15)
    data['YearsInCurrentRole'] = np.minimum(data['YearsInCurrentRole'], data['YearsAtCompany'])
    
    data['YearsSinceLastPromotion'] = np.random.randint(0, 10, num_samples)
    data['YearsSinceLastPromotion'] = np.minimum(data['YearsSinceLastPromotion'], data['YearsAtCompany'])
    
    data['NumPromotions'] = np.random.randint(0, 6, num_samples)
    data['NumPromotions'] = np.minimum(data['NumPromotions'], data['YearsAtCompany'] // 2)
    
    base_salary = {
        'Entry': 35000, 'Junior': 50000, 'Mid': 75000, 'Senior': 110000, 'Executive': 180000
    }
    data['MonthlyIncome'] = np.array([
        base_salary[level] * np.random.uniform(0.9, 1.2)
        for level in data['JobLevel']
    ])
    data['MonthlyIncome'] = data['MonthlyIncome'].round(2)
    
    data['SalaryHikePercent'] = np.random.normal(loc=8, scale=3, size=num_samples).round(1)
    data['SalaryHikePercent'] = np.clip(data['SalaryHikePercent'], 0, 25)
    
    data['JobSatisfaction'] = np.random.randint(1, 5, num_samples)
    data['EnvironmentSatisfaction'] = np.random.randint(1, 5, num_samples)
    data['RelationshipSatisfaction'] = np.random.randint(1, 5, num_samples)
    data['WorkLifeBalance'] = np.random.randint(1, 5, num_samples)
    
    data['TrainingTimesLastYear'] = np.random.poisson(lam=2.5, size=num_samples)
    data['TrainingTimesLastYear'] = np.clip(data['TrainingTimesLastYear'], 0, 10)
    
    data['PerformanceRating'] = np.random.choice([1, 2, 3, 4, 5], num_samples, p=[0.05, 0.15, 0.4, 0.3, 0.1])
    
    data['OverTime'] = np.random.choice(['Yes', 'No'], num_samples, p=[0.3, 0.7])
    
    data['AverageMonthlyHours'] = np.random.normal(loc=160, scale=20, size=num_samples).astype(int)
    data['AverageMonthlyHours'] = np.clip(data['AverageMonthlyHours'], 120, 220)
    
    data['AbsentDays'] = np.random.poisson(lam=5, size=num_samples)
    data['AbsentDays'] = np.clip(data['AbsentDays'], 0, 20)
    
    data['DistanceFromHome'] = np.random.randint(1, 30, num_samples)
    
    data['NumCompaniesWorked'] = np.random.randint(0, 10, num_samples)
    
    data['Attrition'] = 0
    
    for i in range(num_samples):
        prob = 0.1
        
        if data['JobSatisfaction'][i] <= 2:
            prob += 0.15
        if data['EnvironmentSatisfaction'][i] <= 2:
            prob += 0.1
        if data['OverTime'][i] == 'Yes':
            prob += 0.12
        if data['YearsAtCompany'][i] <= 2:
            prob += 0.1
        if data['NumCompaniesWorked'][i] >= 5:
            prob += 0.1
        if data['YearsSinceLastPromotion'][i] >= 5:
            prob += 0.08
        if data['AverageMonthlyHours'][i] >= 190:
            prob += 0.1
        if data['WorkLifeBalance'][i] <= 2:
            prob += 0.1
        if data['SalaryHikePercent'][i] <= 3:
            prob += 0.08
        if data['PerformanceRating'][i] >= 4:
            prob -= 0.05
        
        prob = np.clip(prob, 0.02, 0.8)
        data['Attrition'][i] = np.random.binomial(1, prob)
    
    df = pd.DataFrame(data)
    
    return df

if __name__ == "__main__":
    df = generate_hr_data(num_samples=2000)
    df.to_csv('hr_employee_data.csv', index=False)
    print(f"生成HR数据完成，共 {len(df)} 条记录")
    print(f"\n离职率: {df['Attrition'].mean():.2%}")
    print(f"\n特征列: {list(df.columns)}")
    print(f"\n前5行数据:")
    print(df.head())
