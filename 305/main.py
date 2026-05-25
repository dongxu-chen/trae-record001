import sys
import pygame
import numpy as np
import imgui

from cloth import Cloth
from integrators import ExplicitEulerIntegrator, VerletIntegrator, SemiImplicitEulerIntegrator
from forces import ForceSystem
from collision import SphereCollider, PlaneCollider
from self_collision import SelfCollision
from rigid_body import RigidSphere, RigidBox, ClothRigidCoupling
from gpu_accelerator import GPUForceSystem, is_cuda_available
from renderer import Renderer
from gui import SimulationGUI


class ClothSimulation:
    def __init__(self):
        self.width = 1280
        self.height = 720
        
        self.renderer = Renderer(self.width, self.height, "Cloth Simulation - Advanced")
        
        self.cloth_width = 15
        self.cloth_height = 15
        self.cloth_spacing = 0.4
        
        self._create_cloth(self.cloth_width, self.cloth_height)
        
        self.force_system = ForceSystem(
            gravity=9.81,
            wind_strength=0.0,
            wind_direction=(1.0, 0.0, 0.5),
            global_damping=0.05,
            wind_turbulence=0.3,
            wind_speed=2.0
        )
        
        self.use_gpu_acceleration = False
        self.gpu_force_system = GPUForceSystem(self.cloth, use_gpu=self.use_gpu_acceleration)
        
        self.integrator = VerletIntegrator(damping=0.999, constraint_iterations=3)
        
        self.sphere_collider = SphereCollider(
            center=(0.0, 1.5, 0.0),
            radius=1.2,
            restitution=0.6,
            friction=0.3
        )
        self.sphere_collider.enabled = True
        
        self.plane_collider = PlaneCollider(
            normal=(0.0, 1.0, 0.0),
            point=(0.0, -2.0, 0.0),
            restitution=0.3,
            friction=0.5
        )
        self.plane_collider.enabled = True
        
        self.self_collision = SelfCollision(
            cloth=self.cloth,
            threshold=0.08,
            stiffness=0.9,
            friction=0.3,
            restitution=0.1,
            use_bvh=True,
            max_leaf_size=4
        )
        self.self_collision.enabled = True
        
        self.dynamic_sphere = RigidSphere(
            position=(0.0, 2.0, 0.0),
            radius=0.8,
            mass=2.0,
            restitution=0.5,
            friction=0.4,
            is_dynamic=True
        )
        self.dynamic_sphere.enabled = True
        self.dynamic_sphere.couple_with_cloth = True
        
        self.dynamic_box = RigidBox(
            position=(-2.0, 1.0, 0.0),
            size=(0.6, 0.6, 0.6),
            mass=1.0,
            restitution=0.4,
            friction=0.5,
            is_dynamic=True
        )
        self.dynamic_box.enabled = False
        self.dynamic_box.couple_with_cloth = True
        
        self.rigid_bodies = [self.dynamic_sphere, self.dynamic_box]
        
        self.cloth_rigid_coupling = ClothRigidCoupling(
            cloth=self.cloth,
            rigid_bodies=self.rigid_bodies
        )
        
        self.gui = SimulationGUI(
            renderer=self.renderer,
            cloth=self.cloth,
            force_system=self.force_system,
            integrator=self.integrator,
            sphere_collider=self.sphere_collider,
            plane_collider=self.plane_collider,
            self_collision=self.self_collision,
            rigid_bodies=self.rigid_bodies,
            gpu_force_system=self.gpu_force_system,
            reset_callback=self._reset_simulation
        )
        
        self.running = True
        self.clock = pygame.time.Clock()
        self.fixed_dt = 1.0 / 60.0
        self.accumulator = 0.0
        self.last_time = pygame.time.get_ticks() / 1000.0
        
    def _create_cloth(self, width: int, height: int):
        start_x = -(width - 1) * self.cloth_spacing / 2.0
        self.cloth = Cloth(
            width=width,
            height=height,
            spacing=self.cloth_spacing,
            mass=0.1,
            structural_stiffness=1500.0,
            shear_stiffness=800.0,
            bend_stiffness=200.0,
            damping=0.2,
            tear_threshold=0.3,
            tear_enabled=False,
            start_pos=(start_x, 5.0, 0.0)
        )
    
    def _reset_simulation(self, width: int, height: int):
        self.cloth_width = width
        self.cloth_height = height
        self._create_cloth(width, height)
        self.gui.cloth = self.cloth
        self.self_collision.rebuild_bvh(self.cloth)
        self.cloth_rigid_coupling.cloth = self.cloth
        self.gpu_force_system.cloth = self.cloth
        
        self.dynamic_sphere.state.position = np.array([0.0, 2.0, 0.0])
        self.dynamic_sphere.state.velocity = np.zeros(3)
        self.dynamic_sphere.state.angular_velocity = np.zeros(3)
        self.dynamic_sphere.state.orientation = np.array([1.0, 0.0, 0.0, 0.0])
        
        self.dynamic_box.state.position = np.array([-2.0, 1.0, 0.0])
        self.dynamic_box.state.velocity = np.zeros(3)
        self.dynamic_box.state.angular_velocity = np.zeros(3)
        self.dynamic_box.state.orientation = np.array([1.0, 0.0, 0.0, 0.0])
    
    def _handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_r and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    self._reset_simulation(self.cloth_width, self.cloth_height)
                self.gui.handle_keypress(event.key)
            
            if event.type == pygame.VIDEORESIZE:
                self.width = event.w
                self.height = event.h
                io = imgui.get_io()
                io.display_size = (self.width, self.height)
            
            self.gui.process_event(event)
        
        return True
    
    def _physics_step(self, dt: float):
        self.force_system.update_time(dt)
        
        substeps = self.gui.get_substeps()
        sub_dt = dt / substeps
        
        for _ in range(substeps):
            self.cloth_rigid_coupling.compute_coupling_forces(sub_dt)
            
            if self.use_gpu_acceleration and self.gpu_force_system.use_gpu:
                self.gpu_force_system.gravity = np.array([0.0, -self.force_system.gravity, 0.0])
                self.gpu_force_system.wind_force = self.force_system.wind_direction * self.force_system.wind_strength
                self.gpu_force_system.global_damping = self.force_system.global_damping
                self.gpu_force_system.spring_damping = self.cloth.damping
                
                forces_func = self.gpu_force_system
            else:
                forces_func = self.force_system
            
            self.integrator.step(
                cloth=self.cloth,
                dt=sub_dt,
                forces_func=forces_func,
                collision_funcs=[self.sphere_collider, self.plane_collider, self.self_collision]
            )
            
            self.cloth_rigid_coupling.update_attachments()
            self.cloth_rigid_coupling.integrate_rigid_bodies(sub_dt)
    
    def _render(self):
        self.renderer.clear()
        
        if self.gui.show_grid():
            self.renderer.draw_grid(size=15.0, steps=30)
        
        self.renderer.draw_plane(self.plane_collider)
        self.renderer.draw_sphere(self.sphere_collider)
        
        for body in self.rigid_bodies:
            self.renderer.draw_rigid_body(body)
        
        self.renderer.draw_cloth(self.cloth)
        
        self.gui.draw()
        
        self.renderer.swap_buffers()
    
    def run(self):
        print("\n" + "="*60)
        print("Cloth Simulation System")
        print("="*60)
        print(f"CUDA Available: {is_cuda_available()}")
        if is_cuda_available():
            print(f"GPU Acceleration: {'Enabled' if self.use_gpu_acceleration else 'Disabled'}")
        print("="*60)
        print("\nControls:")
        print("  Left drag: Orbit camera")
        print("  Right drag: Pan camera")
        print("  Scroll: Zoom")
        print("  H: Toggle GUI")
        print("  Shift+R: Reset simulation")
        print("  ESC: Exit")
        print("\n" + "="*60 + "\n")
        
        while self.running:
            self.running = self._handle_events()
            
            current_time = pygame.time.get_ticks() / 1000.0
            frame_dt = current_time - self.last_time
            self.last_time = current_time
            
            frame_dt = min(frame_dt, 1.0 / 30.0)
            
            fps = 1.0 / max(frame_dt, 1e-6)
            
            self.gui.update(frame_dt, fps)
            
            if self.gui.should_step():
                self._physics_step(self.fixed_dt)
            
            self._render()
            
            self.clock.tick(60)
        
        self.cleanup()
    
    def cleanup(self):
        self.gui.cleanup()
        self.renderer.cleanup()
        print("\nSimulation ended.")


def main():
    try:
        sim = ClothSimulation()
        sim.run()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
