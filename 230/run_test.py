import sys
from io import StringIO

old_stdout = sys.stdout
sys.stdout = buffer = StringIO()

try:
    exec(open('test_bn.py', encoding='utf-8').read())
except Exception as e:
    print(f"Error: {e}", file=old_stdout)
    import traceback
    traceback.print_exc(file=old_stdout)
finally:
    sys.stdout = old_stdout
    output = buffer.getvalue()
    print(output)
    with open('test_output.txt', 'w', encoding='utf-8') as f:
        f.write(output)
