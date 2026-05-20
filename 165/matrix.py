class Matrix:
    def __init__(self, data):
        if not data or not data[0]:
            raise ValueError("矩阵不能为空")
        row_length = len(data[0])
        for row in data:
            if len(row) != row_length:
                raise ValueError("所有行的长度必须相同")
        self.data = [row[:] for row in data]
        self.rows = len(data)
        self.cols = len(data[0])

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, value):
        self.data[index] = value

    def __str__(self):
        max_width = max(len(str(elem)) for row in self.data for elem in row)
        lines = []
        for row in self.data:
            line = "[" + " ".join(f"{elem:>{max_width}}" for elem in row) + "]"
            lines.append(line)
        return "\n".join(lines)

    def __repr__(self):
        return f"Matrix({self.data!r})"

    def __add__(self, other):
        if self.rows != other.rows or self.cols != other.cols:
            raise ValueError("矩阵维度不匹配，无法相加")
        result = [
            [self.data[i][j] + other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ]
        return Matrix(result)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            result = [[elem * other for elem in row] for row in self.data]
            return Matrix(result)
        elif isinstance(other, Matrix):
            if not isinstance(other, Matrix):
                raise TypeError("右侧操作数必须是Matrix类型")
            if self.cols != other.rows:
                raise ValueError(
                    f"矩阵维度不匹配，无法相乘: "
                    f"({self.rows}x{self.cols}) * ({other.rows}x{other.cols})，"
                    f"要求左矩阵列数等于右矩阵行数"
                )
            result = [
                [
                    sum(self.data[i][k] * other.data[k][j] for k in range(self.cols))
                    for j in range(other.cols)
                ]
                for i in range(self.rows)
            ]
            return Matrix(result)
        else:
            raise TypeError(f"不支持的乘法类型: {type(other)}，支持的类型: int, float, Matrix")

    def __rmul__(self, scalar):
        return self * scalar

    def transpose(self):
        result = [
            [self.data[i][j] for i in range(self.rows)]
            for j in range(self.cols)
        ]
        return Matrix(result)

    def identity(size):
        result = [[0.0] * size for _ in range(size)]
        for i in range(size):
            result[i][i] = 1.0
        return Matrix(result)

    identity = staticmethod(identity)

    def determinant(self):
        if self.rows != self.cols:
            raise ValueError("只有方阵才能计算行列式")
        n = self.rows
        mat = [row[:] for row in self.data]
        det = 1.0
        for i in range(n):
            pivot = -1
            for j in range(i, n):
                if abs(mat[j][i]) > 1e-10:
                    pivot = j
                    break
            if pivot == -1:
                return 0.0
            if pivot != i:
                mat[i], mat[pivot] = mat[pivot], mat[i]
                det *= -1
            det *= mat[i][i]
            for j in range(i + 1, n):
                factor = mat[j][i] / mat[i][i]
                for k in range(i, n):
                    mat[j][k] -= factor * mat[i][k]
        return det

    def inverse(self):
        if self.rows != self.cols:
            raise ValueError(f"只有方阵才能求逆，当前矩阵维度: {self.rows}x{self.cols}")
        
        n = self.rows
        eps = 1e-12
        
        aug = [[0.0] * (2 * n) for _ in range(n)]
        for i in range(n):
            for j in range(n):
                aug[i][j] = float(self.data[i][j])
            aug[i][n + i] = 1.0
        
        for i in range(n):
            max_row = i
            max_val = abs(aug[i][i])
            for j in range(i + 1, n):
                curr_val = abs(aug[j][i])
                if curr_val > max_val:
                    max_val = curr_val
                    max_row = j
            
            if max_val < eps:
                raise ValueError("矩阵是奇异的（行列式接近0），无法求逆")
            
            if max_row != i:
                aug[i], aug[max_row] = aug[max_row], aug[i]
            
            pivot_val = aug[i][i]
            for j in range(i, 2 * n):
                aug[i][j] /= pivot_val
            
            for j in range(n):
                if j != i:
                    factor = aug[j][i]
                    if abs(factor) > eps:
                        for k in range(i, 2 * n):
                            aug[j][k] -= factor * aug[i][k]
        
        inv_data = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                inv_data[i][j] = aug[i][n + j]
        
        return Matrix(inv_data)

    def to_list(self):
        return [row[:] for row in self.data]

    def transpose_inplace(self):
        if self.rows == self.cols:
            for i in range(self.rows):
                for j in range(i + 1, self.cols):
                    self.data[i][j], self.data[j][i] = self.data[j][i], self.data[i][j]
        else:
            new_data = [
                [self.data[i][j] for i in range(self.rows)]
                for j in range(self.cols)
            ]
            self.data = new_data
            self.rows, self.cols = self.cols, self.rows

    def dot(self, other):
        if self.cols != other.rows:
            raise ValueError(
                f"矩阵维度不匹配: ({self.rows}x{self.cols}) · ({other.rows}x{other.cols})"
            )
        result = [
            [
                sum(self.data[i][k] * other.data[k][j] for k in range(self.cols))
                for j in range(other.cols)
            ]
            for i in range(self.rows)
        ]
        return Matrix(result)

    def norm_fro(self):
        return sum(elem * elem for row in self.data for elem in row) ** 0.5

    def qr_decomposition(self):
        if self.rows < self.cols:
            raise ValueError("QR分解要求行数 >= 列数")
        
        n, m = self.rows, self.cols
        Q = [[0.0] * m for _ in range(n)]
        R = [[0.0] * m for _ in range(m)]
        
        for j in range(m):
            for i in range(n):
                Q[i][j] = self.data[i][j]
            
            for k in range(j):
                r_kj = sum(Q[i][k] * self.data[i][j] for i in range(n))
                R[k][j] = r_kj
                for i in range(n):
                    Q[i][j] -= r_kj * Q[i][k]
            
            norm = sum(Q[i][j] ** 2 for i in range(n)) ** 0.5
            if norm < 1e-12:
                raise ValueError("矩阵列向量线性相关，无法进行QR分解")
            
            R[j][j] = norm
            for i in range(n):
                Q[i][j] /= norm
        
        return Matrix(Q), Matrix(R)

    def _hessenberg_reduction(self):
        n = self.rows
        H = [row[:] for row in self.data]
        
        for k in range(n - 2):
            x = [H[i][k] for i in range(k + 1, n)]
            x_norm = sum(xi ** 2 for xi in x) ** 0.5
            
            if x_norm < 1e-12:
                continue
            
            if x[0] >= 0:
                x[0] += x_norm
            else:
                x[0] -= x_norm
            
            beta = 2.0 / sum(xi ** 2 for xi in x)
            
            for j in range(k, n):
                s = sum(H[k + 1 + i][j] * x[i] for i in range(n - k - 1))
                for i in range(n - k - 1):
                    H[k + 1 + i][j] -= beta * s * x[i]
            
            for i in range(n):
                s = sum(H[i][k + 1 + j] * x[j] for j in range(n - k - 1))
                for j in range(n - k - 1):
                    H[i][k + 1 + j] -= beta * s * x[j]
        
        return Matrix(H)

    def eigenvalues(self, max_iter=1000, tol=1e-10):
        if self.rows != self.cols:
            raise ValueError("只有方阵才能计算特征值")
        
        n = self.rows
        H = self._hessenberg_reduction()
        
        for _ in range(max_iter):
            if n <= 1:
                break
            
            shift = H[n - 1][n - 1]
            for i in range(n):
                H.data[i][i] -= shift
            
            try:
                Q, R = H.qr_decomposition()
            except ValueError:
                pass
            
            H = R.dot(Q)
            
            for i in range(n):
                H.data[i][i] += shift
            
            converged = True
            for i in range(1, n):
                if abs(H.data[i][i - 1]) > tol:
                    converged = False
                    break
            
            if converged:
                break
        
        eigvals = []
        for i in range(n):
            if i < n - 1 and abs(H.data[i + 1][i]) > tol:
                a = H.data[i][i]
                b = H.data[i][i + 1]
                c = H.data[i + 1][i]
                d = H.data[i + 1][i + 1]
                
                trace = a + d
                det = a * d - b * c
                disc = trace * trace - 4 * det
                
                if disc < 0:
                    real = trace / 2
                    imag = (-disc) ** 0.5 / 2
                    eigvals.append(complex(real, imag))
                    eigvals.append(complex(real, -imag))
                else:
                    eigvals.append((trace + disc ** 0.5) / 2)
                    eigvals.append((trace - disc ** 0.5) / 2)
                i += 1
            else:
                eigvals.append(H.data[i][i])
        
        return eigvals

    def eigenvectors(self, eigenvalues, tol=1e-10):
        if self.rows != self.cols:
            raise ValueError("只有方阵才能计算特征向量")
        
        n = self.rows
        eigvecs = []
        
        for eigval in eigenvalues:
            if isinstance(eigval, complex):
                continue
            
            A_minus_lambda = [[self.data[i][j] - (eigval if i == j else 0) 
                             for j in range(n)] for i in range(n)]
            
            found = False
            for start_col in range(n):
                aug = [row[:] + [0.0] for row in A_minus_lambda]
                
                for i in range(n):
                    max_row = i
                    for j in range(i, n):
                        if abs(aug[j][i]) > abs(aug[max_row][i]):
                            max_row = j
                    
                    if abs(aug[max_row][i]) < tol:
                        continue
                    
                    if max_row != i:
                        aug[i], aug[max_row] = aug[max_row], aug[i]
                    
                    pivot = aug[i][i]
                    for j in range(i, n + 1):
                        aug[i][j] /= pivot
                    
                    for j in range(n):
                        if j != i:
                            factor = aug[j][i]
                            for k in range(i, n + 1):
                                aug[j][k] -= factor * aug[i][k]
                
                vec = [aug[i][n] for i in range(n)]
                vec[start_col] = 1.0
                
                norm = sum(v * v for v in vec) ** 0.5
                if norm > tol:
                    vec = [v / norm for v in vec]
                    eigvecs.append(vec)
                    found = True
                    break
            
            if not found:
                eigvecs.append([0.0] * n)
        
        return Matrix(eigvecs).transpose()

    def svd(self, max_iter=100, tol=1e-10):
        m, n = self.rows, self.cols
        
        AtA = self.transpose().dot(self)
        
        eigvals = AtA.eigenvalues(max_iter=max_iter, tol=tol)
        
        real_eigvals = []
        for ev in eigvals:
            if isinstance(ev, complex):
                if abs(ev.imag) < tol:
                    real_eigvals.append(max(0.0, ev.real))
            else:
                real_eigvals.append(max(0.0, ev))
        
        real_eigvals.sort(reverse=True)
        singular_values = [max(0.0, ev) ** 0.5 for ev in real_eigvals]
        
        V = Matrix.identity(n)
        remaining = Matrix([row[:] for row in AtA.data])
        
        for i in range(min(n, m)):
            if singular_values[i] < tol:
                continue
            
            vec = [remaining.data[j][i] for j in range(n)]
            norm = sum(v * v for v in vec) ** 0.5
            
            if norm > tol:
                vec = [v / norm for v in vec]
                for j in range(n):
                    V.data[j][i] = vec[j]
        
        S_data = [[0.0] * n for _ in range(m)]
        for i in range(min(m, n, len(singular_values))):
            S_data[i][i] = singular_values[i]
        S = Matrix(S_data)
        
        U_data = [[0.0] * m for _ in range(m)]
        for i in range(min(m, n)):
            if singular_values[i] > tol:
                for j in range(m):
                    s = sum(self.data[j][k] * V.data[k][i] for k in range(n))
                    U_data[j][i] = s / singular_values[i]
            else:
                U_data[i][i] = 1.0
        
        for i in range(min(m, n), m):
            U_data[i][i] = 1.0
        
        U = Matrix(U_data)
        
        return U, S, V.transpose()
