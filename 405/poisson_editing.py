import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
import warnings
warnings.filterwarnings('ignore')

try:
    from numba import jit, prange, cuda
    HAS_NUMBA = True
    HAS_CUDA = cuda.is_available() if HAS_NUMBA else False
except ImportError:
    HAS_NUMBA = False
    HAS_CUDA = False


class GradientField:
    def __init__(self, grad_x: np.ndarray, grad_y: np.ndarray, weight: float = 1.0):
        self.grad_x = grad_x
        self.grad_y = grad_y
        self.weight = weight


class MixedGradientField:
    def __init__(self):
        self.fields: List[GradientField] = []
    
    def add_field(self, grad_x: np.ndarray, grad_y: np.ndarray, weight: float = 1.0):
        self.fields.append(GradientField(grad_x, grad_y, weight))
    
    def compute_blended(self, shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray]:
        if not self.fields:
            return np.zeros(shape, dtype=np.float64), np.zeros(shape, dtype=np.float64)
        
        total_weight = sum(f.weight for f in self.fields)
        if total_weight == 0:
            return np.zeros(shape, dtype=np.float64), np.zeros(shape, dtype=np.float64)
        
        blended_x = np.zeros(shape, dtype=np.float64)
        blended_y = np.zeros(shape, dtype=np.float64)
        
        for field in self.fields:
            w = field.weight / total_weight
            h, w = field.grad_x.shape
            target_h, target_w = shape
            
            if (h, w) != shape:
                fx = cv2.resize(field.grad_x, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
                fy = cv2.resize(field.grad_y, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
            else:
                fx = field.grad_x
                fy = field.grad_y
            
            blended_x += w * fx
            blended_y += w * fy
        
        return blended_x, blended_y


if HAS_NUMBA and HAS_CUDA:
    @cuda.jit
    def _cuda_jacobi_smooth(u, f, mask, result):
        y, x = cuda.grid(2)
        h, w = u.shape
        
        if 0 < y < h - 1 and 0 < x < w - 1 and mask[y, x] > 0:
            laplacian = u[y-1, x] + u[y+1, x] + u[y, x-1] + u[y, x+1]
            result[y, x] = (laplacian - f[y, x]) / 4.0
    
    @cuda.jit
    def _cuda_compute_residual(u, f, mask, residual):
        y, x = cuda.grid(2)
        h, w = u.shape
        
        if 0 <= y < h and 0 <= x < w and mask[y, x] > 0:
            count = 0
            laplacian = 0.0
            
            if y > 0:
                laplacian += u[y-1, x]
                count += 1
            if y < h - 1:
                laplacian += u[y+1, x]
                count += 1
            if x > 0:
                laplacian += u[y, x-1]
                count += 1
            if x < w - 1:
                laplacian += u[y, x+1]
                count += 1
            
            laplacian -= count * u[y, x]
            residual[y, x] = f[y, x] - laplacian


class GPUMultigridSolver:
    def __init__(self, max_levels: int = 3):
        self.max_levels = max_levels
        self.pre_smooth = 2
        self.post_smooth = 1
        self.coarse_solve = 5
        self.available = HAS_CUDA
    
    def _cuda_smooth(self, u: np.ndarray, f: np.ndarray, mask: np.ndarray, iterations: int) -> np.ndarray:
        if not self.available:
            return self._cpu_smooth(u, f, mask, iterations)
        
        h, w = u.shape
        result = u.copy()
        
        threadsperblock = (16, 16)
        blockspergrid_x = (w + threadsperblock[0] - 1) // threadsperblock[0]
        blockspergrid_y = (h + threadsperblock[1] - 1) // threadsperblock[1]
        blockspergrid = (blockspergrid_x, blockspergrid_y)
        
        d_u = cuda.to_device(result)
        d_f = cuda.to_device(f)
        d_mask = cuda.to_device(mask)
        d_result = cuda.to_device(result)
        
        for _ in range(iterations):
            _cuda_jacobi_smooth[blockspergrid, threadsperblock](d_u, d_f, d_mask, d_result)
            d_u, d_result = d_result, d_u
        
        return d_u.copy_to_host()
    
    def _cpu_smooth(self, u: np.ndarray, f: np.ndarray, mask: np.ndarray, iterations: int) -> np.ndarray:
        result = u.copy()
        mask_bool = mask > 0
        
        for _ in range(iterations):
            laplacian = np.zeros_like(result)
            count = np.zeros_like(result)
            
            laplacian[1:, :] += result[:-1, :]
            count[1:, :] += 1
            laplacian[:-1, :] += result[1:, :]
            count[:-1, :] += 1
            laplacian[:, 1:] += result[:, :-1]
            count[:, 1:] += 1
            laplacian[:, :-1] += result[:, 1:]
            count[:, :-1] += 1
            
            new_val = (laplacian - f) / np.maximum(count, 1)
            result[mask_bool] = new_val[mask_bool]
        
        return result
    
    def smooth(self, u: np.ndarray, f: np.ndarray, mask: np.ndarray, iterations: int) -> np.ndarray:
        if self.available and u.nbytes > 10000:
            return self._cuda_smooth(u, f, mask, iterations)
        return self._cpu_smooth(u, f, mask, iterations)


class MultigridSolver:
    def __init__(self, max_levels: int = 3, use_gpu: bool = False):
        self.max_levels = max_levels
        self.pre_smooth = 2
        self.post_smooth = 1
        self.coarse_solve = 5
        self.use_gpu = use_gpu and HAS_CUDA
        
        if self.use_gpu:
            self.gpu_solver = GPUMultigridSolver(max_levels)
    
    def relax_jacobi(self, u: np.ndarray, f: np.ndarray, mask: np.ndarray, iterations: int) -> np.ndarray:
        if self.use_gpu:
            return self.gpu_solver.smooth(u, f, mask, iterations)
        
        result = u.copy()
        mask_bool = mask > 0
        
        for _ in range(iterations):
            laplacian = np.zeros_like(result)
            count = np.zeros_like(result)
            
            laplacian[1:, :] += result[:-1, :]
            count[1:, :] += 1
            laplacian[:-1, :] += result[1:, :]
            count[:-1, :] += 1
            laplacian[:, 1:] += result[:, :-1]
            count[:, 1:] += 1
            laplacian[:, :-1] += result[:, 1:]
            count[:, :-1] += 1
            
            new_val = (laplacian - f) / np.maximum(count, 1)
            result[mask_bool] = new_val[mask_bool]
        
        return result
    
    def restrict(self, arr: np.ndarray) -> np.ndarray:
        h, w = arr.shape
        new_h, new_w = (h + 1) // 2, (w + 1) // 2
        resized = cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized
    
    def interpolate(self, x: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
        result = cv2.resize(x, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_LINEAR)
        return result
    
    def compute_residual(self, u: np.ndarray, f: np.ndarray, mask: np.ndarray) -> np.ndarray:
        laplacian = np.zeros_like(u)
        count = np.zeros_like(u)
        
        laplacian[1:, :] += u[:-1, :]
        count[1:, :] += 1
        laplacian[:-1, :] += u[1:, :]
        count[:-1, :] += 1
        laplacian[:, 1:] += u[:, :-1]
        count[:, 1:] += 1
        laplacian[:, :-1] += u[:, 1:]
        count[:, :-1] += 1
        
        laplacian -= count * u
        
        residual = np.where(mask > 0, f - laplacian, 0)
        return residual
    
    def v_cycle(self, u: np.ndarray, f: np.ndarray, mask: np.ndarray, level: int) -> np.ndarray:
        if level == 0 or min(u.shape) <= 8:
            return self.relax_jacobi(u, f, mask, self.coarse_solve)
        
        u = self.relax_jacobi(u, f, mask, self.pre_smooth)
        
        residual = self.compute_residual(u, f, mask)
        
        coarse_f = self.restrict(residual)
        coarse_mask = self.restrict(mask)
        coarse_u = np.zeros_like(coarse_f)
        
        coarse_u = self.v_cycle(coarse_u, coarse_f, coarse_mask, level - 1)
        
        correction = self.interpolate(coarse_u, u.shape)
        u = u + correction
        
        u = self.relax_jacobi(u, f, mask, self.post_smooth)
        
        return u
    
    def solve(self, initial_u: np.ndarray, rhs: np.ndarray, mask: np.ndarray, max_iterations: int = 15) -> np.ndarray:
        u = initial_u.copy().astype(np.float64)
        f = rhs.copy().astype(np.float64)
        mask_float = mask.astype(np.float64)
        
        for i in range(max_iterations):
            u = self.v_cycle(u, f, mask_float, self.max_levels)
        
        return u


class PoissonEditing:
    def __init__(self, solver_type: str = 'multigrid', use_gpu: bool = False):
        self.solver_type = solver_type
        self.max_iter = 5000
        self.tol = 1e-5
        self.multigrid = MultigridSolver(max_levels=3, use_gpu=use_gpu)
        self.feather_radius = 5
        self.use_gpu = use_gpu and HAS_CUDA
        
        if self.use_gpu:
            print(f"GPU加速已启用: {cuda.get_current_device().name if HAS_CUDA else 'Unknown'}")
        else:
            print("使用CPU求解 (未检测到CUDA或Numba)")
    
    def compute_gradient(self, img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        grad_x = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
        return grad_x, grad_y
    
    def create_mixed_gradient_field(self, 
                                    sources: List[np.ndarray], 
                                    weights: Optional[List[float]] = None,
                                    channel: Optional[int] = None) -> MixedGradientField:
        if weights is None:
            weights = [1.0] * len(sources)
        
        mixed_field = MixedGradientField()
        for src, w in zip(sources, weights):
            src_processed = src[:, :, channel] if (channel is not None and len(src.shape) == 3) else src
            gx, gy = self.compute_gradient(src_processed)
            mixed_field.add_field(gx, gy, w)
        
        return mixed_field
    
    def blend_gradients(self, 
                         src_grad_x: np.ndarray, 
                         src_grad_y: np.ndarray,
                         dst_grad_x: np.ndarray, 
                         dst_grad_y: np.ndarray,
                         mix_weight: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
        if mix_weight <= 0:
            return dst_grad_x, dst_grad_y
        elif mix_weight >= 1:
            return src_grad_x, src_grad_y
        
        blended_x = mix_weight * src_grad_x + (1 - mix_weight) * dst_grad_x
        blended_y = mix_weight * src_grad_y + (1 - mix_weight) * dst_grad_y
        
        return blended_x, blended_y
    
    def feather_mask(self, mask: np.ndarray, radius: int = None) -> np.ndarray:
        if radius is None:
            radius = self.feather_radius
        
        if radius <= 0:
            return mask.astype(np.float64)
        
        mask_bin = (mask > 127).astype(np.uint8)
        
        dist = cv2.distanceTransform(mask_bin, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        
        max_dist = min(radius, dist.max())
        if max_dist > 0:
            feather = np.clip(dist / max_dist, 0, 1)
        else:
            feather = mask_bin.astype(np.float64)
        
        return feather
    
    def compute_divergence(self, grad_x: np.ndarray, grad_y: np.ndarray) -> np.ndarray:
        h, w = grad_x.shape
        div = np.zeros((h, w), dtype=np.float64)
        
        for y in range(h):
            for x in range(w):
                dxx = 0.0
                dyy = 0.0
                
                if x > 0:
                    dxx += grad_x[y, x] - grad_x[y, x - 1]
                else:
                    dxx += grad_x[y, x]
                
                if y > 0:
                    dyy += grad_y[y, x] - grad_y[y - 1, x]
                else:
                    dyy += grad_y[y, x]
                
                div[y, x] = dxx + dyy
        
        return div
    
    def solve_multigrid(self,
                        src_channel: np.ndarray,
                        dst_channel: np.ndarray,
                        mask: np.ndarray,
                        mix_weight: float = 1.0,
                        feather: bool = True,
                        src_gradients: Optional[Tuple[np.ndarray, np.ndarray]] = None) -> np.ndarray:
        h, w = dst_channel.shape
        
        if src_gradients is not None:
            src_grad_x, src_grad_y = src_gradients
        else:
            src_grad_x, src_grad_y = self.compute_gradient(src_channel)
        
        dst_grad_x, dst_grad_y = self.compute_gradient(dst_channel)
        
        blended_grad_x, blended_grad_y = self.blend_gradients(
            src_grad_x, src_grad_y, dst_grad_x, dst_grad_y, mix_weight
        )
        
        div = self.compute_divergence(blended_grad_x, blended_grad_y)
        
        mask_bin = (mask > 127).astype(np.uint8)
        
        initial_u = dst_channel.copy().astype(np.float64)
        
        solution = self.multigrid.solve(initial_u, div, mask_bin, max_iterations=15)
        
        if feather and self.feather_radius > 0:
            feather_weights = self.feather_mask(mask_bin, self.feather_radius)
            feather_weights = feather_weights[:, :, np.newaxis] if len(solution.shape) == 3 else feather_weights
            solution = solution * feather_weights + dst_channel * (1 - feather_weights)
        
        solution = np.clip(solution, 0, 255)
        
        result = dst_channel.copy().astype(np.float64)
        result[mask_bin > 0] = solution[mask_bin > 0]
        
        return result.astype(np.uint8)
    
    def fuse_mixed_gradients(self,
                            sources: List[np.ndarray],
                            dst_img: np.ndarray,
                            mask: np.ndarray,
                            offsets: Optional[List[Tuple[int, int]]] = None,
                            weights: Optional[List[float]] = None,
                            feather: bool = True) -> np.ndarray:
        if weights is None:
            weights = [1.0] * len(sources)
        
        if offsets is None:
            offsets = [(0, 0)] * len(sources)
        
        if len(sources) != len(weights) or len(sources) != len(offsets):
            raise ValueError("sources, weights and offsets must have the same length")
        
        result = dst_img.copy()
        h, w = dst_img.shape[:2]
        
        if mask.shape[:2] != (h, w):
            mask_full = np.zeros((h, w), dtype=np.uint8)
            for (dy, dx), src in zip(offsets, sources):
                sh, sw = src.shape[:2]
                y1, y2 = max(0, dy), min(h, dy + sh)
                x1, x2 = max(0, dx), min(w, dx + sw)
                my1, my2 = max(0, -dy), min(sh, h - dy)
                mx1, mx2 = max(0, -dx), min(sw, w - dx)
                if y2 > y1 and x2 > x1 and mask.shape[:2] == src.shape[:2]:
                    mask_full[y1:y2, x1:x2] = np.maximum(
                        mask_full[y1:y2, x1:x2], 
                        mask[my1:my2, mx1:mx2]
                    )
            mask = mask_full
        
        if len(dst_img.shape) == 3:
            for c in range(3):
                sources_gray = []
                for src, (dy, dx) in zip(sources, offsets):
                    src_gray = src[:, :, c] if len(src.shape) == 3 else src
                    src_full = np.zeros((h, w), dtype=np.float64)
                    sh, sw = src_gray.shape
                    y1, y2 = max(0, dy), min(h, dy + sh)
                    x1, x2 = max(0, dx), min(w, dx + sw)
                    my1, my2 = max(0, -dy), min(sh, h - dy)
                    mx1, mx2 = max(0, -dx), min(sw, w - dx)
                    if y2 > y1 and x2 > x1:
                        src_full[y1:y2, x1:x2] = src_gray[my1:my2, mx1:mx2].astype(np.float64)
                    sources_gray.append(src_full)
                
                mixed_field = self.create_mixed_gradient_field(sources_gray, weights)
                blended_x, blended_y = mixed_field.compute_blended((h, w))
                
                src_c = np.zeros_like(dst_img[:, :, c])
                result[:, :, c] = self.solve_multigrid(
                    src_c, dst_img[:, :, c], mask, mix_weight=1.0, 
                    feather=feather, src_gradients=(blended_x, blended_y)
                )
        else:
            sources_full = []
            for src, (dy, dx) in zip(sources, offsets):
                src_full = np.zeros((h, w), dtype=np.float64)
                sh, sw = src.shape[:2]
                y1, y2 = max(0, dy), min(h, dy + sh)
                x1, x2 = max(0, dx), min(w, dx + sw)
                my1, my2 = max(0, -dy), min(sh, h - dy)
                mx1, mx2 = max(0, -dx), min(sw, w - dx)
                if y2 > y1 and x2 > x1:
                    src_full[y1:y2, x1:x2] = src[my1:my2, mx1:mx2].astype(np.float64)
                sources_full.append(src_full)
            
            mixed_field = self.create_mixed_gradient_field(sources_full, weights)
            blended_x, blended_y = mixed_field.compute_blended((h, w))
            
            src_c = np.zeros_like(dst_img)
            result = self.solve_multigrid(
                src_c, dst_img, mask, mix_weight=1.0,
                feather=feather, src_gradients=(blended_x, blended_y)
            )
        
        return result
    
    def fuse(self,
            src_img: np.ndarray,
            dst_img: np.ndarray,
            masks: List[np.ndarray],
            offsets: List[Tuple[int, int]],
            mix_weights: Optional[List[float]] = None,
            feather: bool = True) -> np.ndarray:
        if mix_weights is None:
            mix_weights = [1.0] * len(masks)
        
        if len(masks) != len(offsets) or len(masks) != len(mix_weights):
            raise ValueError("masks, offsets, and mix_weights must have the same length")
        
        result = dst_img.copy()
        
        for mask, offset, mix_weight in zip(masks, offsets, mix_weights):
            if src_img.shape[:2] != mask.shape[:2]:
                raise ValueError(f"Source image shape {src_img.shape[:2]} does not match mask shape {mask.shape[:2]}")
            
            dy, dx = offset
            src_h, src_w = src_img.shape[:2]
            dst_h, dst_w = dst_img.shape[:2]
            
            y1, y2 = max(0, dy), min(dst_h, dy + src_h)
            x1, x2 = max(0, dx), min(dst_w, dx + src_w)
            
            src_y1, src_y2 = max(0, -dy), min(src_h, dst_h - dy)
            src_x1, src_x2 = max(0, -dx), min(src_w, dst_w - dx)
            
            if y2 <= y1 or x2 <= x1:
                continue
            
            src_roi = src_img[src_y1:src_y2, src_x1:src_x2]
            mask_roi = mask[src_y1:src_y2, src_x1:src_x2]
            dst_roi = result[y1:y2, x1:x2]
            
            if len(src_img.shape) == 3 and len(dst_img.shape) == 3:
                fused_roi = np.zeros_like(dst_roi)
                for c in range(3):
                    fused_roi[:, :, c] = self.solve_multigrid(
                        src_roi[:, :, c], dst_roi[:, :, c], mask_roi, mix_weight, feather
                    )
            else:
                fused_roi = self.solve_multigrid(
                    src_roi, dst_roi, mask_roi, mix_weight, feather
                )
            
            mask_bin = (mask_roi > 127)
            if len(fused_roi.shape) == 3:
                mask_bin = mask_bin[:, :, np.newaxis]
            result[y1:y2, x1:x2] = np.where(mask_bin, fused_roi, dst_roi)
        
        return result
    
    def seamless_clone(self,
                      src_img: np.ndarray,
                      dst_img: np.ndarray,
                      mask: np.ndarray,
                      center: Tuple[int, int],
                      mix_weight: float = 1.0,
                      feather: bool = True) -> np.ndarray:
        h, w = src_img.shape[:2]
        offset = (center[1] - h // 2, center[0] - w // 2)
        return self.fuse(src_img, dst_img, [mask], [offset], [mix_weight], feather)


class VideoPoissonEditor:
    def __init__(self, use_gpu: bool = False, temporal_smoothing: float = 0.3):
        self.poisson = PoissonEditing(use_gpu=use_gpu)
        self.temporal_smoothing = temporal_smoothing
        self.prev_result = None
    
    def process_frame(self, 
                     src_img: np.ndarray, 
                     dst_frame: np.ndarray, 
                     mask: np.ndarray, 
                     offset: Tuple[int, int],
                     mix_weight: float = 1.0) -> np.ndarray:
        current_result = self.poisson.fuse(
            src_img, dst_frame, [mask], [offset], [mix_weight], feather=True
        )
        
        if self.prev_result is not None and self.temporal_smoothing > 0:
            alpha = self.temporal_smoothing
            current_result = cv2.addWeighted(
                current_result, 1 - alpha, self.prev_result, alpha, 0
            )
        
        self.prev_result = current_result.copy()
        return current_result
    
    def process_video(self,
                     src_img: np.ndarray,
                     video_path: str,
                     output_path: str,
                     mask: np.ndarray,
                     offset: Tuple[int, int],
                     mix_weight: float = 1.0,
                     start_frame: int = 0,
                     max_frames: int = -1) -> bool:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"无法打开视频: {video_path}")
            return False
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if start_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        frame_count = 0
        self.prev_result = None
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if max_frames > 0 and frame_count >= max_frames:
                break
            
            result = self.process_frame(src_img, frame, mask, offset, mix_weight)
            out.write(result)
            
            frame_count += 1
            if frame_count % 10 == 0:
                progress = (start_frame + frame_count) / total_frames * 100
                print(f"处理进度: {progress:.1f}% ({start_frame + frame_count}/{total_frames})")
        
        cap.release()
        out.release()
        print(f"视频处理完成，共{frame_count}帧，输出: {output_path}")
        
        return True
    
    def reset(self):
        self.prev_result = None


def test_poisson_editing():
    src = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.circle(src, (50, 50), 30, (255, 0, 0), -1)
    
    dst = np.ones((200, 200, 3), dtype=np.uint8) * 128
    
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 30, 255, -1)
    
    poisson = PoissonEditing(use_gpu=HAS_CUDA)
    result = poisson.seamless_clone(src, dst, mask, (100, 100), mix_weight=1.0, feather=True)
    
    print("Test completed successfully!")
    print(f"GPU可用: {HAS_CUDA}")
    print(f"Input shape: {dst.shape}")
    print(f"Output shape: {result.shape}")
    
    return result


if __name__ == "__main__":
    test_poisson_editing()
