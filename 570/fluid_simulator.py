import numpy as np
from abc import ABC, abstractmethod
import threading
import queue
import time


class FluidSimulator(ABC):
    def __init__(self, width=512, height=512, tau=0.6):
        self.width = width
        self.height = height
        self.tau = tau
        self.rho0 = 1.0
        
        self.w = np.array([1/36, 1/9, 1/36, 1/9, 4/9, 1/9, 1/36, 1/9, 1/36], dtype=np.float32)
        self.cx = np.array([-1, 0, 1, -1, 0, 1, -1, 0, 1], dtype=np.int32)
        self.cy = np.array([-1, -1, -1, 0, 0, 0, 1, 1, 1], dtype=np.int32)
        
        self.obstacles = np.zeros((height, width), dtype=bool)
        self.obstacle_fraction = np.zeros((height, width), dtype=np.float32)
        self.u = np.zeros((height, width, 2), dtype=np.float32)
        self.rho = np.ones((height, width), dtype=np.float32)
        
        self.enable_stabilization = True
        self.enable_subgrid = True
        self.max_velocity = 0.5
        self.min_density = 0.1
        self.max_density = 10.0
        
        self._data_lock = threading.Lock()
        self._simulation_thread = None
        self._running = False
        self._steps_per_second = 0
        self._step_count = 0
        self._last_step_time = time.time()
        
        self.initialize()
    
    @abstractmethod
    def initialize(self):
        pass
    
    @abstractmethod
    def step(self):
        pass
    
    @abstractmethod
    def get_velocity(self):
        pass
    
    @abstractmethod
    def get_pressure(self):
        pass
    
    @abstractmethod
    def get_vorticity(self):
        pass
    
    def add_obstacle_circle(self, cx, cy, radius):
        y, x = np.ogrid[:self.height, :self.width]
        dx = x - cx
        dy = y - cy
        dist = np.sqrt(dx**2 + dy**2)
        
        mask = dist <= radius
        self.obstacles[mask] = True
        
        if self.enable_subgrid:
            boundary = (dist > radius - 1.5) & (dist < radius + 1.5)
            self.obstacle_fraction[boundary] = np.clip(1.0 - (dist[boundary] - radius + 0.5), 0.0, 1.0)
            self.obstacle_fraction[mask] = 1.0
        
        self._update_obstacles()
    
    def add_obstacle_rect(self, x0, y0, x1, y1):
        self.obstacles[y0:y1, x0:x1] = True
        
        if self.enable_subgrid:
            y, x = np.ogrid[:self.height, :self.width]
            dx = np.minimum(np.abs(x - x0 + 0.5), np.abs(x - x1 - 0.5))
            dy = np.minimum(np.abs(y - y0 + 0.5), np.abs(y - y1 - 0.5))
            
            edge_x = (dx < 1.0) & (y >= y0) & (y < y1)
            edge_y = (dy < 1.0) & (x >= x0) & (x < x1)
            
            self.obstacle_fraction[edge_x] = np.clip(1.0 - dx[edge_x], 0.0, 1.0)
            self.obstacle_fraction[edge_y] = np.clip(1.0 - dy[edge_y], 0.0, 1.0)
            self.obstacle_fraction[y0:y1, x0:x1] = 1.0
        
        self._update_obstacles()
    
    def clear_obstacles(self):
        self.obstacles.fill(False)
        self.obstacle_fraction.fill(0.0)
        self._update_obstacles()
    
    @abstractmethod
    def _update_obstacles(self):
        pass
    
    def set_inflow_velocity(self, ux, uy):
        pass
    
    def set_tau(self, tau):
        self.tau = max(0.51, tau)
    
    def _stabilize_distribution(self, f):
        if not self.enable_stabilization:
            return f
        
        f = np.clip(f, 1e-6, 1e6)
        return f
    
    def _stabilize_macroscopic(self):
        if not self.enable_stabilization:
            return
        
        self.rho = np.clip(self.rho, self.min_density, self.max_density)
        
        vel_mag = np.sqrt(self.u[:, :, 0]**2 + self.u[:, :, 1]**2)
        scale = np.ones_like(vel_mag)
        mask = vel_mag > self.max_velocity
        scale[mask] = self.max_velocity / (vel_mag[mask] + 1e-10)
        
        self.u[:, :, 0] *= scale
        self.u[:, :, 1] *= scale
    
    def start_async(self, target_fps=60):
        if self._simulation_thread is not None and self._simulation_thread.is_alive():
            return
        
        self._running = True
        self._simulation_thread = threading.Thread(target=self._run_async, args=(target_fps,), daemon=True)
        self._simulation_thread.start()
    
    def stop_async(self):
        self._running = False
        if self._simulation_thread is not None:
            self._simulation_thread.join(timeout=1.0)
    
    def _run_async(self, target_fps):
        interval = 1.0 / target_fps
        while self._running:
            start_time = time.time()
            
            self.step()
            
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            self._step_count += 1
            if time.time() - self._last_step_time >= 1.0:
                self._steps_per_second = self._step_count
                self._step_count = 0
                self._last_step_time = time.time()
    
    def get_simulation_rate(self):
        return self._steps_per_second
    
    def is_async_running(self):
        return self._running
    
    def lock(self):
        self._data_lock.acquire()
    
    def unlock(self):
        self._data_lock.release()
