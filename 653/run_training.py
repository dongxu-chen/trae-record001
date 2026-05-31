import sys
sys.stdout.reconfigure(encoding='utf-8')

print("="*60, flush=True)
print("开始训练薪资预测模型", flush=True)
print("="*60, flush=True)

import pandas as pd
from train_model import SalaryPredictor

print("\n1. 加载数据...", flush=True)
df = pd.read_csv("job_salary_data.csv", encoding="utf-8-sig")
print(f"   数据量: {len(df)} 条", flush=True)

print("\n2. 训练模型...", flush=True)
predictor = SalaryPredictor()
predictor.train(df)

print("\n3. 验证模型...", flush=True)
test_data = pd.DataFrame([
    {
        "岗位标题": "Python开发工程师",
        "岗位描述": "负责后端开发，熟悉Python、Django、MySQL",
        "地区": "北京",
        "公司规模": "150-500人",
        "学历要求": "本科"
    },
    {
        "岗位标题": "数据科学家",
        "岗位描述": "负责机器学习模型开发和数据分析",
        "地区": "上海",
        "公司规模": "1000人以上",
        "学历要求": "硕士"
    }
])

results = predictor.predict(test_data)
print("\n   测试预测结果:", flush=True)
for i, row in results.iterrows():
    print(f"   {row['岗位标题']} ({row['地区']}): {row['预测薪资下限']:,} - {row['预测薪资上限']:,} 元/月", flush=True)

print("\n" + "="*60, flush=True)
print("模型训练完成！", flush=True)
print("="*60, flush=True)
