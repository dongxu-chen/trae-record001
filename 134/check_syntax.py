import ast
import sys

files_to_check = [
    'trend_analyzer.py',
    'slow_sql_analyzer.py',
    'deadlock_predictor.py',
    'dingtalk_alert.py',
    'main.py'
]

print("=" * 60)
print("语法检查开始")
print("=" * 60)

all_passed = True
for filename in files_to_check:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        print(f"✅ {filename} - 语法正确")
    except Exception as e:
        print(f"❌ {filename} - 语法错误: {e}")
        all_passed = False

print("=" * 60)
if all_passed:
    print("所有文件语法检查通过!")
else:
    print("部分文件存在语法错误!")
print("=" * 60)
