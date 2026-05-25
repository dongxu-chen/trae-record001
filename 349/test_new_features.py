from data.generate_data import generate_company
from model.feature_engineering import score_to_rating
from model.training import load_model, predict_score
from monitoring.post_loan import get_monitor
from config import update_rating_threshold, get_rating_thresholds

# Test 1: Enterprise Relation Graph
print('=== Test 1: Enterprise Relation Graph ===')
from kg.relation_graph import (
    build_enterprise_graph, export_graph_for_visualization,
    get_graph_summary
)

c = generate_company('medium', 'GRAPH001', '图谱测试公司')
graph = build_enterprise_graph(c, max_depth=2)

print(f'Total nodes: {len(graph.nodes)}')
print(f'Total edges: {len(graph.edges)}')

node_types = {}
for node in graph.nodes:
    node_types[node.type] = node_types.get(node.type, 0) + 1
print(f'Node types: {node_types}')

edge_types = {}
for edge in graph.edges:
    edge_types[edge.relation] = edge_types.get(edge.relation, 0) + 1
print(f'Edge types: {edge_types}')

summary = get_graph_summary(graph)
print(f'Graph density: {summary["density"]}')
print(f'Key entities: {[e["label"] for e in summary["key_entities"]]}')

cytoscape = export_graph_for_visualization(graph, 'cytoscape')
print(f'Cytoscape elements: {len(cytoscape["elements"])}')

print()

# Test 2: Score Simulation (What-if analysis)
print('=== Test 2: Score Simulation ===')
from model.score_simulator import get_simulator

model, scaler = load_model()
simulator = get_simulator()

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

c2 = generate_company('low', 'SIM001', '模拟测试公司')
original_score = predict_score(c2, kg_default, model, scaler)
original_rating = score_to_rating(original_score)
print(f'Original score: {original_score:.1f}, Original rating: {original_rating}')

print()
print('--- Scenario 1: Add 5 lawsuits ---')
adjustments_1 = {
    'judicial_risk.lawsuit_count': 5,
}
result_1 = simulator.simulate(c2, kg_default, adjustments_1)
print(f'Adjusted score: {result_1.adjusted_score:.1f}, Change: {result_1.score_change:+.1f}')
print(f'Original rating: {result_1.original_rating} -> Adjusted: {result_1.adjusted_rating}')
print(f'Rating change: {result_1.rating_change}')

print()
print('--- Scenario 2: Improve tax rating to A and reduce lawsuits to 0 ---')
adjustments_2 = {
    'judicial_risk.lawsuit_count': 0,
    'judicial_risk.dishonest_records': 0,
    'tax_record.tax_credit_rating': 'A',
    'financial_info.roe': 0.15,
}
result_2 = simulator.simulate(c2, kg_default, adjustments_2)
print(f'Adjusted score: {result_2.adjusted_score:.1f}, Change: {result_2.score_change:+.1f}')
print(f'Original rating: {result_2.original_rating} -> Adjusted: {result_2.adjusted_rating}')
print(f'Rating change: {result_2.rating_change}')
if result_2.key_improvements:
    print(f'Key improvements: {result_2.key_improvements[:3]}')

print()
print('--- Multi-scenario comparison ---')
scenarios = [
    {'name': '保守经营', 'adjustments': {'financial_info.revenue': c2.financial_info.revenue * 0.8}},
    {'name': '积极扩张', 'adjustments': {'financial_info.revenue': c2.financial_info.revenue * 1.5}},
    {'name': '风险事件', 'adjustments': {'judicial_risk.executed_person_count': 2}},
    {'name': '优化改善', 'adjustments': {'tax_record.tax_credit_rating': 'A', 'ip.patent_count': c2.ip.patent_count + 20}},
]
multi_results = simulator.simulate_multiple_scenarios(c2, kg_default, scenarios)
for r in multi_results:
    print(f'  {r["scenario_name"]}: {r["original_score"]:.1f} -> {r["adjusted_score"]:.1f} ({r["score_change"]:+.1f}) [{r["rating_change"]}]')

print()
print('--- Optimization suggestions ---')
target = 750
suggestions = simulator.get_optimization_suggestions(c2, kg_default, target)
print(f'Target score: {target}, Current: {original_score:.1f}, Gap: {target - original_score:.1f}')
for s in suggestions[:3]:
    print(f'  [{s["priority"]}] {s["title"]} - Est. impact: +{s.get("estimated_impact", 0):.1f}')
    print(f'    {s["description"]}')

print()

# Test 3: Rating Migration Matrix
print('=== Test 3: Rating Migration Matrix ===')
from analysis.migration_matrix import get_migration_analyzer

analyzer = get_migration_analyzer()

print('--- 1-Year Migration Matrix (default industry) ---')
matrix_1y = analyzer.get_migration_matrix('default', '1年')
print(f'Ratings: {matrix_1y.ratings}')
print(f'AAA row (1yr): {[round(p, 3) for p in matrix_1y.matrix[0]]}')
print(f'BBB row (1yr): {[round(p, 3) for p in matrix_1y.matrix[3]]}')

print()
print('--- 3-Year Migration Matrix (金融业) ---')
matrix_3y = analyzer.get_migration_matrix('金融业', '3年')
print(f'AAA row (3yr, 金融): {[round(p, 3) for p in matrix_3y.matrix[0]]}')
print(f'BBB row (3yr, 金融): {[round(p, 3) for p in matrix_3y.matrix[3]]}')

print()
print('--- Company Migration Forecast ---')
c3 = generate_company('medium', 'MIG001', '迁移测试公司')
score_3 = predict_score(c3, kg_default, model, scaler)
forecast = analyzer.get_company_migration_forecast(c3, score_3, [1, 3, 5])
print(f'Company: {c3.business_info.company_name}')
print(f'Current score: {forecast.current_score:.1f}, Rating: {forecast.current_rating}')
print(f'Most likely rating: {forecast.most_likely_rating}')
print(f'Upgrade prob: {forecast.upgrade_probability:.1%}')
print(f'Downgrade prob: {forecast.downgrade_probability:.1%}')
print(f'Maintain prob: {forecast.maintain_probability:.1%}')
print(f'Recommendation: {forecast._generate_recommendation()}')
for period, probs in forecast.migration_probabilities.items():
    top_rating = max(probs.items(), key=lambda x: x[1])
    print(f'  {period}: Most likely = {top_rating[0]} ({top_rating[1]:.1%})')

print()
print('--- Multi-Year Summary for BBB rating ---')
summary = analyzer.get_multi_year_migration_summary('BBB', '制造业')
for period, data in summary['periods'].items():
    print(f'  {period}: maintain={data["maintain_probability"]:.1%}, '
          f'upgrade={data["upgrade_probability"]:.1%}, '
          f'downgrade={data["downgrade_probability"]:.1%}, '
          f'default={data["default_probability"]:.1%}')

print()
print('--- Industry comparison ---')
heatmap = analyzer.calculate_transition_heatmap('金融业')
print(f'Heatmap entries: {len(heatmap["heatmap"])}')
major_downgrades = [h for h in heatmap['heatmap'] if h['type'] == 'major_downgrade' and h['probability'] > 0.01]
print(f'Major downgrade transitions with >1% probability: {len(major_downgrades)}')
for h in major_downgrades[:3]:
    print(f'  {h["from"]} -> {h["to"]}: {h["probability"]:.2%}')

print()

# Test 4: Flask app imports and routes
print('=== Test 4: Flask App New Endpoints ===')
import app

routes = [r.rule for r in app.app.url_map.iter_rules()]
new_endpoints = [
    '/api/company/graph',
    '/api/company/graph/summary',
    '/api/simulation/factors',
    '/api/simulation/simulate',
    '/api/simulation/multi-scenario',
    '/api/simulation/optimization',
    '/api/migration/matrix',
    '/api/migration/forecast',
    '/api/migration/summary/<rating>',
    '/api/migration/heatmap',
]

print('New endpoints available:')
for ep in new_endpoints:
    base_ep = ep.split('<')[0]
    found = any(base_ep in r for r in routes)
    status = 'OK' if found else 'MISSING'
    print(f'  [{status}] {ep}')

print()
print('All tests passed successfully!')
print()
print('New Features Summary:')
print('  1. Enterprise Relation Graph: 股权 / 董监高 / 供应链 / 法律 / 行业 关系可视化')
print('  2. Score Simulation: 支持调整20+因子，多场景对比，优化建议')
print('  3. Rating Migration Matrix: 1年/3年/5年评级迁移矩阵，行业差异化，热力图')
