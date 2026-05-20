from sci_calc import *
import time
import random


def test_inverse_optimization():
    print("=" * 70)
    print("测试1: 优化后的矩阵求逆")
    print("=" * 70)
    
    sizes = [3, 5, 10]
    for n in sizes:
        data = [[random.random() * 10 for _ in range(n)] for _ in range(n)]
        for i in range(n):
            data[i][i] += n * 10
        
        A = Matrix(data)
        
        start = time.time()
        A_inv = A.inverse()
        elapsed = time.time() - start
        
        I = A.dot(A_inv)
        max_error = max(abs(I[i][j] - (1 if i == j else 0)) 
                       for i in range(n) for j in range(n))
        
        print(f"\n{n}x{n} 矩阵:")
        print(f"  求逆时间: {elapsed*1000:.3f} ms")
        print(f"  验证误差: {max_error:.2e}")
        print(f"  精度: {'通过' if max_error < 1e-6 else '失败'}")


def test_multiplication_validation():
    print("\n" + "=" * 70)
    print("测试2: 矩阵乘法维度校验")
    print("=" * 70)
    
    A = Matrix([[1, 2, 3], [4, 5, 6]])
    B = Matrix([[1, 2], [3, 4]])
    
    print(f"\n矩阵 A: {A.rows}x{A.cols}")
    print(f"矩阵 B: {B.rows}x{B.cols}")
    
    try:
        result = A * B
        print("错误: 应该抛出维度不匹配异常")
    except ValueError as e:
        print(f"\n维度校验成功:")
        print(f"  {e}")
    
    try:
        result = A * "not a matrix"
        print("错误: 应该抛出类型异常")
    except TypeError as e:
        print(f"\n类型校验成功:")
        print(f"  {e}")
    
    C = Matrix([[1, 2], [3, 4], [5, 6]])
    print(f"\n矩阵 C: {C.rows}x{C.cols}")
    result = A * C
    print(f"A * C 成功: {result.rows}x{result.cols}")
    print(result)


def test_latex_escaping():
    print("\n" + "=" * 70)
    print("测试3: LaTeX特殊字符转义")
    print("=" * 70)
    
    test_cases = [
        "hello_world",
        "a&b&c",
        "100%",
        "price$50",
        "a#b",
        "{braces}",
        "a^b",
        "a~b",
        "a\\b",
        "a < b > c",
        "a|b",
    ]
    
    print("\n特殊字符转义测试:")
    for test in test_cases:
        escaped = escape_latex(test)
        print(f"  '{test}' -> '{escaped}'")
    
    A = Matrix([[1.5, 2.3], [4.7, 8.9]])
    print("\n矩阵 LaTeX 输出 (含精度控制):")
    print_latex(A, decimal_places=2, matrix_type='bmatrix')


def test_eigenvalues():
    print("\n" + "=" * 70)
    print("测试4: 特征值和特征向量")
    print("=" * 70)
    
    A = Matrix([
        [2, 1, 0],
        [1, 2, 1],
        [0, 1, 2]
    ])
    
    print("\n三对角矩阵:")
    print(A)
    
    eigvals = A.eigenvalues()
    print(f"\n特征值:")
    for i, val in enumerate(eigvals):
        if isinstance(val, complex):
            print(f"  λ{i+1} = {val.real:.6f} + {val.imag:.6f}i")
        else:
            print(f"  λ{i+1} = {val:.6f}")
    
    print(f"\n特征值计算: {'完成'}")


def test_svd():
    print("\n" + "=" * 70)
    print("测试5: SVD奇异值分解")
    print("=" * 70)
    
    A = Matrix([
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9]
    ])
    
    print("\n测试矩阵:")
    print(A)
    
    U, S, Vt = A.svd()
    
    print(f"\nU 形状: {U.rows}x{U.cols}")
    print(f"S 形状: {S.rows}x{S.cols}")
    print(f"Vt 形状: {Vt.rows}x{Vt.cols}")
    
    singular_values = [S[i][i] for i in range(min(S.rows, S.cols))]
    print(f"\n奇异值: {[f'{s:.4f}' for s in singular_values]}")
    
    US = U.dot(S)
    A_recon = US.dot(Vt)
    max_error = max(abs(A[i][j] - A_recon[i][j]) 
                   for i in range(A.rows) for j in range(A.cols))
    print(f"\n重构误差: {max_error:.2e}")
    print(f"SVD测试: {'通过' if max_error < 1e-6 else '需要注意'}")


def test_qr_decomposition():
    print("\n" + "=" * 70)
    print("测试6: QR分解")
    print("=" * 70)
    
    A = Matrix([
        [1, 2],
        [3, 4],
        [5, 6]
    ])
    
    print("\n测试矩阵:")
    print(A)
    
    Q, R = A.qr_decomposition()
    
    print(f"\nQ 正交矩阵:")
    print(Q)
    print(f"\nR 上三角矩阵:")
    print(R)
    
    QR = Q.dot(R)
    max_error = max(abs(A[i][j] - QR[i][j]) 
                   for i in range(A.rows) for j in range(A.cols))
    print(f"\nQ·R 重构误差: {max_error:.2e}")
    
    QtQ = Q.transpose().dot(Q)
    ortho_error = max(abs(QtQ[i][j] - (1 if i == j else 0)) 
                      for i in range(QtQ.rows) for j in range(QtQ.cols))
    print(f"正交性误差: {ortho_error:.2e}")
    print(f"QR测试: {'通过' if max_error < 1e-6 and ortho_error < 1e-6 else '需要注意'}")


def test_visualization():
    print("\n" + "=" * 70)
    print("测试7: 可视化功能")
    print("=" * 70)
    
    data = [
        [1, 2, 3, 4],
        [2, 4, 6, 8],
        [3, 6, 9, 12],
        [4, 8, 12, 16]
    ]
    A = Matrix(data)
    
    print("\n测试矩阵 (乘法表):")
    print(A)
    
    print("\n生成热力图...")
    heatmap(A, filename='test_heatmap.svg', 
            title='测试热力图', 
            cmap='viridis',
            show_values=True)
    
    print("生成Spy图...")
    spy(A, filename='test_spy.svg', precision=1e-6)
    
    print("可视化测试: 完成")


def main():
    test_inverse_optimization()
    test_multiplication_validation()
    test_latex_escaping()
    test_eigenvalues()
    test_svd()
    test_qr_decomposition()
    test_visualization()
    
    print("\n" + "=" * 70)
    print("所有测试完成！")
    print("=" * 70)
    print("\n生成的测试文件:")
    print("  - test_heatmap.svg  测试热力图")
    print("  - test_spy.svg      测试Spy图")
    print("\n使用 'python example_advanced.py' 查看完整功能演示！")


if __name__ == "__main__":
    main()
