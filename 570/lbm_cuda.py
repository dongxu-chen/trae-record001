import numpy as np
try:
    import pycuda.autoinit
    import pycuda.driver as cuda
    from pycuda.compiler import SourceModule
    from pycuda import gpuarray
    CUDA_AVAILABLE = True
except ImportError:
    CUDA_AVAILABLE = False

from fluid_simulator import FluidSimulator


class LBM_CUDA(FluidSimulator):
    def __init__(self, width=512, height=512, tau=0.6):
        if not CUDA_AVAILABLE:
            raise ImportError("PyCUDA is not available")
        
        super().__init__(width, height, tau)
        
        self.opposite = [8, 7, 6, 5, 4, 3, 2, 1, 0]
        self.use_mrt = True
        
        self._compile_kernels()
    
    def _compile_kernels(self):
        kernel_code = """
        __device__ __constant__ float M_d[9][9] = {
            {1, 1, 1, 1, 1, 1, 1, 1, 1},
            {-4, -1, -1, -1, -1, 2, 2, 2, 2},
            {4, -2, -2, -2, -2, 1, 1, 1, 1},
            {0, 1, 0, -1, 0, 1, -1, -1, 1},
            {0, -2, 0, 2, 0, 1, -1, -1, 1},
            {0, 0, 1, 0, -1, 1, 1, -1, -1},
            {0, 0, -2, 0, 2, 1, 1, -1, -1},
            {0, 1, -1, 1, -1, 0, 0, 0, 0},
            {0, 0, 0, 0, 0, 1, -1, 1, -1}
        };
        
        __device__ __constant__ float M_inv_d[9][9] = {
            {1.0f/9, -4.0f/9, 4.0f/9, 0, 0, 0, 0, 0, 0},
            {1.0f/9, -1.0f/9, -2.0f/9, 1.0f/6, -1.0f/3, 0, 0, 0.5f, 0},
            {1.0f/9, -1.0f/9, -2.0f/9, 0, 0, 1.0f/6, -1.0f/3, -0.5f, 0},
            {1.0f/9, -1.0f/9, -2.0f/9, -1.0f/6, 1.0f/3, 0, 0, 0.5f, 0},
            {1.0f/9, -1.0f/9, -2.0f/9, 0, 0, 0, 0, 0, 0},
            {1.0f/9, 2.0f/9, 1.0f/9, 1.0f/6, 1.0f/6, 1.0f/6, 1.0f/6, 0, 0.5f},
            {1.0f/9, 2.0f/9, 1.0f/9, -1.0f/6, -1.0f/6, 1.0f/6, 1.0f/6, 0, -0.5f},
            {1.0f/9, 2.0f/9, 1.0f/9, -1.0f/6, -1.0f/6, -1.0f/6, -1.0f/6, 0, 0.5f},
            {1.0f/9, 2.0f/9, 1.0f/9, 1.0f/6, 1.0f/6, -1.0f/6, -1.0f/6, 0, -0.5f}
        };
        
        __global__ void compute_macroscopic(float *f, float *rho, float *u, bool *obstacles,
                                           int *cx, int *cy, int width, int height,
                                           float min_rho, float max_rho, float max_vel) {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            int total = width * height;
            
            if (idx < total) {
                float r = 0.0f;
                float ux = 0.0f;
                float uy = 0.0f;
                
                for (int i = 0; i < 9; i++) {
                    float fi = f[idx * 9 + i];
                    r += fi;
                    ux += fi * (float)cx[i];
                    uy += fi * (float)cy[i];
                }
                
                r = max(min_rho, min(max_rho, r));
                rho[idx] = r;
                
                if (obstacles[idx]) {
                    u[idx * 2] = 0.0f;
                    u[idx * 2 + 1] = 0.0f;
                } else {
                    float vel_x = ux / r;
                    float vel_y = uy / r;
                    float vel_mag = sqrt(vel_x * vel_x + vel_y * vel_y);
                    
                    if (vel_mag > max_vel) {
                        float scale = max_vel / (vel_mag + 1e-10f);
                        vel_x *= scale;
                        vel_y *= scale;
                    }
                    
                    u[idx * 2] = vel_x;
                    u[idx * 2 + 1] = vel_y;
                }
            }
        }
        
        __global__ void mrt_collision(float *f, float *rho, float *u, bool *obstacles,
                                     float tau, int width, int height) {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            int total = width * height;
            
            if (idx < total && !obstacles[idx]) {
                float f_local[9];
                float m[9];
                float m_eq[9];
                
                for (int i = 0; i < 9; i++) {
                    f_local[i] = f[idx * 9 + i];
                }
                
                for (int i = 0; i < 9; i++) {
                    m[i] = 0.0f;
                    for (int j = 0; j < 9; j++) {
                        m[i] += M_d[i][j] * f_local[j];
                    }
                }
                
                float r = rho[idx];
                float ux = u[idx * 2];
                float uy = u[idx * 2 + 1];
                float u_sq = ux * ux + uy * uy;
                
                m_eq[0] = r;
                m_eq[1] = r * (-2.0f + 3.0f * u_sq);
                m_eq[2] = r * (1.0f - 3.0f * u_sq);
                m_eq[3] = r * ux;
                m_eq[4] = r * (-ux);
                m_eq[5] = r * uy;
                m_eq[6] = r * (-uy);
                m_eq[7] = r * (ux * ux - uy * uy);
                m_eq[8] = r * ux * uy;
                
                float omega = 1.0f / max(tau, 0.51f);
                float S_d[9] = {0, omega, omega, 0, omega, 0, omega, omega, omega};
                
                for (int i = 0; i < 9; i++) {
                    m[i] = m[i] - S_d[i] * (m[i] - m_eq[i]);
                }
                
                for (int i = 0; i < 9; i++) {
                    f_local[i] = 0.0f;
                    for (int j = 0; j < 9; j++) {
                        f_local[i] += M_inv_d[i][j] * m[j];
                    }
                }
                
                for (int i = 0; i < 9; i++) {
                    f[idx * 9 + i] = max(1e-6f, min(1e6f, f_local[i]));
                }
            }
        }
        
        __global__ void bgk_collision(float *f, float *rho, float *u, float *w, int *cx, int *cy,
                                     float tau, int width, int height) {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            int total = width * height;
            
            if (idx < total) {
                float r = rho[idx];
                float ux = u[idx * 2];
                float uy = u[idx * 2 + 1];
                float u_sq = ux * ux + uy * uy;
                
                for (int i = 0; i < 9; i++) {
                    float cxi = (float)cx[i];
                    float cyi = (float)cy[i];
                    float cu = cxi * ux + cyi * uy;
                    float feq = w[i] * r * (1.0f + 3.0f * cu + 4.5f * cu * cu - 1.5f * u_sq);
                    
                    float omega = 1.0f / max(tau, 0.51f);
                    float fi = f[idx * 9 + i] - omega * (f[idx * 9 + i] - feq);
                    f[idx * 9 + i] = max(1e-6f, min(1e6f, fi));
                }
            }
        }
        
        __global__ void streaming(float *f, float *f_tmp, int *cx, int *cy, int width, int height) {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            int total = width * height;
            
            if (idx < total) {
                int x = idx % width;
                int y = idx / width;
                
                for (int i = 0; i < 9; i++) {
                    int x_prev = x - cx[i];
                    int y_prev = y - cy[i];
                    
                    if (x_prev >= 0 && x_prev < width && y_prev >= 0 && y_prev < height) {
                        int prev_idx = (y_prev * width + x_prev) * 9 + i;
                        f_tmp[idx * 9 + i] = f[prev_idx];
                    }
                }
            }
        }
        
        __global__ void subgrid_bounce_back(float *f, bool *obstacles, float *fraction,
                                           int *cx, int *cy, int width, int height) {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            int total = width * height;
            
            if (idx < total) {
                float delta = fraction[idx];
                
                if (delta >= 1.0f) {
                    float tmp[9];
                    for (int i = 0; i < 9; i++) {
                        tmp[i] = f[idx * 9 + i];
                    }
                    for (int i = 0; i < 9; i++) {
                        f[idx * 9 + i] = tmp[8 - i];
                    }
                } else if (delta > 0.0f) {
                    float tmp[9];
                    for (int i = 0; i < 9; i++) {
                        tmp[i] = f[idx * 9 + i];
                    }
                    for (int i = 0; i < 9; i++) {
                        f[idx * 9 + i] = (1.0f - delta) * tmp[i] + delta * tmp[8 - i];
                    }
                }
            }
        }
        
        __global__ void apply_inflow(float *f, float *rho, float *u, float u_in, float v_in,
                                    float *w, int *cx, int *cy, int width, int height) {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            
            if (idx < height) {
                int y = idx;
                float u_sq = u_in * u_in + v_in * v_in;
                
                for (int i = 0; i < 9; i++) {
                    float cxi = (float)cx[i];
                    float cyi = (float)cy[i];
                    float cu = cxi * u_in + cyi * v_in;
                    float feq = w[i] * 1.0f * (1.0f + 3.0f * cu + 4.5f * cu * cu - 1.5f * u_sq);
                    f[(y * width + 0) * 9 + i] = feq;
                }
                
                rho[y * width + 0] = 1.0f;
                u[(y * width + 0) * 2] = u_in;
                u[(y * width + 0) * 2 + 1] = v_in;
            }
        }
        
        __global__ void apply_wall_boundaries(float *f, int width, int height) {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            
            if (idx < width) {
                int x = idx;
                
                float tmp0 = f[(0 * width + x) * 9 + 0];
                float tmp1 = f[(0 * width + x) * 9 + 1];
                float tmp2 = f[(0 * width + x) * 9 + 2];
                f[(0 * width + x) * 9 + 0] = f[(0 * width + x) * 9 + 6];
                f[(0 * width + x) * 9 + 1] = f[(0 * width + x) * 9 + 7];
                f[(0 * width + x) * 9 + 2] = f[(0 * width + x) * 9 + 8];
                f[(0 * width + x) * 9 + 6] = tmp0;
                f[(0 * width + x) * 9 + 7] = tmp1;
                f[(0 * width + x) * 9 + 8] = tmp2;
                
                int y2 = height - 1;
                tmp0 = f[(y2 * width + x) * 9 + 6];
                tmp1 = f[(y2 * width + x) * 9 + 7];
                tmp2 = f[(y2 * width + x) * 9 + 8];
                f[(y2 * width + x) * 9 + 6] = f[(y2 * width + x) * 9 + 0];
                f[(y2 * width + x) * 9 + 7] = f[(y2 * width + x) * 9 + 1];
                f[(y2 * width + x) * 9 + 8] = f[(y2 * width + x) * 9 + 2];
                f[(y2 * width + x) * 9 + 0] = tmp0;
                f[(y2 * width + x) * 9 + 1] = tmp1;
                f[(y2 * width + x) * 9 + 2] = tmp2;
            }
        }
        """
        
        mod = SourceModule(kernel_code)
        self.kernel_macro = mod.get_function("compute_macroscopic")
        self.kernel_mrt = mod.get_function("mrt_collision")
        self.kernel_bgk = mod.get_function("bgk_collision")
        self.kernel_str = mod.get_function("streaming")
        self.kernel_bb = mod.get_function("subgrid_bounce_back")
        self.kernel_inflow = mod.get_function("apply_inflow")
        self.kernel_walls = mod.get_function("apply_wall_boundaries")
        
        self.block_size = 256
        self.grid_size = (self.width * self.height + self.block_size - 1) // self.block_size
        self.grid_size_w = (self.width + self.block_size - 1) // self.block_size
        self.grid_size_h = (self.height + self.block_size - 1) // self.block_size
    
    def initialize(self):
        self.f = gpuarray.to_gpu(np.ones((self.height, self.width, 9), dtype=np.float32) * self.rho0 / 9.0)
        self.f_eq = gpuarray.empty_like(self.f)
        self.f_tmp = gpuarray.empty_like(self.f)
        
        self.rho_gpu = gpuarray.to_gpu(np.ones((self.height, self.width), dtype=np.float32))
        self.u_gpu = gpuarray.to_gpu(np.zeros((self.height, self.width, 2), dtype=np.float32))
        self.obstacles_gpu = gpuarray.to_gpu(self.obstacles.astype(np.bool_))
        self.fraction_gpu = gpuarray.to_gpu(self.obstacle_fraction.astype(np.float32))
        
        self.w_gpu = gpuarray.to_gpu(self.w.astype(np.float32))
        self.cx_gpu = gpuarray.to_gpu(self.cx.astype(np.int32))
        self.cy_gpu = gpuarray.to_gpu(self.cy.astype(np.int32))
        
        self.u_in = 0.1
        self.v_in = 0.0
    
    def _update_obstacles(self):
        if hasattr(self, 'obstacles_gpu'):
            self.obstacles_gpu.set(self.obstacles.astype(np.bool_))
            self.fraction_gpu.set(self.obstacle_fraction.astype(np.float32))
    
    def step(self):
        self.lock()
        try:
            self.kernel_macro(self.f, self.rho_gpu, self.u_gpu, self.obstacles_gpu,
                             self.cx_gpu, self.cy_gpu,
                             np.int32(self.width), np.int32(self.height),
                             np.float32(self.min_density), np.float32(self.max_density),
                             np.float32(self.max_velocity),
                             block=(self.block_size, 1, 1), grid=(self.grid_size, 1))
            
            self.kernel_inflow(self.f, self.rho_gpu, self.u_gpu,
                              np.float32(self.u_in), np.float32(self.v_in),
                              self.w_gpu, self.cx_gpu, self.cy_gpu,
                              np.int32(self.width), np.int32(self.height),
                              block=(self.block_size, 1, 1), grid=(self.grid_size_h, 1))
            
            if self.use_mrt:
                self.kernel_mrt(self.f, self.rho_gpu, self.u_gpu, self.obstacles_gpu,
                               np.float32(self.tau),
                               np.int32(self.width), np.int32(self.height),
                               block=(self.block_size, 1, 1), grid=(self.grid_size, 1))
            else:
                self.kernel_bgk(self.f, self.rho_gpu, self.u_gpu, self.w_gpu,
                               self.cx_gpu, self.cy_gpu,
                               np.float32(self.tau),
                               np.int32(self.width), np.int32(self.height),
                               block=(self.block_size, 1, 1), grid=(self.grid_size, 1))
            
            self.kernel_str(self.f, self.f_tmp, self.cx_gpu, self.cy_gpu,
                           np.int32(self.width), np.int32(self.height),
                           block=(self.block_size, 1, 1), grid=(self.grid_size, 1))
            
            self.f, self.f_tmp = self.f_tmp, self.f
            
            if self.enable_subgrid:
                self.kernel_bb(self.f, self.obstacles_gpu, self.fraction_gpu,
                              self.cx_gpu, self.cy_gpu,
                              np.int32(self.width), np.int32(self.height),
                              block=(self.block_size, 1, 1), grid=(self.grid_size, 1))
            else:
                solid_fraction = gpuarray.to_gpu(self.obstacles.astype(np.float32))
                self.kernel_bb(self.f, self.obstacles_gpu, solid_fraction,
                              self.cx_gpu, self.cy_gpu,
                              np.int32(self.width), np.int32(self.height),
                              block=(self.block_size, 1, 1), grid=(self.grid_size, 1))
            
            self.kernel_walls(self.f, np.int32(self.width), np.int32(self.height),
                             block=(self.block_size, 1, 1), grid=(self.grid_size_w, 1))
        finally:
            self.unlock()
    
    def get_velocity(self):
        self.lock()
        try:
            return self.u_gpu.get()
        finally:
            self.unlock()
    
    def get_pressure(self):
        self.lock()
        try:
            return self.rho_gpu.get() / 3.0
        finally:
            self.unlock()
    
    def get_vorticity(self):
        self.lock()
        try:
            u = self.u_gpu.get()
            ux = u[:, :, 0]
            uy = u[:, :, 1]
            vorticity = np.gradient(uy, axis=1) - np.gradient(ux, axis=0)
            return vorticity
        finally:
            self.unlock()
    
    def set_inflow_velocity(self, ux, uy):
        self.u_in = ux
        self.v_in = uy
