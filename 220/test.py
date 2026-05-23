import sys
sys.path.insert(0, 'd:/Trae/project/record001/220')

from quantum_simulator import QuantumSimulator
import numpy as np

np.random.seed(42)

print("Testing Bell state...")
qs = QuantumSimulator(2)
qs.h(0)
qs.cnot(0, 1)

print("State:")
qs.print_state()
print("Probabilities:")
qs.print_probabilities()

result = qs.measure_all()
print(f"Measurement result: |{result}>")
print("Test completed successfully!")
