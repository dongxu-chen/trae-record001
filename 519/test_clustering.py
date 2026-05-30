import sys
import os
sys.path.insert(0, os.getcwd())

from data_generator import CustomerDataGenerator
from clustering_module import LoyaltyClusterer

print("Generating data...")
gen = CustomerDataGenerator(n_customers=200)
data = gen.generate_all_data()

print("Initializing clusterer...")
clusterer = LoyaltyClusterer(n_clusters=3, method='kmeans')

print("Preparing features...")
features = clusterer.prepare_features(data)
print(f"Features shape: {features.shape}")
print(f"Columns: {list(features.columns[:10])}...")

print("Selecting features...")
selected = clusterer.select_features(features)
print(f"Selected shape: {selected.shape}")
print(f"Column types: {[type(c) for c in selected.columns][:5]}")

print("Fitting...")
try:
    result = clusterer.fit(features)
    print(f"Fit done. Clusters: {result['cluster'].unique()}")
except Exception as e:
    print(f"ERROR in fit: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Getting cluster profiles...")
try:
    profiles = clusterer.get_cluster_profiles(result)
    print(f"Profiles shape: {profiles.shape}")
    print(f"Profiles columns: {list(profiles.columns)}")
except Exception as e:
    print(f"ERROR in get_cluster_profiles: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Getting cluster characteristics...")
try:
    chars = clusterer.get_cluster_characteristics(result)
    print(f"Characteristics keys: {list(chars.keys())}")
except Exception as e:
    print(f"ERROR in get_cluster_characteristics: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All clustering tests passed!")
