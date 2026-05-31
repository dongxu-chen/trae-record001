import sys
sys.stdout.reconfigure(encoding='utf-8')

log_file = open("test_enhanced_v2_log.txt", "w", encoding="utf-8")

def log(msg):
    print(msg, flush=True)
    log_file.write(msg + "\n")
    log_file.flush()

log("=" * 80)
log("招聘岗位薪资预测系统 V2 增强版 - 功能测试")
log("=" * 80)

try:
    log("\n[1/6] 导入核心模块...")
    import pandas as pd
    import numpy as np
    log("   ✓ 数据处理模块导入成功")
    
    from salary_analytics import SalaryTrendAnalyzer, JobCompetitionScorer, SkillPremiumAnalyzer
    log("   ✓ 薪资分析模块导入成功")
    
    log("\n[2/6] 加载数据集...")
    import os
    if os.path.exists("job_salary_data_v2.csv"):
        df = pd.read_csv("job_salary_data_v2.csv", encoding="utf-8-sig", parse_dates=["发布日期"])
        log(f"   ✓ 数据加载成功，共 {len(df)} 条记录")
        log(f"   ✓ 时间范围: {df['发布日期'].min().date()} ~ {df['发布日期'].max().date()}")
    else:
        from generate_data_v2 import generate_timeseries_dataset
        df = generate_timeseries_dataset(3000)
        df.to_csv("job_salary_data_v2.csv", index=False, encoding="utf-8-sig")
        log(f"   ✓ 数据生成成功，共 {len(df)} 条记录")
    
    log("\n[3/6] 薪资趋势分析测试...")
    trend_analyzer = SalaryTrendAnalyzer(df)
    log("   ✓ 趋势分析器初始化成功")
    
    city_trend = trend_analyzer.get_city_trend("北京", "M")
    log(f"   ✓ 北京月度薪资趋势: {len(city_trend)} 个月数据")
    log(f"   ✓ 最新薪资均值: {int(city_trend['薪资均值'].iloc[-1]):,} 元/月")
    
    category_trend = trend_analyzer.get_job_category_trend("技术开发", "Q")
    log(f"   ✓ 技术开发季度趋势: {len(category_trend)} 个季度")
    
    comparison = trend_analyzer.get_cross_comparison("地区")
    log(f"   ✓ 地区薪资对比: {len(comparison)} 个城市")
    log(f"   ✓ 最高薪资城市: {comparison.iloc[0]['地区']} ({int(comparison.iloc[0]['薪资均值']):,}元)")
    
    log("\n[4/6] 岗位竞争力评分测试...")
    scorer = JobCompetitionScorer(df)
    log("   ✓ 竞争力评分器初始化成功")
    
    score_result = scorer.calculate_score("Python开发工程师", "北京", 25000, 35000)
    log(f"   ✓ 竞争力评分: {score_result['竞争力评分']}分")
    log(f"   ✓ 竞争力等级: {score_result['竞争力等级']}")
    log(f"   ✓ 同地区百分位: {score_result['同地区百分位']}%")
    log(f"   ✓ 同岗位百分位: {score_result['同岗位百分位']}%")
    log(f"   ✓ 同地区同岗位百分位: {score_result['同地区同岗位百分位']}%")
    
    log("\n[5/6] 技能溢价分析测试...")
    skill_analyzer = SkillPremiumAnalyzer(df)
    log("   ✓ 技能溢价分析器初始化成功")
    
    top_skills = skill_analyzer.get_top_skills(10)
    log(f"   ✓ Top 10 高溢价技能分析完成")
    if len(top_skills) > 0:
        log(f"   ✓ 最高溢价技能: {top_skills.iloc[0]['技能']} (+{top_skills.iloc[0]['溢价比例']}%)")
    
    category_stats = skill_analyzer.get_premium_by_category()
    log(f"   ✓ 技能分类统计: {len(category_stats)} 个分类")
    if len(category_stats) > 0:
        log(f"   ✓ 最高溢价分类: {category_stats.iloc[0]['技能分类']} (+{category_stats.iloc[0]['平均溢价比例']}%)")
    
    k8s_detail = skill_analyzer.get_skill_detail("Kubernetes")
    if "error" not in k8s_detail:
        log(f"   ✓ Kubernetes溢价: +{k8s_detail['溢价比例']}% (¥{k8s_detail['溢价金额']:,})")
    
    pytorch_detail = skill_analyzer.get_skill_detail("PyTorch")
    if "error" not in pytorch_detail:
        log(f"   ✓ PyTorch溢价: +{pytorch_detail['溢价比例']}% (¥{pytorch_detail['溢价金额']:,})")
    
    test_desc = "负责后端服务开发，使用Python和Django框架，熟悉Docker和K8s容器化部署，有PyTorch深度学习经验"
    job_skill_analysis = skill_analyzer.analyze_job_skills(test_desc)
    log(f"   ✓ 岗位技能分析: 识别到 {len(job_skill_analysis['识别技能'])} 个技能")
    log(f"   ✓ 技能溢价汇总: ¥{job_skill_analysis['技能溢价汇总']:,}")
    log(f"   ✓ 技能增值潜力: {job_skill_analysis['技能增值潜力']}")
    
    log("\n[6/6] 导入验证Streamlit模块...")
    try:
        import streamlit as st
        import plotly.express as px
        import plotly.graph_objects as go
        log("   ✓ Streamlit可视化模块导入成功")
    except Exception as e:
        log(f"   ⚠ Streamlit模块警告 (不影响核心功能): {e}")
    
    log("\n" + "=" * 80)
    log("🎉 所有增强功能测试通过！")
    log("=" * 80)
    
    log("\n📋 V2增强版功能总结:")
    log("")
    log("【1️⃣ 薪资趋势分析】")
    log("   - 按城市展示薪资变化曲线（支持月度/季度/周度）")
    log("   - 按岗位类型展示趋势对比")
    log("   - 地区/公司规模/学历横向对比")
    log("   - 同比/环比增长率计算")
    log("")
    log("【2️⃣ 岗位竞争力评分】")
    log("   - S/A/B/C/D五级竞争力评级")
    log("   - 同地区薪资百分位对比")
    log("   - 同岗位薪资百分位对比")
    log("   - 同地区同岗位百分位对比")
    log("   - 可视化仪表盘展示")
    log("")
    log("【3️⃣ 技能溢价分析】")
    log("   - 覆盖8大技能分类，40+热门技能")
    log("   - Kubernetes、PyTorch、Docker等溢价分析")
    log("   - 技能溢价排行榜")
    log("   - 岗位描述自动识别技能并计算溢价")
    log("   - 技能增值潜力评估")
    log("")
    log("🚀 启动增强版应用: streamlit run app_v2.py --server.port=8502")
    
except Exception as e:
    log(f"\n✗ 测试失败: {e}")
    import traceback
    traceback.print_exc(file=log_file)
    traceback.print_exc()

finally:
    log_file.close()
    print("\n详细日志已保存到 test_enhanced_v2_log.txt")
