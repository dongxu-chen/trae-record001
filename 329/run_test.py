import sys
import io
import warnings
warnings.filterwarnings('ignore')

# 捕获输出
old_stdout = sys.stdout
sys.stdout = mystdout = io.StringIO()

try:
    from test_model import test_all_modules
    success = test_all_modules()
except Exception as e:
    import traceback
    traceback.print_exc()
    success = False

sys.stdout = old_stdout
output = mystdout.getvalue()

# 打印最后100行
lines = output.split('\n')
print('\n'.join(lines[-120:]))
print(f'\n\n测试{"成功" if success else "失败"}')
sys.exit(0 if success else 1)
