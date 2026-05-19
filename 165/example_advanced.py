from sci_calc import *
import random


def demo_eigenvalues():
    print("=" * 70)
    print("1. 特征值和特征向量计算")
    print("=" * 70)
    
    A = Matrix([
        [4, -2, 1],
        [-2, 3, -1],
        [1, -1, 2]
    ])
    
    print("\n对称矩阵 A:")
    print(A)
    
    eigvals = A.eigenvalues()
    print(f"\n特征值 (共 {len(eigvals)} 个):")
    for i, val in enumerate(eigvals):
        if isinstance(val, complex):
            print(f"  λ{i+1} = {val.real:.6f} + {val.imag:.6f}i")
        else:
            print(f"  λ{i+1} = {val:.6f}")
    
    real_eigvals = [v.real if isinstance(v, complex) else v for v in eigvals 
                    if (not isinstance(v, complex)) or abs(v.imag) < 1e-6]
    
    if real_eigvals:
        eigvecs = A.eigenvectors(real_eigvals)
        print(f"\n特征向量矩阵 (列对应特征向量):")
        print(eigvecs)
        
        print("\n验证 A·v = λ·v:")
        for i in range(min(3, len(real_eigvals))):
            v = [eigvecs[j][i] for j in range(eigvecs.rows)]
            Av = [sum(A[j][k] * v[k] for k in range(A.cols)) for j in range(A.rows)]
            lv = [v[j] * real_eigvals[i] for j in range(len(v))]
            error = sum(abs(Av[j] - lv[j]) for j in range(len(v)))
            print(f"  特征值 {real_eigvals[i]:.4f} 的验证误差: {error:.2e}")


def demo_svd():
    print("\n" + "=" * 70)
    print("2. SVD奇异值分解")
    print("=" * 70)
    
    m, n = 5, 3
    data = [[random.gauss(0, 1) for _ in range(n)] for _ in range(m)]
    A = Matrix(data)
    
    print(f"\n随机矩阵 A ({m}x{n}):")
    print(A)
    
    U, S, Vt = A.svd()
    
    print(f"\nU 矩阵 ({U.rows}x{U.cols} - 左奇异向量):")
    print(U)
    
    print(f"\nS 矩阵 (奇异值对角矩阵):")
    print(S)
    
    print(f"\nV^T 矩阵 ({Vt.rows}x{Vt.cols} - 右奇异向量转置):")
    print(Vt)
    
    print(f"\n奇异值:")
    singular_values = [S[i][i] for i in range(min(m, n))]
    for i, s in enumerate(singular_values):
        print(f"  σ{i+1} = {s:.6f}")
    
    print("\n验证 A = U·S·V^T:")
    US = U.dot(S)
    A_reconstructed = US.dot(Vt)
    max_error = max(abs(A[i][j] - A_reconstructed[i][j]) 
                    for i in range(m) for j in range(n))
    print(f"  最大重构误差: {max_error:.2e}")
    
    print(f"\n矩阵秩估计 (大于 1e-6 的奇异值数量):")
    rank = sum(1 for s in singular_values if s > 1e-6)
    print(f"  秩 ≈ {rank}")


def demo_heatmap():
    print("\n" + "=" * 70)
    print("3. 矩阵热力图可视化")
    print("=" * 70)
    
    n = 6
    data = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                data[i][j] = 5.0
            elif abs(i - j) == 1:
                data[i][j] = 2.0
            elif abs(i - j) == 2:
                data[i][j] = -1.0
            else:
                data[i][j] = random.random() - 0.5
    
    A = Matrix(data)
    
    print(f"\n带状矩阵 A ({n}x{n}):")
    print(A)
    
    print(f"\n生成热力图...")
    
    heatmap(A, filename='heatmap_matrix.svg', 
            title='矩阵热力图', 
            cmap='coolwarm',
            show_values=True,
            figsize=(700, 600))
    
    print("\n生成 Spy 图 (非零元素分布)...")
    spy(A, filename='spy_matrix.svg', precision=1e-6)
    
    print("\n生成随机矩阵热力图 (viridis 配色)...")
    random_data = [[random.random() * 10 for _ in range(8)] for _ in range(6)]
    B = Matrix(random_data)
    heatmap(B, filename='heatmap_random.svg',
            title='随机矩阵热力图',
            cmap='viridis',
            show_values=True)


def demo_qr_decomposition():
    print("\n" + "=" * 70)
    print("4. QR分解")
    print("=" * 70)
    
    A = Matrix([
        [12, -51, 4],
        [6, 167, -68],
        [-4, 24, -41]
    ])
    
    print("\n矩阵 A:")
    print(A)
    
    Q, R = A.qr_decomposition()
    
    print(f"\nQ 正交矩阵:")
    print(Q)
    
    print(f"\nR 上三角矩阵:")
    print(R)
    
    print("\n验证 Q^T·Q = I:")
    QtQ = Q.transpose().dot(Q)
    max_error = max(abs(QtQ[i][j] - (1 if i == j else 0)) 
                    for i in range(QtQ.rows) for j in range(QtQ.cols))
    print(f"  最大误差: {max_error:.2e}")
    
    print("\n验证 Q·R = A:")
    QR = Q.dot(R)
    max_error = max(abs(A[i][j] - QR[i][j]) 
                    for i in range(A.rows) for j in range(A.cols))
    print(f"  最大误差: {max_error:.2e}")


def main():
    print("\n" + "*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + "科学计算工具 - 高级功能演示".center(68) + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print()
    
    demo_eigenvalues()
    demo_svd()
    demo_qr_decomposition()
    demo_heatmap()
    
    print("\n" + "=" * 70)
    print("所有演示完成！")
    print("=" * 70)
    print("\n生成的文件:")
    print("  - heatmap_matrix.svg   矩阵热力图")
    print("  - heatmap_random.svg   随机矩阵热力图")
    print("  - spy_matrix.svg       非零元素分布图")
    print("\n提示: SVG文件可用浏览器或矢量图形编辑器打开查看。")


if __name__ == "__main__":
    main()
