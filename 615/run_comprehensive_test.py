
import subprocess
import sys
import os

os.chdir('d:\\Trae\\project\\record001\\615')

result = subprocess.run(
    [sys.executable, 'test_new_features.py'],
    capture_output=True,
    text=True,
    timeout=600
)

with open('comprehensive_test_result.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 70 + "\n")
    f.write("COMPREHENSIVE TEST RESULT\n")
    f.write("=" * 70 + "\n\n")
    f.write("STDOUT:\n")
    f.write("-" * 70 + "\n")
    f.write(result.stdout)
    f.write("\n\nSTDERR:\n")
    f.write("-" * 70 + "\n")
    f.write(result.stderr)
    f.write(f"\n\nReturn code: {result.returncode}")

print("Test complete!")
print("Return code:", result.returncode)
print("\nSTDOUT:")
print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
if result.stderr:
    print("\nSTDERR:")
    print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
