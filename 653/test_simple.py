import sys
import io

old_stdout = sys.stdout
sys.stdout = buffer = io.StringIO()

try:
    print("开始测试...")
    
    print("1. 导入模块...")
    import pandas as pd
    from train_model import SalaryPredictor
    print("   导入成功")
    
    print("2. 加载数据...")
    df = pd.read_csv("job_salary_data.csv", encoding="utf-8-sig")
    print(f"   数据加载成功，共 {len(df)} 条")
    
    print("3. 训练模型（使用少量数据）...")
    predictor = SalaryPredictor()
    predictor.train(df.head(200))
    print("   训练完成")
    
    print("4. 测试预测...")
    test_data = pd.DataFrame([{
        "岗位标题": "Python开发工程师",
        "岗位描述": "负责后端开发",
        "地区": "北京",
        "公司规模": "150-500人",
        "学历要求": "本科"
    }])
    result = predictor.predict(test_data)
    print(f"   预测结果: {result['预测薪资下限'].values[0]} - {result['预测薪资上限'].values[0]}")
    
    print("\n✅ 所有测试成功！")
    
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

finally:
    output = buffer.getvalue()
    sys.stdout = old_stdout
    print(output)
    
    with open("test_output.txt", "w", encoding="utf-8") as f:
        f.write(output)
