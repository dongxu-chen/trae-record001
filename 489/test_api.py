import requests

print('=' * 50)
print('COMPREHENSIVE API TEST')
print('=' * 50)

try:
    # 1. 测试算法列表 API
    print()
    print('1. Testing /api/algorithms')
    r = requests.get('http://localhost:5000/api/algorithms')
    print('   Status:', r.status_code)
    if r.status_code == 200:
        data = r.json()
        print('   Temporal methods:', data.get('temporal_methods'))
        print('   Multivar methods:', data.get('multivar_methods'))

    # 2. 测试时序插值 API
    print()
    print('2. Testing /api/temporal-interpolate')
    r = requests.post('http://localhost:5000/api/temporal-interpolate', data={
        'variable': 'temperature', 'date_col': 'date',
        'temporal_method': 'spline', 'steps': 10
    })
    print('   Status:', r.status_code)
    if r.status_code == 200:
        data = r.json()
        plot_ok = len(data.get('plot_image', '')) > 100
        print('   Method:', data.get('method'), ', Plot OK:', plot_ok)
    else:
        print('   Error:', r.text[:200])

    # 3. 测试预测 API
    print()
    print('3. Testing /api/forecast')
    r = requests.post('http://localhost:5000/api/forecast', data={
        'variable': 'precipitation', 'date_col': 'date',
        'forecast_method': 'drift', 'steps': 7
    })
    print('   Status:', r.status_code)
    if r.status_code == 200:
        data = r.json()
        plot_ok = len(data.get('plot_image', '')) > 100
        print('   Method:', data.get('method'), ', Plot OK:', plot_ok)
    else:
        print('   Error:', r.text[:200])

    # 4. 测试协同克里金
    print()
    print('4. Testing /api/cokriging (collocated_cokriging)')
    r = requests.post('http://localhost:5000/api/cokriging', data={
        'primary_variable': 'temperature', 'secondary_variable': 'precipitation',
        'cokriging_method': 'collocated_cokriging', 'variogram_model': 'linear',
        'nx': 30, 'ny': 30
    })
    print('   Status:', r.status_code)
    if r.status_code == 200:
        data = r.json()
        plot_ok = len(data.get('comparison_image', '')) > 100
        print('   Correlation:', data.get('correlation'), ', Plot OK:', plot_ok)
    else:
        print('   Error:', r.text[:200])

    # 5. 测试回归克里金
    print()
    print('5. Testing /api/cokriging (regression_kriging)')
    r = requests.post('http://localhost:5000/api/cokriging', data={
        'primary_variable': 'temperature', 'secondary_variable': 'precipitation',
        'cokriging_method': 'regression_kriging', 'variogram_model': 'linear',
        'nx': 30, 'ny': 30
    })
    print('   Status:', r.status_code)
    if r.status_code == 200:
        data = r.json()
        plot_ok = len(data.get('comparison_image', '')) > 100
        print('   Plot OK:', plot_ok)
    else:
        print('   Error:', r.text[:200])

    # 6. 测试不确定性评估
    print()
    print('6. Testing /api/uncertainty')
    r = requests.post('http://localhost:5000/api/uncertainty', data={
        'algorithm': 'ordinary_kriging', 'variable': 'temperature',
        'confidence': 0.95, 'nx': 30, 'ny': 30
    })
    print('   Status:', r.status_code)
    if r.status_code == 200:
        data = r.json()
        uc_ok = len(data.get('uncertainty_image', '')) > 100
        prob_ok = len(data.get('probability_image', '')) > 100
        print('   Confidence:', data.get('confidence'))
        print('   Uncertainty plot OK:', uc_ok)
        print('   Probability plot OK:', prob_ok)
        print('   Report length:', len(data.get('report', '')))
    else:
        print('   Error:', r.text[:200])

    print()
    print('=' * 50)
    print('ALL TESTS COMPLETED!')
    print('=' * 50)

except Exception as e:
    print()
    print('ERROR:', str(e))
