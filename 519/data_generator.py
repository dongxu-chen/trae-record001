import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random


class CustomerDataGenerator:
    def __init__(self, n_customers=1000, random_seed=42):
        self.n_customers = n_customers
        np.random.seed(random_seed)
        random.seed(random_seed)

    def generate_customer_profiles(self):
        customer_ids = [f'CUST_{i:06d}' for i in range(self.n_customers)]
        
        age = np.random.randint(18, 75, size=self.n_customers)
        gender = np.random.choice(['Male', 'Female', 'Other'], size=self.n_customers, p=[0.48, 0.48, 0.04])
        
        segments = np.random.choice(
            ['Young Professional', 'Family', 'Senior', 'Student', 'High Net Worth'],
            size=self.n_customers,
            p=[0.25, 0.3, 0.15, 0.15, 0.15]
        )
        
        channels = np.random.choice(
            ['Online', 'Store', 'Hybrid'],
            size=self.n_customers,
            p=[0.4, 0.35, 0.25]
        )
        
        regions = np.random.choice(
            ['North', 'South', 'East', 'West', 'Central'],
            size=self.n_customers
        )
        
        loyalty_tendency = np.random.beta(2, 2, size=self.n_customers)
        
        price_sensitivity = np.random.beta(2, 3, size=self.n_customers)
        
        promotion_responsiveness = np.random.beta(3, 2, size=self.n_customers)
        
        profiles = pd.DataFrame({
            'customer_id': customer_ids,
            'age': age,
            'gender': gender,
            'segment': segments,
            'channel': channels,
            'region': regions,
            'loyalty_tendency': loyalty_tendency,
            'price_sensitivity': price_sensitivity,
            'promotion_responsiveness': promotion_responsiveness
        })
        
        return profiles

    def generate_purchase_history(self, profiles):
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2025, 12, 31)
        observation_days = (end_date - start_date).days
        
        category_config = {
            'Electronics': {
                'base_price': (300, 100),
                'purchase_cycle_days': 180,
                'promotion_frequency': 0.15,
                'typical_discount': (0.1, 0.3)
            },
            'Clothing': {
                'base_price': (80, 30),
                'purchase_cycle_days': 60,
                'promotion_frequency': 0.35,
                'typical_discount': (0.2, 0.5)
            },
            'Home': {
                'base_price': (150, 50),
                'purchase_cycle_days': 120,
                'promotion_frequency': 0.2,
                'typical_discount': (0.1, 0.25)
            },
            'Beauty': {
                'base_price': (50, 20),
                'purchase_cycle_days': 45,
                'promotion_frequency': 0.25,
                'typical_discount': (0.15, 0.35)
            },
            'Food': {
                'base_price': (30, 10),
                'purchase_cycle_days': 14,
                'promotion_frequency': 0.4,
                'typical_discount': (0.05, 0.2)
            },
            'Sports': {
                'base_price': (120, 40),
                'purchase_cycle_days': 90,
                'promotion_frequency': 0.2,
                'typical_discount': (0.1, 0.3)
            }
        }
        
        self.category_config = category_config
        
        purchase_records = []
        
        for _, customer in profiles.iterrows():
            base_purchase_freq = max(0.5, 3 - customer['loyalty_tendency'] * 2.5)
            
            n_purchases = np.random.poisson(lam=observation_days / (base_purchase_freq * 30))
            n_purchases = max(1, min(n_purchases, 50))
            
            purchase_dates = sorted([
                start_date + timedelta(days=np.random.randint(0, observation_days))
                for _ in range(n_purchases)
            ])
            
            categories = list(category_config.keys())
            category_p = [0.2, 0.25, 0.15, 0.15, 0.15, 0.1]
            
            for i, purchase_date in enumerate(purchase_dates):
                category = np.random.choice(categories, p=category_p)
                cat_config = category_config[category]
                
                base_price = np.random.normal(cat_config['base_price'][0], cat_config['base_price'][1])
                base_price = max(10, base_price)
                
                base_promo_prob = cat_config['promotion_frequency']
                promo_prob = base_promo_prob * (0.5 + customer['promotion_responsiveness'])
                is_promotion = np.random.binomial(1, p=min(promo_prob, 0.8))
                
                if is_promotion:
                    discount_min, discount_max = cat_config['typical_discount']
                    discount_pct = np.random.uniform(
                        discount_min * (1 + customer['price_sensitivity'] * 0.5),
                        discount_max * (1 + customer['price_sensitivity'] * 0.5)
                    )
                    discount_pct = min(discount_pct, 0.8)
                    discount_amount = base_price * discount_pct
                    final_price = base_price - discount_amount
                    
                    promotion_types = ['Direct Discount', 'Coupon', 'Bundle Deal', 'Membership Discount', 'Seasonal Sale']
                    promotion_type = np.random.choice(promotion_types, p=[0.35, 0.25, 0.15, 0.15, 0.1])
                else:
                    discount_pct = 0
                    discount_amount = 0
                    final_price = base_price
                    promotion_type = 'None'
                
                final_price = max(1, final_price)
                
                discount_used = 1 if is_promotion else 0
                is_returned = np.random.binomial(1, p=0.08 - customer['loyalty_tendency'] * 0.06)
                
                purchase_records.append({
                    'customer_id': customer['customer_id'],
                    'purchase_date': purchase_date,
                    'purchase_amount': round(final_price, 2),
                    'base_price': round(base_price, 2),
                    'discount_amount': round(discount_amount, 2),
                    'discount_pct': round(discount_pct, 4),
                    'is_promotion': is_promotion,
                    'promotion_type': promotion_type,
                    'order_number': i + 1,
                    'discount_used': discount_used,
                    'is_returned': is_returned,
                    'product_category': category,
                    'price_sensitivity': customer['price_sensitivity'],
                    'promotion_responsiveness': customer['promotion_responsiveness']
                })
        
        purchases_df = pd.DataFrame(purchase_records)
        return purchases_df

    def generate_nps_surveys(self, profiles, purchases_df):
        nps_records = []
        
        for _, customer in profiles.iterrows():
            customer_purchases = purchases_df[purchases_df['customer_id'] == customer['customer_id']]
            
            if len(customer_purchases) == 0:
                continue
            
            n_surveys = min(len(customer_purchases), np.random.randint(1, 4))
            survey_indices = sorted(random.sample(range(len(customer_purchases)), n_surveys))
            
            for idx in survey_indices:
                purchase = customer_purchases.iloc[idx]
                
                base_nps = 5 + customer['loyalty_tendency'] * 8
                base_nps += np.random.normal(0, 1.5)
                
                if purchase['is_returned']:
                    base_nps -= 3
                if purchase['discount_used']:
                    base_nps += 0.5
                
                nps_score = max(0, min(10, int(round(base_nps))))
                
                nps_records.append({
                    'customer_id': customer['customer_id'],
                    'survey_date': purchase['purchase_date'] + timedelta(days=np.random.randint(1, 14)),
                    'nps_score': nps_score,
                    'purchase_id': purchase.name,
                    'ease_of_use': max(1, min(5, int(round(base_nps / 2 + np.random.normal(0, 0.5))))),
                    'product_quality': max(1, min(5, int(round(base_nps / 2 + np.random.normal(0, 0.5))))),
                    'customer_service': max(1, min(5, int(round(base_nps / 2 + np.random.normal(0, 0.8)))))
                })
        
        nps_df = pd.DataFrame(nps_records)
        return nps_df

    def generate_complaints(self, profiles, purchases_df):
        complaint_records = []
        
        for _, customer in profiles.iterrows():
            customer_purchases = purchases_df[purchases_df['customer_id'] == customer['customer_id']]
            n_purchases = len(customer_purchases)
            
            complaint_prob = 0.1 - customer['loyalty_tendency'] * 0.08
            n_complaints = np.random.binomial(n_purchases, p=complaint_prob)
            
            if n_complaints > 0:
                complaint_indices = random.sample(range(n_purchases), n_complaints)
                
                for idx in complaint_indices:
                    purchase = customer_purchases.iloc[idx]
                    
                    complaint_type = np.random.choice(
                        ['Product Defect', 'Delivery Issue', 'Customer Service', 'Billing Error', 'Other'],
                        p=[0.3, 0.25, 0.2, 0.15, 0.1]
                    )
                    
                    resolution_time = np.random.randint(1, 15)
                    is_resolved = np.random.binomial(1, p=0.75 + customer['loyalty_tendency'] * 0.15)
                    
                    complaint_records.append({
                        'customer_id': customer['customer_id'],
                        'complaint_date': purchase['purchase_date'] + timedelta(days=np.random.randint(1, 7)),
                        'complaint_type': complaint_type,
                        'severity': np.random.choice(['Low', 'Medium', 'High'], p=[0.4, 0.4, 0.2]),
                        'resolution_time_days': resolution_time if is_resolved else None,
                        'is_resolved': is_resolved,
                        'purchase_id': purchase.name
                    })
        
        complaints_df = pd.DataFrame(complaint_records)
        return complaints_df

    def generate_interactions(self, profiles):
        interaction_records = []
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2025, 12, 31)
        
        for _, customer in profiles.iterrows():
            base_interactions = 3 + customer['loyalty_tendency'] * 10
            n_interactions = np.random.poisson(base_interactions)
            
            for _ in range(n_interactions):
                interaction_date = start_date + timedelta(days=np.random.randint(0, (end_date - start_date).days))
                interaction_type = np.random.choice(
                    ['Email Open', 'Click-Through', 'Social Media', 'Support Call', 'App Visit'],
                    p=[0.35, 0.25, 0.2, 0.1, 0.1]
                )
                
                interaction_records.append({
                    'customer_id': customer['customer_id'],
                    'interaction_date': interaction_date,
                    'interaction_type': interaction_type,
                    'duration_seconds': np.random.randint(10, 600) if interaction_type in ['App Visit', 'Click-Through'] else 0
                })
        
        interactions_df = pd.DataFrame(interaction_records)
        return interactions_df

    def generate_competitor_switches(self, profiles, purchases_df):
        competitors = ['BrandA', 'BrandB', 'BrandC', 'BrandD', 'BrandE']
        switch_reasons = [
            '更低价格', '更好品质', '更优服务', '更多促销', '新品吸引',
            '口碑推荐', '便利性', '品牌形象', '会员权益', '产品丰富度'
        ]
        switch_records = []
        
        for _, customer in profiles.iterrows():
            churn_prob = 0.3 - customer['loyalty_tendency'] * 0.25
            n_switches = np.random.binomial(1, p=max(0.02, churn_prob))
            
            if n_switches > 0:
                customer_purchases = purchases_df[purchases_df['customer_id'] == customer['customer_id']]
                if len(customer_purchases) == 0:
                    continue
                
                switch_date = customer_purchases['purchase_date'].max() + timedelta(days=np.random.randint(7, 90))
                
                target_competitor = np.random.choice(competitors, p=[0.3, 0.25, 0.2, 0.15, 0.1])
                
                n_reasons = np.random.randint(1, 4)
                selected_reasons = list(np.random.choice(switch_reasons, size=n_reasons, replace=False))
                
                price_sens = customer['price_sensitivity']
                promo_resp = customer['promotion_responsiveness']
                
                reason_weights = {
                    '更低价格': price_sens * 2,
                    '更多促销': promo_resp * 1.5,
                    '更好品质': (1 - price_sens) * 1.5,
                    '更优服务': customer['loyalty_tendency'] * 0.8,
                    '新品吸引': np.random.uniform(0.2, 0.8),
                    '口碑推荐': np.random.uniform(0.1, 0.5),
                    '便利性': np.random.uniform(0.2, 0.6),
                    '品牌形象': (1 - price_sens) * 1.2,
                    '会员权益': promo_resp * 1.0,
                    '产品丰富度': np.random.uniform(0.2, 0.7)
                }
                
                is_returned = np.random.binomial(1, p=0.15 + customer['loyalty_tendency'] * 0.2)
                return_date = switch_date + timedelta(days=np.random.randint(30, 180)) if is_returned else None
                
                switch_records.append({
                    'customer_id': customer['customer_id'],
                    'switch_date': switch_date,
                    'target_competitor': target_competitor,
                    'switch_reasons': '; '.join(selected_reasons),
                    'primary_reason': selected_reasons[0],
                    'price_sensitivity': price_sens,
                    'promotion_responsiveness': promo_resp,
                    'loyalty_tendency': customer['loyalty_tendency'],
                    'previous_spend': customer_purchases['purchase_amount'].sum(),
                    'previous_frequency': len(customer_purchases),
                    'is_returned': is_returned,
                    'return_date': return_date,
                    'return_competitor': np.random.choice(competitors) if is_returned else None,
                    'category_switched': customer_purchases['product_category'].mode().values[0] if len(customer_purchases) > 0 else 'Unknown'
                })
        
        return pd.DataFrame(switch_records)

    def generate_loyalty_trends(self, profiles, purchases_df):
        trend_records = []
        periods = [(datetime(2023, 3, 31), 'Q1_2023'), (datetime(2023, 6, 30), 'Q2_2023'),
                    (datetime(2023, 9, 30), 'Q3_2023'), (datetime(2023, 12, 31), 'Q4_2023'),
                    (datetime(2024, 3, 31), 'Q1_2024'), (datetime(2024, 6, 30), 'Q2_2024'),
                    (datetime(2024, 9, 30), 'Q3_2024'), (datetime(2024, 12, 31), 'Q4_2024'),
                    (datetime(2025, 3, 31), 'Q1_2025'), (datetime(2025, 6, 30), 'Q2_2025'),
                    (datetime(2025, 9, 30), 'Q3_2025'), (datetime(2025, 12, 31), 'Q4_2025')]
        
        start_date = datetime(2023, 1, 1)
        purchases_df = purchases_df.copy()
        purchases_df['purchase_date'] = pd.to_datetime(purchases_df['purchase_date'])
        
        period_bounds = []
        for i, (period_end, period_name) in enumerate(periods):
            period_start = start_date + timedelta(days=90 * i) if i > 0 else start_date
            period_bounds.append((period_start, period_end, period_name))
        
        quarter_purchases = {}
        for period_start, period_end, period_name in period_bounds:
            mask = (purchases_df['purchase_date'] >= period_start) & (purchases_df['purchase_date'] <= period_end)
            quarter_data = purchases_df[mask].groupby('customer_id').agg(
                purchase_count=('purchase_amount', 'count'),
                total_spend=('purchase_amount', 'sum'),
                avg_discount=('discount_used', 'mean')
            ).reset_index()
            quarter_purchases[period_name] = quarter_data
        
        for _, customer in profiles.iterrows():
            base_loyalty = 40 + customer['loyalty_tendency'] * 40
            trend_direction = np.random.choice([-1, 0, 1], p=[0.25, 0.35, 0.4])
            trend_strength = np.random.uniform(0.5, 3.0)
            cid = customer['customer_id']
            
            for i, (period_start, period_end, period_name) in enumerate(period_bounds):
                quarter_factor = i * trend_direction * trend_strength
                noise = np.random.normal(0, 5)
                
                q_data = quarter_purchases.get(period_name)
                if q_data is not None and cid in q_data['customer_id'].values:
                    row = q_data[q_data['customer_id'] == cid].iloc[0]
                    purchase_count = int(row['purchase_count'])
                    spend = float(row['total_spend'])
                    avg_disc = float(row['avg_discount']) if not pd.isna(row['avg_discount']) else 0
                else:
                    purchase_count = 0
                    spend = 0
                    avg_disc = 0
                
                activity_bonus = min(purchase_count * 0.5, 10)
                loyalty_score = max(0, min(100, base_loyalty + quarter_factor + noise + activity_bonus))
                
                trend_records.append({
                    'customer_id': cid,
                    'period': period_name,
                    'period_end_date': period_end,
                    'loyalty_score': round(loyalty_score, 1),
                    'purchase_count_quarter': purchase_count,
                    'spend_quarter': spend,
                    'nps_quarter': avg_disc,
                    'trend_direction': 'up' if trend_direction > 0 else ('down' if trend_direction < 0 else 'stable')
                })
        
        return pd.DataFrame(trend_records)

    def generate_referrals(self, profiles, purchases_df):
        referral_records = []
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2025, 12, 31)
        
        loyal_customers = profiles[profiles['loyalty_tendency'] > 0.5]
        
        for _, referrer in loyal_customers.iterrows():
            n_referrals = np.random.poisson(lam=referrer['loyalty_tendency'] * 2)
            
            for j in range(n_referrals):
                referral_date = start_date + timedelta(days=np.random.randint(0, (end_date - start_date).days))
                referred_customer_id = f'CUST_{np.random.randint(0, self.n_customers):06d}'
                
                conversion_prob = 0.4 + referrer['loyalty_tendency'] * 0.3
                is_converted = np.random.binomial(1, p=conversion_prob)
                
                referral_channel = np.random.choice(
                    ['Word of Mouth', 'Social Media', 'Referral Link', 'Review/Rating', 'Community Forum'],
                    p=[0.35, 0.25, 0.2, 0.12, 0.08]
                )
                
                if is_converted:
                    first_purchase_days = np.random.randint(1, 30)
                    converted_date = referral_date + timedelta(days=first_purchase_days)
                    referred_spend = np.random.uniform(50, 500)
                    referred_frequency = np.random.randint(1, 8)
                    is_still_active = np.random.binomial(1, p=0.6 + referrer['loyalty_tendency'] * 0.2)
                else:
                    converted_date = None
                    referred_spend = 0
                    referred_frequency = 0
                    is_still_active = False
                
                referral_records.append({
                    'referrer_id': referrer['customer_id'],
                    'referred_customer_id': referred_customer_id,
                    'referral_date': referral_date,
                    'referral_channel': referral_channel,
                    'is_converted': is_converted,
                    'converted_date': converted_date,
                    'referred_first_spend': referred_spend if is_converted else 0,
                    'referred_frequency': referred_frequency,
                    'referred_still_active': is_still_active,
                    'referrer_loyalty_tendency': referrer['loyalty_tendency'],
                    'referrer_segment': referrer['segment'],
                    'referrer_price_sensitivity': referrer['price_sensitivity'],
                    'referrer_promotion_responsiveness': referrer['promotion_responsiveness']
                })
        
        return pd.DataFrame(referral_records)

    def generate_all_data(self):
        print("Generating customer profiles...")
        profiles = self.generate_customer_profiles()
        
        print("Generating purchase history...")
        purchases = self.generate_purchase_history(profiles)
        
        print("Generating NPS surveys...")
        nps = self.generate_nps_surveys(profiles, purchases)
        
        print("Generating complaints...")
        complaints = self.generate_complaints(profiles, purchases)
        
        print("Generating interactions...")
        interactions = self.generate_interactions(profiles)
        
        print("Generating competitor switch data...")
        competitor_switches = self.generate_competitor_switches(profiles, purchases)
        
        print("Generating loyalty trends...")
        loyalty_trends = self.generate_loyalty_trends(profiles, purchases)
        
        print("Generating referral data...")
        referrals = self.generate_referrals(profiles, purchases)
        
        return {
            'profiles': profiles,
            'purchases': purchases,
            'nps': nps,
            'complaints': complaints,
            'interactions': interactions,
            'competitor_switches': competitor_switches,
            'loyalty_trends': loyalty_trends,
            'referrals': referrals
        }

    def save_data(self, data_dict, output_dir='data'):
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for name, df in data_dict.items():
            df.to_csv(f'{output_dir}/{name}.csv', index=False)
            print(f"Saved {output_dir}/{name}.csv ({len(df)} records)")


if __name__ == '__main__':
    generator = CustomerDataGenerator(n_customers=1000)
    data = generator.generate_all_data()
    generator.save_data(data)
    print("\nData generation complete!")
