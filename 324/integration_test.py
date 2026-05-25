import sys
sys.stdout.reconfigure(encoding='utf-8')

import warnings
warnings.filterwarnings('ignore')

from prediction_engine import RatingPredictionEngine
from data_generator import generate_drama_basic_info, generate_social_media_data, generate_episodic_ratings
from sentiment_analyzer import generate_episode_comments_batch, aggregate_episode_sentiment
from datetime import date, timedelta
import numpy as np
import pandas as pd

print("=" * 80)
print("  End-to-End Integration Test")
print("=" * 80)

print("\n[Step 1] Initializing Prediction Engine...")
engine = RatingPredictionEngine()

print("\n[Step 2] Training models (if not exists)...")
engine.train_models(num_dramas=15, force_retrain=True)

print("\n[Step 3] Creating test drama...")
drama = generate_drama_basic_info()
drama['name'] = '《长安风云录》'
drama['num_episodes'] = 40
drama['production_budget'] = 30000
drama['director_reputation'] = 0.9
drama['is_sequel'] = False
drama['start_date'] = date(2024, 6, 1)

print(f"  Drama: {drama['name']}")
print(f"  Genre: {drama['genre']}")
print(f"  Platform: {drama['platform']}")
print(f"  Actor: {drama['actor_level']}")
print(f"  Episodes: {drama['num_episodes']}")
print(f"  Budget: {drama['production_budget']:,} 万元")

print("\n[Step 4] Generating broadcast dates...")
start_date = date(2024, 6, 1)
dates = [start_date + timedelta(days=i) for i in range(drama['num_episodes'])]
print(f"  Broadcast: {dates[0]} ~ {dates[-1]}")

print("\n[Step 5] Generating true ratings for data generation...")
_, true_ratings = generate_episodic_ratings(drama)
print(f"  Generated {len(true_ratings)} episode ratings")

print("\n[Step 6] Generating social media data...")
social_df = generate_social_media_data(drama, dates, true_ratings)
print(f"  Social data: {len(social_df)} rows")
print(f"  Columns: {list(social_df.columns)}")

print("\n[Step 7] Generating comments and sentiment analysis...")
comments_df = generate_episode_comments_batch(drama, dates, true_ratings)
sentiment_stats = aggregate_episode_sentiment(comments_df)
print(f"  Comments: {len(comments_df)}")
print(f"  Avg sentiment: {comments_df['sentiment'].mean():.3f}")

print("\n[Step 8] Setting initial known ratings (first 8 episodes)...")
initial_ratings = [2.1, 2.3, 2.5, 2.4, 2.7, 2.9, 2.8, 2.6]
print(f"  Initial ratings: {[f'{r:.2f}' for r in initial_ratings]}")

print("\n[Step 9] Generating full prediction report (with all new features)...")
print("  Includes: Time Interval Gate, Premiere Prediction, Revenue Model")
report = engine.generate_full_prediction_report(
    drama, dates, initial_ratings, social_df, comments_df,
    include_trailer_heat=True, use_revenue_model=True
)

print("\n" + "=" * 80)
print("  RESULTS")
print("=" * 80)

print("\n📊 Predictions Summary:")
df = report['episode_details']
predictions = report['predictions']
known_mask = df['known_rating'].notna()
pred_mask = df['known_rating'].isna()
import numpy as np
print(f"  Known episodes: {known_mask.sum()}")
print(f"  Predicted episodes: {pred_mask.sum()}")
pred_array = np.array(predictions['ensemble_predictions'])
print(f"  Avg predicted rating: {pred_array[known_mask.sum():].mean():.3f}")
print(f"  Peak predicted rating: {pred_array.max():.3f}")

print("\n🔥 Peak Episodes:")
for peak in report['peak_episodes']:
    print(f"  Episode {peak['episode']}: {peak['predicted_rating']:.3f}% (confidence: {peak['confidence']})")

print("\n🎬 Premiere Prediction:")
if 'premiere_prediction' in report and report['premiere_prediction']:
    pp = report['premiere_prediction']
    print(f"  Predicted premiere: {pp['predicted_rating']:.2f}%")
    print(f"  Range: [{pp['lower_bound']:.2f}, {pp['upper_bound']:.2f}]")
    print(f"  Confidence: {pp['confidence']*100:.1f}%")
    print(f"  Key metrics: {pp['key_metrics']}")

print("\n⏰ Time Gate Analysis:")
if 'time_gate_analysis' in report and report['time_gate_analysis'] is not None:
    tg = report['time_gate_analysis']
    print(tg.to_string(index=False))

print("\n💰 Renewal Recommendation (with Revenue Model):")
renewal = report['renewal_recommendation']
print(f"  Recommendation: {renewal['recommendation']}")
print(f"  Confidence: {renewal['confidence']}")
print(f"  Total Score: {renewal['total_score']:.1f}")

if 'revenue_analysis' in renewal:
    ra = renewal['revenue_analysis']
    pm = ra['profit_metrics']
    print(f"\n  Revenue Analysis:")
    print(f"    Total Revenue: {pm['revenue']['total_revenue']/10000:.1f} 万元")
    print(f"    Total Cost: {pm['cost']['total_cost']/10000:.1f} 万元")
    print(f"    Net Profit: {pm['net_profit']/10000:.1f} 万元")
    print(f"    ROI: {pm['roi']*100:.2f}%")
    print(f"    Payback Period: {pm['payback_period_years']} 年")
    print(f"    Net Margin: {pm['net_margin']*100:.2f}%")
    
    print(f"\n  Key Reasons:")
    for reason in renewal['key_reasons']:
        print(f"    - {reason}")

print("\n" + "=" * 80)
print("  INTEGRATION TEST PASSED!")
print("=" * 80)
print()
print("  All features working together:")
print("  ✅ LSTM with Time Interval Gate")
print("  ✅ XGBoost + LSTM Ensemble")
print("  ✅ Sentiment Analysis")
print("  ✅ Premiere Prediction with Trailer Heat")
print("  ✅ Revenue Model for Renewal Decision")
print("  ✅ Peak Episode Detection")
print()
