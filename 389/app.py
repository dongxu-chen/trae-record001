from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from data_generator import AdDataGenerator, prepare_model_data
from causal_model import IncrementalValueModel
from optimizer import BudgetOptimizer
from position_analyzer import PositionValueAnalyzer
from bid_simulator import DynamicBidSimulator
from auction_simulator import AuctionSimulator
import traceback

app = Flask(__name__)

data_store = {
    'df_users': None,
    'df_ads': None,
    'df_positions': None,
    'df_impressions': None,
    'df_auctions': None,
    'X': None,
    'T': None,
    'Y': None,
    'ad_ids': None,
    'user_ids': None,
    'impression_ids': None,
    'causal_model': None,
    'value_results': None,
    'optimizer': None,
    'position_analyzer': None,
    'bid_simulator': None,
    'auction_simulator': None,
    'position_metrics': None,
    'initialized': False
}


def initialize_data(n_users=5000, n_ads=50, n_impressions=30000, n_positions=5, n_competitors=5):
    generator = AdDataGenerator(n_users=n_users, n_ads=n_ads, n_impressions=n_impressions, n_positions=n_positions)
    df_users, df_ads, df_positions, df_impressions, df_auctions = generator.generate_all_data(n_competitors=n_competitors)

    X, T, Y, ad_ids, user_ids, impression_ids, _ = prepare_model_data(df_impressions, df_users, df_ads, df_positions)

    data_store['df_users'] = df_users
    data_store['df_ads'] = df_ads
    data_store['df_positions'] = df_positions
    data_store['df_impressions'] = df_impressions
    data_store['df_auctions'] = df_auctions
    data_store['X'] = X
    data_store['T'] = T
    data_store['Y'] = Y
    data_store['ad_ids'] = ad_ids
    data_store['user_ids'] = user_ids
    data_store['impression_ids'] = impression_ids

    return df_users, df_ads, df_positions, df_impressions, df_auctions


def run_causal_analysis(method='causal_forest', use_ps_weighting=False,
                         total_budget=300000.0, frequency_decay_alpha=0.1,
                         max_budget_change_pct=30.0, min_budget_ratio=0.02,
                         max_budget_ratio=0.25):
    if not data_store['initialized']:
        initialize_data()

    model = IncrementalValueModel(
        n_trees=300, max_depth=8, n_splits=5,
        use_ps_weighting=use_ps_weighting
    )
    value_results = model.compute_counterfactual_values(
        data_store['X'],
        data_store['T'],
        data_store['Y'],
        data_store['ad_ids'],
        data_store['impression_ids'],
        method=method
    )

    data_store['causal_model'] = model
    data_store['value_results'] = value_results
    data_store['optimizer'] = BudgetOptimizer(
        total_budget=total_budget,
        frequency_decay_alpha=frequency_decay_alpha,
        max_budget_change_pct=max_budget_change_pct,
        min_budget_ratio=min_budget_ratio,
        max_budget_ratio=max_budget_ratio
    )

    position_analyzer = PositionValueAnalyzer()
    position_metrics = position_analyzer.analyze_position_values(value_results, data_store['df_positions'])
    data_store['position_analyzer'] = position_analyzer
    data_store['position_metrics'] = position_metrics

    data_store['bid_simulator'] = DynamicBidSimulator(total_budget=total_budget, time_horizon=30, roi_threshold=1.2)
    data_store['auction_simulator'] = AuctionSimulator()
    data_store['auction_simulator'].load_auction_logs(data_store['df_auctions'])

    data_store['initialized'] = True

    return value_results


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'initialized': data_store['initialized'],
        'model_loaded': data_store['causal_model'] is not None,
        'available_methods': ['causal_forest', 'double_ml'],
        'features': [
            'propensity_score_weighting',
            'frequency_decay_ranking',
            'smoothed_budget_allocation',
            'position_analysis',
            'bid_simulation',
            'auction_simulation'
        ]
    })


@app.route('/api/init', methods=['POST'])
def initialize():
    try:
        params = request.get_json() or {}
        n_users = params.get('n_users', 5000)
        n_ads = params.get('n_ads', 50)
        n_impressions = params.get('n_impressions', 30000)
        n_positions = params.get('n_positions', 5)
        n_competitors = params.get('n_competitors', 5)

        initialize_data(n_users=n_users, n_ads=n_ads, n_impressions=n_impressions,
                        n_positions=n_positions, n_competitors=n_competitors)

        return jsonify({
            'status': 'success',
            'message': 'Data initialized successfully',
            'data_summary': {
                'n_users': len(data_store['df_users']),
                'n_ads': len(data_store['df_ads']),
                'n_positions': len(data_store['df_positions']),
                'n_impressions': len(data_store['df_impressions']),
                'n_auctions': len(data_store['df_auctions'])
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        params = request.get_json() or {}
        method = params.get('method', 'causal_forest')
        use_ps_weighting = params.get('use_ps_weighting', False)
        total_budget = params.get('total_budget', 300000.0)
        frequency_decay_alpha = params.get('frequency_decay_alpha', 0.1)
        max_budget_change_pct = params.get('max_budget_change_pct', 30.0)
        min_budget_ratio = params.get('min_budget_ratio', 0.02)
        max_budget_ratio = params.get('max_budget_ratio', 0.25)

        if method not in ['causal_forest', 'double_ml']:
            return jsonify({'status': 'error', 'message': 'Method must be causal_forest or double_ml'}), 400

        run_causal_analysis(
            method=method,
            use_ps_weighting=use_ps_weighting,
            total_budget=total_budget,
            frequency_decay_alpha=frequency_decay_alpha,
            max_budget_change_pct=max_budget_change_pct,
            min_budget_ratio=min_budget_ratio,
            max_budget_ratio=max_budget_ratio
        )

        optimizer = data_store['optimizer']
        report = optimizer.generate_optimization_report(
            data_store['value_results'],
            data_store['df_ads'],
            data_store['df_users']
        )

        return jsonify({
            'status': 'success',
            'method': method,
            'use_ps_weighting': use_ps_weighting,
            'config': {
                'total_budget': total_budget,
                'frequency_decay_alpha': frequency_decay_alpha,
                'max_budget_change_pct': max_budget_change_pct,
                'min_budget_ratio': min_budget_ratio,
                'max_budget_ratio': max_budget_ratio
            },
            'report': report
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/position-analysis', methods=['GET'])
def position_analysis():
    try:
        if data_store['position_metrics'] is None:
            if data_store['value_results'] is None:
                return jsonify({'status': 'error', 'message': 'Run analysis first'}), 400
            position_analyzer = PositionValueAnalyzer()
            position_metrics = position_analyzer.analyze_position_values(
                data_store['value_results'],
                data_store['df_positions']
            )
            data_store['position_metrics'] = position_metrics
            data_store['position_analyzer'] = position_analyzer
        else:
            position_metrics = data_store['position_metrics']
            position_analyzer = data_store['position_analyzer']

        position_comparison = position_analyzer.compare_positions(position_metrics)

        ad_position_metrics = position_analyzer.analyze_position_by_ad(
            data_store['value_results'],
            data_store['df_positions'],
            data_store['df_ads']
        )

        positions_list = data_store['df_positions'].to_dict('records')
        position_metrics_list = position_metrics.to_dict('records')
        ad_position_metrics_list = ad_position_metrics.to_dict('records')

        return jsonify({
            'status': 'success',
            'positions': positions_list,
            'position_metrics': position_metrics_list,
            'position_comparison': position_comparison,
            'ad_position_metrics': ad_position_metrics_list
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/bid-simulation', methods=['POST'])
def bid_simulation():
    try:
        if data_store['value_results'] is None:
            return jsonify({'status': 'error', 'message': 'Run analysis first'}), 400

        params = request.get_json() or {}
        total_budget = params.get('total_budget', 300000.0)
        time_horizon = params.get('time_horizon', 30)
        roi_threshold = params.get('roi_threshold', 1.2)

        ad_summary = data_store['value_results'].merge(
            data_store['df_ads'][['ad_id', 'category', 'base_bid', 'ad_quality_score']],
            on='ad_id', how='left'
        )
        ad_summary_grouped = ad_summary.groupby('ad_id').agg(
            total_impressions=('impression_id', 'count'),
            total_clicks=('click', 'sum'),
            mean_incremental_value=('incremental_value', 'mean'),
            total_conversion_value=('conversion_value', 'sum')
        ).reset_index()
        ad_summary_grouped = ad_summary_grouped.merge(
            data_store['df_ads'][['ad_id', 'base_bid', 'ad_quality_score', 'category']],
            on='ad_id', how='left'
        )
        ad_summary_grouped['ctr'] = ad_summary_grouped['total_clicks'] / ad_summary_grouped['total_impressions']
        ad_summary_grouped['value_roi'] = ad_summary_grouped['total_conversion_value'] / ad_summary_grouped['base_bid']

        bid_simulator = DynamicBidSimulator(
            total_budget=total_budget,
            time_horizon=time_horizon,
            roi_threshold=roi_threshold
        )

        position_metrics = data_store['position_metrics']
        if position_metrics is None:
            position_analyzer = PositionValueAnalyzer()
            position_metrics = position_analyzer.analyze_position_values(
                data_store['value_results'],
                data_store['df_positions']
            )

        allocation_df, simulation_df = bid_simulator.simulate_bidding_with_budget(
            ad_summary_grouped, position_metrics, total_budget=total_budget
        )

        bid_recommendations = bid_simulator.generate_bid_recommendations(
            ad_summary_grouped, position_metrics, total_budget=total_budget
        )

        return jsonify({
            'status': 'success',
            'config': {
                'total_budget': total_budget,
                'time_horizon': time_horizon,
                'roi_threshold': roi_threshold
            },
            'bid_allocation': allocation_df.to_dict('records'),
            'bid_recommendations': bid_recommendations.to_dict('records'),
            'simulation_summary': {
                'total_allocated': allocation_df['allocated_budget'].sum(),
                'avg_expected_roi': allocation_df['expected_roi'].mean(),
                'max_expected_roi': allocation_df['expected_roi'].max(),
                'num_positive_roi': len(allocation_df[allocation_df['expected_roi'] >= roi_threshold])
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/auction-simulation', methods=['POST'])
def auction_simulation():
    try:
        if data_store['df_auctions'] is None:
            return jsonify({'status': 'error', 'message': 'Initialize data first'}), 400

        params = request.get_json() or {}
        ad_id = params.get('ad_id')
        bid_multiplier = params.get('bid_multiplier', 1.0)
        strategy_type = params.get('strategy_type', 'fixed')

        if ad_id is None:
            return jsonify({'status': 'error', 'message': 'ad_id is required'}), 400

        auction_simulator = data_store['auction_simulator']
        if auction_simulator is None or auction_simulator.auction_logs is None:
            auction_simulator = AuctionSimulator()
            auction_simulator.load_auction_logs(data_store['df_auctions'])
            data_store['auction_simulator'] = auction_simulator

        if strategy_type == 'fixed':
            def bid_strategy(auctions, original_bids, aid):
                return original_bids * bid_multiplier
        elif strategy_type == 'aggressive':
            def bid_strategy(auctions, original_bids, aid):
                return original_bids * 1.3
        elif strategy_type == 'conservative':
            def bid_strategy(auctions, original_bids, aid):
                return original_bids * 0.8
        else:
            def bid_strategy(auctions, original_bids, aid):
                return original_bids * bid_multiplier

        simulation_results = auction_simulator.simulate_strategy(int(ad_id), bid_strategy)

        if len(simulation_results) == 0:
            return jsonify({
                'status': 'success',
                'message': f'No auctions found for ad_id {ad_id}',
                'simulation_results': [],
                'metrics': []
            })

        metrics = auction_simulator.calculate_key_metrics(simulation_results)

        daily_budgets = {}
        for date_str in simulation_results['_date'].unique():
            daily_budgets[str(date_str)] = 10000.0

        daily_df, summary_df = auction_simulator.backtest_budget_pacing(
            int(ad_id), daily_budgets, bid_strategy
        )

        results_list = simulation_results.head(100).to_dict('records')
        metrics_list = metrics.to_dict('records')
        daily_list = daily_df.to_dict('records')
        summary_list = summary_df.to_dict('records')

        return jsonify({
            'status': 'success',
            'ad_id': ad_id,
            'strategy_type': strategy_type,
            'bid_multiplier': bid_multiplier,
            'simulation_results': results_list,
            'metrics': metrics_list,
            'daily_pacing': daily_list,
            'pacing_summary': summary_list,
            'total_auctions_simulated': len(simulation_results)
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/exposure-ranking', methods=['GET'])
def get_exposure_ranking():
    try:
        if data_store['value_results'] is None:
            return jsonify({'status': 'error', 'message': 'Run analysis first'}), 400

        optimizer = data_store['optimizer']
        ranked = optimizer.rank_exposures_by_value(
            data_store['value_results'],
            data_store['df_ads'],
            data_store['df_users']
        )

        top_n = request.args.get('top_n', 50, type=int)
        sort_by = request.args.get('sort_by', 'value_per_impression')

        ranked = ranked.head(top_n)

        return jsonify({
            'status': 'success',
            'total_count': len(data_store['value_results']),
            'returned_count': len(ranked),
            'exposures': ranked.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/ad-value-summary', methods=['GET'])
def get_ad_value_summary():
    try:
        if data_store['value_results'] is None:
            return jsonify({'status': 'error', 'message': 'Run analysis first'}), 400

        optimizer = data_store['optimizer']
        summary = optimizer.compute_ad_value_summary(
            data_store['value_results'],
            data_store['df_ads']
        )

        return jsonify({
            'status': 'success',
            'ads_summary': summary.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/bid-advisements', methods=['GET'])
def get_bid_advisements():
    try:
        if data_store['value_results'] is None:
            return jsonify({'status': 'error', 'message': 'Run analysis first'}), 400

        optimizer = data_store['optimizer']
        ad_summary = optimizer.compute_ad_value_summary(
            data_store['value_results'],
            data_store['df_ads']
        )
        adjustments = optimizer.generate_bid_adjustments(ad_summary)

        return jsonify({
            'status': 'success',
            'bid_advisements': adjustments.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/budget-allocation', methods=['GET'])
def get_budget_allocation():
    try:
        if data_store['value_results'] is None:
            return jsonify({'status': 'error', 'message': 'Run analysis first'}), 400

        optimizer = data_store['optimizer']
        ad_summary = optimizer.compute_ad_value_summary(
            data_store['value_results'],
            data_store['df_ads']
        )
        allocation = optimizer.optimize_budget_allocation(ad_summary)

        return jsonify({
            'status': 'success',
            'total_budget': data_store['optimizer'].total_budget,
            'budget_allocation': allocation.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/ad/<int:ad_id>/recommendation', methods=['GET'])
def get_ad_recommendation(ad_id):
    try:
        if data_store['value_results'] is None:
            return jsonify({'status': 'error', 'message': 'Run analysis first'}), 400

        optimizer = data_store['optimizer']
        ad_summary = optimizer.compute_ad_value_summary(
            data_store['value_results'],
            data_store['df_ads']
        )

        bid_rec = optimizer.get_bid_recommendation_for_ad(ad_id, ad_summary)
        budget_rec = optimizer.get_budget_recommendation_for_ad(ad_id, ad_summary)

        if bid_rec is None and budget_rec is None:
            return jsonify({'status': 'error', 'message': f'Ad {ad_id} not found'}), 404

        return jsonify({
            'status': 'success',
            'ad_id': ad_id,
            'bid_recommendation': bid_rec,
            'budget_recommendation': budget_rec
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/feature-importance', methods=['GET'])
def get_feature_importance():
    try:
        if data_store['causal_model'] is None:
            return jsonify({'status': 'error', 'message': 'Run analysis first'}), 400

        importance = data_store['causal_model'].get_feature_importance(
            data_store['X'],
            data_store['T'],
            data_store['Y']
        )

        return jsonify({
            'status': 'success',
            'feature_importance': importance.to_dict('records')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    try:
        if data_store['df_users'] is None:
            return jsonify({'status': 'error', 'message': 'Initialize data first'}), 400

        user = data_store['df_users'][data_store['df_users']['user_id'] == user_id]

        if len(user) == 0:
            return jsonify({'status': 'error', 'message': f'User {user_id} not found'}), 404

        user_impressions = data_store['df_impressions'][data_store['df_impressions']['user_id'] == user_id]

        return jsonify({
            'status': 'success',
            'user_profile': user.iloc[0].to_dict(),
            'impression_stats': {
                'total_impressions': len(user_impressions),
                'total_clicks': user_impressions['click'].sum(),
                'total_conversions': user_impressions['conversion'].sum() if 'conversion' in user_impressions.columns else 0,
                'total_conversion_value': user_impressions['conversion_value'].sum()
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/report', methods=['GET'])
def get_full_report():
    try:
        if data_store['value_results'] is None:
            return jsonify({'status': 'error', 'message': 'Run analysis first'}), 400

        optimizer = data_store['optimizer']
        report = optimizer.generate_optimization_report(
            data_store['value_results'],
            data_store['df_ads'],
            data_store['df_users']
        )

        return jsonify({
            'status': 'success',
            'report': report
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    print("Initializing ad exposure value evaluation model server...")
    print("Generating simulated data...")
    initialize_data()
    print("Data generated successfully.")
    print("Starting server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
