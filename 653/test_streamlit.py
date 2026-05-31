import subprocess
import sys

result = subprocess.run(
    ["streamlit", "run", "app.py", "--server.port", "8501"],
    capture_output=True,
    text=True,
    timeout=10
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")
