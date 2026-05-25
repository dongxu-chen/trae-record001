from data.generate_data import generate_company
from model.feature_engineering import score_to_rating
from model.training import load_model, predict_score
from monitoring.post_loan import get_monitor
from config import update_rating_threshold, get_rating_thresholds

# Test 1: Dynamic rating thresholds
print('=== Test 1: Dynamic Rating Thresholds ===')
original = get_rating_thresholds()
print('Original AAA:', original["AAA"])

updated = update_rating_threshold('AAA', 920, 1000)
print('Updated AAA:', updated["AAA"])

# Restore
update_rating_threshold('AAA', 900, 1000)
restored = get_rating_thresholds()
print('Restored AAA:', restored["AAA"])

# Test 2: Industry-specific monitoring
print()
print('=== Test 2: Industry-Specific Monitoring ===')
monitor = get_monitor()

# Register with different industries
monitor.register_loan('FIN001', 700, '金融业')
monitor.register_loan('RE001', 600, '房地产')

# Report negative events with industry-specific weights
alert_fin = monitor.report_negative_event('FIN001', 'executed_person', '金融企业被执行人')
alert_re = monitor.report_negative_event('RE001', 'executed_person', '房地产企业被执行人')
print('金融业 event impact:', alert_fin["impact_score"])
print('房地产 event impact:', alert_re["impact_score"])

# Generate monitoring reports
report_fin = monitor.generate_monitoring_report('FIN001')
report_re = monitor.generate_monitoring_report('RE001')
print('金融业 report industry:', report_fin["industry"])
print('金融业 warning_line:', report_fin["industry_warning_line"])
print('房地产 report industry:', report_re["industry"])
print('房地产 warning_line:', report_re["industry_warning_line"])

# Test 3: Industry warning lines
print()
print('=== Test 3: Industry Warning Lines ===')
lines = monitor.get_industry_warning_lines()
for industry in ['金融业', '房地产', '建筑业']:
    if industry in lines:
        l = lines[industry]
        print(f'{industry}: baseline={l["baseline_score"]}, warning={l["warning_line"]}, critical={l["critical_line"]}')

# Test 4: Score with dynamic thresholds
print()
print('=== Test 4: Score to Rating with Dynamic Thresholds ===')
model, scaler = load_model()
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
c = generate_company('low', 'TEST001', '测试公司')
score = predict_score(c, kg_default, model, scaler)
rating = score_to_rating(score)
print(f'Score: {score:.1f}, Rating: {rating}')

# Test 5: Time decay function
print()
print('=== Test 5: Time Decay Function ===')
from kg.neo4j_client import _time_decay_factor
from datetime import datetime, timedelta

# Fresh relation (today)
fresh = _time_decay_factor('OWNS', datetime.now().strftime('%Y-%m-%d'))
print(f'Fresh (today) decay: {fresh:.4f}')

# 1 year old relation
one_year = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
decay_1y = _time_decay_factor('OWNS', one_year)
print(f'1 year old decay: {decay_1y:.4f}')

# 3 years old relation
three_years = (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d')
decay_3y = _time_decay_factor('OWNS', three_years)
print(f'3 years old decay: {decay_3y:.4f}')

# Very old relation (10 years)
ten_years = (datetime.now() - timedelta(days=3650)).strftime('%Y-%m-%d')
decay_10y = _time_decay_factor('OWNS', ten_years)
print(f'10 years old decay: {decay_10y:.4f}')

# Different relation types have different half-lives
decay_supply_1y = _time_decay_factor('SUPPLIES_TO', one_year)
print(f'Supply chain 1y decay: {decay_supply_1y:.4f}')

print()
print('All tests passed!')
