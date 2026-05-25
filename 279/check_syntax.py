import ast
import sys

files = [
    'src/__init__.py',
    'src/data_processing.py',
    'src/prophet_features.py',
    'src/autoencoder.py',
    'src/anomaly_detector.py',
    'app.py'
]

print("语法检查中...\n")
all_ok = True

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        ast.parse(content)
        print(f'✓ {f}')
    except SyntaxError as e:
        print(f'✗ {f} - 第{e.lineno}行: {e.msg}')
        all_ok = False
    except FileNotFoundError:
        print(f'? {f} - 文件不存在')
        all_ok = False

print('\n' + '=' * 40)
if all_ok:
    print('✓ 所有文件语法检查通过!')
else:
    print('✗ 存在语法错误，请检查!')
    sys.exit(1)
