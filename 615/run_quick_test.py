
import subprocess
import sys

result = subprocess.run(
    [sys.executable, 'quick_test.py'],
    capture_output=True,
    text=True,
    cwd='d:\\Trae\\project\\record001\\615'
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print("\nReturn code:", result.returncode)
