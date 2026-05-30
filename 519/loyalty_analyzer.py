import pandas as pd
import numpy as np
import os
from data_generator import CustomerDataGenerator
from survival_analysis import SurvivalAnalyzer
from clustering_module import LoyaltyClusterer
from attribution_model import AttributionAnalyzer
from loyalty_index import LoyaltyIndexCalculator
from competitor_analysis import CompetitorSwitchAnalyzer
from loyalty_predictor import LoyaltyPredictor
from referral_analysis import ReferralAnalyzer
import warnings
warnings.filterwarnings('ignore')


class BrandLoyaltyAnalyzer:
    def __init__(self, n_customers=1000, use_cached_data=True):
        self.n_customers = n_customers
        self.use_cached_data = use_cached_data
        
        self.data_generator = CustomerDataGenerator(n_customers=n_customers)
        self.survival_analyzer = SurvivalAnalyzer()
        self.clusterer = LoyaltyClusterer(n_clusters=3, method='kmeans')
        self.attribution_analyzer = AttributionAnalyzer()
        self.loyalty_calculator = LoyaltyIndexCalculator()
        self.competitor_analyzer = CompetitorSwitchAnalyzer()
        self.loyalty_predictor = LoyaltyPredictor()
        self.referral_analyzer = ReferralAnalyzer()
        
        self.data = None
        self.survival_results = None
        self.clustering_results = None
        self.attribution_results = None
        self.loyalty_results = None
        self.competitor_results = None
        self.prediction_results = None
        self.referral_results = None
        
    def load_or_generate_data(self):
        data_dir = 'data'
        required_files = ['profiles.csv', 'purchases.csv', 'nps.csv', 'complaints.csv', 'interactions.csv']
        
        if self.use_cached_data and os.path.exists(data_dir):
            all_exist = all(os.path.exists(f'{data_dir}/{f}') for f in required_files)
            if all_exist:
                print("Loading cached data...")
                self.data = {
                    'profiles': pd.read_csv(f'{data_dir}/profiles.csv'),
                    'purchases': pd.read_csv(f'{data_dir}/purchases.csv'),
                    'nps': pd.read_csv(f'{data_dir}/nps.csv'),
                    'complaints': pd.read_csv(f'{data_dir}/complaints.csv'),
                    'interactions': pd.read_csv(f'{data_dir}/interactions.csv')
                }
                for extra_file in ['competitor_switches.csv', 'loyalty_trends.csv', 'referrals.csv']:
                    path = f'{data_dir}/{extra_file}'
                    if os.path.exists(path):
                        self.data[extra_file.replace('.csv', '')] = pd.read_csv(path)
                print(f"Loaded {len(self.data['profiles'])} customers")
                return self.data
        
        print("Generating new data...")
        self.data = self.data_generator.generate_all_data()
        self.data_generator.save_data(self.data)
        
        return self.data
    
    def run_survival_analysis(self):
        if self.data is None:
            self.load_or_generate_data()
        
        print("\n=== Running Survival Analysis ===")
        self.survival_results = self.survival_analyzer.run_full_survival_analysis(
            self.data['purchases'],
            self.data['profiles']
        )
        
        return self.survival_results
    
    def run_clustering(self, find_optimal_k=False):
        if self.data is None:
            self.load_or_generate_data()
        
        print("\n=== Running Clustering Analysis ===")
        self.clustering_results = self.clusterer.run_clustering_analysis(
            self.data,
            find_optimal_k=find_optimal_k
        )
        
        return self.clustering_results
    
    def run_attribution_analysis(self):
        if self.clustering_results is None:
            self.run_clustering()
        
        print("\n=== Running Attribution Analysis ===")
        self.attribution_results = self.attribution_analyzer.run_full_attribution_analysis(
            self.clustering_results['features_with_clusters'],
            self.data
        )
        
        return self.attribution_results
    
    def run_loyalty_index_calculation(self):
        if self.survival_results is None:
            self.run_survival_analysis()
        if self.clustering_results is None:
            self.run_clustering()
        if self.attribution_results is None:
            self.run_attribution_analysis()
        
        print("\n=== Running Loyalty Index Calculation ===")
        self.loyalty_results = self.loyalty_calculator.run_full_index_calculation(
            self.clustering_results['features_with_clusters'],
            self.data,
            self.survival_results['survival_data'],
            self.attribution_results
        )
        
        return self.loyalty_results
    
    def run_competitor_analysis(self):
        if self.data is None:
            self.load_or_generate_data()
        
        print("\n=== Running Competitor Switch Analysis ===")
        self.competitor_results = self.competitor_analyzer.run_full_analysis(
            self.data, self.loyalty_results
        )
        
        return self.competitor_results
    
    def run_loyalty_prediction(self):
        if self.data is None:
            self.load_or_generate_data()
        
        print("\n=== Running Loyalty Prediction ===")
        self.prediction_results = self.loyalty_predictor.run_full_analysis(
            self.data, self.loyalty_results
        )
        
        return self.prediction_results
    
    def run_referral_analysis(self):
        if self.data is None:
            self.load_or_generate_data()
        
        print("\n=== Running Referral Analysis ===")
        self.referral_results = self.referral_analyzer.run_full_analysis(
            self.data, self.loyalty_results
        )
        
        return self.referral_results
    
    def run_full_analysis(self):
        print("=" * 60)
        print("BRAND LOYALTY ANALYSIS PLATFORM")
        print("=" * 60)
        
        self.load_or_generate_data()
        self.run_survival_analysis()
        self.run_clustering()
        self.run_attribution_analysis()
        self.run_loyalty_index_calculation()
        self.run_competitor_analysis()
        self.run_loyalty_prediction()
        self.run_referral_analysis()
        
        print("\n" + "=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)
        
        return self.get_summary_report()
    
    def get_summary_report(self):
        report = {}
        
        if self.survival_results:
            surv_data = self.survival_results['survival_data']
            report['survival'] = {
                'total_customers': len(surv_data),
                'churn_rate': surv_data['churned'].mean() * 100,
                'median_survival_days': self.survival_results['km_overall']['overall']['median_survival_time'],
                'avg_repurchase_prob': surv_data['repurchase_probability'].mean() * 100,
                'avg_purchase_frequency': surv_data['total_purchases'].mean(),
                'category_churn_thresholds': self.survival_results.get('category_churn_thresholds', {}),
                'category_inter_purchase_medians': self.survival_results.get('category_inter_purchase_medians', {})
            }
            if 'category_stats' in self.survival_results:
                report['survival']['category_stats'] = self.survival_results['category_stats'].to_dict('records')
        
        if self.clustering_results:
            cluster_profiles = self.clustering_results['cluster_profiles']
            report['clustering'] = {
                'n_clusters': len(cluster_profiles),
                'cluster_distribution': cluster_profiles.to_dict('records'),
                'high_loyalty_percent': cluster_profiles[cluster_profiles['忠诚度层级'] == '高']['用户占比'].values[0] * 100 if '高' in cluster_profiles['忠诚度层级'].values else 0,
                'medium_loyalty_percent': cluster_profiles[cluster_profiles['忠诚度层级'] == '中']['用户占比'].values[0] * 100 if '中' in cluster_profiles['忠诚度层级'].values else 0,
                'low_loyalty_percent': cluster_profiles[cluster_profiles['忠诚度层级'] == '低']['用户占比'].values[0] * 100 if '低' in cluster_profiles['忠诚度层级'].values else 0
            }
            if 'cluster_characteristics' in self.clustering_results:
                report['clustering']['characteristics'] = self.clustering_results['cluster_characteristics']
        
        if self.attribution_results:
            importance = self.attribution_results['importance_results']
            report['attribution'] = {
                'top_drivers': importance['importance_df']['feature'].head(5).tolist(),
                'factor_impact': self.attribution_results['factor_impact'].head(5).to_dict('records')
            }
            if 'price_promotion_impact' in self.attribution_results:
                report['attribution']['price_promotion_impact'] = self.attribution_results['price_promotion_impact']
        
        if self.loyalty_results:
            index_summary = self.loyalty_results['index_summary']
            report['loyalty_index'] = {
                'overall_avg': index_summary['overall']['avg_loyalty_index'],
                'overall_median': index_summary['overall']['median_loyalty_index'],
                'tier_summary': index_summary['tier_summary'].to_dict('records'),
                'high_tier_avg': index_summary['tier_summary'][index_summary['tier_summary']['忠诚度层级'] == '高忠诚度']['平均指数'].values[0] if '高忠诚度' in index_summary['tier_summary']['忠诚度层级'].values else 0,
                'medium_tier_avg': index_summary['tier_summary'][index_summary['tier_summary']['忠诚度层级'] == '中忠诚度']['平均指数'].values[0] if '中忠诚度' in index_summary['tier_summary']['忠诚度层级'].values else 0,
                'low_tier_avg': index_summary['tier_summary'][index_summary['tier_summary']['忠诚度层级'] == '低忠诚度']['平均指数'].values[0] if '低忠诚度' in index_summary['tier_summary']['忠诚度层级'].values else 0
            }
            if 'personalized_recommendations' in self.loyalty_results:
                report['personalized_recommendations'] = self.loyalty_results['personalized_recommendations'].to_dict('records')
            if 'segment_recommendations' in self.loyalty_results:
                report['segment_recommendations'] = self.loyalty_results['segment_recommendations']
        
        return report
    
    def get_nps_metrics(self):
        if self.data is None:
            self.load_or_generate_data()
        
        nps_df = self.data['nps']
        
        def classify_nps(score):
            if score >= 9:
                return 'promoter'
            elif score >= 7:
                return 'passive'
            else:
                return 'detractor'
        
        nps_df['category'] = nps_df['nps_score'].apply(classify_nps)
        
        total = len(nps_df)
        promoters = (nps_df['category'] == 'promoter').sum()
        passives = (nps_df['category'] == 'passive').sum()
        detractors = (nps_df['category'] == 'detractor').sum()
        
        nps_score = ((promoters - detractors) / total) * 100
        
        return {
            'nps_score': nps_score,
            'promoter_pct': (promoters / total) * 100,
            'passive_pct': (passives / total) * 100,
            'detractor_pct': (detractors / total) * 100,
            'avg_score': nps_df['nps_score'].mean(),
            'total_surveys': total
        }
    
    def get_complaint_metrics(self):
        if self.data is None:
            self.load_or_generate_data()
        
        complaints_df = self.data['complaints']
        profiles_df = self.data['profiles']
        
        total_customers = len(profiles_df)
        customers_with_complaints = complaints_df['customer_id'].nunique()
        
        complaint_rate = (customers_with_complaints / total_customers) * 100
        
        complaint_type_dist = complaints_df['complaint_type'].value_counts(normalize=True) * 100
        resolution_rate = complaints_df['is_resolved'].mean() * 100
        avg_resolution_time = complaints_df['resolution_time_days'].mean()
        
        return {
            'complaint_rate': complaint_rate,
            'total_complaints': len(complaints_df),
            'customers_with_complaints': customers_with_complaints,
            'complaint_type_distribution': complaint_type_dist.to_dict(),
            'resolution_rate': resolution_rate,
            'avg_resolution_time_days': avg_resolution_time
        }
    
    def get_repurchase_metrics(self):
        if self.data is None:
            self.load_or_generate_data()
        
        purchases_df = self.data['purchases']
        profiles_df = self.data['profiles']
        
        total_customers = len(profiles_df)
        customer_purchase_counts = purchases_df.groupby('customer_id').size()
        repeat_customers = (customer_purchase_counts > 1).sum()
        repurchase_rate = (repeat_customers / total_customers) * 100
        
        avg_purchases_per_customer = customer_purchase_counts.mean()
        
        purchases_df['purchase_date'] = pd.to_datetime(purchases_df['purchase_date'])
        purchases_sorted = purchases_df.sort_values(['customer_id', 'purchase_date'])
        purchases_sorted['prev_purchase'] = purchases_sorted.groupby('customer_id')['purchase_date'].shift(1)
        purchases_sorted['inter_purchase_days'] = (purchases_sorted['purchase_date'] - purchases_sorted['prev_purchase']).dt.days
        
        avg_inter_purchase = purchases_sorted['inter_purchase_days'].mean()
        
        return {
            'repurchase_rate': repurchase_rate,
            'repeat_customers': repeat_customers,
            'total_customers': total_customers,
            'avg_purchases_per_customer': avg_purchases_per_customer,
            'avg_days_between_purchases': avg_inter_purchase
        }
    
    def export_results(self, output_dir='results'):
        import os
        import json
        os.makedirs(output_dir, exist_ok=True)
        
        if self.loyalty_results:
            self.loyalty_results['metrics_with_index'].to_csv(
                f'{output_dir}/customer_loyalty_scores.csv', index=False
            )
            
            if 'personalized_recommendations' in self.loyalty_results:
                self.loyalty_results['personalized_recommendations'].to_csv(
                    f'{output_dir}/personalized_recommendations.csv', index=False
                )
            
            if 'segment_recommendations' in self.loyalty_results:
                seg_recs = pd.DataFrame([
                    {
                        'segment': seg,
                        'user_count': info['user_count'],
                        'avg_loyalty_index': info['avg_loyalty_index'],
                        'avg_total_spend': info['avg_total_spend'],
                        'strategies': '; '.join(info['targeted_strategies'])
                    }
                    for seg, info in self.loyalty_results['segment_recommendations'].items()
                ])
                seg_recs.to_csv(f'{output_dir}/segment_recommendations.csv', index=False)
        
        if self.clustering_results:
            self.clustering_results['cluster_profiles'].to_csv(
                f'{output_dir}/cluster_profiles.csv', index=False
            )
        
        if self.attribution_results:
            self.attribution_results['importance_results']['all_importance'].to_csv(
                f'{output_dir}/feature_importance.csv', index=False
            )
            self.attribution_results['factor_impact'].to_csv(
                f'{output_dir}/factor_impact.csv', index=False
            )
            self.attribution_results['recommendations'].to_csv(
                f'{output_dir}/recommendations.csv', index=False
            )
            
            if 'price_promotion_impact' in self.attribution_results:
                pp_impact = self.attribution_results['price_promotion_impact']
                with open(f'{output_dir}/price_promotion_impact.json', 'w', encoding='utf-8') as f:
                    json.dump(pp_impact, f, ensure_ascii=False, indent=2, default=str)
        
        if self.survival_results:
            self.survival_results['survival_data'].to_csv(
                f'{output_dir}/survival_metrics.csv', index=False
            )
            
            if 'category_stats' in self.survival_results:
                self.survival_results['category_stats'].to_csv(
                    f'{output_dir}/category_purchase_cycles.csv', index=False
                )
        
        if self.competitor_results:
            switch_data = self.data.get('competitor_switches')
            if switch_data is not None and len(switch_data) > 0:
                switch_data.to_csv(f'{output_dir}/competitor_switches.csv', index=False)
            
            if 'switch_prediction' in self.competitor_results and 'all_risk_scores' in self.competitor_results['switch_prediction']:
                self.competitor_results['switch_prediction']['all_risk_scores'].to_csv(
                    f'{output_dir}/switch_risk_scores.csv', index=False
                )
        
        if self.prediction_results:
            trend_data = self.data.get('loyalty_trends')
            if trend_data is not None and len(trend_data) > 0:
                trend_data.to_csv(f'{output_dir}/loyalty_trends.csv', index=False)
            
            if 'loyalty_prediction' in self.prediction_results and 'user_predictions' in self.prediction_results['loyalty_prediction']:
                self.prediction_results['loyalty_prediction']['user_predictions'].to_csv(
                    f'{output_dir}/loyalty_predictions.csv', index=False
                )
        
        if self.referral_results:
            referral_data = self.data.get('referrals')
            if referral_data is not None and len(referral_data) > 0:
                referral_data.to_csv(f'{output_dir}/referrals.csv', index=False)
        
        print(f"Results exported to {output_dir}/ directory")
    
    def get_strategy_recommendations(self):
        recommendations = []
        
        if self.loyalty_results and 'tiered_strategies' in self.loyalty_results:
            tiered = self.loyalty_results['tiered_strategies']
            for tier, info in tiered.items():
                rec = {
                    'category': 'tiered',
                    'tier': tier,
                    'focus': info['focus'],
                    'count': info['count'],
                    'avg_index': info['avg_index'],
                    'strategies': info['key_strategies'],
                    'expected_impact': info['expected_impact'],
                    'key_metrics': info['key_metrics']
                }
                if 'avg_price_sensitivity' in info:
                    rec['avg_price_sensitivity'] = info['avg_price_sensitivity']
                    rec['avg_promotion_responsiveness'] = info['avg_promotion_responsiveness']
                recommendations.append(rec)
        
        if self.loyalty_results and 'segment_recommendations' in self.loyalty_results:
            for seg, info in self.loyalty_results['segment_recommendations'].items():
                recommendations.append({
                    'category': 'segment',
                    'segment': seg,
                    'description': info['segment_description'],
                    'user_count': info['user_count'],
                    'avg_loyalty_index': info['avg_loyalty_index'],
                    'strategies': info['targeted_strategies'],
                    'tier_distribution': info.get('tier_distribution', {})
                })
        
        if self.attribution_results and 'recommendations' in self.attribution_results:
            attr_recs = self.attribution_results['recommendations']
            for _, rec in attr_recs.iterrows():
                recommendations.append({
                    'category': 'factor',
                    'type': rec['type'],
                    'factor': rec['factor'],
                    'impact': rec['impact'],
                    'strategy': rec['strategy'],
                    'priority': rec['priority']
                })
        
        if self.loyalty_results and 'personalized_recommendations' in self.loyalty_results:
            personal_recs = self.loyalty_results['personalized_recommendations']
            for _, rec in personal_recs.head(20).iterrows():
                recommendations.append({
                    'category': 'personalized',
                    'customer_id': rec['customer_id'],
                    'loyalty_tier': rec['loyalty_tier'],
                    'loyalty_index': rec['loyalty_index'],
                    'user_segment': rec['user_segment'],
                    'strategies': [s['strategy'] for s in rec['personalized_strategies']],
                    'product_recommendations': rec['product_recommendations'],
                    'promotion_recommendations': rec['promotion_recommendations'],
                    'communication_recommendations': rec['communication_recommendations'],
                    'expected_outcome': rec['expected_outcome'],
                    'priority_score': rec['priority_score']
                })
        
        return recommendations
    
    def get_personalized_recommendation(self, customer_id):
        if self.loyalty_results and 'personalized_recommendations' in self.loyalty_results:
            personal_recs = self.loyalty_results['personalized_recommendations']
            user_rec = personal_recs[personal_recs['customer_id'] == customer_id]
            if len(user_rec) > 0:
                return user_rec.iloc[0].to_dict()
        return None
    
    def get_price_promotion_insights(self):
        if self.attribution_results and 'price_promotion_impact' in self.attribution_results:
            return self.attribution_results['price_promotion_impact']
        return None


if __name__ == '__main__':
    analyzer = BrandLoyaltyAnalyzer(n_customers=1000, use_cached_data=False)
    
    summary = analyzer.run_full_analysis()
    
    print("\n" + "=" * 60)
    print("SUMMARY REPORT")
    print("=" * 60)
    
    print("\n📊 Key Metrics:")
    nps = analyzer.get_nps_metrics()
    complaints = analyzer.get_complaint_metrics()
    repurchase = analyzer.get_repurchase_metrics()
    
    print(f"  NPS Score: {nps['nps_score']:.1f}")
    print(f"  Repurchase Rate: {repurchase['repurchase_rate']:.1f}%")
    print(f"  Complaint Rate: {complaints['complaint_rate']:.1f}%")
    
    print("\n🏷️  Loyalty Distribution:")
    if 'clustering' in summary:
        for cluster in summary['clustering']['cluster_distribution']:
            print(f"  {cluster['忠诚度层级']}: {cluster['用户数量']} users ({cluster['用户占比']*100:.1f}%)")
    
    print("\n📈 Overall Loyalty Index:")
    if 'loyalty_index' in summary:
        print(f"  Average: {summary['loyalty_index']['overall_avg']:.1f}")
        print(f"  Median: {summary['loyalty_index']['overall_median']:.1f}")
    
    print("\n💡 Top Recommendations:")
    strategies = analyzer.get_strategy_recommendations()
    for i, strat in enumerate(strategies[:5], 1):
        if 'strategy' in strat:
            print(f"  {i}. {strat['strategy']}")
        else:
            print(f"  {i}. [{strat['tier']}] {strat['focus']}: {strat['strategies'][0]}")
    
    print("\nExporting results...")
    analyzer.export_results()
    
    print("\nDone!")
