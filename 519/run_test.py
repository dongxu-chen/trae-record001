import io
import sys

output_buffer = io.StringIO()
sys.stdout = output_buffer
sys.stderr = output_buffer

try:
    exec(open('simple_test.py', encoding='utf-8').read())
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()

sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

output = output_buffer.getvalue()
with open('captured_output.txt', 'w', encoding='utf-8') as f:
    f.write(output)

print(output)
