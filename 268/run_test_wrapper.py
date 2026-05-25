import subprocess
import sys

result = subprocess.run(
    [sys.executable, 'run_test.py'],
    capture_output=True,
    text=True,
    cwd=r'd:\Trae\project\record001\268'
)

print('=' * 60)
print('STDOUT:')
print('=' * 60)
print(result.stdout)
print('=' * 60)
print('STDERR:')
print('=' * 60)
print(result.stderr)
print('=' * 60)
print(f'Return Code: {result.returncode}')
print('=' * 60)
