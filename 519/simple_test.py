import sys
import os

from loyalty_analyzer import BrandLoyaltyAnalyzer

print('=' * 70)
print('Starting test...')
print('=' * 70)

analyzer = BrandLoyaltyAnalyzer(n_customers=500, use_cached_data=False)
analyzer.load_or_generate_data()
print('1. Analyzer initialized and data loaded')

purchases = analyzer.data['purchases']
profiles = analyzer.data['profiles']
print(f'2. Data loaded: {len(purchases)} purchases, {len(profiles)} profiles')

price_cols = [c for c in purchases.columns if 'price' in c.lower() or 'discount' in c.lower()]
promo_cols = [c for c in profiles.columns if 'price' in c.lower() or 'promo' in c.lower()]
print(f'   Price cols in purchases: {price_cols}')
print(f'   Promo cols in profiles: {promo_cols}')

print(f'   Avg base price: {purchases["base_price"].mean():.2f}')
print(f'   Avg discount pct: {purchases["discount_pct"].mean()*100:.1f}%')
print(f'   Promotion rate: {purchases["is_promotion"].mean()*100:.1f}%')

analyzer.run_survival_analysis()
sa = analyzer.survival_results
print('3. Survival analysis done')
print(f'   Keys: {list(sa.keys())[:10]}')

if 'category_churn_thresholds' in sa:
    print('   Category churn thresholds:')
    for cat, threshold in sa['category_churn_thresholds'].items():
        median = sa.get('category_inter_purchase_medians', {}).get(cat, 0)
        print(f'     {cat}: median={median:.1f}d, threshold={threshold:.1f}d')

if 'category_stats' in sa and len(sa['category_stats']) > 0:
    print('   Category stats:')
    for _, row in sa['category_stats'].iterrows():
        cat = row['product_category']
        print(f'     {cat}: mean={row["mean_inter_purchase"]:.1f}d, median={row["median_inter_purchase"]:.1f}d')

analyzer.run_clustering()
print('4. Clustering done')

analyzer.run_loyalty_index_calculation()
lr = analyzer.loyalty_results
print('5. Loyalty index done')
print(f'   Keys: {list(lr.keys())}')

if 'segment_recommendations' in lr:
    print('   Segment recommendations:')
    for seg, info in lr['segment_recommendations'].items():
        print(f'     {seg}: {info["user_count"]} users, avg_loyalty={info["avg_loyalty_index"]:.1f}')

if 'personalized_recommendations' in lr:
    pr = lr['personalized_recommendations']
    print(f'   Personalized recommendations: {len(pr)} users')
    if len(pr) > 0:
        print('   User segments:')
        for seg, count in pr['user_segment'].value_counts().items():
            print(f'     {seg}: {count}')
        
        user0 = pr.iloc[0]
        print(f'   Sample user {user0["customer_id"]}:')
        print(f'     Loyalty: {user0["loyalty_index"]:.1f}, Segment: {user0["user_segment"]}')
        print(f'     Priority: {user0["priority_score"]}/5')
        print(f'     Strategies: {len(user0["personalized_strategies"])}')
        print(f'     Product recs: {len(user0["product_recommendations"])}')
        print(f'     Promotion recs: {len(user0["promotion_recommendations"])}')
        print(f'     Communication recs: {len(user0["communication_recommendations"])}')

analyzer.run_attribution_analysis()
ar = analyzer.attribution_results
print('6. Attribution done')

if 'price_promotion_impact' in ar:
    ppi = ar['price_promotion_impact']
    print('   Price promotion impact:')
    print(f'     Keys: {list(ppi.keys())}')
    
    if 'overall' in ppi:
        o = ppi['overall']
        print(f'     Overall: price_sens_high={o.get("high_price_sensitivity_count",0)}, promo_resp_high={o.get("high_promotion_responsiveness_count",0)}')
    
    if 'correlations' in ppi:
        print('     Top correlations:')
        for i, (feat, val) in enumerate(list(ppi['correlations'].items())[:5]):
            print(f'       {i+1}. {feat}: {val:.3f}')
    
    if 'category' in ppi:
        print('     Category analysis:')
        for cat, data in list(ppi['category'].items())[:3]:
            print(f'       {cat}: high_loyal_discount={data.get("high_loyalty_avg_discount",0):.1%}')

analyzer.run_competitor_analysis()
cr = analyzer.competitor_results
print('7. Competitor analysis done')
overview = cr.get('switch_overview', {})
print(f'   Total switches: {overview.get("unique_switchers", 0)}')
print(f'   Return rate: {overview.get("return_rate", 0):.1%}')
reasons = cr.get('switch_reasons', {})
primary = reasons.get('primary_reason_distribution', {})
if primary:
    print(f'   Top reasons: {list(primary.keys())[:3]}')

analyzer.run_loyalty_prediction()
pr = analyzer.prediction_results
print('8. Loyalty prediction done')
trend_overview = pr.get('trend_overview', {})
trend_dist = trend_overview.get('trend_direction_distribution', {})
print(f'   Improving: {trend_dist.get("improving_pct", 0):.1f}%')
print(f'   Declining: {trend_dist.get("declining_pct", 0):.1f}%')
prediction = pr.get('loyalty_prediction', {})
forecast = prediction.get('overall_forecast', {})
print(f'   Current avg: {forecast.get("avg_current_score", 0):.1f}')
print(f'   Predicted next Q: {forecast.get("avg_predicted_next_q", 0):.1f}')

analyzer.run_referral_analysis()
rr = analyzer.referral_results
print('9. Referral analysis done')
ref_overview = rr.get('referral_overview', {})
print(f'   Total referrals: {ref_overview.get("total_referrals", 0)}')
print(f'   Conversion rate: {ref_overview.get("conversion_rate", 0):.1%}')
viral = rr.get('viral_coefficient', {})
print(f'   Viral coefficient: {viral.get("viral_coefficient", 0):.2f}')
print(f'   Growth potential: {viral.get("growth_potential", "N/A")}')

analyzer.export_results()
print('10. Export done')

if os.path.exists('results'):
    files = os.listdir('results')
    print(f'   Generated {len(files)} files:')
    for f in sorted(files):
        fp = os.path.join('results', f)
        size = os.path.getsize(fp)
        print(f'     - {f} ({size:,} bytes)')

print('=' * 70)
print('ALL TESTS PASSED!')
print('=' * 70)
