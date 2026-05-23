import numpy as np
import matrix_mul

print("=" * 50)
print("High Performance Matrix Multiplication - Python Demo")
print("=" * 50)

print(f"\nGPU Available: {matrix_mul.has_gpu()}")
print(f"GPU Info: {matrix_mul.gpu_info()}")

N = 512
print(f"\n=== Testing {N}x{N} Matrix Multiplication ===")

A = np.random.randn(N, N).astype(np.float32)
B = np.random.randn(N, N).astype(np.float32)

print(f"\nMatrix A shape: {A.shape}")
print(f"Matrix B shape: {B.shape}")

info = matrix_mul.get_matrix_info(A)
print(f"Sparsity: {info['sparsity']:.4f}")

print("\n1. Using automatic algorithm selection...")
C_auto = matrix_mul.multiply(A, B)
print(f"   Result shape: {C_auto.shape}")

print("\n2. Using blocked algorithm...")
C_blocked = matrix_mul.multiply(A, B, algorithm='blocked')
print(f"   Result shape: {C_blocked.shape}")

print("\n3. Using Strassen algorithm...")
C_strassen = matrix_mul.multiply(A, B, algorithm='strassen')
print(f"   Result shape: {C_strassen.shape}")

np.testing.assert_allclose(C_auto, C_blocked, rtol=1e-4)
np.testing.assert_allclose(C_auto, C_strassen, rtol=1e-3)
print("\n✓ All results match!")

print("\n=== Testing Sparse Matrix ===")

sparse_A = np.zeros((1024, 1024), dtype=np.float32)
nnz = 1024 * 1024 // 100
indices = np.random.choice(1024 * 1024, nnz, replace=False)
sparse_A.flat[indices] = np.random.randn(nnz).astype(np.float32)

sparse_info = matrix_mul.get_matrix_info(sparse_A)
print(f"Sparsity: {sparse_info['sparsity']:.4f} (90% threshold: auto switches to sparse)")

sparse_B = np.random.randn(1024, 128).astype(np.float32)
C_sparse = matrix_mul.multiply(sparse_A, sparse_B, sparsity_threshold=0.9)
print(f"Sparse result shape: {C_sparse.shape}")

print("\n=== Double Precision ===")
A_double = np.random.randn(256, 256).astype(np.float64)
B_double = np.random.randn(256, 256).astype(np.float64)
C_double = matrix_mul.multiply(A_double, B_double)
print(f"Double result shape: {C_double.shape}")

print("\n" + "=" * 50)
print("All tests passed!")
print("=" * 50)
