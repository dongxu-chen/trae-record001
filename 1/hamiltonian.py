import numpy as np

class TightBindingHamiltonian:
    def __init__(self, lattice_constant=5.431, use_soc=False, lambda_soc=0.044):
        self.a = lattice_constant
        self.a0 = lattice_constant / 4.0
        self.d1 = np.array([1, 1, 1]) * self.a0
        self.d2 = np.array([1, -1, -1]) * self.a0
        self.d3 = np.array([-1, 1, -1]) * self.a0
        self.d4 = np.array([-1, -1, 1]) * self.a0
        self.nn_vectors = [self.d1, self.d2, self.d3, self.d4]
        self.use_soc = use_soc
        self.lambda_soc = lambda_soc
        self._setup_parameters()

    def _setup_parameters(self):
        self.E_s = -4.0
        self.E_p = 3.5
        self.V_ss = -1.4
        self.V_sp = 1.84
        self.V_xx = 3.2
        self.V_xy = 0.95
        self._build_soc_onsite()

    def _ss(self, k):
        return self.V_ss * sum(np.exp(1j * np.dot(k, d)) for d in self.nn_vectors)

    def _sp_component(self, k, alpha):
        return self.V_sp * sum(np.exp(1j * np.dot(k, d)) * d[alpha] / self.a0 for d in self.nn_vectors)

    def _pp_component(self, k, alpha, beta):
        if alpha == beta:
            return (self.V_xx - self.V_xy) * sum(np.exp(1j * np.dot(k, d)) * d[alpha]**2 / self.a0**2 for d in self.nn_vectors) + self.V_xy * sum(np.exp(1j * np.dot(k, d)) for d in self.nn_vectors)
        else:
            return (self.V_xx - self.V_xy) * sum(np.exp(1j * np.dot(k, d)) * d[alpha] * d[beta] / self.a0**2 for d in self.nn_vectors)

    def build(self, k_frac):
        k_cart = 2 * np.pi / self.a * k_frac
        H = np.zeros((8, 8), dtype=np.complex128)
        E_s = self.E_s
        E_p = self.E_p
        H_ss = self._ss(k_cart)
        H_sp_x = self._sp_component(k_cart, 0)
        H_sp_y = self._sp_component(k_cart, 1)
        H_sp_z = self._sp_component(k_cart, 2)
        H_xx = self._pp_component(k_cart, 0, 0)
        H_yy = self._pp_component(k_cart, 1, 1)
        H_zz = self._pp_component(k_cart, 2, 2)
        H_xy = self._pp_component(k_cart, 0, 1)
        H_xz = self._pp_component(k_cart, 0, 2)
        H_yz = self._pp_component(k_cart, 1, 2)
        H[0, 0] = E_s
        H[1, 1] = E_s
        H[2, 2] = E_p
        H[3, 3] = E_p
        H[4, 4] = E_p
        H[5, 5] = E_p
        H[6, 6] = E_p
        H[7, 7] = E_p
        H[0, 1] = H_ss
        H[1, 0] = np.conj(H_ss)
        H[0, 2] = H_sp_x
        H[2, 0] = np.conj(H_sp_x)
        H[0, 3] = H_sp_y
        H[3, 0] = np.conj(H_sp_y)
        H[0, 4] = H_sp_z
        H[4, 0] = np.conj(H_sp_z)
        H[1, 5] = H_sp_x
        H[5, 1] = np.conj(H_sp_x)
        H[1, 6] = H_sp_y
        H[6, 1] = np.conj(H_sp_y)
        H[1, 7] = H_sp_z
        H[7, 1] = np.conj(H_sp_z)
        H[2, 5] = H_xx
        H[5, 2] = np.conj(H_xx)
        H[3, 6] = H_yy
        H[6, 3] = np.conj(H_yy)
        H[4, 7] = H_zz
        H[7, 4] = np.conj(H_zz)
        H[2, 6] = H_xy
        H[6, 2] = np.conj(H_xy)
        H[2, 7] = H_xz
        H[7, 2] = np.conj(H_xz)
        H[3, 5] = H_xy
        H[5, 3] = np.conj(H_xy)
        H[3, 7] = H_yz
        H[7, 3] = np.conj(H_yz)
        H[4, 5] = H_xz
        H[5, 4] = np.conj(H_xz)
        H[4, 6] = H_yz
        H[6, 4] = np.conj(H_yz)
        if self.use_soc:
            H = self._add_soc_to_hamiltonian(H)
        return H

    def _build_soc_onsite(self):
        sigma_x = np.array([[0, 1], [1, 0]], dtype=np.complex128)
        sigma_y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
        sigma_z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
        sigma = {'x': sigma_x, 'y': sigma_y, 'z': sigma_z}
        L = np.zeros((3, 4, 4), dtype=np.complex128)
        sqrt2 = np.sqrt(2)
        L[0, 1, 2] = 1j / sqrt2
        L[0, 2, 1] = -1j / sqrt2
        L[0, 2, 3] = 1j / sqrt2
        L[0, 3, 2] = -1j / sqrt2
        L[1, 1, 2] = -1 / sqrt2
        L[1, 2, 1] = -1 / sqrt2
        L[1, 2, 3] = 1 / sqrt2
        L[1, 3, 2] = 1 / sqrt2
        L[2, 1, 3] = 1j
        L[2, 3, 1] = -1j
        self.L_matrix = L
        self.sigma_matrices = sigma

    def _add_soc_to_hamiltonian(self, H0):
        n_orb = H0.shape[0]
        n_orb_spin = 16
        H = np.zeros((n_orb_spin, n_orb_spin), dtype=np.complex128)
        H[:8, :8] = H0
        H[8:, 8:] = H0
        L = self.L_matrix
        sigma = self.sigma_matrices
        lambda_soc = self.lambda_soc
        for spin1 in range(2):
            for spin2 in range(2):
                sigma_matrix = np.zeros((2, 2), dtype=np.complex128)
                if spin1 == 0 and spin2 == 1:
                    sigma_matrix = sigma['x'] - 1j * sigma['y']
                elif spin1 == 1 and spin2 == 0:
                    sigma_matrix = sigma['x'] + 1j * sigma['y']
                elif spin1 == 0 and spin2 == 0:
                    sigma_matrix = sigma['z']
                elif spin1 == 1 and spin2 == 1:
                    sigma_matrix = -sigma['z']
                for alpha in range(3):
                    for atom in range(2):
                        orb_offset = atom * 4
                        spin1_offset = spin1 * 8
                        spin2_offset = spin2 * 8
                        for i in range(4):
                            for j in range(4):
                                L_val = L[alpha, i, j]
                                sigma_val = sigma_matrix[spin1, spin2]
                                val = L_val * sigma_val * lambda_soc / 2.0
                                row = spin1_offset + orb_offset + i
                                col = spin2_offset + orb_offset + j
                                H[row, col] += val
        return H

    def is_soc_enabled(self):
        return self.use_soc

    def get_hamiltonian_size(self):
        return 16 if self.use_soc else 8

    def set_lambda_soc(self, lambda_soc):
        self.lambda_soc = lambda_soc
        self._build_soc_onsite()
