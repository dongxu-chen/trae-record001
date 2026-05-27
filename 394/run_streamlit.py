import subprocess
import sys
import os

os.chdir(r'd:\Trae\project\record001\394')
result = subprocess.Popen(
    [sys.executable, '-m', 'streamlit', 'run', 'app.py', '--server.port', '8502', '--server.headless', 'true'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
import time
time.sleep(8)
result.terminate()
try:
    stdout, stderr = result.communicate(timeout=5)
except:
    stdout, stderr = '', ''
    
with open(r'd:\Trae\project\record001\394\streamlit_log.txt', 'w', encoding='utf-8') as f:
    f.write(f"STDOUT:\n{stdout[-3000:]}\n\n")
    f.write(f"STDERR:\n{stderr[-3000:]}\n\n")
    f.write(f"Return code: {result.returncode}\n")
print("Log written to streamlit_log.txt")