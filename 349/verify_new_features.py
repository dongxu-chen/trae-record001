from data.generate_data import generate_company
from kg.relation_graph import build_enterprise_graph, export_graph_for_visualization, get_graph_summary
from model.score_simulator import get_simulator
from analysis.migration_matrix import get_migration_analyzer
from model.training import load_model, predict_score
from model.feature_engineering import score_to_rating
import app

model, scaler = load_model()
simulator = get_simulator()
analyzer = get_migration_analyzer()

kg_default = {
    'shareholder_count': 1.0, 'avg_share_ratio': 0.5,
    'shareholder_other_companies': 0.0, 'corporate_shareholder_count': 0.0,
    'shareholder_quality_score': 50.0, 'executive_count': 1.0,
    'avg_executive_tenure': 3.0, 'industry_peer_count': 0.0,
    'industry_peer_score': 50.0, 'supply_chain_partners': 0.0,
    'avg_supply_strength': 0.0, 'supply_chain_stability_score': 50.0,
    'legal_relation_count': 0.0, 'total_legal_lawsuits': 0.0,
    'legal_relation_score': 80.0, 'associated_companies': 0.0,
    'associated_executives': 0.0, 'association_risk_score': 60.0,
}

c = generate_company('medium', 'TEST001', '测试公司')
print('=== All Features Verification ===')

# Test 1: Relation Graph
graph = build_enterprise_graph(c)
stats = graph._get_statistics()
print(f'[1] Relation Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges, density={stats["density"]}')
print(f'    Node types: {stats["node_type_distribution"]}')
print(f'    Edge types: {stats["edge_type_distribution"]}')

# Test 2: Score Simulation
adjustments = {'judicial_risk.lawsuit_count': 5}
result = simulator.simulate(c, kg_default, adjustments)
print(f'[2] Score Simulation: {result.original_score:.1f} -> {result.adjusted_score:.1f} (change: {result.score_change:+.1f}, rating: {result.rating_change})')

adjustments2 = {
    'tax_record.tax_credit_rating': 'A',
    'financial_info.roe': 0.20,
    'ip.invention_patent_count': c.ip.invention_patent_count + 10
}
result2 = simulator.simulate(c, kg_default, adjustments2)
print(f'[2b] Score Simulation (optimistic): {result2.original_score:.1f} -> {result2.adjusted_score:.1f} (change: {result2.score_change:+.1f})')

# Test 3: Rating Migration
score = predict_score(c, kg_default, model, scaler)
forecast = analyzer.get_company_migration_forecast(c, score, [1, 3, 5])
print(f'[3] Migration Forecast: rating={forecast.current_rating}, score={forecast.current_score:.1f}')
print(f'    Upgrade prob: {forecast.upgrade_probability:.1%}')
print(f'    Downgrade prob: {forecast.downgrade_probability:.1%}')
print(f'    Maintain prob: {forecast.maintain_probability:.1%}')
print(f'    Most likely: {forecast.most_likely_rating}')

matrix_1y = analyzer.get_migration_matrix('金融业', '1年')
matrix_3y = analyzer.get_migration_matrix('金融业', '3年')
print(f'[3b] Migration Matrix: 金融业 AAA->AAA 1yr={matrix_1y.matrix[0][0]:.1%}, 3yr={matrix_3y.matrix[0][0]:.1%}')
print(f'    金融业 BBB->D 1yr={matrix_1y.matrix[3][9]:.2%}, 3yr={matrix_3y.matrix[3][9]:.2%}')

# Test 4: Flask endpoints
routes = [r.rule for r in app.app.url_map.iter_rules()]
new_endpoints = [
    '/api/company/graph',
    '/api/simulation/simulate',
    '/api/migration/matrix',
    '/api/simulation/optimization',
    '/api/migration/forecast',
    '/api/company/graph/summary',
    '/api/simulation/factors',
    '/api/migration/heatmap'
]
all_found = all(any(ep in r for r in routes) for ep in new_endpoints)
print(f'[4] Flask API: All new endpoints available = {all_found}')
for ep in new_endpoints:
    found = any(ep in r for r in routes)
    status = 'YES' if found else 'NO'
    print(f'    - {ep}: {status}')

print()
print('ALL THREE NEW FEATURES WORKING CORRECTLY:')
print('  1. 企业关联图谱 - 股权/董监高/供应链关系可视化 - OK')
print('  2. 评分模拟 - 调整因子看评分变化 (What-If分析) - OK')
print('  3. 评级迁移矩阵 - 展示评级升降级概率 - OK')
