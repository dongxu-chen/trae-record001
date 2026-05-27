import sys
import io

old_stdout = sys.stdout
sys.stdout = io.StringIO()

try:
    with open(r'd:\Trae\project\record001\394\test_improvements.py', 'r', encoding='utf-8') as f:
        code = f.read()
    exec(code)
    output = sys.stdout.getvalue()
    with open(r'd:\Trae\project\record001\394\test_result.txt', 'w', encoding='utf-8') as f:
        f.write(output)
    print("SUCCESS: output written to test_result.txt")
except Exception as e:
    output = sys.stdout.getvalue()
    with open(r'd:\Trae\project\record001\394\test_result.txt', 'w', encoding='utf-8') as f:
        f.write(output)
        f.write(f"\n\nERROR: {e}")
    print(f"ERROR: {e}")
finally:
    sys.stdout = old_stdout