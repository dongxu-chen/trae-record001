import numpy as np


class GPUAccelerator:
    def __init__(self, block_size=256, tile_size=16):
        self._cupy = None
        self._available = False
        self.block_size = block_size
        self.tile_size = tile_size
        self._kernels = {}
        self._init_cupy()
        if self._available:
            self._compile_kernels()

    def _init_cupy(self):
        try:
            import cupy as cp
            self._cupy = cp
            device_count = cp.cuda.runtime.getDeviceCount()
            if device_count > 0:
                self._available = True
                props = cp.cuda.runtime.getDeviceProperties(0)
                self._device_name = props["name"].decode() if isinstance(props["name"], bytes) else props["name"]
                self._max_shared_memory = props["sharedMemPerBlock"]
                self._max_threads_per_block = props["maxThreadsPerBlock"]
            else:
                self._available = False
        except (ImportError, Exception):
            self._available = False
            self._cupy = None

    def _compile_kernels(self):
        cp = self._cupy

        histogram_kernel = cp.RawKernel(r"""
            extern "C" __global__
            void compute_histogram_block(
                const float* __restrict__ fixed,
                const float* __restrict__ moving,
                const int64_t n,
                const float fmin, const float fmax,
                const float mmin, const float mmax,
                const int32_t num_bins,
                int32_t* __restrict__ block_histograms,
                const int32_t num_blocks)
            {
                const int32_t tid = threadIdx.x;
                const int32_t bid = blockIdx.x;
                const int32_t block_size = blockDim.x;
                const int32_t hist_size = num_bins * num_bins;

                extern __shared__ int32_t sh_hist[];
                for (int32_t i = tid; i < hist_size; i += block_size) {
                    sh_hist[i] = 0;
                }
                __syncthreads();

                const int64_t start = bid * block_size + tid;
                const int64_t step = block_size * num_blocks;

                const float f_range_inv = rcp(fmax - fmin + 1e-10f);
                const float m_range_inv = rcp(mmax - mmin + 1e-10f);
                const float nb = (float)(num_bins - 1);

                for (int64_t i = start; i < n; i += step) {
                    float f = fixed[i];
                    float m = moving[i];

                    if (!isnan(f) && !isnan(m) && !isinf(f) && !isinf(m)) {
                        int32_t fi = (int32_t)floorf((f - fmin) * f_range_inv * nb);
                        int32_t mi = (int32_t)floorf((m - mmin) * m_range_inv * nb);

                        fi = max(0, min(num_bins - 1, fi));
                        mi = max(0, min(num_bins - 1, mi));

                        int32_t idx = fi * num_bins + mi;
                        atomicAdd(&sh_hist[idx], 1);
                    }
                }
                __syncthreads();

                for (int32_t i = tid; i < hist_size; i += block_size) {
                    block_histograms[bid * hist_size + i] = sh_hist[i];
                }
            }
        """, "compute_histogram_block")

        reduce_kernel = cp.RawKernel(r"""
            extern "C" __global__
            void reduce_histograms(
                const int32_t* __restrict__ block_histograms,
                const int32_t num_blocks,
                const int32_t hist_size,
                int32_t* __restrict__ final_histogram)
            {
                const int32_t tid = threadIdx.x;
                const int32_t block_size = blockDim.x;

                extern __shared__ int32_t sh_reduce[];

                for (int32_t i = tid; i < hist_size; i += block_size) {
                    int32_t sum = 0;
                    for (int32_t b = 0; b < num_blocks; b++) {
                        sum += block_histograms[b * hist_size + i];
                    }
                    sh_reduce[i] = sum;
                }
                __syncthreads();

                for (int32_t i = tid; i < hist_size; i += block_size) {
                    final_histogram[i] = sh_reduce[i];
                }
            }
        """, "reduce_histograms")

        resample_2d_kernel = cp.RawKernel(r"""
            extern "C" __global__
            void resample_image_2d(
                const float* __restrict__ image,
                const int32_t in_rows, const int32_t in_cols,
                const int32_t out_rows, const int32_t out_cols,
                const float* __restrict__ inv_matrix,
                float* __restrict__ output)
            {
                const int32_t col = blockIdx.x * blockDim.x + threadIdx.x;
                const int32_t row = blockIdx.y * blockDim.y + threadIdx.y;

                if (row < out_rows && col < out_cols) {
                    const float ox = (float)row + 0.5f;
                    const float oy = (float)col + 0.5f;

                    const float m00 = inv_matrix[0];
                    const float m01 = inv_matrix[1];
                    const float m02 = inv_matrix[2];
                    const float m10 = inv_matrix[3];
                    const float m11 = inv_matrix[4];
                    const float m12 = inv_matrix[5];

                    float sx = m00 * ox + m01 * oy + m02 - 0.5f;
                    float sy = m10 * ox + m11 * oy + m12 - 0.5f;

                    float val = 0.0f;
                    if (sx >= 0.0f && sx < in_rows - 1.0f &&
                        sy >= 0.0f && sy < in_cols - 1.0f) {

                        int32_t x0 = (int32_t)floorf(sx);
                        int32_t y0 = (int32_t)floorf(sy);
                        int32_t x1 = x0 + 1;
                        int32_t y1 = y0 + 1;

                        float fx = sx - x0;
                        float fy = sy - y0;

                        int32_t idx00 = x0 * in_cols + y0;
                        int32_t idx01 = x0 * in_cols + y1;
                        int32_t idx10 = x1 * in_cols + y0;
                        int32_t idx11 = x1 * in_cols + y1;

                        float v00 = image[idx00];
                        float v01 = image[idx01];
                        float v10 = image[idx10];
                        float v11 = image[idx11];

                        float v0 = v00 * (1 - fx) + v10 * fx;
                        float v1 = v01 * (1 - fx) + v11 * fx;
                        val = v0 * (1 - fy) + v1 * fy;
                    }

                    output[row * out_cols + col] = val;
                }
            }
        """, "resample_image_2d")

        self._kernels["histogram_block"] = histogram_kernel
        self._kernels["reduce_histograms"] = reduce_kernel
        self._kernels["resample_2d"] = resample_2d_kernel

    @property
    def available(self):
        return self._available

    @property
    def device_name(self):
        if self._available:
            return self._device_name
        return "No GPU available"

    def to_gpu(self, array):
        if not self._available:
            return array
        return self._cupy.asarray(array)

    def to_cpu(self, array):
        if not self._available:
            return array
        if isinstance(array, self._cupy.ndarray):
            return self._cupy.asnumpy(array)
        return np.asarray(array)

    def compute_mutual_information_gpu(self, fixed, moving, num_bins=64):
        if not self._available:
            return self._compute_mutual_information_fallback(fixed, moving, num_bins)

        cp = self._cupy
        try:
            fixed_flat = cp.asarray(fixed.ravel(), dtype=cp.float32)
            moving_flat = cp.asarray(moving.ravel(), dtype=cp.float32)

            n = int(fixed_flat.shape[0])

            fmin = float(fixed_flat.min())
            fmax = float(fixed_flat.max())
            mmin = float(moving_flat.min())
            mmax = float(moving_flat.max())

            if abs(fmax - fmin) < 1e-10 or abs(mmax - mmin) < 1e-10:
                return 0.0

            num_blocks = min(64, max(8, (n + self.block_size - 1) // self.block_size))
            hist_size = num_bins * num_bins

            block_histograms = cp.zeros((num_blocks, hist_size), dtype=cp.int32)
            final_histogram = cp.zeros(hist_size, dtype=cp.int32)

            sh_mem_size = hist_size * 4
            sh_mem_reduce = hist_size * 4

            kernel = self._kernels["histogram_block"]
            kernel(
                (num_blocks,), (self.block_size,),
                (fixed_flat, moving_flat, n, fmin, fmax, mmin, mmax, num_bins, block_histograms, num_blocks),
                shared_mem=sh_mem_size
            )

            reduce_kernel = self._kernels["reduce_histograms"]
            reduce_block = min(self.block_size, hist_size)
            reduce_kernel(
                (1,), (reduce_block,),
                (block_histograms, num_blocks, hist_size, final_histogram),
                shared_mem=sh_mem_reduce
            )

            hist_2d = final_histogram.reshape(num_bins, num_bins)
            total = hist_2d.sum()
            if total <= 0:
                return 0.0

            pxy = hist_2d.astype(cp.float64) / total
            px = pxy.sum(axis=1)
            py = pxy.sum(axis=0)
            px_py = px[:, cp.newaxis] * py[cp.newaxis, :]

            nonzero = pxy > 0
            mi = float(cp.sum(pxy[nonzero] * cp.log(pxy[nonzero] / px_py[nonzero])))
            return mi

        except Exception as e:
            print(f"[GPU Error] MI computation failed: {e}, falling back to CPU")
            return self._compute_mutual_information_fallback(fixed, moving, num_bins)

    def _compute_mutual_information_fallback(self, fixed, moving, num_bins):
        fixed_flat = fixed.ravel()
        moving_flat = moving.ravel()
        mask = np.isfinite(fixed_flat) & np.isfinite(moving_flat)
        fixed_flat = fixed_flat[mask]
        moving_flat = moving_flat[mask]

        if len(fixed_flat) == 0:
            return 0.0

        hist_2d, _, _ = np.histogram2d(fixed_flat, moving_flat, bins=num_bins)
        pxy = hist_2d / hist_2d.sum()
        px = pxy.sum(axis=1)
        py = pxy.sum(axis=0)
        px_py = px[:, np.newaxis] * py[np.newaxis, :]

        nonzero = pxy > 0
        return float(np.sum(pxy[nonzero] * np.log(pxy[nonzero] / px_py[nonzero])))

    def resample_image_gpu(self, image, transform_matrix, output_shape=None):
        if not self._available:
            return None

        cp = self._cupy
        if output_shape is None:
            output_shape = image.shape

        dim = len(output_shape)
        if dim != 2:
            return None

        try:
            image_gpu = cp.asarray(image, dtype=cp.float32)
            inv_matrix = np.linalg.inv(transform_matrix).astype(np.float32).ravel()
            inv_matrix_gpu = cp.asarray(inv_matrix, dtype=cp.float32)

            in_rows, in_cols = image_gpu.shape
            out_rows, out_cols = output_shape

            output_gpu = cp.zeros((out_rows, out_cols), dtype=cp.float32)

            tile = self.tile_size
            grid_x = (out_cols + tile - 1) // tile
            grid_y = (out_rows + tile - 1) // tile

            kernel = self._kernels["resample_2d"]
            kernel(
                (grid_x, grid_y), (tile, tile),
                (image_gpu, in_rows, in_cols, out_rows, out_cols, inv_matrix_gpu, output_gpu)
            )

            return cp.asnumpy(output_gpu)

        except Exception as e:
            print(f"[GPU Error] Resample failed: {e}")
            return None

    def compute_joint_histogram_gpu(self, fixed, moving, num_bins=64):
        if not self._available:
            return None, None, None

        cp = self._cupy
        fixed_flat = cp.asarray(fixed.ravel(), dtype=cp.float32)
        moving_flat = cp.asarray(moving.ravel(), dtype=cp.float32)

        n = int(fixed_flat.shape[0])
        fmin = float(fixed_flat.min())
        fmax = float(fixed_flat.max())
        mmin = float(moving_flat.min())
        mmax = float(moving_flat.max())

        num_blocks = min(64, max(8, (n + self.block_size - 1) // self.block_size))
        hist_size = num_bins * num_bins

        block_histograms = cp.zeros((num_blocks, hist_size), dtype=cp.int32)
        final_histogram = cp.zeros(hist_size, dtype=cp.int32)

        kernel = self._kernels["histogram_block"]
        kernel(
            (num_blocks,), (self.block_size,),
            (fixed_flat, moving_flat, n, fmin, fmax, mmin, mmax, num_bins, block_histograms, num_blocks),
            shared_mem=hist_size * 4
        )

        reduce_kernel = self._kernels["reduce_histograms"]
        reduce_block = min(self.block_size, hist_size)
        reduce_kernel(
            (1,), (reduce_block,),
            (block_histograms, num_blocks, hist_size, final_histogram),
            shared_mem=hist_size * 4
        )

        hist_2d = final_histogram.reshape(num_bins, num_bins)
        return (
            cp.asnumpy(hist_2d),
            np.linspace(fmin, fmax, num_bins + 1),
            np.linspace(mmin, mmax, num_bins + 1),
        )

    def gpu_info(self):
        if not self._available:
            return {"available": False, "message": "CuPy not available or no CUDA device found"}

        cp = self._cupy
        mem_info = cp.cuda.runtime.memGetInfo()
        total_mem = mem_info[1] / (1024 ** 3)
        free_mem = mem_info[0] / (1024 ** 3)

        return {
            "available": True,
            "device_name": self._device_name,
            "total_memory_gb": round(total_mem, 2),
            "free_memory_gb": round(free_mem, 2),
            "cuda_version": cp.cuda.runtime.runtimeGetVersion(),
            "max_shared_memory_bytes": self._max_shared_memory,
            "max_threads_per_block": self._max_threads_per_block,
            "block_size": self.block_size,
            "tile_size": self.tile_size,
            "kernels_compiled": list(self._kernels.keys()),
        }
