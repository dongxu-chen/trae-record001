"""
企业征信评分系统 - 端到端测试脚本
======================================
该脚本演示完整的企业征信评分流程：
1. 生成样本数据
2. 训练XGBoost模型
3. 构建知识图谱特征
4. 信用评分与评级
5. SHAP风险因子分析
6. 贷后监测预警
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.generate_data import generate_company, generate_training_data
from kg.neo4j_client import create_company_graph, extract_kg_features, Neo4jClient
from model.feature_engineering import (
    build_feature_vector, compute_ground_truth_score, score_to_rating, score_to_risk_level
)
from model.training import train_model, predict_score, load_model, get_feature_importance
from analysis.risk_analysis import (
    analyze_risk_factors, get_key_strengths, get_risk_warnings,
    get_category_contributions, generate_recommendation, create_explainer, save_explainer
)
from monitoring.post_loan import get_monitor


def print_separator(title: str = ""):
    print(f"\n{'='*70}")
    if title:
        print(f"  {title}")
        print(f"{'='*70}")


def print_subtitle(title: str):
    print(f"\n  --- {title} ---")


def test_sample_generation():
    print_separator("步骤1: 生成企业样本数据")

    print("\n  生成低风险企业:")
    low_risk = generate_company("low", "COMP001", "华盛科技有限公司")
    print(f"    公司: {low_risk.business_info.company_name}")
    print(f"    注册资本: {low_risk.business_info.registered_capital}万")
    print(f"    员工数: {low_risk.business_info.number_of_employees}")
    print(f"    诉讼数: {low_risk.judicial_risk.lawsuit_count}")
    print(f"    专利数: {low_risk.ip.patent_count}")
    print(f"    纳税等级: {low_risk.tax_record.tax_credit_rating}")

    print("\n  生成中风险企业:")
    mid_risk = generate_company("medium", "COMP002", "中兴贸易有限公司")
    print(f"    公司: {mid_risk.business_info.company_name}")
    print(f"    注册资本: {mid_risk.business_info.registered_capital}万")
    print(f"    诉讼数: {mid_risk.judicial_risk.lawsuit_count}")
    print(f"    欠税次数: {mid_risk.tax_record.tax_arrears_count}")

    print("\n  生成高风险企业:")
    high_risk = generate_company("high", "COMP003", "鑫源投资有限公司")
    print(f"    公司: {high_risk.business_info.company_name}")
    print(f"    注册资本: {high_risk.business_info.registered_capital}万")
    print(f"    被执行人: {high_risk.judicial_risk.executed_person_count}")
    print(f"    失信记录: {high_risk.judicial_risk.dishonest_records}")
    print(f"    逾期天数: {high_risk.loan_records[0].overdue_days}")

    return [low_risk, mid_risk, high_risk]


def test_kg_construction(companies):
    print_separator("步骤2: 构建知识图谱")

    for company in companies:
        try:
            create_company_graph(company)
            print(f"  ✓ 已构建图谱: {company.business_info.company_name}")
        except Exception as e:
            print(f"  ✗ 图谱构建跳过(Neo4j未连接): {company.business_info.company_name}")

    print("\n  知识图谱特征提取:")
    for company in companies:
        try:
            kg_features = extract_kg_features(company.business_info.company_id)
            print(f"\n  {company.business_info.company_name}:")
            print(f"    股东质量评分: {kg_features.get('shareholder_quality_score', 'N/A'):.1f}")
            print(f"    行业地位评分: {kg_features.get('industry_peer_score', 'N/A'):.1f}")
            print(f"    供应链稳定性: {kg_features.get('supply_chain_stability_score', 'N/A'):.1f}")
            print(f"    法律关系评分: {kg_features.get('legal_relation_score', 'N/A'):.1f}")
            print(f"    关联风险评分: {kg_features.get('association_risk_score', 'N/A'):.1f}")
        except Exception as e:
            print(f"\n  {company.business_info.company_name}: 使用默认KG特征")
            print(f"    (Neo4j未连接，使用本地模拟特征)")


def test_model_training():
    print_separator("步骤3: 训练XGBoost信用评分模型")

    n_samples = 200
    print(f"\n  生成 {n_samples} 个训练样本...")
    companies = generate_training_data(n_samples)

    kg_features_list = []
    for company in companies:
        try:
            kg_feats = extract_kg_features(company.business_info.company_id)
        except Exception:
            kg_feats = {
                "shareholder_count": 1.0, "avg_share_ratio": 0.5,
                "shareholder_other_companies": 0.0, "corporate_shareholder_count": 0.0,
                "shareholder_quality_score": 50.0, "executive_count": 1.0,
                "avg_executive_tenure": 3.0, "industry_peer_count": 0.0,
                "industry_peer_score": 50.0, "supply_chain_partners": 0.0,
                "avg_supply_strength": 0.0, "supply_chain_stability_score": 50.0,
                "legal_relation_count": 0.0, "total_legal_lawsuits": 0.0,
                "legal_relation_score": 80.0, "associated_companies": 0.0,
                "associated_executives": 0.0, "association_risk_score": 60.0,
            }
        kg_features_list.append(kg_feats)

    print("  训练XGBoost模型...")
    model, scaler = train_model(companies, kg_features_list)

    print("\n  Top 10 重要特征:")
    importance = get_feature_importance(model)
    for i, (feature, imp) in enumerate(list(importance.items())[:10]):
        print(f"    {i+1:2d}. {feature}: {imp:.4f}")

    print("\n  初始化SHAP解释器...")
    from model.feature_engineering import feature_vector_to_array
    from model.training import prepare_training_data
    X, _ = prepare_training_data(companies, kg_features_list)
    X_scaled = scaler.transform(X)
    explainer = create_explainer(model, X_scaled)
    save_explainer(explainer)
    print("  ✓ SHAP解释器已保存")

    return model, scaler, explainer


def test_credit_scoring(companies, model, scaler, explainer):
    print_separator("步骤4: 信用评分与风险分析")

    for company in companies:
        try:
            kg_feats = extract_kg_features(company.business_info.company_id)
        except Exception:
            kg_feats = {
                "shareholder_count": 1.0, "avg_share_ratio": 0.5,
                "shareholder_other_companies": 0.0, "corporate_shareholder_count": 0.0,
                "shareholder_quality_score": 50.0, "executive_count": 1.0,
                "avg_executive_tenure": 3.0, "industry_peer_count": 0.0,
                "industry_peer_score": 50.0, "supply_chain_partners": 0.0,
                "avg_supply_strength": 0.0, "supply_chain_stability_score": 50.0,
                "legal_relation_count": 0.0, "total_legal_lawsuits": 0.0,
                "legal_relation_score": 80.0, "associated_companies": 0.0,
                "associated_executives": 0.0, "association_risk_score": 60.0,
            }

        score = predict_score(company, kg_feats, model, scaler)
        rating = score_to_rating(score)
        risk_level = score_to_risk_level(score)

        print(f"\n  {company.business_info.company_name}")
        print(f"  {'─'*40}")
        print(f"    信用评分: {score:.1f} / 1000")
        print(f"    信用评级: {rating}")
        print(f"    风险等级: {risk_level}")

        print_subtitle("风险因子分析 (Top 5)")
        risk_factors = analyze_risk_factors(company, kg_feats, score)
        for i, rf in enumerate(risk_factors[:5]):
            arrow = "↑" if rf["direction"] == "正面影响" else "↓"
            print(f"    {i+1}. {arrow} {rf['description']} ({rf['category']})")
            print(f"       影响值: {rf['impact']:+.1f} | 严重程度: {rf['severity']}")

        print_subtitle("核心优势")
        strengths = get_key_strengths(risk_factors)
        for s in strengths[:3]:
            print(f"    ✓ {s}")

        print_subtitle("风险警示")
        warnings = get_risk_warnings(risk_factors)
        for w in warnings[:3]:
            print(f"    ⚠ {w}")

        print_subtitle("授信建议")
        recommendation = generate_recommendation(risk_factors, score)
        print(f"    {recommendation}")


def test_post_loan_monitoring(companies, model, scaler):
    print_separator("步骤5: 贷后监测与预警")

    monitor = get_monitor()

    for company in companies:
        try:
            kg_feats = extract_kg_features(company.business_info.company_id)
        except Exception:
            kg_feats = {
                "shareholder_count": 1.0, "avg_share_ratio": 0.5,
                "shareholder_other_companies": 0.0, "corporate_shareholder_count": 0.0,
                "shareholder_quality_score": 50.0, "executive_count": 1.0,
                "avg_executive_tenure": 3.0, "industry_peer_count": 0.0,
                "industry_peer_score": 50.0, "supply_chain_partners": 0.0,
                "avg_supply_strength": 0.0, "supply_chain_stability_score": 50.0,
                "legal_relation_count": 0.0, "total_legal_lawsuits": 0.0,
                "legal_relation_score": 80.0, "associated_companies": 0.0,
                "associated_executives": 0.0, "association_risk_score": 60.0,
            }

        baseline_score = predict_score(company, kg_feats, model, scaler)
        monitor.register_loan(company.business_info.company_id, baseline_score)

        print(f"\n  {company.business_info.company_name}")
        print(f"  {'─'*40}")
        print(f"    初始评分: {baseline_score:.1f}")

        print_subtitle("模拟贷后事件")

        new_score = max(0, baseline_score - 80)
        alerts = monitor.update_score(company.business_info.company_id, new_score)
        print(f"    评分更新: {baseline_score:.1f} → {new_score:.1f} (变化: {new_score - baseline_score:+.1f})")
        if alerts:
            print(f"    ⚠ 预警: {alerts[0]['description']}")

        alert = monitor.report_negative_event(
            company.business_info.company_id,
            "lawsuit",
            "新增重大诉讼案件，涉案金额500万元"
        )
        print(f"    📢 事件预警: [{alert['alert_level'].upper()}] {alert['description']}")
        print(f"       建议措施: {alert['recommended_action']}")

        alert2 = monitor.report_negative_event(
            company.business_info.company_id,
            "tax_arrears",
            "发现新增欠税记录，欠税金额80万元"
        )
        print(f"    📢 事件预警: [{alert2['alert_level'].upper()}] {alert2['description']}")
        print(f"       建议措施: {alert2['recommended_action']}")

        print_subtitle("监测报告摘要")
        report = monitor.generate_monitoring_report(company.business_info.company_id)
        print(f"    当前评分: {report['current_score']:.1f}")
        print(f"    评分变化: {report['score_change']:+.1f} ({report['score_change_percent']:+.1f}%)")
        print(f"    预警数量: {report['alert_count']}")
        print(f"    风险评估: {report['risk_assessment']}")
        print(f"    监测状态: {report['monitoring_status']}")


def test_rating_distribution(model, scaler):
    print_separator("步骤6: 评分分布验证")

    n_test = 100
    test_companies = generate_training_data(n_test)

    scores = []
    ratings_count = {}
    for company in test_companies:
        try:
            kg_feats = extract_kg_features(company.business_info.company_id)
        except Exception:
            kg_feats = {
                "shareholder_count": 1.0, "avg_share_ratio": 0.5,
                "shareholder_other_companies": 0.0, "corporate_shareholder_count": 0.0,
                "shareholder_quality_score": 50.0, "executive_count": 1.0,
                "avg_executive_tenure": 3.0, "industry_peer_count": 0.0,
                "industry_peer_score": 50.0, "supply_chain_partners": 0.0,
                "avg_supply_strength": 0.0, "supply_chain_stability_score": 50.0,
                "legal_relation_count": 0.0, "total_legal_lawsuits": 0.0,
                "legal_relation_score": 80.0, "associated_companies": 0.0,
                "associated_executives": 0.0, "association_risk_score": 60.0,
            }
        score = predict_score(company, kg_feats, model, scaler)
        rating = score_to_rating(score)
        scores.append(score)
        ratings_count[rating] = ratings_count.get(rating, 0) + 1

    print(f"\n  测试样本数: {n_test}")
    print(f"  平均评分: {sum(scores)/len(scores):.1f}")
    print(f"  最低评分: {min(scores):.1f}")
    print(f"  最高评分: {max(scores):.1f}")

    print(f"\n  评级分布:")
    for rating in ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]:
        count = ratings_count.get(rating, 0)
        bar = "█" * (count // 2) if count > 0 else ""
        print(f"    {rating:4s}: {count:3d}家 {bar}")


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║            企业征信评分系统 - 端到端演示                              ║
║   Enterprise Credit Rating System (XGBoost + Knowledge Graph)        ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    companies = test_sample_generation()
    test_kg_construction(companies)
    model, scaler, explainer = test_model_training()
    test_credit_scoring(companies, model, scaler, explainer)
    test_post_loan_monitoring(companies, model, scaler)
    test_rating_distribution(model, scaler)

    print_separator("测试完成")
    print("""
  ✓ 样本数据生成 - 完成
  ✓ 知识图谱构建 - 完成（Neo4j可选）
  ✓ XGBoost模型训练 - 完成
  ✓ 信用评分与评级 - 完成
  ✓ SHAP风险因子分析 - 完成
  ✓ 贷后监测预警 - 完成
  ✓ 评分分布验证 - 完成

  启动Flask API: python app.py
  API端点:
    POST /api/credit/score        - 企业信用评分
    GET  /api/credit/rating/<r>   - 评级信息
    GET  /api/credit/feature-importance - 特征重要性
    POST /api/monitoring/register - 注册贷后监测
    POST /api/monitoring/update   - 更新监测数据
    GET  /api/monitoring/report/<id> - 监测报告
    POST /api/model/train         - 重新训练模型
""")


if __name__ == "__main__":
    main()
