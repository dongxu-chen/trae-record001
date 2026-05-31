import numpy as np
import warnings
from typing import Optional

warnings.filterwarnings("ignore")


class RXGPU:
    def __init__(self, chunk_size: int = 10000):
        self._cuda_available = False
        self._gpu = None
        self.chunk_size = chunk_size
        self._try_init_cuda()

    def _try_init_cuda(self):
        try:
            import pycuda.driver as cuda
            import pycuda.autoinit
            from pycuda.compiler import SourceModule

            self._cuda = cuda
            self._SourceModule = SourceModule
            self._cuda_available = True

            self._rx_kernel = self._SourceModule("""
                __global__ void compute_rx_scores(
                    float *data, 
                    float *mean, 
                    float *cov_inv, 
                    float *scores,
                    int n_samples, 
                    int n_bands)
                {
                    int idx = blockIdx.x * blockDim.x + threadIdx.x;
                    
                    if (idx < n_samples) {
                        float centered[256];
                        float temp[256];
                        
                        for (int j = 0; j < n_bands; j++) {
                            centered[j] = data[idx * n_bands + j] - mean[j];
                        }
                        
                        for (int j = 0; j < n_bands; j++) {
                            temp[j] = 0.0f;
                            for (int k = 0; k < n_bands; k++) {
                                temp[j] += centered[k] * cov_inv[k * n_bands + j];
                            }
                        }
                        
                        float score = 0.0f;
                        for (int j = 0; j < n_bands; j++) {
                            score += centered[j] * temp[j];
                        }
                        
                        scores[idx] = score;
                    }
                }
            """)

            self._rx_kernel_dynamic = self._SourceModule("""
                __global__ void compute_rx_scores_dynamic(
                    float *data, 
                    float *mean, 
                    float *cov_inv, 
                    float *scores,
                    int n_samples, 
                    int n_bands)
                {
                    int idx = blockIdx.x * 64 + threadIdx.x;
                    
                    if (idx < n_samples) {
                        float sum = 0.0f;
                        
                        for (int j = 0; j < n_bands; j++) {
                            float c_j = data[idx * n_bands + j] - mean[j];
                            float mat_sum = 0.0f;
                            
                            for (int k = 0; k < n_bands; k++) {
                                mat_sum += (data[idx * n_bands + k] - mean[k]) * 
                                           cov_inv[k * n_bands + j];
                            }
                            
                            sum += c_j * mat_sum;
                        }
                        
                        scores[idx] = sum;
                    }
                }
            """)

            print("CUDA initialized successfully")
        except ImportError:
            print("PyCUDA not installed. GPU acceleration will not be available.")
            self._cuda_available = False
        except Exception as e:
            print(f"CUDA initialization failed: {e}")
            self._cuda_available = False

    def is_available(self) -> bool:
        return self._cuda_available

    def _compute_chunk_gpu(self, data_chunk: np.ndarray, mean: np.ndarray, 
                            cov_inv: np.ndarray, n_bands: int) -> np.ndarray:
        n_samples = data_chunk.shape[0]

        data_gpu = data_chunk.astype(np.float32)
        mean_gpu = mean.astype(np.float32)
        cov_inv_gpu = cov_inv.astype(np.float32)
        scores_gpu = np.zeros(n_samples, dtype=np.float32)

        data_ptr = self._cuda.to_device(data_gpu)
        mean_ptr = self._cuda.to_device(mean_gpu)
        cov_inv_ptr = self._cuda.to_device(cov_inv_gpu)
        scores_ptr = self._cuda.to_device(scores_gpu)

        block_size = 64
        grid_size = (n_samples + block_size - 1) // block_size

        if n_bands <= 256:
            rx_func = self._rx_kernel.get_function("compute_rx_scores")
            rx_func(
                data_ptr, mean_ptr, cov_inv_ptr, scores_ptr,
                np.int32(n_samples), np.int32(n_bands),
                block=(block_size, 1, 1),
                grid=(grid_size, 1)
            )
        else:
            rx_func = self._rx_kernel_dynamic.get_function("compute_rx_scores_dynamic")
            shared_size = min(n_bands * n_bands * 4, 48 * 1024)
            rx_func(
                data_ptr, mean_ptr, cov_inv_ptr, scores_ptr,
                np.int32(n_samples), np.int32(n_bands),
                block=(block_size, 1, 1),
                grid=(grid_size, 1),
                shared=shared_size
            )

        self._cuda.memcpy_dtoh(scores_gpu, scores_ptr)
        
        self._cuda.free(data_ptr)
        self._cuda.free(scores_ptr)

        return scores_gpu

    def compute_rx_scores(self, data: np.ndarray, mean: np.ndarray, 
                           cov_inv: np.ndarray) -> np.ndarray:
        if not self._cuda_available:
            centered = data - mean
            return np.sum(centered @ cov_inv * centered, axis=1)

        n_samples, n_bands = data.shape
        
        if n_samples <= self.chunk_size:
            return self._compute_chunk_gpu(data, mean, cov_inv, n_bands).astype(np.float64)
        
        return self.compute_rx_scores_chunked(data, mean, cov_inv)

    def compute_rx_scores_chunked(self, data: np.ndarray, mean: np.ndarray, 
                                   cov_inv: np.ndarray, 
                                   chunk_size: Optional[int] = None) -> np.ndarray:
        if chunk_size is None:
            chunk_size = self.chunk_size

        if not self._cuda_available:
            centered = data - mean
            return np.sum(centered @ cov_inv * centered, axis=1)

        n_samples, n_bands = data.shape
        all_scores = np.zeros(n_samples, dtype=np.float64)
        
        n_chunks = (n_samples + chunk_size - 1) // chunk_size
        
        for i in range(n_chunks):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, n_samples)
            
            data_chunk = data[start_idx:end_idx]
            chunk_scores = self._compute_chunk_gpu(data_chunk, mean, cov_inv, n_bands)
            all_scores[start_idx:end_idx] = chunk_scores.astype(np.float64)
        
        return all_scores

    def process_image_chunked(self, image: np.ndarray, mean: np.ndarray, 
                               cov_inv: np.ndarray, 
                               chunk_size: Optional[int] = None) -> np.ndarray:
        if image.ndim == 3:
            h, w, bands = image.shape
            flat_data = image.reshape(-1, bands)
            scores = self.compute_rx_scores_chunked(flat_data, mean, cov_inv, chunk_size)
            return scores.reshape(h, w)
        else:
            return self.compute_rx_scores_chunked(image, mean, cov_inv, chunk_size)


def benchmark_gpu_cpu(data: np.ndarray, mean: np.ndarray, cov_inv: np.ndarray) -> dict:
    import time

    gpu = RXGPU()

    start = time.time()
    centered = data - mean
    cpu_scores = np.sum(centered @ cov_inv * centered, axis=1)
    cpu_time = time.time() - start

    start = time.time()
    gpu_scores = gpu.compute_rx_scores(data, mean, cov_inv)
    gpu_time = time.time() - start

    max_diff = np.max(np.abs(cpu_scores - gpu_scores))

    return {
        "cpu_time": cpu_time,
        "gpu_time": gpu_time,
        "speedup": cpu_time / gpu_time if gpu_time > 0 else float('inf'),
        "max_difference": max_diff,
        "gpu_available": gpu.is_available()
    }


def benchmark_chunked_processing(data: np.ndarray, mean: np.ndarray, 
                                   cov_inv: np.ndarray, 
                                   chunk_sizes: list = [1000, 5000, 10000, 25000]) -> dict:
    import time

    gpu = RXGPU()
    results = {}

    if gpu.is_available():
        for chunk_size in chunk_sizes:
            start = time.time()
            scores = gpu.compute_rx_scores_chunked(data, mean, cov_inv, chunk_size=chunk_size)
            elapsed = time.time() - start
            results[chunk_size] = elapsed
    else:
        print("GPU not available for chunked benchmark")

    return results
