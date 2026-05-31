import os
import sys

def test_imports():
    print("="*60)
    print("测试 1: 检查依赖包导入")
    print("="*60)
    try:
        import pandas
        import numpy
        import xgboost
        import shap
        import streamlit
        import sklearn
        import jieba
        import plotly
        print("✅ 所有依赖包导入成功")
        return True
    except ImportError as e:
        print(f"❌ 依赖包缺失: {e}")
        return False

def test_data_generation():
    print("\n" + "="*60)
    print("测试 2: 数据集生成")
    print("="*60)
    try:
        from generate_data import generate_dataset
        df = generate_dataset(1000)
        print(f"✅ 数据集生成成功，共 {len(df)} 条数据")
        print(f"   字段: {list(df.columns)}")
        df.to_csv("job_salary_data.csv", index=False, encoding="utf-8-sig")
        return True
    except Exception as e:
        print(f"❌ 数据集生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_feature_engineering():
    print("\n" + "="*60)
    print("测试 3: 特征工程")
    print("="*60)
    try:
        import pandas as pd
        from feature_engineering import FeatureEngineer
        
        df = pd.read_csv("job_salary_data.csv", encoding="utf-8-sig")
        fe = FeatureEngineer()
        X, feature_names = fe.fit_transform(df.head(100))
        print(f"✅ 特征工程完成")
        print(f"   特征矩阵形状: {X.shape}")
        print(f"   特征数量: {len(feature_names)}")
        return True
    except Exception as e:
        print(f"❌ 特征工程失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_training():
    print("\n" + "="*60)
    print("测试 4: 模型训练")
    print("="*60)
    try:
        import pandas as pd
        from train_model import SalaryPredictor
        
        df = pd.read_csv("job_salary_data.csv", encoding="utf-8-sig")
        df_sample = df.head(500)
        
        predictor = SalaryPredictor()
        predictor.train(df_sample, test_size=0.2)
        print("✅ 模型训练完成")
        return True
    except Exception as e:
        print(f"❌ 模型训练失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prediction():
    print("\n" + "="*60)
    print("测试 5: 预测功能")
    print("="*60)
    try:
        import pandas as pd
        from train_model import SalaryPredictor
        
        predictor = SalaryPredictor()
        predictor.load()
        
        test_data = pd.DataFrame([{
            "岗位标题": "Python开发工程师",
            "岗位描述": "负责后端开发，熟悉Python、Django、MySQL",
            "地区": "北京",
            "公司规模": "150-500人",
            "学历要求": "本科"
        }])
        
        result = predictor.predict(test_data)
        print(f"✅ 预测成功")
        print(f"   预测薪资下限: {result['预测薪资下限'].values[0]}")
        print(f"   预测薪资上限: {result['预测薪资上限'].values[0]}")
        return True
    except Exception as e:
        print(f"❌ 预测失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_anomaly_detection():
    print("\n" + "="*60)
    print("测试 6: 异常检测")
    print("="*60)
    try:
        import pandas as pd
        from train_model import SalaryPredictor
        
        predictor = SalaryPredictor()
        predictor.load()
        
        test_data = pd.DataFrame([{
            "岗位标题": "Python开发工程师",
            "岗位描述": "负责后端开发",
            "地区": "北京",
            "公司规模": "150-500人",
            "学历要求": "本科",
            "薪资下限": 50000,
            "薪资上限": 80000
        }])
        
        result = predictor.detect_anomaly(test_data)
        print(f"✅ 异常检测成功")
        print(f"   异常类型: {result['异常类型'].values[0]}")
        print(f"   是否异常(Z分数): {result['是否异常(Z分数)'].values[0]}")
        return True
    except Exception as e:
        print(f"❌ 异常检测失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_shap_analysis():
    print("\n" + "="*60)
    print("测试 7: SHAP分析")
    print("="*60)
    try:
        import pandas as pd
        from train_model import SalaryPredictor
        
        predictor = SalaryPredictor()
        predictor.load()
        
        test_data = pd.DataFrame([{
            "岗位标题": "数据科学家",
            "岗位描述": "负责数据分析和建模",
            "地区": "上海",
            "公司规模": "1000人以上",
            "学历要求": "硕士"
        }])
        
        X = predictor.feature_engineer.transform(test_data)
        shap_result = predictor.get_shap_analysis(X, 0)
        print(f"✅ SHAP分析成功")
        print(f"   特征数量: {len(shap_result['feature_shap_df'])}")
        print(f"   Top 3 影响特征:")
        for i, row in shap_result["feature_shap_df"].head(3).iterrows():
            print(f"     - {row['feature']}: {row['shap_value']:.4f}")
        return True
    except Exception as e:
        print(f"❌ SHAP分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "🚀 开始快速测试" + "\n")
    
    results = []
    results.append(("依赖包导入", test_imports()))
    results.append(("数据集生成", test_data_generation()))
    results.append(("特征工程", test_feature_engineering()))
    results.append(("模型训练", test_model_training()))
    results.append(("预测功能", test_prediction()))
    results.append(("异常检测", test_anomaly_detection()))
    results.append(("SHAP分析", test_shap_analysis()))
    
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有测试通过！可以启动 Streamlit 应用了")
        print("   运行命令: streamlit run app.py")
    else:
        print("⚠️  部分测试失败，请检查错误信息")
    print("="*60 + "\n")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
