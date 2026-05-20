print('测试环境...')

try:
    import flask
    print(f'Flask: OK - {flask.__version__}')
except ImportError as e:
    print(f'Flask: FAIL - {e}')

try:
    import flask_cors
    print('Flask-Cors: OK')
except ImportError as e:
    print(f'Flask-Cors: FAIL - {e}')

try:
    import snownlp
    print('SnowNLP: OK')
except ImportError as e:
    print(f'SnowNLP: FAIL - {e}')

try:
    import jieba
    print(f'jieba: OK - {jieba.__version__}')
except ImportError as e:
    print(f'jieba: FAIL - {e}')

try:
    import pandas
    print(f'pandas: OK - {pandas.__version__}')
except ImportError as e:
    print(f'pandas: FAIL - {e}')

try:
    import numpy
    print(f'numpy: OK - {numpy.__version__}')
except ImportError as e:
    print(f'numpy: FAIL - {e}')

print('\n环境测试完成！')
