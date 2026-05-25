"""
Bloch equation solver module
Contains CPU and GPU (PyCUDA) versions of the Bloch equation numerical solver

Bloch equation:
dM/dt = gamma * (M x B) - (Mx i + My j)/T2 - (Mz - M0)k/T1

Where:
- M = (Mx, My, Mz) is the magnetization vector
- gamma is the gyromagnetic ratio (~42.58 MHz/T for hydrogen)
- B is the total magnetic field (B0 + B1 + gradient fields)
- T1, T2 are the relaxation times
- M0 is the equilibrium magnetization (proportional to proton density)
"""

import numpy as np
from scipy.integrate import ode

try:
    import pycuda.driver as cuda
    import pycuda.autoinit
    from pycuda.compiler import SourceModule
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

GAMMA = 42.576e6
GAMMA_RAD = GAMMA * 2 * np.pi


class BlochSolver:
    """
    CPU version of the Bloch equation solver
    Uses analytical solution in rotating frame for efficient computation
    Supports adaptive time stepping (based on shortest T2/10)
    """

    def __init__(self, n_voxels, gamma=GAMMA_RAD):
        """
        Initialize Bloch solver

        Parameters:
            n_voxels: number of voxels
            gamma: gyromagnetic ratio (rad/s/T)
        """
        self.n_voxels = n_voxels
        self.gamma = gamma

        self.Mx = np.zeros(n_voxels, dtype=np.float64)
        self.My = np.zeros(n_voxels, dtype=np.float64)
        self.Mz = np.ones(n_voxels, dtype=np.float64)

        self.M0 = np.ones(n_voxels, dtype=np.float64)
        self.T1 = np.ones(n_voxels, dtype=np.float64)
        self.T2 = np.ones(n_voxels, dtype=np.float64)

        self.delta_B0 = np.zeros(n_voxels, dtype=np.float64)
        self.B1_correction = np.ones(n_voxels, dtype=np.float64)

        self._adaptive_dt = None
        self._min_T2 = None

    def set_params(self, pd, t1, t2):
        """
        Set tissue parameters for each voxel

        Parameters:
            pd: proton density array
            t1: T1 relaxation time array (seconds)
            t2: T2 relaxation time array (seconds)
        """
        self.M0 = pd.astype(np.float64)
        self.T1 = t1.astype(np.float64)
        self.T2 = t2.astype(np.float64)
        self.Mz = self.M0.copy()
        self.Mx.fill(0.0)
        self.My.fill(0.0)

        self.delta_B0 = np.zeros_like(pd)
        self.B1_correction = np.ones_like(pd)

        self._update_adaptive_dt()

    def set_field_inhomogeneity(self, delta_B0=None, B1_correction=None):
        """
        Set B0/B1 field inhomogeneity parameters

        Parameters:
            delta_B0: B0 field inhomogeneity (Hz), shape (n_voxels,)
            B1_correction: B1 field correction factor, shape (n_voxels,), range 0.5-1.5
        """
        if delta_B0 is not None:
            self.delta_B0 = delta_B0.astype(np.float64)

        if B1_correction is not None:
            self.B1_correction = B1_correction.astype(np.float64)

        self._update_adaptive_dt()

    def _update_adaptive_dt(self):
        """
        Update adaptive time step
        Based on 1/10 of the shortest valid T2 (T2 > 0)
        Also considers fast precession caused by B0 inhomogeneity
        """
        eps = 1e-10
        valid_T2 = self.T2[self.T2 > eps]
        if len(valid_T2) > 0:
            self._min_T2 = np.min(valid_T2)
            dt_T2 = self._min_T2 / 10.0
        else:
            self._min_T2 = 1.0
            dt_T2 = 0.1

        if np.max(np.abs(self.delta_B0)) > eps:
            max_frequency = np.max(np.abs(self.delta_B0))
            dt_B0 = 1.0 / (10.0 * max_frequency) if max_frequency > eps else dt_T2
            self._adaptive_dt = min(dt_T2, dt_B0)
        else:
            self._adaptive_dt = dt_T2

    def get_adaptive_dt(self):
        """Get adaptive time step"""
        if self._adaptive_dt is None:
            self._update_adaptive_dt()
        return self._adaptive_dt

    def reset_magnetization(self):
        """Reset magnetization to equilibrium state"""
        self.Mx.fill(0.0)
        self.My.fill(0.0)
        self.Mz = self.M0.copy()

    def apply_excitation(self, flip_angle, phase=0.0):
        """
        Apply excitation pulse with arbitrary flip angle (considering B1 inhomogeneity)

        Parameters:
            flip_angle: nominal flip angle (radians)
            phase: pulse phase (radians)
        """
        effective_flip = flip_angle * self.B1_correction

        cos_a = np.cos(effective_flip)
        sin_a = np.sin(effective_flip)
        cos_p = np.cos(phase)
        sin_p = np.sin(phase)

        new_Mx = (cos_a * cos_p ** 2 + sin_p ** 2) * self.Mx + \
                 (cos_a - 1) * cos_p * sin_p * self.My - \
                 sin_a * cos_p * self.Mz

        new_My = (cos_a - 1) * cos_p * sin_p * self.Mx + \
                 (cos_a * sin_p ** 2 + cos_p ** 2) * self.My - \
                 sin_a * sin_p * self.Mz

        new_Mz = sin_a * cos_p * self.Mx + \
                 sin_a * sin_p * self.My + \
                 cos_a * self.Mz

        self.Mx = new_Mx
        self.My = new_My
        self.Mz = new_Mz

    def relax(self, duration):
        """
        Evolution considering relaxation (adaptive step)

        Parameters:
            duration: total evolution time (seconds)
        """
        dt = self.get_adaptive_dt()
        remaining = duration

        while remaining > 1e-12:
            step = min(dt, remaining)
            self._relax_single_step(step)
            remaining -= step

    def _relax_single_step(self, dt):
        """Single step relaxation evolution"""
        eps = 1e-10
        T1_safe = np.maximum(self.T1, eps)
        T2_safe = np.maximum(self.T2, eps)

        e1 = np.exp(-dt / T1_safe)
        e2 = np.exp(-dt / T2_safe)

        e1[self.T1 <= 0] = 0.0
        e2[self.T2 <= 0] = 0.0
        M0_mask = (self.T1 > 0) & (self.T2 > 0)

        self.Mx = self.Mx * e2
        self.My = self.My * e2
        self.Mz = self.Mz * e1 + self.M0 * (1 - e1) * M0_mask

    def precess(self, duration, gx, gy, x, y):
        """
        Free precession considering gradient fields (adaptive step)

        Parameters:
            duration: total precession time (seconds)
            gx: gradient in x direction (T/m)
            gy: gradient in y direction (T/m)
            x, y: voxel coordinates (m)
        """
        dt = self.get_adaptive_dt()
        remaining = duration

        while remaining > 1e-12:
            step = min(dt, remaining)
            self._precess_single_step(step, gx, gy, x, y)
            remaining -= step

    def _precess_single_step(self, dt, gx, gy, x, y):
        """Single step precession evolution (considering B0 inhomogeneity)"""
        delta_omega_grad = self.gamma * (gx * x + gy * y)
        delta_omega_B0 = 2 * np.pi * self.delta_B0
        delta_omega = delta_omega_grad + delta_omega_B0

        phi = delta_omega * dt

        cos_phi = np.cos(phi)
        sin_phi = np.sin(phi)

        new_Mx = self.Mx * cos_phi - self.My * sin_phi
        new_My = self.Mx * sin_phi + self.My * cos_phi

        self.Mx = new_Mx
        self.My = new_My

    def evolve(self, duration, gx=0.0, gy=0.0, x=None, y=None):
        """
        Evolution considering both relaxation and precession (adaptive step)

        Parameters:
            duration: total evolution time (seconds)
            gx: gradient in x direction (T/m)
            gy: gradient in y direction (T/m)
            x, y: voxel coordinates (m)
        """
        dt = self.get_adaptive_dt()
        remaining = duration

        while remaining > 1e-12:
            step = min(dt, remaining)
            self._relax_single_step(step)

            if gx != 0.0 or gy != 0.0:
                if x is None or y is None:
                    raise ValueError("When applying gradients, voxel coordinates x and y must be provided")
                self._precess_single_step(step, gx, gy, x, y)

            remaining -= step

    def get_signal(self, coil_sensitivity=None):
        """
        Get current MR signal (complex sum of transverse magnetization)

        Parameters:
            coil_sensitivity: coil sensitivity map (optional)

        Returns:
            Complex signal sum (S = Mx + iMy)
        """
        signal = self.Mx + 1j * self.My
        if coil_sensitivity is not None:
            signal = signal * coil_sensitivity
        return np.sum(signal)

    def get_transverse(self):
        """Get transverse magnetization vector"""
        return self.Mx, self.My

    def get_longitudinal(self):
        """Get longitudinal magnetization"""
        return self.Mz


class BlochSolverGPU:
    """
    GPU version of the Bloch equation solver
    Uses PyCUDA for parallel computation, full GPU memory operation
    Supports adaptive time stepping (based on shortest T2/10)
    """

    def __init__(self, n_voxels, gamma=GAMMA_RAD):
        """
        Initialize GPU Bloch solver

        Parameters:
            n_voxels: number of voxels
            gamma: gyromagnetic ratio (rad/s/T)
        """
        if not GPU_AVAILABLE:
            raise RuntimeError("PyCUDA not available, please install PyCUDA or use CPU version")

        self.n_voxels = n_voxels
        self.gamma = gamma

        self._Mx = cuda.mem_alloc(n_voxels * 8)
        self._My = cuda.mem_alloc(n_voxels * 8)
        self._Mz = cuda.mem_alloc(n_voxels * 8)
        self._M0 = cuda.mem_alloc(n_voxels * 8)
        self._T1 = cuda.mem_alloc(n_voxels * 8)
        self._T2 = cuda.mem_alloc(n_voxels * 8)
        self._x = cuda.mem_alloc(n_voxels * 8)
        self._y = cuda.mem_alloc(n_voxels * 8)
        self._delta_B0 = cuda.mem_alloc(n_voxels * 8)
        self._B1_correction = cuda.mem_alloc(n_voxels * 8)

        self._kspace_line = None
        self._kspace_line_size = 0

        self._compile_kernels()

        Mx_h = np.zeros(n_voxels, dtype=np.float64)
        My_h = np.zeros(n_voxels, dtype=np.float64)
        Mz_h = np.ones(n_voxels, dtype=np.float64)
        M0_h = np.ones(n_voxels, dtype=np.float64)
        T1_h = np.ones(n_voxels, dtype=np.float64)
        T2_h = np.ones(n_voxels, dtype=np.float64)
        x_h = np.zeros(n_voxels, dtype=np.float64)
        y_h = np.zeros(n_voxels, dtype=np.float64)
        delta_B0_h = np.zeros(n_voxels, dtype=np.float64)
        B1_correction_h = np.ones(n_voxels, dtype=np.float64)

        cuda.memcpy_htod(self._Mx, Mx_h)
        cuda.memcpy_htod(self._My, My_h)
        cuda.memcpy_htod(self._Mz, Mz_h)
        cuda.memcpy_htod(self._M0, M0_h)
        cuda.memcpy_htod(self._T1, T1_h)
        cuda.memcpy_htod(self._T2, T2_h)
        cuda.memcpy_htod(self._x, x_h)
        cuda.memcpy_htod(self._y, y_h)
        cuda.memcpy_htod(self._delta_B0, delta_B0_h)
        cuda.memcpy_htod(self._B1_correction, B1_correction_h)

        self._adaptive_dt = 0.1
        self._min_T2 = 1.0
        self._max_delta_B0 = 0.0

    def _compile_kernels(self):
        """Compile CUDA kernels"""
        kernel_code = """
        __global__ void apply_excitation_kernel(
            double *Mx, double *My, double *Mz,
            double *B1_correction,
            double flip_angle, double phase, int n)
        {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            if (idx >= n) return;

            double b1 = B1_correction[idx];
            double effective_flip = flip_angle * b1;

            double cos_a = cos(effective_flip);
            double sin_a = sin(effective_flip);
            double cos_p = cos(phase);
            double sin_p = sin(phase);

            double mx = Mx[idx];
            double my = My[idx];
            double mz = Mz[idx];

            double new_Mx = (cos_a * cos_p * cos_p + sin_p * sin_p) * mx +
                           (cos_a - 1.0) * cos_p * sin_p * my -
                           sin_a * cos_p * mz;

            double new_My = (cos_a - 1.0) * cos_p * sin_p * mx +
                           (cos_a * sin_p * sin_p + cos_p * cos_p) * my -
                           sin_a * sin_p * mz;

            double new_Mz = sin_a * cos_p * mx +
                           sin_a * sin_p * my +
                           cos_a * mz;

            Mx[idx] = new_Mx;
            My[idx] = new_My;
            Mz[idx] = new_Mz;
        }

        __global__ void relax_single_step_kernel(
            double *Mx, double *My, double *Mz,
            double *M0, double *T1, double *T2,
            double dt, int n)
        {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            if (idx >= n) return;

            double t1 = T1[idx];
            double t2 = T2[idx];
            double eps = 1e-10;

            double t1_safe = t1 > eps ? t1 : eps;
            double t2_safe = t2 > eps ? t2 : eps;

            double e1 = exp(-dt / t1_safe);
            double e2 = exp(-dt / t2_safe);

            if (t1 <= eps) e1 = 0.0;
            if (t2 <= eps) e2 = 0.0;

            double m0_mask = (t1 > eps) && (t2 > eps) ? 1.0 : 0.0;

            Mx[idx] *= e2;
            My[idx] *= e2;
            Mz[idx] = Mz[idx] * e1 + M0[idx] * (1.0 - e1) * m0_mask;
        }

        __global__ void precess_single_step_kernel(
            double *Mx, double *My, double *Mz,
            double *x, double *y, double *delta_B0,
            double dt, double gx, double gy,
            double gamma, int n)
        {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            if (idx >= n) return;

            double delta_omega_grad = gamma * (gx * x[idx] + gy * y[idx]);
            double delta_omega_B0 = 6.283185307179586 * delta_B0[idx];
            double delta_omega = delta_omega_grad + delta_omega_B0;

            double phi = delta_omega * dt;

            double cos_phi = cos(phi);
            double sin_phi = sin(phi);

            double mx = Mx[idx];
            double my = My[idx];

            Mx[idx] = mx * cos_phi - my * sin_phi;
            My[idx] = mx * sin_phi + my * cos_phi;
        }

        __global__ void reset_magnetization_kernel(
            double *Mx, double *My, double *Mz,
            double *M0, int n)
        {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            if (idx >= n) return;

            Mx[idx] = 0.0;
            My[idx] = 0.0;
            Mz[idx] = M0[idx];
        }

        __global__ void find_min_T2_kernel(
            double *T2, double *min_val, int n)
        {
            __shared__ double shared_min[256];

            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            int tid = threadIdx.x;

            shared_min[tid] = 1e20;

            for (int i = idx; i < n; i += gridDim.x * blockDim.x) {
                double t2 = T2[i];
                if (t2 > 1e-10) {
                    shared_min[tid] = min(shared_min[tid], t2);
                }
            }
            __syncthreads();

            for (int s = 128; s > 0; s >>= 1) {
                if (tid < s) {
                    shared_min[tid] = min(shared_min[tid], shared_min[tid + s]);
                }
                __syncthreads();
            }

            if (tid == 0) {
                min_val[blockIdx.x] = shared_min[0];
            }
        }

        __global__ void find_max_abs_kernel(
            double *data, double *result, int n)
        {
            __shared__ double shared_max[256];

            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            int tid = threadIdx.x;

            shared_max[tid] = 0.0;

            for (int i = idx; i < n; i += gridDim.x * blockDim.x) {
                double val = fabs(data[i]);
                shared_max[tid] = max(shared_max[tid], val);
            }
            __syncthreads();

            for (int s = 128; s > 0; s >>= 1) {
                if (tid < s) {
                    shared_max[tid] = max(shared_max[tid], shared_max[tid + s]);
                }
                __syncthreads();
            }

            if (tid == 0) {
                result[blockIdx.x] = shared_max[0];
            }
        }

        __global__ void sum_signal_kernel(
            double *Mx, double *My, double *result_real, double *result_imag, int n)
        {
            __shared__ double sum_real[256];
            __shared__ double sum_imag[256];

            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            int tid = threadIdx.x;

            sum_real[tid] = 0.0;
            sum_imag[tid] = 0.0;

            for (int i = idx; i < n; i += gridDim.x * blockDim.x) {
                sum_real[tid] += Mx[i];
                sum_imag[tid] += My[i];
            }
            __syncthreads();

            for (int s = 128; s > 0; s >>= 1) {
                if (tid < s) {
                    sum_real[tid] += sum_real[tid + s];
                    sum_imag[tid] += sum_imag[tid + s];
                }
                __syncthreads();
            }

            if (tid == 0) {
                result_real[blockIdx.x] = sum_real[0];
                result_imag[blockIdx.x] = sum_imag[0];
            }
        }

        __global__ void acquire_kspace_point_kernel(
            double *Mx, double *My, double *kspace,
            int kx_idx, int n_voxels)
        {
            __shared__ double sum_real[256];
            __shared__ double sum_imag[256];

            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            int tid = threadIdx.x;

            sum_real[tid] = 0.0;
            sum_imag[tid] = 0.0;

            for (int i = idx; i < n_voxels; i += gridDim.x * blockDim.x) {
                sum_real[tid] += Mx[i];
                sum_imag[tid] += My[i];
            }
            __syncthreads();

            for (int s = 128; s > 0; s >>= 1) {
                if (tid < s) {
                    sum_real[tid] += sum_real[tid + s];
                    sum_imag[tid] += sum_imag[tid + s];
                }
                __syncthreads();
            }

            if (tid == 0) {
                kspace[kx_idx * 2] = sum_real[0];
                kspace[kx_idx * 2 + 1] = sum_imag[0];
            }
        }
        """

        mod = SourceModule(kernel_code)
        self._excitation_kernel = mod.get_function("apply_excitation_kernel")
        self._relax_single_step_kernel = mod.get_function("relax_single_step_kernel")
        self._precess_single_step_kernel = mod.get_function("precess_single_step_kernel")
        self._reset_magnetization_kernel = mod.get_function("reset_magnetization_kernel")
        self._find_min_T2_kernel = mod.get_function("find_min_T2_kernel")
        self._find_max_abs_kernel = mod.get_function("find_max_abs_kernel")
        self._sum_signal_kernel = mod.get_function("sum_signal_kernel")
        self._acquire_kspace_point_kernel = mod.get_function("acquire_kspace_point_kernel")

        self._block_size = 256
        self._grid_size = min(64, (self.n_voxels + self._block_size - 1) // self._block_size)

    def set_field_inhomogeneity(self, delta_B0=None, B1_correction=None):
        """
        Set B0/B1 field inhomogeneity parameters (GPU version)

        Parameters:
            delta_B0: B0 field inhomogeneity (Hz), shape (n_voxels,)
            B1_correction: B1 field correction factor, shape (n_voxels,), range 0.5-1.5
        """
        if delta_B0 is not None:
            delta_B0 = delta_B0.astype(np.float64)
            cuda.memcpy_htod(self._delta_B0, delta_B0)

        if B1_correction is not None:
            B1_correction = B1_correction.astype(np.float64)
            cuda.memcpy_htod(self._B1_correction, B1_correction)

        self._update_adaptive_dt()

    def _get_max_delta_B0_gpu(self):
        """Compute maximum absolute B0 inhomogeneity on GPU"""
        max_val_gpu = cuda.mem_alloc(self._grid_size * 8)
        max_val_h = np.empty(self._grid_size, dtype=np.float64)

        self._find_max_abs_kernel(
            self._delta_B0, max_val_gpu, np.int32(self.n_voxels),
            block=(self._block_size, 1, 1),
            grid=(self._grid_size, 1)
        )

        cuda.memcpy_dtoh(max_val_h, max_val_gpu)
        result = np.max(max_val_h)

        max_val_gpu.free()
        return result

    def _update_adaptive_dt(self):
        """Compute shortest T2 on GPU and update adaptive time step"""
        eps = 1e-10
        min_val_gpu = cuda.mem_alloc(self._grid_size * 8)
        min_val_h = np.empty(self._grid_size, dtype=np.float64)

        self._find_min_T2_kernel(
            self._T2, min_val_gpu, np.int32(self.n_voxels),
            block=(self._block_size, 1, 1),
            grid=(self._grid_size, 1)
        )

        cuda.memcpy_dtoh(min_val_h, min_val_gpu)
        valid_min = min_val_h[min_val_h < 1e20]
        if len(valid_min) > 0:
            self._min_T2 = np.min(valid_min)
            dt_T2 = self._min_T2 / 10.0
        else:
            self._min_T2 = 1.0
            dt_T2 = 0.1

        min_val_gpu.free()

        self._max_delta_B0 = self._get_max_delta_B0_gpu()
        if self._max_delta_B0 > eps:
            dt_B0 = 1.0 / (10.0 * self._max_delta_B0)
            self._adaptive_dt = min(dt_T2, dt_B0)
        else:
            self._adaptive_dt = dt_T2

    def get_adaptive_dt(self):
        """Get adaptive time step"""
        return self._adaptive_dt

    def set_params(self, pd, t1, t2):
        """
        Set tissue parameters for each voxel

        Parameters:
            pd: proton density array
            t1: T1 relaxation time array (seconds)
            t2: T2 relaxation time array (seconds)
        """
        pd = pd.astype(np.float64)
        t1 = t1.astype(np.float64)
        t2 = t2.astype(np.float64)
        delta_B0_h = np.zeros_like(pd)
        B1_correction_h = np.ones_like(pd)

        cuda.memcpy_htod(self._M0, pd)
        cuda.memcpy_htod(self._T1, t1)
        cuda.memcpy_htod(self._T2, t2)
        cuda.memcpy_htod(self._delta_B0, delta_B0_h)
        cuda.memcpy_htod(self._B1_correction, B1_correction_h)

        self._update_adaptive_dt()
        self.reset_magnetization()

    def set_positions(self, x, y):
        """
        Set voxel spatial coordinates (for gradient precession computation)

        Parameters:
            x, y: voxel coordinate arrays (meters)
        """
        x = x.astype(np.float64)
        y = y.astype(np.float64)

        cuda.memcpy_htod(self._x, x)
        cuda.memcpy_htod(self._y, y)

    def reset_magnetization(self):
        """Reset magnetization to equilibrium state (GPU direct execution, no CPU-GPU transfer)"""
        self._reset_magnetization_kernel(
            self._Mx, self._My, self._Mz, self._M0,
            np.int32(self.n_voxels),
            block=(self._block_size, 1, 1),
            grid=(self._grid_size, 1)
        )

    def apply_excitation(self, flip_angle, phase=0.0):
        """
        Apply excitation pulse with arbitrary flip angle (considering B1 inhomogeneity)

        Parameters:
            flip_angle: nominal flip angle (radians)
            phase: pulse phase (radians)
        """
        self._excitation_kernel(
            self._Mx, self._My, self._Mz,
            self._B1_correction,
            np.float64(flip_angle), np.float64(phase),
            np.int32(self.n_voxels),
            block=(self._block_size, 1, 1),
            grid=(self._grid_size, 1)
        )

    def relax(self, duration):
        """
        Evolution considering relaxation (adaptive step)

        Parameters:
            duration: total evolution time (seconds)
        """
        dt = self._adaptive_dt
        remaining = duration

        while remaining > 1e-12:
            step = min(dt, remaining)
            self._relax_single_step_kernel(
                self._Mx, self._My, self._Mz,
                self._M0, self._T1, self._T2,
                np.float64(step), np.int32(self.n_voxels),
                block=(self._block_size, 1, 1),
                grid=(self._grid_size, 1)
            )
            remaining -= step

    def precess(self, duration, gx, gy):
        """
        Free precession considering gradient fields (adaptive step, considering B0 inhomogeneity)

        Parameters:
            duration: total precession time (seconds)
            gx: gradient in x direction (T/m)
            gy: gradient in y direction (T/m)
        """
        dt = self._adaptive_dt
        remaining = duration

        while remaining > 1e-12:
            step = min(dt, remaining)
            self._precess_single_step_kernel(
                self._Mx, self._My, self._Mz,
                self._x, self._y, self._delta_B0,
                np.float64(step), np.float64(gx), np.float64(gy),
                np.float64(self.gamma), np.int32(self.n_voxels),
                block=(self._block_size, 1, 1),
                grid=(self._grid_size, 1)
            )
            remaining -= step

    def evolve(self, duration, gx=0.0, gy=0.0):
        """
        Evolution considering both relaxation and precession (adaptive step)

        Parameters:
            duration: total evolution time (seconds)
            gx: gradient in x direction (T/m)
            gy: gradient in y direction (T/m)
        """
        dt = self._adaptive_dt
        remaining = duration

        while remaining > 1e-12:
            step = min(dt, remaining)

            self._relax_single_step_kernel(
                self._Mx, self._My, self._Mz,
                self._M0, self._T1, self._T2,
                np.float64(step), np.int32(self.n_voxels),
                block=(self._block_size, 1, 1),
                grid=(self._grid_size, 1)
            )

            if gx != 0.0 or gy != 0.0:
                self._precess_single_step_kernel(
                    self._Mx, self._My, self._Mz,
                    self._x, self._y, self._delta_B0,
                    np.float64(step), np.float64(gx), np.float64(gy),
                    np.float64(self.gamma), np.int32(self.n_voxels),
                    block=(self._block_size, 1, 1),
                    grid=(self._grid_size, 1)
                )

            remaining -= step

    def get_signal(self):
        """
        Get current MR signal (complex sum of transverse magnetization)

        Returns:
            Complex signal sum (S = Mx + iMy)
        """
        result_real = cuda.mem_alloc(self._grid_size * 8)
        result_imag = cuda.mem_alloc(self._grid_size * 8)

        self._sum_signal_kernel(
            self._Mx, self._My, result_real, result_imag,
            np.int32(self.n_voxels),
            block=(self._block_size, 1, 1),
            grid=(self._grid_size, 1)
        )

        real_h = np.empty(self._grid_size, dtype=np.float64)
        imag_h = np.empty(self._grid_size, dtype=np.float64)

        cuda.memcpy_dtoh(real_h, result_real)
        cuda.memcpy_dtoh(imag_h, result_imag)

        result = np.sum(real_h) + 1j * np.sum(imag_h)

        result_real.free()
        result_imag.free()

        return result

    def acquire_kspace_line(self, Nx, dwell_time, gx_amp):
        """
        Acquire an entire K-space line directly on GPU

        Parameters:
            Nx: number of sampling points in x direction
            dwell_time: sampling interval (seconds)
            gx_amp: readout gradient amplitude in x direction (T/m)

        Returns:
            K-space line data (Nx,)
        """
        required_size = Nx * 16
        if self._kspace_line is None or required_size > self._kspace_line_size:
            if self._kspace_line is not None:
                self._kspace_line.free()
            self._kspace_line = cuda.mem_alloc(max(required_size, 4096 * 16))
            self._kspace_line_size = max(required_size, 4096 * 16)

        kspace_h = np.zeros(Nx * 2, dtype=np.float64)

        for kx_idx in range(Nx):
            if kx_idx > 0:
                self.evolve(dwell_time, gx_amp, 0.0)

            self._acquire_kspace_point_kernel(
                self._Mx, self._My, self._kspace_line,
                np.int32(kx_idx), np.int32(self.n_voxels),
                block=(self._block_size, 1, 1),
                grid=(self._grid_size, 1)
            )

        cuda.memcpy_dtoh(kspace_h, self._kspace_line)

        kspace_complex = kspace_h[0::2] + 1j * kspace_h[1::2]
        return kspace_complex[:Nx]

    def get_magnetization(self):
        """
        Get magnetization data from GPU

        Returns:
            (Mx, My, Mz) arrays
        """
        Mx_h = np.empty(self.n_voxels, dtype=np.float64)
        My_h = np.empty(self.n_voxels, dtype=np.float64)
        Mz_h = np.empty(self.n_voxels, dtype=np.float64)

        cuda.memcpy_dtoh(Mx_h, self._Mx)
        cuda.memcpy_dtoh(My_h, self._My)
        cuda.memcpy_dtoh(Mz_h, self._Mz)

        return Mx_h, My_h, Mz_h

    def __del__(self):
        """Release GPU memory"""
        if hasattr(self, '_Mx'):
            self._Mx.free()
            self._My.free()
            self._Mz.free()
            self._M0.free()
            self._T1.free()
            self._T2.free()
            self._x.free()
            self._y.free()
            if hasattr(self, '_delta_B0'):
                self._delta_B0.free()
            if hasattr(self, '_B1_correction'):
                self._B1_correction.free()
            if hasattr(self, '_kspace_line') and self._kspace_line is not None:
                self._kspace_line.free()
