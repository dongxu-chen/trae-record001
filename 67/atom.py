import numpy as np


class GaussianBasis:
    def __init__(self, exponents, coefficients, center, l=0, m=0, n=0):
        self.exponents = np.array(exponents, dtype=np.float64)
        self.coefficients = np.array(coefficients, dtype=np.float64)
        self.center = np.array(center, dtype=np.float64)
        self.l = l
        self.m = m
        self.n = n
        self.norm_constants = self._normalize()

    def _normalize(self):
        norm_constants = []
        for alpha in self.exponents:
            norm = self._gaussian_norm(alpha, self.l, self.m, self.n)
            norm_constants.append(norm)
        return np.array(norm_constants, dtype=np.float64)

    @staticmethod
    def _gaussian_norm(alpha, l, m, n):
        from math import gamma

        lmn = l + m + n
        numerator = (2 * alpha / np.pi) ** 0.75
        denominator = (
            (4 * alpha) ** lmn
            * gamma(l + 0.5)
            * gamma(m + 0.5)
            * gamma(n + 0.5)
        ) ** 0.5
        return numerator / denominator


def sto3g_hydrogen(center):
    exponents = [3.42525091, 0.62391373, 0.16885540]
    coefficients = [0.15432897, 0.53532814, 0.44463454]
    return GaussianBasis(exponents, coefficients, center)


def sto3g_helium(center):
    exponents = [6.36242139, 1.15892300, 0.31364979]
    coefficients = [0.15432897, 0.53532814, 0.44463454]
    return GaussianBasis(exponents, coefficients, center)


def sto3g_lithium(center):
    s_exponents = [16.11943300, 2.93620070, 0.79465050]
    s_coefficients = [0.15432897, 0.53532814, 0.44463454]
    
    sp_exponents = [0.63628970, 0.14786010, 0.04808870]
    s_2_coefficients = [-0.09996723, 0.39951283, 0.70011546]
    p_coefficients = [0.15591627, 0.60768372, 0.39195739]
    
    basis = [
        GaussianBasis(s_exponents, s_coefficients, center),
        GaussianBasis(sp_exponents, s_2_coefficients, center),
        GaussianBasis(sp_exponents, p_coefficients, center, l=1, m=0, n=0),
        GaussianBasis(sp_exponents, p_coefficients, center, l=0, m=1, n=0),
        GaussianBasis(sp_exponents, p_coefficients, center, l=0, m=0, n=1),
    ]
    return basis


def sto3g_carbon(center):
    s_exponents = [71.61683700, 13.04509600, 3.53051220]
    s_coefficients = [0.15432897, 0.53532814, 0.44463454]
    
    sp_exponents = [2.94124940, 0.68348310, 0.22228990]
    s_2_coefficients = [-0.09996723, 0.39951283, 0.70011546]
    p_coefficients = [0.15591627, 0.60768372, 0.39195739]
    
    basis = [
        GaussianBasis(s_exponents, s_coefficients, center),
        GaussianBasis(sp_exponents, s_2_coefficients, center),
        GaussianBasis(sp_exponents, p_coefficients, center, l=1, m=0, n=0),
        GaussianBasis(sp_exponents, p_coefficients, center, l=0, m=1, n=0),
        GaussianBasis(sp_exponents, p_coefficients, center, l=0, m=0, n=1),
    ]
    return basis


def sto3g_oxygen(center):
    s_exponents = [130.7093200, 23.8088660, 6.44360830]
    s_coefficients = [0.15432897, 0.53532814, 0.44463454]
    
    sp_exponents = [5.03315130, 1.16959610, 0.38038900]
    s_2_coefficients = [-0.09996723, 0.39951283, 0.70011546]
    p_coefficients = [0.15591627, 0.60768372, 0.39195739]
    
    basis = [
        GaussianBasis(s_exponents, s_coefficients, center),
        GaussianBasis(sp_exponents, s_2_coefficients, center),
        GaussianBasis(sp_exponents, p_coefficients, center, l=1, m=0, n=0),
        GaussianBasis(sp_exponents, p_coefficients, center, l=0, m=1, n=0),
        GaussianBasis(sp_exponents, p_coefficients, center, l=0, m=0, n=1),
    ]
    return basis


BASIS_SETS = {
    'H': sto3g_hydrogen,
    'He': sto3g_helium,
    'Li': sto3g_lithium,
    'C': sto3g_carbon,
    'O': sto3g_oxygen,
}


ATOMIC_NUMBERS = {
    'H': 1,
    'He': 2,
    'Li': 3,
    'C': 6,
    'O': 8,
}


def get_basis(atoms):
    basis = []
    for symbol, center in atoms:
        if symbol not in BASIS_SETS:
            raise ValueError(f"Unsupported atom: {symbol}")
        atom_basis = BASIS_SETS[symbol](center)
        if isinstance(atom_basis, list):
            basis.extend(atom_basis)
        else:
            basis.append(atom_basis)
    return basis
