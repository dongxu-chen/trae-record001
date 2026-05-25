import numpy as np
from typing import Tuple, Optional

try:
    from numba import cuda, float64, int32
    _CUDA_AVAILABLE = True
except ImportError:
    _CUDA_AVAILABLE = False
    cuda = None
    float64 = None
    int32 = None


def is_cuda_available() -> bool:
    if not _CUDA_AVAILABLE:
        return False
    try:
        return cuda.is_available()
    except:
        return False


def get_device_count() -> int:
    if not is_cuda_available():
        return 0
    try:
        return len(cuda.list_devices())
    except:
        return 0


class GPUAccelerator:
    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu and is_cuda_available()
        self._device = None
        
        if self.use_gpu:
            self._init_gpu()
        
        self._threads_per_block = 256
        
        self._d_positions = None
        self._d_velocities = None
        self._d_forces = None
        self._d_p1_indices = None
        self._d_p2_indices = None
        self._d_rest_lengths = None
        self._d_stiffnesses = None
        self._d_masses = None
        self._d_pinned_mask = None
        
        self._n_points = 0
        self._n_springs = 0
    
    def _init_gpu(self):
        try:
            self._device = cuda.get_current_device()
            self._threads_per_block = min(256, self._device.WARP_SIZE * 8)
            print(f"GPU Accelerator initialized with device: {self._device.name}")
            print(f"  Compute capability: {self._device.compute_capability}")
            print(f"  Multiprocessors: {self._device.MULTIPROCESSOR_COUNT}")
        except Exception as e:
            print(f"GPU initialization failed: {e}, falling back to CPU")
            self.use_gpu = False
    
    def _allocate_buffers(self, n_points: int, n_springs: int):
        if not self.use_gpu:
            return
        
        if n_points != self._n_points or n_springs != self._n_springs:
            self._d_positions = cuda.device_array((n_points, 3), dtype=np.float64)
            self._d_velocities = cuda.device_array((n_points, 3), dtype=np.float64)
            self._d_forces = cuda.device_array((n_points, 3), dtype=np.float64)
            self._d_masses = cuda.device_array(n_points, dtype=np.float64)
            self._d_pinned_mask = cuda.device_array(n_points, dtype=np.bool_)
            
            if n_springs > 0:
                self._d_p1_indices = cuda.device_array(n_springs, dtype=np.int32)
                self._d_p2_indices = cuda.device_array(n_springs, dtype=np.int32)
                self._d_rest_lengths = cuda.device_array(n_springs, dtype=np.float64)
                self._d_stiffnesses = cuda.device_array(n_springs, dtype=np.float64)
            
            self._n_points = n_points
            self._n_springs = n_springs
    
    def copy_to_device(self, positions: np.ndarray, velocities: np.ndarray,
                       masses: np.ndarray, pinned_mask: np.ndarray,
                       spring_data: Optional[Tuple[np.ndarray, ...]] = None):
        if not self.use_gpu:
            return
        
        n_points = len(positions)
        n_springs = len(spring_data[0]) if spring_data else 0
        
        self._allocate_buffers(n_points, n_springs)
        
        cuda.to_device(positions.astype(np.float64), to=self._d_positions)
        cuda.to_device(velocities.astype(np.float64), to=self._d_velocities)
        cuda.to_device(masses.astype(np.float64), to=self._d_masses)
        cuda.to_device(pinned_mask.astype(np.bool_), to=self._d_pinned_mask)
        
        if spring_data and n_springs > 0:
            p1_indices, p2_indices, rest_lengths, stiffnesses = spring_data
            cuda.to_device(p1_indices.astype(np.int32), to=self._d_p1_indices)
            cuda.to_device(p2_indices.astype(np.int32), to=self._d_p2_indices)
            cuda.to_device(rest_lengths.astype(np.float64), to=self._d_rest_lengths)
            cuda.to_device(stiffnesses.astype(np.float64), to=self._d_stiffnesses)
    
    def copy_from_device(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not self.use_gpu:
            return np.zeros(0), np.zeros(0), np.zeros(0)
        
        positions = self._d_positions.copy_to_host()
        velocities = self._d_velocities.copy_to_host()
        forces = self._d_forces.copy_to_host()
        
        return positions, velocities, forces
    
    def compute_spring_forces_gpu(self, spring_damping: float = 0.2):
        if not self.use_gpu:
            return
        
        n_springs = self._n_springs
        if n_springs == 0:
            return
        
        blocks_per_grid = (n_springs + self._threads_per_block - 1) // self._threads_per_block
        
        _cuda_compute_spring_forces[blocks_per_grid, self._threads_per_block](
            self._d_positions,
            self._d_velocities,
            self._d_p1_indices,
            self._d_p2_indices,
            self._d_rest_lengths,
            self._d_stiffnesses,
            spring_damping,
            self._d_forces,
            self._d_pinned_mask,
            n_springs
        )
    
    def integrate_euler_gpu(self, dt: float, gravity: np.ndarray,
                            global_damping: float, wind_force: np.ndarray):
        if not self.use_gpu:
            return
        
        n_points = self._n_points
        blocks_per_grid = (n_points + self._threads_per_block - 1) // self._threads_per_block
        
        _cuda_integrate_euler[blocks_per_grid, self._threads_per_block](
            self._d_positions,
            self._d_velocities,
            self._d_forces,
            self._d_masses,
            self._d_pinned_mask,
            np.float64(dt),
            gravity.astype(np.float64),
            np.float64(global_damping),
            wind_force.astype(np.float64),
            n_points
        )
    
    def compute_spring_forces_cpu(self, positions: np.ndarray, velocities: np.ndarray,
                                  p1_indices: np.ndarray, p2_indices: np.ndarray,
                                  rest_lengths: np.ndarray, stiffnesses: np.ndarray,
                                  spring_damping: float, pinned_mask: np.ndarray) -> np.ndarray:
        n_points = len(positions)
        forces = np.zeros((n_points, 3), dtype=np.float64)
        
        for i in range(len(p1_indices)):
            p1 = p1_indices[i]
            p2 = p2_indices[i]
            
            if pinned_mask[p1] and pinned_mask[p2]:
                continue
            
            diff = positions[p1] - positions[p2]
            dist = np.linalg.norm(diff)
            
            if dist < 1e-6:
                continue
            
            direction = diff / dist
            stretch = dist - rest_lengths[i]
            
            vel_diff = velocities[p1] - velocities[p2]
            
            spring_force_mag = stiffnesses[i] * stretch
            damping_force_mag = spring_damping * np.dot(vel_diff, direction)
            
            total_force = -(spring_force_mag + damping_force_mag) * direction
            
            if not pinned_mask[p1]:
                forces[p1] += total_force
            if not pinned_mask[p2]:
                forces[p2] -= total_force
        
        return forces
    
    def integrate_euler_cpu(self, positions: np.ndarray, velocities: np.ndarray,
                            forces: np.ndarray, masses: np.ndarray,
                            pinned_mask: np.ndarray, dt: float,
                            gravity: np.ndarray, global_damping: float,
                            wind_force: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        
        new_positions = positions.copy()
        new_velocities = velocities.copy()
        
        masses_2d = masses[:, np.newaxis]
        
        for i in range(len(positions)):
            if pinned_mask[i]:
                continue
            
            total_force = forces[i] + gravity * masses[i]
            total_force += wind_force * masses[i]
            total_force -= velocities[i] * global_damping
            
            acceleration = total_force / masses_2d[i]
            
            new_velocities[i] = velocities[i] + acceleration * dt
            new_positions[i] = positions[i] + new_velocities[i] * dt
        
        return new_positions, new_velocities


if _CUDA_AVAILABLE and is_cuda_available():
    @cuda.jit
    def _cuda_compute_spring_forces(positions, velocities, p1_indices, p2_indices,
                                     rest_lengths, stiffnesses, spring_damping,
                                     forces, pinned_mask, n_springs):
        idx = cuda.grid(1)
        
        if idx >= n_springs:
            return
        
        p1 = p1_indices[idx]
        p2 = p2_indices[idx]
        
        if pinned_mask[p1] and pinned_mask[p2]:
            return
        
        diff_x = positions[p1, 0] - positions[p2, 0]
        diff_y = positions[p1, 1] - positions[p2, 1]
        diff_z = positions[p1, 2] - positions[p2, 2]
        
        dist = float64(np.sqrt(diff_x * diff_x + diff_y * diff_y + diff_z * diff_z))
        
        if dist < 1e-6:
            return
        
        inv_dist = 1.0 / dist
        dir_x = diff_x * inv_dist
        dir_y = diff_y * inv_dist
        dir_z = diff_z * inv_dist
        
        stretch = dist - rest_lengths[idx]
        
        vel_diff_x = velocities[p1, 0] - velocities[p2, 0]
        vel_diff_y = velocities[p1, 1] - velocities[p2, 1]
        vel_diff_z = velocities[p1, 2] - velocities[p2, 2]
        
        spring_force = stiffnesses[idx] * stretch
        damping_force = spring_damping * (vel_diff_x * dir_x + vel_diff_y * dir_y + vel_diff_z * dir_z)
        
        total_force_mag = -(spring_force + damping_force)
        
        fx = total_force_mag * dir_x
        fy = total_force_mag * dir_y
        fz = total_force_mag * dir_z
        
        if not pinned_mask[p1]:
            cuda.atomic.add(forces, (p1, 0), fx)
            cuda.atomic.add(forces, (p1, 1), fy)
            cuda.atomic.add(forces, (p1, 2), fz)
        
        if not pinned_mask[p2]:
            cuda.atomic.add(forces, (p2, 0), -fx)
            cuda.atomic.add(forces, (p2, 1), -fy)
            cuda.atomic.add(forces, (p2, 2), -fz)


    @cuda.jit
    def _cuda_integrate_euler(positions, velocities, forces, masses, pinned_mask,
                               dt, gravity, global_damping, wind_force, n_points):
        idx = cuda.grid(1)
        
        if idx >= n_points:
            return
        
        if pinned_mask[idx]:
            return
        
        m = masses[idx]
        inv_m = 1.0 / m
        
        fx = forces[idx, 0] + gravity[0] * m + wind_force[0] * m - velocities[idx, 0] * global_damping
        fy = forces[idx, 1] + gravity[1] * m + wind_force[1] * m - velocities[idx, 1] * global_damping
        fz = forces[idx, 2] + gravity[2] * m + wind_force[2] * m - velocities[idx, 2] * global_damping
        
        ax = fx * inv_m
        ay = fy * inv_m
        az = fz * inv_m
        
        velocities[idx, 0] = velocities[idx, 0] + ax * dt
        velocities[idx, 1] = velocities[idx, 1] + ay * dt
        velocities[idx, 2] = velocities[idx, 2] + az * dt
        
        positions[idx, 0] = positions[idx, 0] + velocities[idx, 0] * dt
        positions[idx, 1] = positions[idx, 1] + velocities[idx, 1] * dt
        positions[idx, 2] = positions[idx, 2] + velocities[idx, 2] * dt


class GPUForceSystem:
    def __init__(self, cloth, use_gpu: bool = True):
        self.cloth = cloth
        self.accelerator = GPUAccelerator(use_gpu=use_gpu)
        
        self.gravity = np.array([0.0, -9.81, 0.0], dtype=np.float64)
        self.wind_force = np.zeros(3, dtype=np.float64)
        self.global_damping = 0.01
        self.spring_damping = 0.2
        
        self._force_buffer = None
    
    @property
    def use_gpu(self) -> bool:
        return self.accelerator.use_gpu
    
    def _prepare_gpu_data(self):
        positions = self.cloth.get_position_array()
        velocities = self.cloth.get_velocity_array()
        masses = self.cloth.get_mass_array()
        pinned_mask = self.cloth.get_pinned_mask()
        spring_data = self.cloth.get_spring_data()
        
        self.accelerator.copy_to_device(positions, velocities, masses, pinned_mask, spring_data)
    
    def compute_forces_gpu(self) -> Tuple[np.ndarray, np.ndarray]:
        self._prepare_gpu_data()
        
        self.accelerator.compute_spring_forces_gpu(self.spring_damping)
        self.accelerator.integrate_euler_gpu(
            1.0 / 60.0, self.gravity, self.global_damping, self.wind_force
        )
        
        positions, velocities, forces = self.accelerator.copy_from_device()
        return positions, velocities
    
    def compute_forces_cpu(self) -> np.ndarray:
        positions = self.cloth.get_position_array()
        velocities = self.cloth.get_velocity_array()
        masses = self.cloth.get_mass_array()
        pinned_mask = self.cloth.get_pinned_mask()
        p1_indices, p2_indices, rest_lengths, stiffnesses = self.cloth.get_spring_data()
        
        forces = self.accelerator.compute_spring_forces_cpu(
            positions, velocities, p1_indices, p2_indices,
            rest_lengths, stiffnesses, self.spring_damping, pinned_mask
        )
        
        for i in range(len(positions)):
            if pinned_mask[i]:
                continue
            forces[i] += self.gravity * masses[i]
            forces[i] += self.wind_force * masses[i]
            forces[i] -= velocities[i] * self.global_damping
        
        return forces
    
    def __call__(self, cloth):
        if self.accelerator.use_gpu:
            try:
                positions, velocities = self.compute_forces_gpu()
                cloth.set_position_array(positions)
                cloth.set_velocity_array(velocities)
            except Exception as e:
                print(f"GPU computation failed, falling back to CPU: {e}")
                self.accelerator.use_gpu = False
                forces = self.compute_forces_cpu()
                for i, mp in enumerate(cloth.mass_points):
                    if not mp.pinned:
                        mp.force[:] = forces[i]
        else:
            forces = self.compute_forces_cpu()
            for i, mp in enumerate(cloth.mass_points):
                if not mp.pinned:
                    mp.force[:] = forces[i]
