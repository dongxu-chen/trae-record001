from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import traceback

from analysis.psm import PropensityScoreMatching
from analysis.did import DifferenceInDifferences
from analysis.robustness import RobustnessTests
from analysis.lasso_selection import LassoCovariateSelector
from analysis.did_enhanced import ParallelTrendTester
from analysis.placebo_enhanced import EnhancedPlaceboTester
from analysis.causal_graph import CausalGraphAnalyzer
from analysis.sensitivity_analysis import SensitivityAnalyzer
from analysis.report_generator import ReportGenerator

app = Flask(__name__)
CORS(app)


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Causal Inference API is running'})


@app.route('/api/preview', methods=['POST'])
def preview_data():
    try:
        data = request.json.get('data', [])
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        df = pd.DataFrame(data)
        columns = df.columns.tolist()
        preview = df.head(10).to_dict('records')
        missing_values = df.isnull().sum().to_dict()
        dtypes = df.dtypes.astype(str).to_dict()
        column_info = []
        for col in columns:
            col_data = df[col].dropna()
            unique_vals = col_data.unique()
            col_type = 'numeric'
            if len(unique_vals) <= 2 and all(v in [0, 1, '0', '1', True, False] for v in unique_vals):
                col_type = 'binary'
            elif len(unique_vals) < 10:
                col_type = 'categorical'
            elif pd.api.types.is_numeric_dtype(df[col]):
                col_type = 'numeric'
            column_info.append({
                'name': col,
                'type': col_type,
                'uniqueValues': len(unique_vals),
                'sampleValues': col_data.head(5).tolist()
            })
        return jsonify({
            'columns': columns,
            'preview': preview,
            'stats': {
                'rowCount': len(df),
                'columnCount': len(columns),
                'missingValues': {k: int(v) for k, v in missing_values.items()},
                'dtypes': dtypes
            },
            'columnInfo': column_info
        })
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/lasso-select', methods=['POST'])
def lasso_select():
    try:
        data = request.json.get('data', [])
        treatment = request.json.get('treatment')
        outcome = request.json.get('outcome')
        candidate_covariates = request.json.get('candidate_covariates', [])
        method = request.json.get('method', 'double_lasso')
        max_features = request.json.get('max_features', 20)
        
        if not data or not treatment or not outcome or not candidate_covariates:
            return jsonify({'error': 'Missing required parameters'}), 400
            
        df = pd.DataFrame(data)
        df[treatment] = pd.to_numeric(df[treatment], errors='coerce')
        df[outcome] = pd.to_numeric(df[outcome], errors='coerce')
        for cov in candidate_covariates:
            df[cov] = pd.to_numeric(df[cov], errors='coerce')
            
        selector = LassoCovariateSelector(df, treatment, outcome, candidate_covariates)
        selected = selector.auto_select(method=method, max_features=max_features)
        importance = selector.get_covariate_importance()
        
        return jsonify({
            'selected_covariates': selected,
            'covariate_importance': importance,
            'method_used': method
        })
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/analyze/psm', methods=['POST'])
def analyze_psm():
    try:
        data = request.json.get('data', [])
        treatment = request.json.get('treatment')
        outcome = request.json.get('outcome')
        covariates = request.json.get('covariates', [])
        use_auto_selection = request.json.get('useAutoSelection', False)
        auto_selection_method = request.json.get('autoSelectionMethod', 'double_lasso')
        
        if not data or not treatment or not outcome:
            return jsonify({'error': 'Missing required parameters'}), 400
            
        df = pd.DataFrame(data)
        df[treatment] = pd.to_numeric(df[treatment], errors='coerce')
        df[outcome] = pd.to_numeric(df[outcome], errors='coerce')
        for cov in covariates:
            df[cov] = pd.to_numeric(df[cov], errors='coerce')
            
        final_covariates = covariates
        lasso_selection = None
        
        if use_auto_selection and len(covariates) > 3:
            selector = LassoCovariateSelector(df, treatment, outcome, covariates)
            final_covariates = selector.auto_select(method=auto_selection_method, max_features=15)
            lasso_selection = {
                'selected_covariates': final_covariates,
                'covariate_importance': selector.get_covariate_importance(),
                'method_used': auto_selection_method
            }
            
        if len(final_covariates) == 0:
            final_covariates = covariates[:3] if len(covariates) >= 3 else covariates
            
        psm = PropensityScoreMatching(df, treatment, outcome, final_covariates)
        result = psm.run_analysis()
        
        if lasso_selection:
            result['lassoSelection'] = lasso_selection
            
        robustness = RobustnessTests(df, treatment, outcome, final_covariates, 'psm')
        robustness_tests = robustness.run_all_tests()
        
        placebo_tester = EnhancedPlaceboTester(
            df, treatment, outcome, final_covariates, 'psm'
        )
        enhanced_placebo = placebo_tester.run_all_tests(true_estimate=result['ate']['estimate'])
        robustness_tests['enhancedPlacebo'] = enhanced_placebo
        
        graph_analyzer = CausalGraphAnalyzer(df, treatment, outcome, final_covariates)
        causal_graph = graph_analyzer.learn_causal_graph()
        backdoor_paths = graph_analyzer.identify_backdoor_paths()
        causal_graph['backdoor_paths'] = backdoor_paths
        result['causal_graph'] = causal_graph
        
        sens_analyzer = SensitivityAnalyzer(
            df, treatment, outcome, final_covariates,
            result['ate']['estimate'], result['ate']['stdError']
        )
        sensitivity_analysis = sens_analyzer.run_all_analysis()
        result['sensitivity_analysis'] = sensitivity_analysis
        robustness_tests['sensitivityAnalysis'] = robustness_tests.get('sensitivityAnalysis', {})
        robustness_tests['sensitivityAnalysis']['e_value'] = sensitivity_analysis['e_value']
        robustness_tests['sensitivityAnalysis']['rosenbaum'] = sensitivity_analysis['rosenbaum_bounds']
        
        result['robustnessTests'] = robustness_tests
        result['charts'] = {}
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/analyze/did', methods=['POST'])
def analyze_did():
    try:
        data = request.json.get('data', [])
        treatment = request.json.get('treatment')
        outcome = request.json.get('outcome')
        covariates = request.json.get('covariates', [])
        time_variable = request.json.get('timeVariable')
        post_indicator = request.json.get('postTreatmentIndicator')
        use_auto_selection = request.json.get('useAutoSelection', False)
        auto_selection_method = request.json.get('autoSelectionMethod', 'double_lasso')
        
        if not data or not treatment or not outcome:
            return jsonify({'error': 'Missing required parameters'}), 400
            
        df = pd.DataFrame(data)
        df[treatment] = pd.to_numeric(df[treatment], errors='coerce')
        df[outcome] = pd.to_numeric(df[outcome], errors='coerce')
        for cov in covariates:
            df[cov] = pd.to_numeric(df[cov], errors='coerce')
        if time_variable:
            df[time_variable] = pd.to_numeric(df[time_variable], errors='coerce')
            
        final_covariates = covariates
        lasso_selection = None
        
        if use_auto_selection and len(covariates) > 3:
            selector = LassoCovariateSelector(df, treatment, outcome, covariates)
            final_covariates = selector.auto_select(method=auto_selection_method, max_features=15)
            lasso_selection = {
                'selected_covariates': final_covariates,
                'covariate_importance': selector.get_covariate_importance(),
                'method_used': auto_selection_method
            }
            
        if len(final_covariates) == 0:
            final_covariates = covariates[:3] if len(covariates) >= 3 else covariates
            
        did = DifferenceInDifferences(
            df, treatment, outcome, final_covariates,
            time_col=time_variable,
            post_col=post_indicator
        )
        result = did.run_analysis()
        
        if lasso_selection:
            result['lassoSelection'] = lasso_selection
            
        if time_variable:
            pt_tester = ParallelTrendTester(
                df, treatment, outcome, time_variable, final_covariates
            )
            parallel_trend_tests = pt_tester.run_all_tests()
            result['parallelTrendTests'] = parallel_trend_tests
            
            if 'graphical' in parallel_trend_tests:
                result['parallelTrend'] = parallel_trend_tests['graphical']
            
        robustness = RobustnessTests(
            df, treatment, outcome, final_covariates, 'did',
            time_col=time_variable,
            post_col=post_indicator
        )
        robustness_tests = robustness.run_all_tests()
        
        placebo_tester = EnhancedPlaceboTester(
            df, treatment, outcome, final_covariates, 'did',
            time_col=time_variable,
            post_col=post_indicator
        )
        enhanced_placebo = placebo_tester.run_all_tests(true_estimate=result['ate']['estimate'])
        robustness_tests['enhancedPlacebo'] = enhanced_placebo
        
        graph_analyzer = CausalGraphAnalyzer(df, treatment, outcome, final_covariates)
        causal_graph = graph_analyzer.learn_causal_graph()
        backdoor_paths = graph_analyzer.identify_backdoor_paths()
        causal_graph['backdoor_paths'] = backdoor_paths
        result['causal_graph'] = causal_graph
        
        sens_analyzer = SensitivityAnalyzer(
            df, treatment, outcome, final_covariates,
            result['ate']['estimate'], result['ate']['stdError']
        )
        sensitivity_analysis = sens_analyzer.run_all_analysis()
        result['sensitivity_analysis'] = sensitivity_analysis
        robustness_tests['sensitivityAnalysis'] = robustness_tests.get('sensitivityAnalysis', {})
        robustness_tests['sensitivityAnalysis']['e_value'] = sensitivity_analysis['e_value']
        robustness_tests['sensitivityAnalysis']['rosenbaum'] = sensitivity_analysis['rosenbaum_bounds']
        
        result['robustnessTests'] = robustness_tests
        result['charts'] = {}
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    try:
        result = request.json.get('result', {})
        method = request.json.get('method', 'psm')
        treatment = request.json.get('treatment', '')
        outcome = request.json.get('outcome', '')
        covariates = request.json.get('covariates', [])
        sample_size = request.json.get('sampleSize', {})
        report_format = request.json.get('format', 'html')
        
        if not result:
            return jsonify({'error': 'Missing analysis result'}), 400
        
        report_gen = ReportGenerator(
            result, method, treatment, outcome, covariates, sample_size
        )
        
        if report_format == 'html':
            html_report = report_gen.generate_html_report()
            return jsonify({
                'success': True,
                'format': 'html',
                'content': html_report,
                'filename': f'causal_inference_report_{method}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.html'
            })
        else:
            return jsonify({'error': 'Unsupported format'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


if __name__ == '__main__':
    print("Starting Causal Inference API server...")
    app.run(host='0.0.0.0', port=5001, debug=True)
