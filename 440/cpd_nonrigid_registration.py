import numpy as np
import os
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pycpd import DeformableRegistration
from scipy.stats import multivariate_normal
from scipy.spatial.distance import cdist
from scipy.interpolate import griddata, RBFInterpolator
from scipy.ndimage import gaussian_filter1d
from sklearn.cluster import KMeans
from collections import deque
import warnings
warnings.filterwarnings('ignore')

try:
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False
    print("Warning: Open3D not available. Some features (PLY I/O, 3D viewer) will be disabled.")


class NonRigidCPDRegistration:
    def __init__(self, alpha=2.0, beta=0.5, max_iterations=100, tolerance=1e-7, w=0.0,
                 use_two_stage=True, coarse_sample_ratio=0.3, coarse_max_iter=30,
                 anisotropic_weights=None, robust_kernel='gaussian',
                 kernel_param=1.0, temporal_smoothing=0.0):
        self.alpha = alpha
        self.beta = beta
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.w = w
        
        self.use_two_stage = use_two_stage
        self.coarse_sample_ratio = coarse_sample_ratio
        self.coarse_max_iter = coarse_max_iter
        
        self.anisotropic_weights = np.array(anisotropic_weights) if anisotropic_weights is not None else np.array([1.0, 1.0, 1.0])
        self.use_anisotropic = anisotropic_weights is not None
        
        self.robust_kernel = robust_kernel
        self.kernel_param = kernel_param
        self.use_robust_kernel = robust_kernel != 'gaussian'
        
        self.temporal_smoothing = temporal_smoothing
        self.use_temporal = temporal_smoothing > 0
        
        self.source_original = None
        self.target_original = None
        self.source_registered = None
        self.deformation_field = None
        self.gmm_params = None
        self.em_history = []
        
        self.coarse_source_indices = None
        self.coarse_deformation_field = None
        self.outlier_labels = None
        
        self.temporal_buffer = deque(maxlen=5)
        self.sequence_results = []
        
    def generate_synthetic_data(self, num_points=500, shape='sphere', deformation_scale=0.3):
        if shape == 'sphere':
            source = self._generate_sphere(num_points)
        elif shape == 'bunny':
            source = self._generate_bunny(num_points)
        elif shape == 'plane':
            source = self._generate_plane(num_points)
        else:
            source = self._generate_sphere(num_points)
            
        self.source_original = source.copy()
        self.target_original = self._apply_nonrigid_deformation(source, deformation_scale)
        
        return self.source_original, self.target_original
    
    def _generate_sphere(self, num_points):
        phi = np.random.uniform(0, 2 * np.pi, num_points)
        theta = np.random.uniform(0, np.pi, num_points)
        r = 1.0
        
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        
        return np.column_stack((x, y, z))
    
    def _generate_plane(self, num_points):
        x = np.random.uniform(-1, 1, num_points)
        y = np.random.uniform(-1, 1, num_points)
        z = np.sin(2 * np.pi * x) * np.cos(2 * np.pi * y) * 0.3
        
        return np.column_stack((x, y, z))
    
    def _generate_bunny(self, num_points):
        try:
            bunny = o3d.data.BunnyMesh()
            mesh = o3d.io.read_triangle_mesh(bunny.path)
            pcd = mesh.sample_points_uniformly(number_of_points=num_points)
            points = np.asarray(pcd.points)
            
            center = np.mean(points, axis=0)
            points -= center
            scale = np.max(np.linalg.norm(points, axis=1))
            points /= scale
            
            return points
        except:
            return self._generate_sphere(num_points)
    
    def _apply_nonrigid_deformation(self, points, scale=0.3):
        deformed = points.copy()
        
        x, y, z = deformed[:, 0], deformed[:, 1], deformed[:, 2]
        
        dx = scale * np.sin(2 * np.pi * y) * np.cos(2 * np.pi * z)
        dy = scale * np.sin(2 * np.pi * x) * np.cos(2 * np.pi * z) * 0.5
        dz = scale * np.cos(2 * np.pi * x * y) * 0.3
        
        deformed[:, 0] += dx
        deformed[:, 1] += dy
        deformed[:, 2] += dz
        
        return deformed
    
    def load_point_cloud(self, file_path):
        if not OPEN3D_AVAILABLE:
            raise ImportError("Open3D is required for loading point cloud files.")
        
        pcd = o3d.io.read_point_cloud(file_path)
        points = np.asarray(pcd.points)
        
        center = np.mean(points, axis=0)
        points -= center
        scale = np.max(np.linalg.norm(points, axis=1))
        points /= scale
        
        return points
    
    def register(self, source=None, target=None):
        if source is not None:
            self.source_original = source
        if target is not None:
            self.target_original = target
            
        if self.source_original is None or self.target_original is None:
            raise ValueError("Source and target point clouds must be provided")
        
        if self.use_two_stage:
            return self._two_stage_register()
        else:
            return self._single_stage_register()
    
    def _single_stage_register(self):
        reg = DeformableRegistration(
            X=self.target_original,
            Y=self.source_original,
            alpha=self.alpha,
            beta=self.beta,
            w=self.w,
            max_iterations=self.max_iterations,
            tolerance=self.tolerance
        )
        
        result = reg.register()
        self.source_registered = result[0]
        self.deformation_field = self.source_registered - self.source_original
        self.em_history = reg.iteration
        
        self._compute_gmm_with_outliers()
        
        return self.source_registered, self.deformation_field
    
    def _two_stage_register(self):
        print("=" * 50)
        print("Two-Stage Registration: Coarse-to-Fine")
        print("=" * 50)
        
        num_points = self.source_original.shape[0]
        num_coarse = max(int(num_points * self.coarse_sample_ratio), 50)
        
        print(f"\nStage 1: Coarse Registration (sampling {num_coarse}/{num_points} points)")
        self.coarse_source_indices = np.random.choice(num_points, num_coarse, replace=False)
        coarse_source = self.source_original[self.coarse_source_indices]
        
        coarse_target_idx = np.random.choice(self.target_original.shape[0], num_coarse, replace=False)
        coarse_target = self.target_original[coarse_target_idx]
        
        reg_coarse = DeformableRegistration(
            X=coarse_target,
            Y=coarse_source,
            alpha=self.alpha * 1.5,
            beta=self.beta * 1.5,
            w=self.w,
            max_iterations=self.coarse_max_iter,
            tolerance=self.tolerance * 10
        )
        
        result_coarse = reg_coarse.register()
        coarse_registered = result_coarse[0]
        self.coarse_deformation_field = coarse_registered - coarse_source
        
        print(f"  Coarse registration completed. Mean deformation: {np.mean(np.linalg.norm(self.coarse_deformation_field, axis=1)):.6f}")
        
        print(f"\nStage 2: Interpolating coarse deformation to all points...")
        interpolated_deformation = self._interpolate_deformation(
            coarse_source, self.coarse_deformation_field, self.source_original
        )
        
        source_initialized = self.source_original + interpolated_deformation
        
        print(f"Stage 3: Fine Registration (all {num_points} points)")
        reg_fine = DeformableRegistration(
            X=self.target_original,
            Y=source_initialized,
            alpha=self.alpha,
            beta=self.beta,
            w=self.w,
            max_iterations=self.max_iterations,
            tolerance=self.tolerance
        )
        
        result_fine = reg_fine.register()
        self.source_registered = result_fine[0]
        self.deformation_field = self.source_registered - self.source_original
        self.em_history = reg_fine.iteration
        
        print(f"  Fine registration completed. Mean error: {np.mean(np.linalg.norm(self.source_registered - self.target_original, axis=1)):.6f}")
        print("=" * 50)
        
        self._compute_gmm_with_outliers()
        
        return self.source_registered, self.deformation_field
    
    def _interpolate_deformation(self, control_points, control_deformation, query_points):
        try:
            interpolator = RBFInterpolator(
                control_points, control_deformation,
                kernel='thin_plate_spline', smoothing=0.1
            )
            return interpolator(query_points)
        except:
            distances = cdist(query_points, control_points)
            weights = 1.0 / (distances + 1e-8)
            weights = weights / np.sum(weights, axis=1, keepdims=True)
            return weights @ control_deformation
    
    def _apply_anisotropic_scaling(self, deformation_field):
        if not self.use_anisotropic:
            return deformation_field
        
        weights = np.array(self.anisotropic_weights, dtype=np.float64)
        return deformation_field * weights
    
    def _robust_kernel_weight(self, distances):
        if not self.use_robust_kernel:
            return np.ones_like(distances)
        
        kernel_type = self.robust_kernel.lower()
        c = self.kernel_param
        
        if kernel_type == 'huber':
            mask = distances <= c
            weights = np.where(mask, 1.0, c / (distances + 1e-10))
        elif kernel_type == 'tukey':
            mask = distances <= c
            weights = np.where(mask, (1 - (distances / c) ** 2) ** 2, 0.0)
        elif kernel_type == 'lorentzian':
            weights = 1.0 / (1.0 + (distances / c) ** 2)
        elif kernel_type == 'geman_mcclure':
            weights = (c ** 2) / (c ** 2 + distances ** 2) ** 2
        elif kernel_type == 'welsch':
            weights = np.exp(-(distances / c) ** 2)
        else:
            weights = np.ones_like(distances)
        
        return weights
    
    def register_anisotropic(self, source=None, target=None):
        print("=" * 50)
        print("Anisotropic CPD Registration")
        print(f"  Directional weights: {self.anisotropic_weights}")
        print("=" * 50)
        
        if source is not None:
            self.source_original = source
        if target is not None:
            self.target_original = target
        
        if self.source_original is None or self.target_original is None:
            raise ValueError("Source and target point clouds must be provided")
        
        if not self.use_anisotropic:
            print("Warning: Anisotropic weights not set, using isotropic registration")
            return self.register()
        
        source_scaled = self.source_original / self.anisotropic_weights
        target_scaled = self.target_original / self.anisotropic_weights
        
        reg = DeformableRegistration(
            X=target_scaled,
            Y=source_scaled,
            alpha=self.alpha,
            beta=self.beta,
            w=self.w,
            max_iterations=self.max_iterations,
            tolerance=self.tolerance
        )
        
        result = reg.register()
        registered_scaled = result[0]
        
        self.source_registered = registered_scaled * self.anisotropic_weights
        self.deformation_field = self.source_registered - self.source_original
        self.em_history = reg.iteration
        
        self._compute_gmm_with_outliers()
        
        return self.source_registered, self.deformation_field
    
    def register_robust(self, source=None, target=None):
        print("=" * 50)
        print(f"Robust CPD Registration (Kernel: {self.robust_kernel})")
        print(f"  Kernel parameter: {self.kernel_param}")
        print("=" * 50)
        
        if source is not None:
            self.source_original = source
        if target is not None:
            self.target_original = target
        
        if self.source_original is None or self.target_original is None:
            raise ValueError("Source and target point clouds must be provided")
        
        if not self.use_robust_kernel:
            print("Warning: Robust kernel not specified, using standard CPD")
            return self.register()
        
        current_source = self.source_original.copy()
        
        for iteration in range(self.max_iterations):
            reg = DeformableRegistration(
                X=self.target_original,
                Y=current_source,
                alpha=self.alpha,
                beta=self.beta,
                w=self.w,
                max_iterations=3,
                tolerance=self.tolerance
            )
            
            result = reg.register()
            registered = result[0]
            deformation = registered - current_source
            
            distances = np.linalg.norm(registered - self.target_original, axis=1)
            weights = self._robust_kernel_weight(distances)
            
            deformation_weighted = deformation * weights[:, np.newaxis]
            current_source = current_source + deformation_weighted
            
            change = np.mean(np.linalg.norm(deformation_weighted, axis=1))
            if change < self.tolerance:
                print(f"  Converged at iteration {iteration + 1}")
                break
        
        self.source_registered = current_source
        self.deformation_field = self.source_registered - self.source_original
        
        self._compute_gmm_with_outliers()
        
        return self.source_registered, self.deformation_field
    
    def register_sequence(self, source_sequence, target_frame):
        print("=" * 50)
        print("Spatio-Temporal Sequence Registration")
        print(f"  Sequence length: {len(source_sequence)}")
        print(f"  Temporal smoothing: {self.temporal_smoothing}")
        print("=" * 50)
        
        self.sequence_results = []
        self.temporal_buffer.clear()
        
        for i, source in enumerate(source_sequence):
            print(f"\nFrame {i + 1}/{len(source_sequence)}")
            
            if i > 0 and self.temporal_smoothing > 0:
                prev_deformation = self.sequence_results[-1]['deformation_field']
                init_source = source + prev_deformation * self.temporal_smoothing
            else:
                init_source = source.copy()
            
            reg = DeformableRegistration(
                X=target_frame,
                Y=init_source,
                alpha=self.alpha,
                beta=self.beta,
                w=self.w,
                max_iterations=self.max_iterations,
                tolerance=self.tolerance
            )
            
            result = reg.register()
            registered = result[0]
            deformation = registered - source
            
            if len(self.temporal_buffer) >= 2 and self.temporal_smoothing > 0:
                prev_deformations = [r['deformation_field'] for r in self.sequence_results[-2:]]
                smoothed_deformation = self._temporal_smooth(deformation, prev_deformations)
                registered = source + smoothed_deformation
                deformation = smoothed_deformation
            
            self.temporal_buffer.append(deformation)
            
            frame_result = {
                'frame_index': i,
                'source_original': source,
                'source_registered': registered,
                'deformation_field': deformation,
                'error': np.mean(np.linalg.norm(registered - target_frame, axis=1))
            }
            self.sequence_results.append(frame_result)
            
            print(f"  Mean error: {frame_result['error']:.6f}")
        
        self.source_original = source_sequence[-1]
        self.target_original = target_frame
        self.source_registered = self.sequence_results[-1]['source_registered']
        self.deformation_field = self.sequence_results[-1]['deformation_field']
        
        print("\n" + "=" * 50)
        print("Sequence registration completed!")
        print("=" * 50)
        
        return self.sequence_results
    
    def _temporal_smooth(self, current_deformation, previous_deformations):
        if not previous_deformations or self.temporal_smoothing == 0:
            return current_deformation
        
        alpha = self.temporal_smoothing
        smoothed = current_deformation.copy()
        
        for i, prev_def in enumerate(reversed(previous_deformations)):
            weight = alpha * (0.5 ** i)
            smoothed = smoothed * (1 - weight) + prev_def * weight
        
        return smoothed
    
    def visualize_sequence_results(self, save_path=None, subsample=5):
        if not self.sequence_results:
            raise ValueError("No sequence results available. Run register_sequence() first.")
        
        num_frames = len(self.sequence_results)
        num_cols = min(4, num_frames)
        num_rows = (num_frames + num_cols - 1) // num_cols
        
        fig = plt.figure(figsize=(5 * num_cols, 5 * num_rows))
        
        for i, result in enumerate(self.sequence_results):
            ax = fig.add_subplot(num_rows, num_cols, i + 1, projection='3d')
            
            source_sampled = result['source_original'][::subsample]
            registered_sampled = result['source_registered'][::subsample]
            target_sampled = self.target_original[::subsample]
            
            ax.scatter(source_sampled[:, 0], source_sampled[:, 1], source_sampled[:, 2],
                      c='blue', s=15, alpha=0.4, label='Source')
            ax.scatter(registered_sampled[:, 0], registered_sampled[:, 1], registered_sampled[:, 2],
                      c='green', s=15, alpha=0.6, label='Registered')
            ax.scatter(target_sampled[:, 0], target_sampled[:, 1], target_sampled[:, 2],
                      c='red', s=15, alpha=0.4, label='Target')
            
            ax.set_title(f'Frame {i + 1} (Error: {result["error"]:.4f})')
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            ax.set_zlabel('Z')
            
            if i == 0:
                ax.legend()
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
        plt.show()
        
        fig, ax = plt.figure(figsize=(10, 4)), plt.gca()
        errors = [r['error'] for r in self.sequence_results]
        ax.plot(range(1, num_frames + 1), errors, 'bo-', linewidth=2, markersize=6)
        ax.set_xlabel('Frame')
        ax.set_ylabel('Mean Registration Error')
        ax.set_title('Registration Error Over Sequence')
        ax.grid(True, alpha=0.3)
        
        if save_path:
            base, ext = os.path.splitext(save_path)
            plt.savefig(base + '_error' + ext, dpi=150)
        plt.show()
    
    def visualize_anisotropic_comparison(self, save_path=None):
        if not self.use_anisotropic:
            print("Anisotropic weights not set.")
            return
        
        iso_reg = NonRigidCPDRegistration(
            alpha=self.alpha, beta=self.beta, max_iterations=self.max_iterations,
            tolerance=self.tolerance, w=self.w, use_two_stage=False,
            anisotropic_weights=None
        )
        iso_reg.source_original = self.source_original.copy()
        iso_reg.target_original = self.target_original.copy()
        iso_reg._single_stage_register()
        
        fig = plt.figure(figsize=(20, 8))
        
        ax1 = fig.add_subplot(231, projection='3d')
        ax1.scatter(iso_reg.source_registered[:, 0], iso_reg.source_registered[:, 1], iso_reg.source_registered[:, 2],
                   c='blue', s=15, alpha=0.6, label='Isotropic')
        ax1.scatter(self.target_original[:, 0], self.target_original[:, 1], self.target_original[:, 2],
                   c='red', s=15, alpha=0.3, label='Target')
        ax1.set_title('Isotropic Registration')
        ax1.legend()
        
        ax2 = fig.add_subplot(232, projection='3d')
        ax2.scatter(self.source_registered[:, 0], self.source_registered[:, 1], self.source_registered[:, 2],
                   c='green', s=15, alpha=0.6, label='Anisotropic')
        ax2.scatter(self.target_original[:, 0], self.target_original[:, 1], self.target_original[:, 2],
                   c='red', s=15, alpha=0.3, label='Target')
        ax2.set_title(f'Anisotropic Registration {self.anisotropic_weights}')
        ax2.legend()
        
        ax3 = fig.add_subplot(233, projection='3d')
        iso_error = np.linalg.norm(iso_reg.source_registered - self.target_original, axis=1)
        ani_error = np.linalg.norm(self.source_registered - self.target_original, axis=1)
        ax3.scatter(self.source_original[:, 0], self.source_original[:, 1], self.source_original[:, 2],
                   c=ani_error - iso_error, cmap='coolwarm', s=20, alpha=0.8)
        ax3.set_title('Error Difference (Anisotropic - Isotropic)')
        
        ax4 = fig.add_subplot(234)
        deform_iso = iso_reg.deformation_field
        deform_ani = self.deformation_field
        ax4.scatter(deform_iso[:, 0], deform_iso[:, 1], c='blue', s=10, alpha=0.5, label='Isotropic')
        ax4.scatter(deform_ani[:, 0], deform_ani[:, 1], c='green', s=10, alpha=0.5, label='Anisotropic')
        ax4.set_xlabel('X Deformation')
        ax4.set_ylabel('Y Deformation')
        ax4.set_title('Deformation Distribution (XY)')
        ax4.legend()
        ax4.set_aspect('equal')
        
        ax5 = fig.add_subplot(235)
        ax5.scatter(deform_iso[:, 0], deform_iso[:, 2], c='blue', s=10, alpha=0.5, label='Isotropic')
        ax5.scatter(deform_ani[:, 0], deform_ani[:, 2], c='green', s=10, alpha=0.5, label='Anisotropic')
        ax5.set_xlabel('X Deformation')
        ax5.set_ylabel('Z Deformation')
        ax5.set_title('Deformation Distribution (XZ)')
        ax5.legend()
        ax5.set_aspect('equal')
        
        ax6 = fig.add_subplot(236)
        directions = ['X', 'Y', 'Z']
        iso_means = [np.mean(np.abs(deform_iso[:, i])) for i in range(3)]
        ani_means = [np.mean(np.abs(deform_ani[:, i])) for i in range(3)]
        x = np.arange(3)
        width = 0.35
        ax6.bar(x - width/2, iso_means, width, label='Isotropic', alpha=0.7)
        ax6.bar(x + width/2, ani_means, width, label='Anisotropic', alpha=0.7)
        ax6.set_xticks(x)
        ax6.set_xticklabels(directions)
        ax6.set_ylabel('Mean |Deformation|')
        ax6.set_title('Directional Deformation Comparison')
        ax6.legend()
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
        plt.show()
    
    def visualize_robust_kernel_comparison(self, save_path=None):
        if not self.use_robust_kernel:
            print("Robust kernel not set.")
            return
        
        std_reg = NonRigidCPDRegistration(
            alpha=self.alpha, beta=self.beta, max_iterations=self.max_iterations,
            tolerance=self.tolerance, w=self.w, use_two_stage=False
        )
        std_reg.source_original = self.source_original.copy()
        std_reg.target_original = self.target_original.copy()
        std_reg._single_stage_register()
        
        fig = plt.figure(figsize=(20, 6))
        
        ax1 = fig.add_subplot(131, projection='3d')
        ax1.scatter(std_reg.source_registered[:, 0], std_reg.source_registered[:, 1], std_reg.source_registered[:, 2],
                   c='blue', s=15, alpha=0.6, label='Standard CPD')
        ax1.scatter(self.target_original[:, 0], self.target_original[:, 1], self.target_original[:, 2],
                   c='red', s=15, alpha=0.3, label='Target')
        ax1.set_title('Standard CPD')
        ax1.legend()
        
        ax2 = fig.add_subplot(132, projection='3d')
        ax2.scatter(self.source_registered[:, 0], self.source_registered[:, 1], self.source_registered[:, 2],
                   c='green', s=15, alpha=0.6, label=f'Robust ({self.robust_kernel})')
        ax2.scatter(self.target_original[:, 0], self.target_original[:, 1], self.target_original[:, 2],
                   c='red', s=15, alpha=0.3, label='Target')
        ax2.set_title(f'Robust CPD ({self.robust_kernel} kernel)')
        ax2.legend()
        
        ax3 = fig.add_subplot(133)
        std_errors = np.sort(np.linalg.norm(std_reg.source_registered - self.target_original, axis=1))
        rob_errors = np.sort(np.linalg.norm(self.source_registered - self.target_original, axis=1))
        ax3.plot(std_errors, np.linspace(0, 1, len(std_errors)), 'b-', label='Standard CPD', linewidth=2)
        ax3.plot(rob_errors, np.linspace(0, 1, len(rob_errors)), 'g-', label=f'Robust CPD', linewidth=2)
        ax3.set_xlabel('Registration Error')
        ax3.set_ylabel('Cumulative Probability')
        ax3.set_title('CDF of Registration Errors')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
        plt.show()
    
    def generate_synthetic_sequence(self, num_frames=10, num_points=300, 
                                     shape='sphere', deformation_scale=0.3,
                                     motion_type='wave'):
        source_base = self._generate_sphere(num_points) if shape == 'sphere' else self._generate_plane(num_points)
        
        sequence = []
        for i in range(num_frames):
            t = i / (num_frames - 1)
            source = source_base.copy()
            
            if motion_type == 'wave':
                phase = 2 * np.pi * t
                source[:, 0] += 0.1 * np.sin(phase + 2 * np.pi * source[:, 1])
                source[:, 1] += 0.05 * np.cos(phase + 2 * np.pi * source[:, 0])
                source[:, 2] += 0.08 * np.sin(2 * phase + np.pi * source[:, 0] * source[:, 1])
            elif motion_type == 'expansion':
                scale = 1.0 + 0.3 * t
                source *= scale
            elif motion_type == 'rotation':
                theta = np.pi * t
                R = np.array([[np.cos(theta), -np.sin(theta), 0],
                             [np.sin(theta), np.cos(theta), 0],
                             [0, 0, 1]])
                source = source @ R.T
            
            sequence.append(source)
        
        target = self._apply_nonrigid_deformation(source_base, deformation_scale)
        
        return sequence, target
    
    def _compute_gmm_with_outliers(self, outlier_threshold=2.0):
        N = self.target_original.shape[0]
        M = self.source_original.shape[0]
        D = self.source_original.shape[1]
        
        sigma2 = np.mean(np.min(cdist(self.target_original, self.source_registered), axis=1))
        
        distances = cdist(self.target_original, self.source_registered)
        P = np.exp(-distances ** 2 / (2 * sigma2))
        
        noise_component = np.ones((N, 1)) * self.w * (2 * np.pi * sigma2 * 10) ** (-D / 2)
        P_with_noise = np.hstack([P, noise_component])
        
        P_normalized = P_with_noise / (np.sum(P_with_noise, axis=1, keepdims=True) + 1e-10)
        P = P_normalized[:, :-1]
        outlier_probs = P_normalized[:, -1]
        
        self.outlier_labels = outlier_probs > np.mean(outlier_probs) + outlier_threshold * np.std(outlier_probs)
        
        N_p = np.sum(P)
        mu = self.source_registered
        
        inlier_distances = distances[~self.outlier_labels] if np.sum(self.outlier_labels) > 0 else distances
        noise_mean = np.mean(inlier_distances) + 3 * np.std(inlier_distances)
        noise_cov = np.eye(D) * max(sigma2 * 10, 0.1)
        
        self.gmm_params = {
            'responsibilities': P,
            'means': mu,
            'sigma2': sigma2,
            'N_p': N_p,
            'mixture_weights': np.sum(P, axis=0) / N_p,
            'outlier_probabilities': outlier_probs,
            'outlier_mask': self.outlier_labels,
            'noise_component': {
                'mean': noise_mean,
                'covariance': noise_cov,
                'weight': np.mean(outlier_probs)
            },
            'num_outliers': np.sum(self.outlier_labels),
            'outlier_ratio': np.sum(self.outlier_labels) / N
        }
    
    def _compute_gmm_params(self):
        self._compute_gmm_with_outliers()
        
    def visualize_point_clouds(self, save_path=None):
        fig = plt.figure(figsize=(20, 6))
        
        ax1 = fig.add_subplot(131, projection='3d')
        ax1.scatter(self.source_original[:, 0], self.source_original[:, 1], self.source_original[:, 2],
                    c='blue', s=20, alpha=0.6, label='Source')
        ax1.scatter(self.target_original[:, 0], self.target_original[:, 1], self.target_original[:, 2],
                    c='red', s=20, alpha=0.6, label='Target')
        ax1.set_title('Before Registration')
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_zlabel('Z')
        ax1.legend()
        
        ax2 = fig.add_subplot(132, projection='3d')
        ax2.scatter(self.source_registered[:, 0], self.source_registered[:, 1], self.source_registered[:, 2],
                    c='green', s=20, alpha=0.6, label='Registered Source')
        ax2.scatter(self.target_original[:, 0], self.target_original[:, 1], self.target_original[:, 2],
                    c='red', s=20, alpha=0.6, label='Target')
        ax2.set_title('After Registration')
        ax2.set_xlabel('X')
        ax2.set_ylabel('Y')
        ax2.set_zlabel('Z')
        ax2.legend()
        
        ax3 = fig.add_subplot(133, projection='3d')
        errors = np.linalg.norm(self.source_registered - self.target_original, axis=1)
        scatter = ax3.scatter(self.source_registered[:, 0], self.source_registered[:, 1], self.source_registered[:, 2],
                              c=errors, cmap='viridis', s=20, alpha=0.8)
        ax3.set_title('Registration Error Distribution')
        ax3.set_xlabel('X')
        ax3.set_ylabel('Y')
        ax3.set_zlabel('Z')
        plt.colorbar(scatter, ax=ax3, label='Error')
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
        plt.show()
    
    def visualize_deformation_field(self, save_path=None, subsample=20):
        source_sampled = self.source_original[::subsample]
        deformed_sampled = self.source_registered[::subsample]
        
        fig = plt.figure(figsize=(15, 6))
        
        ax1 = fig.add_subplot(121, projection='3d')
        ax1.scatter(source_sampled[:, 0], source_sampled[:, 1], source_sampled[:, 2],
                    c='blue', s=30, alpha=0.8, label='Original Source')
        ax1.scatter(deformed_sampled[:, 0], deformed_sampled[:, 1], deformed_sampled[:, 2],
                    c='green', s=30, alpha=0.8, label='Deformed Source')
        
        for i in range(len(source_sampled)):
            ax1.plot([source_sampled[i, 0], deformed_sampled[i, 0]],
                     [source_sampled[i, 1], deformed_sampled[i, 1]],
                     [source_sampled[i, 2], deformed_sampled[i, 2]],
                     'gray', alpha=0.5, linewidth=1)
        
        ax1.set_title('Point-wise Deformation Vectors')
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_zlabel('Z')
        ax1.legend()
        
        ax2 = fig.add_subplot(122, projection='3d')
        displacements = self.deformation_field[::subsample]
        magnitudes = np.linalg.norm(displacements, axis=1)
        
        quiver = ax2.quiver(source_sampled[:, 0], source_sampled[:, 1], source_sampled[:, 2],
                            displacements[:, 0], displacements[:, 1], displacements[:, 2],
                            cmap='jet', linewidth=1.5, length=0.5, normalize=True)
        ax2.scatter(source_sampled[:, 0], source_sampled[:, 1], source_sampled[:, 2],
                    c=magnitudes, cmap='jet', s=50, alpha=0.8)
        
        ax2.set_title('Deformation Field (Vector Field)')
        ax2.set_xlabel('X')
        ax2.set_ylabel('Y')
        ax2.set_zlabel('Z')
        plt.colorbar(quiver, ax=ax2, label='Displacement Magnitude')
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
        plt.show()
    
    def visualize_deformation_magnitude(self, save_path=None):
        magnitudes = np.linalg.norm(self.deformation_field, axis=1)
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        ax1 = axes[0, 0]
        scatter1 = ax1.scatter(self.source_original[:, 0], self.source_original[:, 1],
                               c=magnitudes, cmap='jet', s=30, alpha=0.8)
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_title('Deformation Magnitude - XY Plane')
        plt.colorbar(scatter1, ax=ax1, label='Magnitude')
        
        ax2 = axes[0, 1]
        scatter2 = ax2.scatter(self.source_original[:, 0], self.source_original[:, 2],
                               c=magnitudes, cmap='jet', s=30, alpha=0.8)
        ax2.set_xlabel('X')
        ax2.set_ylabel('Z')
        ax2.set_title('Deformation Magnitude - XZ Plane')
        plt.colorbar(scatter2, ax=ax2, label='Magnitude')
        
        ax3 = axes[1, 0]
        scatter3 = ax3.scatter(self.source_original[:, 1], self.source_original[:, 2],
                               c=magnitudes, cmap='jet', s=30, alpha=0.8)
        ax3.set_xlabel('Y')
        ax3.set_ylabel('Z')
        ax3.set_title('Deformation Magnitude - YZ Plane')
        plt.colorbar(scatter3, ax=ax3, label='Magnitude')
        
        ax4 = axes[1, 1]
        ax4.hist(magnitudes, bins=30, edgecolor='black', alpha=0.7)
        ax4.set_xlabel('Deformation Magnitude')
        ax4.set_ylabel('Frequency')
        ax4.set_title('Deformation Magnitude Distribution')
        ax4.axvline(np.mean(magnitudes), color='red', linestyle='--', 
                    label=f'Mean: {np.mean(magnitudes):.4f}')
        ax4.legend()
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
        plt.show()
    
    def visualize_gmm_components(self, save_path=None, num_components=10):
        if self.gmm_params is None:
            raise ValueError("GMM parameters not computed. Run register() first.")
        
        fig = plt.figure(figsize=(18, 6))
        
        ax1 = fig.add_subplot(131, projection='3d')
        ax1.scatter(self.target_original[:, 0], self.target_original[:, 1], self.target_original[:, 2],
                    c='gray', s=10, alpha=0.3, label='Target Points')
        
        indices = np.random.choice(self.source_registered.shape[0], num_components, replace=False)
        colors = plt.cm.rainbow(np.linspace(0, 1, num_components))
        
        for i, idx in enumerate(indices):
            mu = self.gmm_params['means'][idx]
            ax1.scatter(mu[0], mu[1], mu[2], c=[colors[i]], s=100, marker='*', 
                       label=f'GMM Component {idx}')
        
        ax1.set_title(f'GMM Component Centers ({num_components} samples)')
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_zlabel('Z')
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        ax2 = fig.add_subplot(132)
        weights = self.gmm_params['mixture_weights']
        sorted_indices = np.argsort(weights)[::-1]
        ax2.bar(range(len(sorted_indices[:50])), weights[sorted_indices[:50]])
        ax2.set_xlabel('Component Index (sorted)')
        ax2.set_ylabel('Mixture Weight')
        ax2.set_title('Top 50 GMM Component Weights')
        ax2.set_xticks(range(0, 50, 5))
        
        ax3 = fig.add_subplot(133, projection='3d')
        outlier_mask = self.gmm_params['outlier_mask']
        ax3.scatter(self.target_original[~outlier_mask, 0], 
                    self.target_original[~outlier_mask, 1], 
                    self.target_original[~outlier_mask, 2],
                    c='blue', s=15, alpha=0.5, label='Inliers')
        ax3.scatter(self.target_original[outlier_mask, 0], 
                    self.target_original[outlier_mask, 1], 
                    self.target_original[outlier_mask, 2],
                    c='red', s=30, alpha=0.8, marker='x', 
                    label=f'Outliers ({np.sum(outlier_mask)})')
        ax3.set_title('Outlier Detection')
        ax3.set_xlabel('X')
        ax3.set_ylabel('Y')
        ax3.set_zlabel('Z')
        ax3.legend()
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
        plt.show()
    
    def visualize_deformation_streamlines(self, save_path=None, num_seed_points=20, integration_steps=10):
        if self.deformation_field is None:
            raise ValueError("Registration not performed. Run register() first.")
        
        print("Generating deformation streamlines...")
        
        magnitudes = np.linalg.norm(self.deformation_field, axis=1)
        seed_indices = np.random.choice(
            self.source_original.shape[0], 
            num_seed_points, 
            replace=False,
            p=magnitudes / np.sum(magnitudes)
        )
        seed_points = self.source_original[seed_indices]
        
        try:
            interpolator = RBFInterpolator(
                self.source_original, self.deformation_field,
                kernel='thin_plate_spline', smoothing=0.05
            )
        except:
            def interpolator(pts):
                dists = cdist(pts, self.source_original)
                weights = 1.0 / (dists + 1e-8)
                weights = weights / np.sum(weights, axis=1, keepdims=True)
                return weights @ self.deformation_field
        
        streamlines = []
        for seed in seed_points:
            streamline = [seed.copy()]
            current = seed.copy()
            
            for _ in range(integration_steps):
                if current.ndim == 1:
                    current_batch = current.reshape(1, -1)
                else:
                    current_batch = current
                
                velocity = interpolator(current_batch)
                if velocity.ndim == 2:
                    velocity = velocity[0]
                
                step_size = 0.1
                current = current + velocity * step_size
                streamline.append(current.copy())
            
            streamlines.append(np.array(streamline))
        
        fig = plt.figure(figsize=(20, 8))
        
        ax1 = fig.add_subplot(121, projection='3d')
        scatter = ax1.scatter(self.source_original[:, 0], self.source_original[:, 1], self.source_original[:, 2],
                              c=magnitudes, cmap='viridis', s=10, alpha=0.3)
        
        for i, sl in enumerate(streamlines):
            color = plt.cm.jet(i / len(streamlines))
            ax1.plot(sl[:, 0], sl[:, 1], sl[:, 2], color=color, linewidth=2, alpha=0.8)
            ax1.scatter(sl[0, 0], sl[0, 1], sl[0, 2], c=[color], s=50, marker='o', edgecolors='black')
            ax1.scatter(sl[-1, 0], sl[-1, 1], sl[-1, 2], c=[color], s=50, marker='s', edgecolors='black')
        
        ax1.set_title('3D Deformation Streamlines')
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_zlabel('Z')
        plt.colorbar(scatter, ax=ax1, label='Deformation Magnitude')
        
        ax2 = fig.add_subplot(122)
        ax2.scatter(self.source_original[:, 0], self.source_original[:, 1],
                    c=magnitudes, cmap='viridis', s=10, alpha=0.3)
        
        for i, sl in enumerate(streamlines):
            color = plt.cm.jet(i / len(streamlines))
            ax2.plot(sl[:, 0], sl[:, 1], color=color, linewidth=2, alpha=0.8)
            ax2.scatter(sl[0, 0], sl[0, 1], c=[color], s=50, marker='o', edgecolors='black')
            ax2.scatter(sl[-1, 0], sl[-1, 1], c=[color], s=50, marker='s', edgecolors='black')
        
        ax2.set_title('2D Projection (XY Plane)')
        ax2.set_xlabel('X')
        ax2.set_ylabel('Y')
        ax2.set_aspect('equal')
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
        plt.show()
        
        return streamlines
    
    def visualize_critical_regions(self, save_path=None, num_regions=5):
        if self.deformation_field is None:
            raise ValueError("Registration not performed. Run register() first.")
        
        magnitudes = np.linalg.norm(self.deformation_field, axis=1)
        
        print(f"Detecting {num_regions} critical regions...")
        kmeans = KMeans(n_clusters=num_regions * 3, random_state=42, n_init=10)
        kmeans.fit(self.source_original)
        
        region_stats = []
        for i in range(num_regions * 3):
            mask = kmeans.labels_ == i
            if np.sum(mask) > 5:
                region_mag = magnitudes[mask]
                region_stats.append({
                    'center': kmeans.cluster_centers_[i],
                    'mean_magnitude': np.mean(region_mag),
                    'max_magnitude': np.max(region_mag),
                    'num_points': np.sum(mask),
                    'points': self.source_original[mask]
                })
        
        region_stats.sort(key=lambda x: x['max_magnitude'], reverse=True)
        critical_regions = region_stats[:num_regions]
        
        fig = plt.figure(figsize=(20, 8))
        
        ax1 = fig.add_subplot(121, projection='3d')
        scatter = ax1.scatter(self.source_original[:, 0], self.source_original[:, 1], self.source_original[:, 2],
                              c=magnitudes, cmap='viridis', s=10, alpha=0.2)
        
        colors = plt.cm.tab10(np.linspace(0, 1, num_regions))
        for i, region in enumerate(critical_regions):
            ax1.scatter(region['points'][:, 0], region['points'][:, 1], region['points'][:, 2],
                        c=[colors[i]], s=30, alpha=0.8, 
                        label=f'Region {i+1} (max={region["max_magnitude"]:.3f})')
            
            center = region['center']
            radius = np.max(np.linalg.norm(region['points'] - center, axis=1))
            u, v = np.mgrid[0:2*np.pi:20j, 0:np.pi:10j]
            x = center[0] + radius * np.cos(u) * np.sin(v)
            y = center[1] + radius * np.sin(u) * np.sin(v)
            z = center[2] + radius * np.cos(v)
            ax1.plot_wireframe(x, y, z, color=colors[i], alpha=0.2, linewidth=0.5)
        
        ax1.set_title(f'Critical Deformation Regions (Top {num_regions})')
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_zlabel('Z')
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        plt.colorbar(scatter, ax=ax1, label='Deformation Magnitude')
        
        ax2 = fig.add_subplot(122)
        region_names = [f'Region {i+1}' for i in range(num_regions)]
        max_mags = [r['max_magnitude'] for r in critical_regions]
        mean_mags = [r['mean_magnitude'] for r in critical_regions]
        
        x = np.arange(num_regions)
        width = 0.35
        ax2.bar(x - width/2, max_mags, width, label='Max Deformation', alpha=0.8)
        ax2.bar(x + width/2, mean_mags, width, label='Mean Deformation', alpha=0.8)
        ax2.set_xlabel('Critical Regions')
        ax2.set_ylabel('Deformation Magnitude')
        ax2.set_title('Region Deformation Statistics')
        ax2.set_xticks(x)
        ax2.set_xticklabels(region_names)
        ax2.legend()
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
        plt.show()
        
        return critical_regions
    
    def visualize_two_stage_progress(self, save_path=None):
        if not self.use_two_stage or self.coarse_deformation_field is None:
            print("Two-stage registration was not used.")
            return
        
        coarse_points = self.source_original[self.coarse_source_indices]
        coarse_deformed = coarse_points + self.coarse_deformation_field
        
        fig = plt.figure(figsize=(20, 6))
        
        ax1 = fig.add_subplot(131, projection='3d')
        ax1.scatter(coarse_points[:, 0], coarse_points[:, 1], coarse_points[:, 2],
                    c='blue', s=50, alpha=0.8, label='Coarse Samples')
        ax1.scatter(self.target_original[:, 0], self.target_original[:, 1], self.target_original[:, 2],
                    c='red', s=10, alpha=0.2, label='Target')
        ax1.set_title('Stage 1: Coarse Sampling')
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_zlabel('Z')
        ax1.legend()
        
        ax2 = fig.add_subplot(132, projection='3d')
        ax2.scatter(coarse_deformed[:, 0], coarse_deformed[:, 1], coarse_deformed[:, 2],
                    c='green', s=50, alpha=0.8, label='Registered Coarse')
        ax2.scatter(coarse_points[:, 0], coarse_points[:, 1], coarse_points[:, 2],
                    c='blue', s=50, alpha=0.3, label='Original Coarse')
        ax2.scatter(self.target_original[:, 0], self.target_original[:, 1], self.target_original[:, 2],
                    c='red', s=10, alpha=0.2, label='Target')
        ax2.set_title('Stage 1: Coarse Registration Result')
        ax2.set_xlabel('X')
        ax2.set_ylabel('Y')
        ax2.set_zlabel('Z')
        ax2.legend()
        
        ax3 = fig.add_subplot(133, projection='3d')
        ax3.scatter(self.source_registered[:, 0], self.source_registered[:, 1], self.source_registered[:, 2],
                    c='green', s=10, alpha=0.5, label='Fine Registered')
        ax3.scatter(self.target_original[:, 0], self.target_original[:, 1], self.target_original[:, 2],
                    c='red', s=10, alpha=0.5, label='Target')
        ax3.set_title('Stage 2: Fine Registration Result')
        ax3.set_xlabel('X')
        ax3.set_ylabel('Y')
        ax3.set_zlabel('Z')
        ax3.legend()
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
        plt.show()
    
    def evaluate_registration(self):
        if self.source_registered is None:
            raise ValueError("Registration not performed. Run register() first.")
        
        before_error = np.mean(np.linalg.norm(self.source_original - self.target_original, axis=1))
        after_error = np.mean(np.linalg.norm(self.source_registered - self.target_original, axis=1))
        rmse = np.sqrt(np.mean(np.linalg.norm(self.source_registered - self.target_original, axis=1) ** 2))
        
        metrics = {
            'initial_mean_error': before_error,
            'final_mean_error': after_error,
            'rmse': rmse,
            'error_reduction': (before_error - after_error) / before_error * 100,
            'max_deformation': np.max(np.linalg.norm(self.deformation_field, axis=1)),
            'mean_deformation': np.mean(np.linalg.norm(self.deformation_field, axis=1))
        }
        
        if self.gmm_params is not None and 'num_outliers' in self.gmm_params:
            metrics['num_outliers'] = self.gmm_params['num_outliers']
            metrics['outlier_ratio'] = self.gmm_params['outlier_ratio']
        
        if self.use_two_stage:
            metrics['two_stage'] = True
            metrics['coarse_samples'] = len(self.coarse_source_indices) if self.coarse_source_indices is not None else 0
        
        print("=" * 50)
        print("Registration Evaluation Metrics")
        print("=" * 50)
        print(f"Initial Mean Error:    {before_error:.6f}")
        print(f"Final Mean Error:      {after_error:.6f}")
        print(f"RMSE:                  {rmse:.6f}")
        print(f"Error Reduction:       {metrics['error_reduction']:.2f}%")
        print(f"Max Deformation:       {metrics['max_deformation']:.6f}")
        print(f"Mean Deformation:      {metrics['mean_deformation']:.6f}")
        
        if self.gmm_params is not None and 'num_outliers' in self.gmm_params:
            print(f"Detected Outliers:     {self.gmm_params['num_outliers']} ({self.gmm_params['outlier_ratio']*100:.2f}%)")
        
        if self.use_two_stage and self.coarse_source_indices is not None:
            print(f"Two-Stage Enabled:     Yes (coarse samples: {len(self.coarse_source_indices)})")
        else:
            print(f"Two-Stage Enabled:     No")
        
        print("=" * 50)
        
        return metrics
    
    def save_results(self, output_dir='./results'):
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        np.save(os.path.join(output_dir, 'source_original.npy'), self.source_original)
        np.save(os.path.join(output_dir, 'target_original.npy'), self.target_original)
        np.save(os.path.join(output_dir, 'source_registered.npy'), self.source_registered)
        np.save(os.path.join(output_dir, 'deformation_field.npy'), self.deformation_field)
        
        if OPEN3D_AVAILABLE:
            source_pcd = o3d.geometry.PointCloud()
            source_pcd.points = o3d.utility.Vector3dVector(self.source_registered)
            o3d.io.write_point_cloud(os.path.join(output_dir, 'source_registered.ply'), source_pcd)
            
            target_pcd = o3d.geometry.PointCloud()
            target_pcd.points = o3d.utility.Vector3dVector(self.target_original)
            o3d.io.write_point_cloud(os.path.join(output_dir, 'target.ply'), target_pcd)
        
        print(f"Results saved to {output_dir}/")
    
    def visualize_open3d(self):
        if not OPEN3D_AVAILABLE:
            raise ImportError("Open3D is required for 3D visualization.")
        
        source_pcd = o3d.geometry.PointCloud()
        source_pcd.points = o3d.utility.Vector3dVector(self.source_original)
        source_pcd.paint_uniform_color([0, 0, 1])
        
        registered_pcd = o3d.geometry.PointCloud()
        registered_pcd.points = o3d.utility.Vector3dVector(self.source_registered)
        registered_pcd.paint_uniform_color([0, 1, 0])
        
        target_pcd = o3d.geometry.PointCloud()
        target_pcd.points = o3d.utility.Vector3dVector(self.target_original)
        target_pcd.paint_uniform_color([1, 0, 0])
        
        o3d.visualization.draw_geometries([source_pcd, target_pcd], 
                                          window_name='Before Registration (Blue: Source, Red: Target)')
        o3d.visualization.draw_geometries([registered_pcd, target_pcd],
                                          window_name='After Registration (Green: Registered, Red: Target)')


def main():
    print("=" * 60)
    print("Non-Rigid Point Cloud Registration using CPD Algorithm")
    print("Advanced Features: Two-Stage + Streamlines + Outlier GMM")
    print("=" * 60)
    
    cpd_reg = NonRigidCPDRegistration(
        alpha=2.0,
        beta=0.5,
        max_iterations=50,
        tolerance=1e-6,
        w=0.1,
        use_two_stage=True,
        coarse_sample_ratio=0.4,
        coarse_max_iter=20
    )
    
    print("\nGenerating synthetic point cloud data...")
    source, target = cpd_reg.generate_synthetic_data(num_points=500, shape='sphere', deformation_scale=0.25)
    print(f"Source points: {source.shape[0]}, Target points: {target.shape[0]}")
    
    print("\nPerforming two-stage non-rigid registration...")
    registered, deformation = cpd_reg.register()
    
    print("\nEvaluating registration results...")
    metrics = cpd_reg.evaluate_registration()
    
    print("\nGenerating visualizations...")
    cpd_reg.visualize_point_clouds(save_path='./results/point_clouds.png')
    cpd_reg.visualize_two_stage_progress(save_path='./results/two_stage_progress.png')
    cpd_reg.visualize_deformation_streamlines(save_path='./results/deformation_streamlines.png', num_seed_points=15)
    cpd_reg.visualize_critical_regions(save_path='./results/critical_regions.png', num_regions=5)
    cpd_reg.visualize_gmm_components(save_path='./results/gmm_outliers.png', num_components=10)
    
    print("\nSaving results...")
    cpd_reg.save_results('./results')
    
    print("\nDone! Check the results directory for output files.")
    
    return cpd_reg


if __name__ == '__main__':
    registration = main()
