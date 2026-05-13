import numpy as np
from math import gamma as gamma_func
from math import factorial, sqrt, pi, erf


def overlap_integral(basis1, basis2):
    S = 0.0
    n_prim1 = len(basis1.exponents)
    n_prim2 = len(basis2.exponents)
    
    for i in range(n_prim1):
        alpha1 = basis1.exponents[i]
        c1 = basis1.coefficients[i]
        n1 = basis1.norm_constants[i]
        
        for j in range(n_prim2):
            alpha2 = basis2.exponents[j]
            c2 = basis2.coefficients[j]
            n2 = basis2.norm_constants[j]
            
            S += (c1 * n1) * (c2 * n2) * _gaussian_overlap(
                alpha1, basis1.l, basis1.m, basis1.n, basis1.center,
                alpha2, basis2.l, basis2.m, basis2.n, basis2.center
            )
    
    return S


def kinetic_integral(basis1, basis2):
    T = 0.0
    n_prim1 = len(basis1.exponents)
    n_prim2 = len(basis2.exponents)
    
    for i in range(n_prim1):
        alpha1 = basis1.exponents[i]
        c1 = basis1.coefficients[i]
        n1 = basis1.norm_constants[i]
        
        for j in range(n_prim2):
            alpha2 = basis2.exponents[j]
            c2 = basis2.coefficients[j]
            n2 = basis2.norm_constants[j]
            
            T += (c1 * n1) * (c2 * n2) * _gaussian_kinetic(
                alpha1, basis1.l, basis1.m, basis1.n, basis1.center,
                alpha2, basis2.l, basis2.m, basis2.n, basis2.center
            )
    
    return T


def nuclear_attraction_integral(basis1, basis2, atoms):
    V = 0.0
    n_prim1 = len(basis1.exponents)
    n_prim2 = len(basis2.exponents)
    
    for i in range(n_prim1):
        alpha1 = basis1.exponents[i]
        c1 = basis1.coefficients[i]
        n1 = basis1.norm_constants[i]
        
        for j in range(n_prim2):
            alpha2 = basis2.exponents[j]
            c2 = basis2.coefficients[j]
            n2 = basis2.norm_constants[j]
            
            for symbol, center in atoms:
                from atom import ATOMIC_NUMBERS
                Z = ATOMIC_NUMBERS[symbol]
                V -= Z * (c1 * n1) * (c2 * n2) * _gaussian_nuclear(
                    alpha1, basis1.l, basis1.m, basis1.n, basis1.center,
                    alpha2, basis2.l, basis2.m, basis2.n, basis2.center,
                    np.array(center, dtype=np.float64)
                )
    
    return V


def _gaussian_overlap(alpha1, l1, m1, n1, A, alpha2, l2, m2, n2, B):
    gamma_val = alpha1 + alpha2
    P = (alpha1 * A + alpha2 * B) / gamma_val
    PA = P - A
    PB = P - B
    AB = A - B
    AB2 = np.dot(AB, AB)
    
    pre = np.exp(-alpha1 * alpha2 * AB2 / gamma_val)
    pre *= (np.pi / gamma_val) ** 1.5
    
    Sx = _hermite_overlap(l1, l2, PA[0], PB[0], gamma_val)
    Sy = _hermite_overlap(m1, m2, PA[1], PB[1], gamma_val)
    Sz = _hermite_overlap(n1, n2, PA[2], PB[2], gamma_val)
    
    return pre * Sx * Sy * Sz


def _hermite_overlap(i, j, PA, PB, gamma_val):
    p = 0
    for k in range(0, min(i, j) + 1):
        term = factorial(i) * factorial(j) * PA ** (i - k) * PB ** (j - k)
        term /= factorial(k) * factorial(i - k) * factorial(j - k)
        term /= (2 * gamma_val) ** ((i + j - k) / 2)
        p += term
    
    if (i + j) % 2 == 0:
        return p * gamma_func(0.5 * (i + j + 1)) / gamma_func(0.5)
    else:
        return p * sqrt(0.5 * np.pi / gamma_val)


def _gaussian_kinetic(alpha1, l1, m1, n1, A, alpha2, l2, m2, n2, B):
    gamma_val = alpha1 + alpha2
    P = (alpha1 * A + alpha2 * B) / gamma_val
    PA = P - A
    PB = P - B
    AB = A - B
    AB2 = np.dot(AB, AB)
    
    pre = np.exp(-alpha1 * alpha2 * AB2 / gamma_val)
    pre *= (np.pi / gamma_val) ** 1.5
    
    T_x = _kinetic_component(l1, m1, n1, l2, m2, n2, PA, PB, gamma_val, 0)
    T_y = _kinetic_component(l1, m1, n1, l2, m2, n2, PA, PB, gamma_val, 1)
    T_z = _kinetic_component(l1, m1, n1, l2, m2, n2, PA, PB, gamma_val, 2)
    
    return 0.5 * (T_x + T_y + T_z) * pre


def _kinetic_component(l1, m1, n1, l2, m2, n2, PA, PB, gamma_val, axis):
    i1, j1, k1 = (l1, m1, n1) if axis == 0 else (
        (m1, l1, n1) if axis == 1 else (n1, l1, m1)
    )
    i2, j2, k2 = (l2, m2, n2) if axis == 0 else (
        (m2, l2, n2) if axis == 1 else (n2, l2, m2)
    )
    
    pa = PA[axis]
    pb = PB[axis]
    
    S_i = _hermite_overlap(i1, i2, pa, pb, gamma_val)
    S_j = _hermite_overlap(j1, j2, PA[(axis + 1) % 3], PB[(axis + 1) % 3], gamma_val)
    S_k = _hermite_overlap(k1, k2, PA[(axis + 2) % 3], PB[(axis + 2) % 3], gamma_val)
    
    term1 = 2 * gamma_val * (i1 + 0.5) * S_i * S_j * S_k
    
    term2 = 0.0
    if i1 >= 2:
        S_i_minus_2 = _hermite_overlap(i1 - 2, i2, pa, pb, gamma_val)
        term2 = -0.5 * i1 * (i1 - 1) * S_i_minus_2 * S_j * S_k
    
    term3 = 0.0
    if i2 >= 2:
        S_i_plus_2 = _hermite_overlap(i1, i2 - 2, pa, pb, gamma_val)
        term3 = -0.5 * i2 * (i2 - 1) * S_i_plus_2 * S_j * S_k
    
    return term1 + term2 + term3


def _gaussian_nuclear(alpha1, l1, m1, n1, A, alpha2, l2, m2, n2, B, C):
    gamma_val = alpha1 + alpha2
    P = (alpha1 * A + alpha2 * B) / gamma_val
    PC = P - C
    PC2 = np.dot(PC, PC)
    AB = A - B
    AB2 = np.dot(AB, AB)
    
    pre = 2 * np.pi / gamma_val
    pre *= np.exp(-alpha1 * alpha2 * AB2 / gamma_val)
    
    F0 = _boys_function(gamma_val * PC2)
    
    Vx = _hermite_nuclear(l1, l2, P[0] - A[0], P[0] - B[0], P[0] - C[0], gamma_val)
    Vy = _hermite_nuclear(m1, m2, P[1] - A[1], P[1] - B[1], P[1] - C[1], gamma_val)
    Vz = _hermite_nuclear(n1, n2, P[2] - A[2], P[2] - B[2], P[2] - C[2], gamma_val)
    
    return pre * F0 * Vx * Vy * Vz


def _hermite_nuclear(i, j, PA, PB, PC, gamma_val):
    result = 0.0
    for k in range(0, i + j + 1):
        E_ij_k = 0.0
        for t in range(0, min(i, j) + 1):
            if (i + j - k) % 2 == 0:
                max_s = (i + j - k) // 2
                for s in range(0, max_s + 1):
                    idx = i - t - s
                    jdx = j - t - s
                    if idx >= 0 and jdx >= 0 and (idx + jdx) >= k:
                        term = factorial(i) * factorial(j)
                        term /= factorial(t) * factorial(s) * factorial(idx) * factorial(jdx)
                        term *= PA ** idx * PB ** jdx * (PC / 2) ** (idx + jdx - k)
                        term /= (2 * gamma_val) ** (t + s)
                        E_ij_k += term
        
        result += E_ij_k * gamma_func((k + 1) / 2) / gamma_func(0.5) * (2 * gamma_val) ** (-k / 2)
    
    return result


def _boys_function(t):
    if t < 1e-10:
        return 1.0
    elif t < 30:
        return 0.5 * sqrt(pi / t) * erf(sqrt(t))
    else:
        return 0.5 * sqrt(pi / t)


def build_overlap_matrix(basis):
    n = len(basis)
    S = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(i, n):
            S[i, j] = overlap_integral(basis[i], basis[j])
            S[j, i] = S[i, j]
    return S


def build_kinetic_matrix(basis):
    n = len(basis)
    T = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(i, n):
            T[i, j] = kinetic_integral(basis[i], basis[j])
            T[j, i] = T[i, j]
    return T


def build_nuclear_matrix(basis, atoms):
    n = len(basis)
    V = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(i, n):
            V[i, j] = nuclear_attraction_integral(basis[i], basis[j], atoms)
            V[j, i] = V[i, j]
    return V


def electron_repulsion_integral(basis1, basis2, basis3, basis4):
    ERI = 0.0
    n_prim1 = len(basis1.exponents)
    n_prim2 = len(basis2.exponents)
    n_prim3 = len(basis3.exponents)
    n_prim4 = len(basis4.exponents)
    
    for i in range(n_prim1):
        alpha1 = basis1.exponents[i]
        c1 = basis1.coefficients[i]
        n1 = basis1.norm_constants[i]
        
        for j in range(n_prim2):
            alpha2 = basis2.exponents[j]
            c2 = basis2.coefficients[j]
            n2 = basis2.norm_constants[j]
            
            gamma12 = alpha1 + alpha2
            P = (alpha1 * basis1.center + alpha2 * basis2.center) / gamma12
            AB = basis1.center - basis2.center
            AB2 = np.dot(AB, AB)
            pre12 = np.exp(-alpha1 * alpha2 * AB2 / gamma12)
            
            for k in range(n_prim3):
                alpha3 = basis3.exponents[k]
                c3 = basis3.coefficients[k]
                n3 = basis3.norm_constants[k]
                
                for l in range(n_prim4):
                    alpha4 = basis4.exponents[l]
                    c4 = basis4.coefficients[l]
                    n4 = basis4.norm_constants[l]
                    
                    ERI += (c1 * n1) * (c2 * n2) * (c3 * n3) * (c4 * n4) * \
                           _gaussian_eri_fast(
                               alpha1, alpha2, gamma12, P, pre12,
                               basis1.l, basis1.m, basis1.n, basis1.center,
                               basis2.l, basis2.m, basis2.n, basis2.center,
                               alpha3, alpha4, basis3.l, basis3.m, basis3.n, basis3.center,
                               basis4.l, basis4.m, basis4.n, basis4.center
                           )
    
    return ERI


def _gaussian_eri_fast(alpha1, alpha2, gamma12, P, pre12,
                       l1, m1, n1, A,
                       l2, m2, n2, B,
                       alpha3, alpha4,
                       l3, m3, n3, C,
                       l4, m4, n4, D):
    gamma34 = alpha3 + alpha4
    
    Q = (alpha3 * C + alpha4 * D) / gamma34
    CD = C - D
    CD2 = np.dot(CD, CD)
    PQ = P - Q
    PQ2 = np.dot(PQ, PQ)
    
    pre = 2 * pi ** 2.5 / (gamma12 * gamma34 * sqrt(gamma12 + gamma34))
    pre *= pre12
    pre *= np.exp(-alpha3 * alpha4 * CD2 / gamma34)
    
    t = (gamma12 * gamma34 / (gamma12 + gamma34)) * PQ2
    F0 = _boys_function(t)
    
    gx = _hermite_coulomb(l1, l2, l3, l4, P[0]-A[0], P[0]-B[0], Q[0]-C[0], Q[0]-D[0], P[0]-Q[0], gamma12, gamma34)
    gy = _hermite_coulomb(m1, m2, m3, m4, P[1]-A[1], P[1]-B[1], Q[1]-C[1], Q[1]-D[1], P[1]-Q[1], gamma12, gamma34)
    gz = _hermite_coulomb(n1, n2, n3, n4, P[2]-A[2], P[2]-B[2], Q[2]-C[2], Q[2]-D[2], P[2]-Q[2], gamma12, gamma34)
    
    return pre * F0 * gx * gy * gz


def _hermite_coulomb(i, j, k, l, PA, PB, QC, QD, PQ, gamma12, gamma34):
    gamma = gamma12 + gamma34
    
    result = 0.0
    for e in range(0, i + j + 1):
        E_ij_e = _hermite_overlap_3d(i, j, PA, PB, e, gamma12)
        for f in range(0, k + l + 1):
            F_kl_f = _hermite_overlap_3d(k, l, QC, QD, f, gamma34)
            for n in range(0, e + f + 1):
                R_efn = _coulomb_hermite(e, f, n, PQ, gamma12, gamma34, gamma)
                result += E_ij_e * F_kl_f * R_efn
    
    return result


def _hermite_overlap_3d(i, j, PA, PB, e, gamma_val):
    if e > i + j:
        return 0.0
    
    result = 0.0
    for t in range(0, min(i, j) + 1):
        if (i + j - e) % 2 == 0:
            max_s = (i + j - e) // 2
            for s in range(0, max_s + 1):
                idx = i - t - s
                jdx = j - t - s
                if idx >= 0 and jdx >= 0 and (idx + jdx) >= e:
                    if (idx + jdx - e) % 2 == 0:
                        term = factorial(i) * factorial(j)
                        term /= factorial(t) * factorial(s) * factorial(idx) * factorial(jdx)
                        term *= PA ** idx * PB ** jdx
                        term /= (2 * gamma_val) ** (t + s)
                        result += term
    
    if (i + j - e) % 2 == 0:
        return result * gamma_func((e + 1) / 2) / gamma_func(0.5) * (2 * gamma_val) ** (-e / 2)
    else:
        return 0.0


def _coulomb_hermite(e, f, n, PQ, gamma12, gamma34, gamma):
    if n > e + f:
        return 0.0
    
    if n > e or n > f:
        return 0.0
    
    prefactor = factorial(e) * factorial(f) / (factorial(e - n) * factorial(f - n))
    
    result = 0.0
    for m in range(0, (e + f - n) // 2 + 1):
        if (e + f - n - 2 * m) % 2 == 0:
            k = (e + f - n - 2 * m) // 2
            if k >= 0:
                term = prefactor * (-1) ** (n + m)
                term *= PQ ** k
                term *= gamma12 ** (e - n - m)
                term *= gamma34 ** (f - n - m)
                term /= (factorial(m) * factorial(k) * (2 * gamma) ** (e + f - n - m))
                result += term
    
    return result


def build_eri_matrix(basis):
    n = len(basis)
    ERI = np.zeros((n, n, n, n), dtype=np.float64)
    
    shell_info = []
    for i, bf in enumerate(basis):
        shell_info.append({
            'exponents': bf.exponents.copy(),
            'coefficients': bf.coefficients.copy(),
            'norm_constants': bf.norm_constants.copy(),
            'center': bf.center.copy(),
            'l': bf.l, 'm': bf.m, 'n': bf.n
        })
    
    for i in range(n):
        info_i = shell_info[i]
        alpha_i = info_i['exponents']
        c_i = info_i['coefficients'] * info_i['norm_constants']
        center_i = info_i['center']
        l_i, m_i, n_i = info_i['l'], info_i['m'], info_i['n']
        
        for j in range(i, n):
            info_j = shell_info[j]
            alpha_j = info_j['exponents']
            c_j = info_j['coefficients'] * info_j['norm_constants']
            center_j = info_j['center']
            l_j, m_j, n_j = info_j['l'], info_j['m'], info_j['n']
            
            pre_ij = np.zeros((len(alpha_i), len(alpha_j)), dtype=np.float64)
            gamma_ij = np.zeros((len(alpha_i), len(alpha_j)), dtype=np.float64)
            P_ij = np.zeros((len(alpha_i), len(alpha_j), 3), dtype=np.float64)
            
            for pi, a1 in enumerate(alpha_i):
                for pj, a2 in enumerate(alpha_j):
                    g = a1 + a2
                    gamma_ij[pi, pj] = g
                    P = (a1 * center_i + a2 * center_j) / g
                    P_ij[pi, pj] = P
                    AB = center_i - center_j
                    pre_ij[pi, pj] = np.exp(-a1 * a2 * np.dot(AB, AB) / g)
            
            for k in range(n):
                info_k = shell_info[k]
                alpha_k = info_k['exponents']
                c_k = info_k['coefficients'] * info_k['norm_constants']
                center_k = info_k['center']
                l_k, m_k, n_k = info_k['l'], info_k['m'], info_k['n']
                
                for l in range(k, n):
                    info_l = shell_info[l]
                    alpha_l = info_l['exponents']
                    c_l = info_l['coefficients'] * info_l['norm_constants']
                    center_l = info_l['center']
                    l_l, m_l, n_l = info_l['l'], info_l['m'], info_l['n']
                    
                    eri_val = 0.0
                    
                    for pi in range(len(alpha_i)):
                        a1 = alpha_i[pi]
                        ci = c_i[pi]
                        
                        for pj in range(len(alpha_j)):
                            a2 = alpha_j[pj]
                            cj = c_j[pj]
                            
                            g12 = gamma_ij[pi, pj]
                            P = P_ij[pi, pj]
                            pre12 = pre_ij[pi, pj]
                            
                            for pk in range(len(alpha_k)):
                                a3 = alpha_k[pk]
                                ck = c_k[pk]
                                
                                for pl in range(len(alpha_l)):
                                    a4 = alpha_l[pl]
                                    cl = c_l[pl]
                                    
                                    eri_val += ci * cj * ck * cl * _gaussian_eri_fast(
                                        a1, a2, g12, P, pre12,
                                        l_i, m_i, n_i, center_i,
                                        l_j, m_j, n_j, center_j,
                                        a3, a4,
                                        l_k, m_k, n_k, center_k,
                                        l_l, m_l, n_l, center_l
                                    )
                    
                    ERI[i, j, k, l] = eri_val
                    ERI[j, i, k, l] = eri_val
                    ERI[i, j, l, k] = eri_val
                    ERI[j, i, l, k] = eri_val
                    ERI[k, l, i, j] = eri_val
                    ERI[l, k, i, j] = eri_val
                    ERI[k, l, j, i] = eri_val
                    ERI[l, k, j, i] = eri_val
    
    return ERI


def _gaussian_overlap_deriv(alpha1, l1, m1, n1, A, alpha2, l2, m2, n2, B, axis=0):
    gamma_val = alpha1 + alpha2
    P = (alpha1 * A + alpha2 * B) / gamma_val
    PA = P - A
    PB = P - B
    AB = A - B
    AB2 = np.dot(AB, AB)
    
    pre = np.exp(-alpha1 * alpha2 * AB2 / gamma_val)
    pre *= (np.pi / gamma_val) ** 1.5
    
    S = _gaussian_overlap(alpha1, l1, m1, n1, A, alpha2, l2, m2, n2, B)
    
    i1, j1, k1 = (l1, m1, n1) if axis == 0 else (
        (m1, l1, n1) if axis == 1 else (n1, l1, m1)
    )
    i2, j2, k2 = (l2, m2, n2) if axis == 0 else (
        (m2, l2, n2) if axis == 1 else (n2, l2, m2)
    )
    
    S_i = _hermite_overlap(i1, i2, PA[axis], PB[axis], gamma_val)
    S_j = _hermite_overlap(j1, j2, PA[(axis + 1) % 3], PB[(axis + 1) % 3], gamma_val)
    S_k = _hermite_overlap(k1, k2, PA[(axis + 2) % 3], PB[(axis + 2) % 3], gamma_val)
    
    dS_dPA = 0.0
    if i1 > 0:
        S_i_minus_1 = _hermite_overlap(i1 - 1, i2, PA[axis], PB[axis], gamma_val)
        dS_dPA += i1 * S_i_minus_1
    if i2 > 0:
        S_i_plus_1 = _hermite_overlap(i1, i2 - 1, PA[axis], PB[axis], gamma_val)
        dS_dPA += i2 * S_i_plus_1
    
    dS_dPA *= 2 * gamma_val
    dS_dPA *= S_j * S_k
    dS_dPA *= pre
    
    dSA = -dS_dPA
    dSB = dS_dPA
    
    return dSA, dSB


def _gaussian_kinetic_deriv(alpha1, l1, m1, n1, A, alpha2, l2, m2, n2, B, axis=0):
    gamma_val = alpha1 + alpha2
    P = (alpha1 * A + alpha2 * B) / gamma_val
    PA = P - A
    PB = P - B
    AB = A - B
    AB2 = np.dot(AB, AB)
    
    pre = np.exp(-alpha1 * alpha2 * AB2 / gamma_val)
    pre *= (np.pi / gamma_val) ** 1.5
    
    T_x = _kinetic_component(l1, m1, n1, l2, m2, n2, PA, PB, gamma_val, 0)
    T_y = _kinetic_component(l1, m1, n1, l2, m2, n2, PA, PB, gamma_val, 1)
    T_z = _kinetic_component(l1, m1, n1, l2, m2, n2, PA, PB, gamma_val, 2)
    T = 0.5 * (T_x + T_y + T_z) * pre
    
    i1, j1, k1 = (l1, m1, n1) if axis == 0 else (
        (m1, l1, n1) if axis == 1 else (n1, l1, m1)
    )
    i2, j2, k2 = (l2, m2, n2) if axis == 0 else (
        (m2, l2, n2) if axis == 1 else (n2, l2, m2)
    )
    
    dT_dPA = 0.0
    
    term1_deriv = 2 * gamma_val * (i1 + 0.5)
    S_i = _hermite_overlap(i1, i2, PA[axis], PB[axis], gamma_val)
    S_j = _hermite_overlap(j1, j2, PA[(axis + 1) % 3], PB[(axis + 1) % 3], gamma_val)
    S_k = _hermite_overlap(k1, k2, PA[(axis + 2) % 3], PB[(axis + 2) % 3], gamma_val)
    
    if i1 > 0:
        S_i_minus_1 = _hermite_overlap(i1 - 1, i2, PA[axis], PB[axis], gamma_val)
        dT_dPA += term1_deriv * i1 * S_i_minus_1 * S_j * S_k
    
    if i2 > 0:
        S_i_plus_1 = _hermite_overlap(i1, i2 - 1, PA[axis], PB[axis], gamma_val)
        dT_dPA += term1_deriv * i2 * S_i_plus_1 * S_j * S_k
    
    dT_dPA *= 2 * gamma_val
    dT_dPA *= pre
    
    dTA = -dT_dPA
    dTB = dT_dPA
    
    return dTA, dTB


def _gaussian_nuclear_deriv(alpha1, l1, m1, n1, A, alpha2, l2, m2, n2, B, C, axis=0):
    gamma_val = alpha1 + alpha2
    P = (alpha1 * A + alpha2 * B) / gamma_val
    PC = P - C
    PC2 = np.dot(PC, PC)
    AB = A - B
    AB2 = np.dot(AB, AB)
    
    pre = 2 * np.pi / gamma_val
    pre *= np.exp(-alpha1 * alpha2 * AB2 / gamma_val)
    
    t = gamma_val * PC2
    F0 = _boys_function(t)
    
    Vx = _hermite_nuclear(l1, l2, P[0] - A[0], P[0] - B[0], P[0] - C[0], gamma_val)
    Vy = _hermite_nuclear(m1, m2, P[1] - A[1], P[1] - B[1], P[1] - C[1], gamma_val)
    Vz = _hermite_nuclear(n1, n2, P[2] - A[2], P[2] - B[2], P[2] - C[2], gamma_val)
    V = pre * F0 * Vx * Vy * Vz
    
    dV_dPC = 0.0
    if PC[axis] != 0:
        F1 = (F0 - (gamma_val * PC[axis] * _boys_function(t + 1) if t + 1 > 0 else 0)) / (2 * PC[axis] + 1e-10)
        dV_dPC = pre * F1 * 2 * gamma_val * PC[axis]
    
    dV_dPA = dV_dPC
    dV_dPB = dV_dPC
    dV_dPC_center = -dV_dPC
    
    dVA = -dV_dPA
    dVB = -dV_dPB
    
    return dVA, dVB, dV_dPC_center


def _eri_deriv_shell_pair(alpha1, alpha2, gamma12, P, pre12,
                          l1, m1, n1, A,
                          l2, m2, n2, B,
                          alpha3, alpha4,
                          l3, m3, n3, C,
                          l4, m4, n4, D,
                          axis=0):
    gamma34 = alpha3 + alpha4
    Q = (alpha3 * C + alpha4 * D) / gamma34
    CD = C - D
    CD2 = np.dot(CD, CD)
    PQ = P - Q
    PQ2 = np.dot(PQ, PQ)
    
    pre = 2 * pi ** 2.5 / (gamma12 * gamma34 * sqrt(gamma12 + gamma34))
    pre *= pre12
    pre *= np.exp(-alpha3 * alpha4 * CD2 / gamma34)
    
    t = (gamma12 * gamma34 / (gamma12 + gamma34)) * PQ2
    F0 = _boys_function(t)
    
    gx = _hermite_coulomb(l1, l2, l3, l4, P[0]-A[0], P[0]-B[0], Q[0]-C[0], Q[0]-D[0], P[0]-Q[0], gamma12, gamma34)
    gy = _hermite_coulomb(m1, m2, m3, m4, P[1]-A[1], P[1]-B[1], Q[1]-C[1], Q[1]-D[1], P[1]-Q[1], gamma12, gamma34)
    gz = _hermite_coulomb(n1, n2, n3, n4, P[2]-A[2], P[2]-B[2], Q[2]-C[2], Q[2]-D[2], P[2]-Q[2], gamma12, gamma34)
    eri = pre * F0 * gx * gy * gz
    
    gamma = gamma12 + gamma34
    t_val = (gamma12 * gamma34 / gamma) * PQ2
    
    if PQ[axis] != 0:
        F1 = (F0 - (gamma12 * gamma34 / gamma) * PQ[axis] * _boys_function(t_val + 1)) / (2 * PQ[axis] + 1e-10)
    else:
        F1 = -(gamma12 * gamma34 / gamma) * _boys_function(t_val + 1) / 2
    
    dERI_dPQ = pre * 2 * (gamma12 * gamma34 / gamma) * PQ[axis] * F1 * gx * gy * gz
    
    dERI_dA = -dERI_dPQ
    dERI_dB = -dERI_dPQ
    dERI_dC = dERI_dPQ
    dERI_dD = dERI_dPQ
    
    return dERI_dA, dERI_dB, dERI_dC, dERI_dD


def compute_gradient(atoms, results):
    from atom import ATOMIC_NUMBERS
    
    P = results['density_matrix']
    if results.get('is_uks', False):
        Pa = results['density_matrix_alpha']
        Pb = results['density_matrix_beta']
        P = Pa + Pb
    
    basis = results['basis']
    ERI = results.get('eri_tensor')
    
    if ERI is None:
        ERI = build_eri_matrix(basis)
    
    n_atoms = len(atoms)
    gradient = np.zeros((n_atoms, 3), dtype=np.float64)
    
    for atom_idx, (symbol, center) in enumerate(atoms):
        Z = ATOMIC_NUMBERS[symbol]
        
        for other_idx, (other_symbol, other_center) in enumerate(atoms):
            if atom_idx == other_idx:
                continue
            
            Ri = np.array(center)
            Rj = np.array(other_center)
            r = np.linalg.norm(Ri - Rj)
            if r > 1e-10:
                Zj = ATOMIC_NUMBERS[other_symbol]
                direction = (Ri - Rj) / r
                gradient[atom_idx] += Z * Zj / (r * r) * direction
    
    return gradient


def compute_numerical_gradient(atoms, scf_func, step=1e-4, **kwargs):
    n_atoms = len(atoms)
    gradient = np.zeros((n_atoms, 3), dtype=np.float64)
    
    for i in range(n_atoms):
        for j in range(3):
            atoms_plus = [(s, list(c)) for s, c in atoms]
            atoms_plus[i][1][j] += step
            
            results_plus = scf_func(atoms_plus, **kwargs)
            E_plus = results_plus['energy']
            
            atoms_minus = [(s, list(c)) for s, c in atoms]
            atoms_minus[i][1][j] -= step
            
            results_minus = scf_func(atoms_minus, **kwargs)
            E_minus = results_minus['energy']
            
            gradient[i, j] = (E_plus - E_minus) / (2 * step)
    
    return gradient
