import sys
print(f"Python: {sys.version}")

try:
    import cupy
    print(f"Cupy: yes ({cupy.__version__})")
except ImportError:
    print("Cupy: no")

try:
    import numpy
    print(f"NumPy: yes ({numpy.__version__})")
except ImportError:
    print("NumPy: no")

try:
    import gzip
    print("gzip: yes")
except ImportError:
    print("gzip: no")

try:
    import multiprocessing
    print("multiprocessing: yes")
except ImportError:
    print("multiprocessing: no")
