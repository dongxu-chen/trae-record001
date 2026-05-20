from sci_calc import *


def main():
    print("=" * 60)
    print("科学计算工具 - 矩阵运算演示")
    print("=" * 60)
    
    print("\n1. 创建矩阵")
    print("-" * 40)
    A = Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 10]])
    B = Matrix([[10, 11], [12, 13], [14, 15]])
    C = Matrix([[1, 0, 0], [0, 2, 0], [0, 0, 3]])
    
    print("矩阵 A:")
    print(A)
    print("\n矩阵 B:")
    print(B)
    print("\n矩阵 C:")
    print(C)
    
    print("\n2. 矩阵加法")
    print("-" * 40)
    try:
        A_plus_C = A + C
        print("A + C =")
        print(A_plus_C)
    except Exception as e:
        print(f"错误: {e}")
    
    print("\n3. 矩阵乘法")
    print("-" * 40)
    try:
        A_times_B = A * B
        print("A * B =")
        print(A_times_B)
        
        C_times_2 = 2 * C
        print("\n2 * C =")
        print(C_times_2)
    except Exception as e:
        print(f"错误: {e}")
    
    print("\n4. 矩阵转置")
    print("-" * 40)
    B_transpose = B.transpose()
    print("B 的转置:")
    print(B_transpose)
    
    print("\n5. 行列式计算")
    print("-" * 40)
    det_A = A.determinant()
    print(f"det(A) = {det_A}")
    det_C = C.determinant()
    print(f"det(C) = {det_C}")
    
    print("\n6. 矩阵求逆")
    print("-" * 40)
    try:
        A_inv = A.inverse()
        print("A 的逆矩阵:")
        print(A_inv)
        
        print("\n验证 A * A⁻¹ = I:")
        identity_check = A * A_inv
        print(identity_check)
    except Exception as e:
        print(f"错误: {e}")
    
    print("\n7. CSV 文件读写")
    print("-" * 40)
    csv_file = "matrix_data.csv"
    write_csv(A, csv_file, header=['col1', 'col2', 'col3'])
    print(f"矩阵 A 已写入 {csv_file}")
    
    A_read = read_csv(csv_file, has_header=True)
    print(f"\n从 {csv_file} 读取的矩阵:")
    print(A_read)
    
    print("\n8. LaTeX 格式输出")
    print("-" * 40)
    print("矩阵 A 的 LaTeX 格式:")
    print_latex(A, decimal_places=2, matrix_type='bmatrix')
    
    latex_file = "matrix.tex"
    save_latex(A, latex_file, wrap_document=True, decimal_places=2)
    print(f"\nLaTeX 文档已保存到 {latex_file}")
    
    print("\n矩阵运算的 LaTeX 公式:")
    eq = equation_to_latex(A, '+', C, A_plus_C, decimal_places=2)
    print(eq)
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
