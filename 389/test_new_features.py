import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_generator import AdDataGenerator, prepare_model_data

print("Testing data generation with positions...")
gen = AdDataGenerator(n_users=500, n_ads=20, n_impressions=2000, n_positions=5)
data = gen.generate_all_data(include_auctions=True)

print(f"Users: {len(data['users'])}")
print(f"Ads: {len(data['ads'])}")
print(f"Positions: {len(data['positions'])}")
print(f"Impressions: {len(data['impressions'])}")
print(f"Auctions: {len(data['auctions'])}")

print("\nPositions data:")
print(data['positions'])

print("\nImpression columns:")
print(data['impressions'].columns.tolist())

print("\nAuction columns:")
print(data['auctions'].columns.tolist())

print("\nPreparing model data...")
X, T, Y, ad_ids, user_ids, impression_ids, position_ids, df = prepare_model_data(
    data['impressions'], data['users'], data['ads'], data['positions']
)
print(f"Features shape: {X.shape}")
print(f"Position IDs in data: {df['position_id'].unique()[:5]}")

print("\nAll tests passed!")