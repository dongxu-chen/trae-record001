import numpy as np
from cloth import Cloth
from typing import Tuple
from perlin_noise import WindTurbulence


class ForceSystem:
    def __init__(self, gravity: float = 9.81,
                 wind_strength: float = 0.0,
                 wind_direction: Tuple[float, float, float] = (1.0, 0.0, 0.0),
                 global_damping: float = 0.01,
                 wind_turbulence: float = 0.0,
                 wind_speed: float = 1.0,
                 turbulence_scale: float = 0.3,
                 turbulence_strength: float = 0.5,
                 use_perlin_noise: bool = True):
        
        self.gravity = gravity
        self.wind_strength = wind_strength
        self.wind_direction = np.array(wind_direction, dtype=np.float64)
        self.wind_direction /= np.linalg.norm(self.wind_direction)
        self.global_damping = global_damping
        self.wind_turbulence = wind_turbulence
        self.wind_speed = wind_speed
        self.turbulence_scale = turbulence_scale
        self.turbulence_strength = turbulence_strength
        self.use_perlin_noise = use_perlin_noise
        self._time = 0.0
        
        self._turbulence = WindTurbulence(
            seed=42,
            scale=turbulence_scale,
            speed=wind_speed,
            strength=turbulence_strength
        )
    
    def update_time(self, dt: float):
        self._time += dt
        if self.use_perlin_noise and self._turbulence is not None:
            self._turbulence.update_time(dt)
            self._turbulence.speed = self.wind_speed
            self._turbulence.scale = self.turbulence_scale
            self._turbulence.strength = self.turbulence_strength
    
    def apply_gravity(self, cloth: Cloth):
        gravity_vec = np.array([0.0, -self.gravity, 0.0], dtype=np.float64)
        for mp in cloth.mass_points:
            if not mp.pinned:
                mp.force += gravity_vec * mp.mass
    
    def apply_spring_forces(self, cloth: Cloth):
        for spring in cloth.springs:
            p1 = cloth.mass_points[spring.p1_idx]
            p2 = cloth.mass_points[spring.p2_idx]
            
            diff = p1.position - p2.position
            dist = np.linalg.norm(diff)
            
            if dist < 1e-6:
                continue
            
            direction = diff / dist
            stretch = dist - spring.rest_length
            
            vel_diff = p1.velocity - p2.velocity
            
            spring_force_mag = spring.stiffness * stretch
            damping_force_mag = spring.damping * np.dot(vel_diff, direction)
            
            total_force = -(spring_force_mag + damping_force_mag) * direction
            
            if not p1.pinned:
                p1.force += total_force
            if not p2.pinned:
                p2.force -= total_force
    
    def apply_wind(self, cloth: Cloth):
        if self.wind_strength <= 0.0:
            return
        
        base_wind = self.wind_direction * self.wind_strength
        
        if self.use_perlin_noise and self._turbulence is not None and self.turbulence_strength > 0:
            for mp in cloth.mass_points:
                if not mp.pinned:
                    turbulence = self._turbulence.sample(mp.position)
                    total_wind = base_wind + turbulence * self.wind_strength * self.wind_turbulence
                    
                    noise_3d = self._turbulence.sample(mp.position + self._time * 0.5)
                    total_wind += noise_3d * 0.3 * self.wind_strength
                    
                    mp.force += total_wind * mp.mass
        else:
            turbulence = np.sin(self._time * self.wind_speed) * self.wind_turbulence
            
            wind_dir = self.wind_direction.copy()
            wind_dir[0] += np.sin(self._time * 2.5) * 0.3 * self.wind_turbulence
            wind_dir[2] += np.cos(self._time * 1.7) * 0.3 * self.wind_turbulence
            wind_dir = wind_dir / np.linalg.norm(wind_dir)
            
            wind_force = wind_dir * self.wind_strength * (1.0 + turbulence)
            
            for mp in cloth.mass_points:
                if not mp.pinned:
                    random_factor = np.random.randn(3) * 0.1 * self.wind_turbulence
                    mp.force += (wind_force + random_factor) * mp.mass
    
    def apply_damping(self, cloth: Cloth):
        if self.global_damping <= 0.0:
            return
        
        for mp in cloth.mass_points:
            if not mp.pinned:
                damping_force = -mp.velocity * self.global_damping
                mp.force += damping_force
    
    def apply_all_forces(self, cloth: Cloth):
        self.apply_gravity(cloth)
        self.apply_spring_forces(cloth)
        self.apply_wind(cloth)
        self.apply_damping(cloth)
    
    def __call__(self, cloth: Cloth):
        self.apply_all_forces(cloth)
