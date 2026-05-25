import numpy as np
from abc import ABC, abstractmethod
from typing import List
from cloth import Cloth, MassPoint, Spring


class Integrator(ABC):
    @abstractmethod
    def step(self, cloth: Cloth, dt: float, forces_func, collision_funcs: List = None):
        pass


class ExplicitEulerIntegrator(Integrator):
    def __init__(self):
        pass
    
    def step(self, cloth: Cloth, dt: float, forces_func, collision_funcs: List = None):
        cloth.reset_forces()
        forces_func(cloth)
        
        pinned_mask = cloth.get_pinned_mask()
        mass_arr = cloth.get_mass_array()
        mass_arr = mass_arr[:, np.newaxis]
        
        positions = cloth.get_position_array()
        velocities = cloth.get_velocity_array()
        
        forces = np.array([mp.force for mp in cloth.mass_points], dtype=np.float64)
        
        accelerations = forces / mass_arr
        accelerations[pinned_mask] = 0.0
        
        new_velocities = velocities + accelerations * dt
        new_positions = positions + new_velocities * dt
        
        if collision_funcs:
            for collision_func in collision_funcs:
                new_positions, new_velocities = collision_func(
                    new_positions, new_velocities, mass_arr
                )
        
        cloth.set_position_array(new_positions)
        cloth.set_velocity_array(new_velocities)
        
        cloth.check_and_tear()
        
        cloth.check_and_tear()


class VerletIntegrator(Integrator):
    def __init__(self, damping: float = 0.999, 
                 constraint_iterations: int = 3,
                 use_velocity_damping: bool = True):
        
        self.damping = damping
        self.constraint_iterations = constraint_iterations
        self.use_velocity_damping = use_velocity_damping
    
    def step(self, cloth: Cloth, dt: float, forces_func, collision_funcs: List = None):
        cloth.reset_forces()
        forces_func(cloth)
        
        pinned_mask = cloth.get_pinned_mask()
        mass_arr = cloth.get_mass_array()
        mass_arr = mass_arr[:, np.newaxis]
        
        forces = np.array([mp.force for mp in cloth.mass_points], dtype=np.float64)
        accelerations = forces / mass_arr
        accelerations[pinned_mask] = 0.0
        
        for i, mp in enumerate(cloth.mass_points):
            if not mp.pinned:
                temp = mp.position.copy()
                
                vel = mp.velocity
                acc = accelerations[i]
                
                mp.position = mp.position + vel * dt + 0.5 * acc * dt * dt
                mp.position = mp.position + (mp.position - mp.old_position) * self.damping
                
                mp.old_position = temp
        
        positions = cloth.get_position_array()
        velocities = cloth.get_velocity_array()
        
        if collision_funcs:
            for collision_func in collision_funcs:
                positions, velocities = collision_func(
                    positions, velocities, mass_arr
                )
                cloth.set_position_array(positions)
        
        self._apply_spring_constraints(cloth)
        
        for i, mp in enumerate(cloth.mass_points):
            if not mp.pinned:
                mp.velocity = (mp.position - mp.old_position) / (2.0 * dt)
                
                if self.use_velocity_damping:
                    mp.velocity *= 0.995
        
        cloth.check_and_tear()
    
    def _apply_spring_constraints(self, cloth: Cloth):
        for _ in range(self.constraint_iterations):
            for spring in cloth.springs:
                if spring.broken:
                    continue
                p1 = cloth.mass_points[spring.p1_idx]
                p2 = cloth.mass_points[spring.p2_idx]
                
                if p1.pinned and p2.pinned:
                    continue
                
                diff = p1.position - p2.position
                dist = np.linalg.norm(diff)
                
                if dist < 1e-6:
                    continue
                
                direction = diff / dist
                stretch = dist - spring.rest_length
                
                if abs(stretch) < 1e-6:
                    continue
                
                m1 = p1.mass
                m2 = p2.mass
                
                if p1.pinned:
                    ratio1 = 0.0
                    ratio2 = 1.0
                elif p2.pinned:
                    ratio1 = 1.0
                    ratio2 = 0.0
                else:
                    total_mass = m1 + m2
                    ratio1 = m2 / total_mass
                    ratio2 = m1 / total_mass
                
                correction = direction * stretch * 0.5
                
                max_stretch_ratio = 1.2
                if abs(stretch) > spring.rest_length * max_stretch_ratio:
                    correction = direction * (abs(stretch) - spring.rest_length * max_stretch_ratio) * np.sign(stretch)
                
                if not p1.pinned:
                    p1.position -= correction * ratio1
                if not p2.pinned:
                    p2.position += correction * ratio2


class SemiImplicitEulerIntegrator(Integrator):
    def __init__(self):
        pass
    
    def step(self, cloth: Cloth, dt: float, forces_func, collision_funcs: List = None):
        cloth.reset_forces()
        forces_func(cloth)
        
        pinned_mask = cloth.get_pinned_mask()
        mass_arr = cloth.get_mass_array()
        mass_arr = mass_arr[:, np.newaxis]
        
        positions = cloth.get_position_array()
        velocities = cloth.get_velocity_array()
        
        forces = np.array([mp.force for mp in cloth.mass_points], dtype=np.float64)
        
        accelerations = forces / mass_arr
        accelerations[pinned_mask] = 0.0
        
        new_velocities = velocities + accelerations * dt
        new_positions = positions + new_velocities * dt
        
        if collision_funcs:
            for collision_func in collision_funcs:
                new_positions, new_velocities = collision_func(
                    new_positions, new_velocities, mass_arr
                )
        
        cloth.set_position_array(new_positions)
        cloth.set_velocity_array(new_velocities)
        
        cloth.check_and_tear()
