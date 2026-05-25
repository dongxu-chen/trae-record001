import imgui
from imgui.integrations.pygame import PygameRenderer
import pygame
from typing import Callable, Tuple, List
from cloth import Cloth
from forces import ForceSystem
from integrators import ExplicitEulerIntegrator, VerletIntegrator, SemiImplicitEulerIntegrator
from collision import SphereCollider, PlaneCollider
from self_collision import SelfCollision
from rigid_body import RigidBody, RigidSphere, RigidBox
from gpu_accelerator import GPUForceSystem, is_cuda_available
from renderer import Renderer


class SimulationGUI:
    def __init__(self, renderer: Renderer,
                 cloth: Cloth,
                 force_system: ForceSystem,
                 integrator,
                 sphere_collider: SphereCollider,
                 plane_collider: PlaneCollider,
                 self_collision: SelfCollision,
                 rigid_bodies: List[RigidBody],
                 gpu_force_system: GPUForceSystem,
                 reset_callback: Callable[[int, int], None]):
        
        self.renderer = renderer
        self.cloth = cloth
        self.force_system = force_system
        self.integrator = integrator
        self.sphere_collider = sphere_collider
        self.plane_collider = plane_collider
        self.self_collision = self_collision
        self.rigid_bodies = rigid_bodies
        self.gpu_force_system = gpu_force_system
        self.reset_callback = reset_callback
        
        self._integrator_type = "verlet"
        self._show_gui = True
        self._paused = False
        self._step_sim = False
        self._substeps = 3
        
        self._cloth_width = cloth.width
        self._cloth_height = cloth.height
        self._cloth_spacing = cloth.spacing
        
        self._structural_stiffness = cloth.structural_stiffness
        self._shear_stiffness = cloth.shear_stiffness
        self._bend_stiffness = cloth.bend_stiffness
        self._damping = cloth.damping
        
        self._tear_enabled = cloth.tear_enabled
        self._tear_threshold = cloth.tear_threshold
        
        self._gravity = force_system.gravity
        self._wind_strength = force_system.wind_strength
        self._wind_turbulence = force_system.wind_turbulence
        self._wind_speed = force_system.wind_speed
        self._global_damping = force_system.global_damping
        self._turbulence_scale = force_system.turbulence_scale
        self._turbulence_strength = force_system.turbulence_strength
        self._use_perlin_noise = force_system.use_perlin_noise
        
        self._sphere_center = list(sphere_collider.center)
        self._sphere_radius = sphere_collider.radius
        self._sphere_enabled = sphere_collider.enabled
        self._sphere_restitution = sphere_collider.restitution
        self._sphere_friction = sphere_collider.friction
        
        self._plane_point = list(plane_collider.point)
        self._plane_enabled = plane_collider.enabled
        self._plane_restitution = plane_collider.restitution
        self._plane_friction = plane_collider.friction
        
        self._self_collision_enabled = self_collision.enabled
        self._self_collision_threshold = self_collision.threshold
        self._self_collision_stiffness = self_collision.stiffness
        self._self_collision_friction = self_collision.friction
        self._self_collision_restitution = self_collision.restitution
        self._use_bvh = self_collision.use_bvh
        
        self._show_points = False
        self._show_wireframe = False
        self._show_grid = True
        self._show_broken_edges = True
        self._color_by_stress = False
        self._max_stress = 0.5
        
        self._use_gpu = gpu_force_system.use_gpu
        self._cuda_available = is_cuda_available()
        
        self._dt = 1.0 / 60.0
        self._fps = 60.0
        self._frame_times = []
        
        self._init_imgui()
    
    def _init_imgui(self):
        imgui.create_context()
        self._impl = PygameRenderer()
        
        io = imgui.get_io()
        io.display_size = (self.renderer.width, self.renderer.height)
    
    def process_event(self, event):
        self._impl.process_event(event)
    
    def update(self, dt: float, fps: float):
        self._dt = dt
        self._fps = fps
        
        self._frame_times.append(dt)
        if len(self._frame_times) > 100:
            self._frame_times.pop(0)
        
        self._impl.process_inputs()
    
    def _update_force_system(self):
        self.force_system.gravity = self._gravity
        self.force_system.wind_strength = self._wind_strength
        self.force_system.wind_turbulence = self._wind_turbulence
        self.force_system.wind_speed = self._wind_speed
        self.force_system.global_damping = self._global_damping
        self.force_system.turbulence_scale = self._turbulence_scale
        self.force_system.turbulence_strength = self._turbulence_strength
        self.force_system.use_perlin_noise = self._use_perlin_noise
    
    def _update_cloth_props(self):
        self.cloth.structural_stiffness = self._structural_stiffness
        self.cloth.shear_stiffness = self._shear_stiffness
        self.cloth.bend_stiffness = self._bend_stiffness
        self.cloth.damping = self._damping
        self.cloth.tear_threshold = self._tear_threshold
        self.cloth.tear_enabled = self._tear_enabled
        self.cloth.recompute_springs()
    
    def _update_colliders(self):
        self.sphere_collider.center = self._sphere_center
        self.sphere_collider.radius = self._sphere_radius
        self.sphere_collider.enabled = self._sphere_enabled
        self.sphere_collider.restitution = self._sphere_restitution
        self.sphere_collider.friction = self._sphere_friction
        
        self.plane_collider.point = self._plane_point
        self.plane_collider.enabled = self._plane_enabled
        self.plane_collider.restitution = self._plane_restitution
        self.plane_collider.friction = self._plane_friction
        
        self.self_collision.enabled = self._self_collision_enabled
        self.self_collision.threshold = self._self_collision_threshold
        self.self_collision.stiffness = self._self_collision_stiffness
        self.self_collision.friction = self._self_collision_friction
        self.self_collision.restitution = self._self_collision_restitution
        self.self_collision.use_bvh = self._use_bvh
    
    def _change_integrator(self, integrator_type: str):
        self._integrator_type = integrator_type
        if integrator_type == "euler":
            self.integrator = ExplicitEulerIntegrator()
        elif integrator_type == "semi_euler":
            self.integrator = SemiImplicitEulerIntegrator()
        else:
            self.integrator = VerletIntegrator(damping=0.999, constraint_iterations=3, use_velocity_damping=True)
    
    def _reset_simulation(self):
        self.reset_callback(self._cloth_width, self._cloth_height)
        self._update_cloth_props()
    
    def _reset_tearing(self):
        self.cloth.reset_tearing()
    
    def _apply_gpu_setting(self):
        self.gpu_force_system.accelerator.use_gpu = self._use_gpu and self._cuda_available
    
    def draw(self):
        if not self._show_gui:
            return
        
        imgui.new_frame()
        
        imgui.set_next_window_position(10, 10, imgui.FIRST_USE_EVER)
        imgui.set_next_window_size(370, 0, imgui.FIRST_USE_EVER)
        
        imgui.begin("Cloth Simulation Controls", True)
        
        if imgui.collapsing_header("Simulation", flags=imgui.TREE_NODE_DEFAULT_OPEN):
            changed, self._paused = imgui.checkbox("Paused", self._paused)
            
            if self._paused:
                imgui.same_line()
                if imgui.button("Step"):
                    self._step_sim = True
            
            changed, self._substeps = imgui.slider_int("Substeps", self._substeps, 1, 10)
            
            if imgui.button("Reset"):
                self._reset_simulation()
            
            imgui.text(f"FPS: {self._fps:.1f}")
            avg_dt = sum(self._frame_times) / max(1, len(self._frame_times)) * 1000
            imgui.text(f"Avg Frame Time: {avg_dt:.2f} ms")
            
            if self._self_collision_enabled:
                collision_count = self.self_collision.get_collision_count()
                imgui.text(f"Self Collisions: {collision_count}")
            
            if self._tear_enabled:
                broken_count = self.cloth.get_broken_count()
                imgui.text(f"Broken Springs: {broken_count}")
            
            if self._cuda_available:
                changed, self._use_gpu = imgui.checkbox("GPU Acceleration", self._use_gpu)
                if changed:
                    self._apply_gpu_setting()
                if self._use_gpu:
                    imgui.same_line()
                    imgui.text_colored(0.0, 1.0, 0.0, 1.0, "(Active)")
            else:
                imgui.text_colored(1.0, 0.5, 0.0, 1.0, "CUDA not available")
        
        if imgui.collapsing_header("Tearing"):
            changed, self._tear_enabled = imgui.checkbox("Enable Tearing", self._tear_enabled)
            
            if self._tear_enabled:
                changed, self._tear_threshold = imgui.slider_float(
                    "Tear Threshold (strain)", self._tear_threshold, 0.05, 1.0
                )
                
                if imgui.button("Reset Tearing"):
                    self._reset_tearing()
                
                imgui.same_line()
                imgui.text(f"Broken: {self.cloth.get_broken_count()}")
            
            self._update_cloth_props()
        
        if imgui.collapsing_header("Integrator"):
            clicked_euler = imgui.radio_button("Explicit Euler", self._integrator_type == "euler")
            imgui.same_line()
            clicked_semi = imgui.radio_button("Semi-Implicit", self._integrator_type == "semi_euler")
            imgui.same_line()
            clicked_verlet = imgui.radio_button("Verlet", self._integrator_type == "verlet")
            
            if clicked_euler:
                self._change_integrator("euler")
            if clicked_semi:
                self._change_integrator("semi_euler")
            if clicked_verlet:
                self._change_integrator("verlet")
            
            if isinstance(self.integrator, VerletIntegrator):
                changed, self.integrator.damping = imgui.slider_float(
                    "Verlet Damping", self.integrator.damping, 0.9, 1.0
                )
                changed, self.integrator.constraint_iterations = imgui.slider_int(
                    "Constraint Iterations", self.integrator.constraint_iterations, 0, 10
                )
                changed, self.integrator.use_velocity_damping = imgui.checkbox(
                    "Velocity Damping", self.integrator.use_velocity_damping
                )
        
        if imgui.collapsing_header("Cloth Properties"):
            changed, self._cloth_width = imgui.slider_int("Width", self._cloth_width, 3, 50)
            changed, self._cloth_height = imgui.slider_int("Height", self._cloth_height, 3, 50)
            
            if imgui.button("Apply Resolution"):
                self._reset_simulation()
            
            imgui.separator()
            
            changed, self._structural_stiffness = imgui.slider_float(
                "Structural Stiffness", self._structural_stiffness, 10.0, 5000.0
            )
            changed, self._shear_stiffness = imgui.slider_float(
                "Shear Stiffness", self._shear_stiffness, 10.0, 3000.0
            )
            changed, self._bend_stiffness = imgui.slider_float(
                "Bend Stiffness", self._bend_stiffness, 10.0, 1000.0
            )
            changed, self._damping = imgui.slider_float(
                "Spring Damping", self._damping, 0.0, 1.0
            )
            
            if imgui.button("Apply Spring Properties"):
                self._update_cloth_props()
        
        if imgui.collapsing_header("Forces"):
            changed, self._gravity = imgui.slider_float(
                "Gravity", self._gravity, 0.0, 20.0
            )
            changed, self._wind_strength = imgui.slider_float(
                "Wind Strength", self._wind_strength, 0.0, 50.0
            )
            changed, self._wind_turbulence = imgui.slider_float(
                "Wind Turbulence", self._wind_turbulence, 0.0, 1.0
            )
            changed, self._wind_speed = imgui.slider_float(
                "Wind Speed", self._wind_speed, 0.1, 5.0
            )
            changed, self._global_damping = imgui.slider_float(
                "Global Damping", self._global_damping, 0.0, 2.0
            )
            
            imgui.separator()
            imgui.text("Perlin Noise Turbulence:")
            changed, self._use_perlin_noise = imgui.checkbox(
                "Use Perlin Noise", self._use_perlin_noise
            )
            if self._use_perlin_noise:
                changed, self._turbulence_scale = imgui.slider_float(
                    "Turbulence Scale", self._turbulence_scale, 0.01, 1.0
                )
                changed, self._turbulence_strength = imgui.slider_float(
                    "Turbulence Strength", self._turbulence_strength, 0.0, 2.0
                )
            
            self._update_force_system()
        
        if imgui.collapsing_header("Collisions"):
            imgui.text("Sphere Collider")
            changed, self._sphere_enabled = imgui.checkbox("Sphere Enabled", self._sphere_enabled)
            
            changed, self._sphere_center[0] = imgui.slider_float(
                "Sphere X", self._sphere_center[0], -5.0, 5.0
            )
            changed, self._sphere_center[1] = imgui.slider_float(
                "Sphere Y", self._sphere_center[1], -5.0, 5.0
            )
            changed, self._sphere_center[2] = imgui.slider_float(
                "Sphere Z", self._sphere_center[2], -5.0, 5.0
            )
            changed, self._sphere_radius = imgui.slider_float(
                "Sphere Radius", self._sphere_radius, 0.1, 3.0
            )
            changed, self._sphere_restitution = imgui.slider_float(
                "Sphere Restitution", self._sphere_restitution, 0.0, 1.0
            )
            changed, self._sphere_friction = imgui.slider_float(
                "Sphere Friction", self._sphere_friction, 0.0, 1.0
            )
            
            imgui.separator()
            imgui.text("Plane Collider")
            changed, self._plane_enabled = imgui.checkbox("Plane Enabled", self._plane_enabled)
            
            changed, self._plane_point[1] = imgui.slider_float(
                "Plane Height", self._plane_point[1], -5.0, 5.0
            )
            changed, self._plane_restitution = imgui.slider_float(
                "Plane Restitution", self._plane_restitution, 0.0, 1.0
            )
            changed, self._plane_friction = imgui.slider_float(
                "Plane Friction", self._plane_friction, 0.0, 1.0
            )
            
            imgui.separator()
            imgui.text("Self Collision")
            changed, self._self_collision_enabled = imgui.checkbox(
                "Self Collision Enabled", self._self_collision_enabled
            )
            if self._self_collision_enabled:
                changed, self._self_collision_threshold = imgui.slider_float(
                    "Collision Threshold", self._self_collision_threshold, 0.01, 0.3
                )
                changed, self._self_collision_stiffness = imgui.slider_float(
                    "Collision Stiffness", self._self_collision_stiffness, 0.1, 1.0
                )
                changed, self._self_collision_friction = imgui.slider_float(
                    "Collision Friction", self._self_collision_friction, 0.0, 1.0
                )
                changed, self._self_collision_restitution = imgui.slider_float(
                    "Collision Restitution", self._self_collision_restitution, 0.0, 1.0
                )
                changed, self._use_bvh = imgui.checkbox(
                    "Use BVH Acceleration", self._use_bvh
                )
            
            self._update_colliders()
        
        if imgui.collapsing_header("Dynamic Rigid Bodies"):
            for i, body in enumerate(self.rigid_bodies):
                body_name = f"Body {i+1}"
                if isinstance(body, RigidSphere):
                    body_name = f"Dynamic Sphere {i+1}"
                elif isinstance(body, RigidBox):
                    body_name = f"Dynamic Box {i+1}"
                
                if imgui.collapsing_header(body_name):
                    changed, body.enabled = imgui.checkbox("Enabled", body.enabled)
                    changed, body.is_dynamic = imgui.checkbox("Dynamic", body.is_dynamic)
                    changed, body.couple_with_cloth = imgui.checkbox("Couple with Cloth", body.couple_with_cloth)
                    
                    changed, body.state.mass = imgui.slider_float(
                        "Mass", body.state.mass, 0.1, 10.0
                    )
                    changed, body.restitution = imgui.slider_float(
                        "Restitution", body.restitution, 0.0, 1.0
                    )
                    changed, body.friction = imgui.slider_float(
                        "Friction", body.friction, 0.0, 1.0
                    )
                    
                    if isinstance(body, RigidSphere):
                        changed, body.radius = imgui.slider_float(
                            "Radius", body.radius, 0.1, 2.0
                        )
                    elif isinstance(body, RigidBox):
                        changed_w = imgui.slider_float("Size X", body.size[0], 0.1, 3.0)
                        changed_h = imgui.slider_float("Size Y", body.size[1], 0.1, 3.0)
                        changed_d = imgui.slider_float("Size Z", body.size[2], 0.1, 3.0)
                        if changed_w or changed_h or changed_d:
                            w, h, d = body.size
                            body.state.inertia_tensor = np.diag([
                                (1.0 / 12.0) * body.state.mass * (h * h + d * d),
                                (1.0 / 12.0) * body.state.mass * (w * w + d * d),
                                (1.0 / 12.0) * body.state.mass * (w * w + h * h)
                            ])
                    
                    imgui.text(f"Position: ({body.state.position[0]:.2f}, {body.state.position[1]:.2f}, {body.state.position[2]:.2f})")
                    imgui.text(f"Velocity: ({body.state.velocity[0]:.2f}, {body.state.velocity[1]:.2f}, {body.state.velocity[2]:.2f})")
                    
                    if imgui.button(f"Reset Body {i+1}"):
                        if isinstance(body, RigidSphere):
                            body.state.position = np.array([0.0, 2.0, 0.0])
                        else:
                            body.state.position = np.array([-2.0, 1.0, 0.0])
                        body.state.velocity = np.zeros(3)
                        body.state.angular_velocity = np.zeros(3)
                        body.state.orientation = np.array([1.0, 0.0, 0.0, 0.0])
        
        if imgui.collapsing_header("Rendering"):
            changed, self._show_wireframe = imgui.checkbox("Wireframe Only", self._show_wireframe)
            self.renderer.show_wireframe = self._show_wireframe
            
            changed, self._show_points = imgui.checkbox("Show Points", self._show_points)
            self.renderer.show_points = self._show_points
            
            changed, self._show_grid = imgui.checkbox("Show Grid", self._show_grid)
            
            changed, self._show_broken_edges = imgui.checkbox("Show Broken Edges", self._show_broken_edges)
            self.renderer.show_broken_edges = self._show_broken_edges
            
            changed, self._color_by_stress = imgui.checkbox("Color by Stress", self._color_by_stress)
            self.renderer.color_by_stress = self._color_by_stress
            
            if self._color_by_stress:
                changed, self._max_stress = imgui.slider_float(
                    "Max Stress", self._max_stress, 0.1, 2.0
                )
                self.renderer.max_stress = self._max_stress
            
            imgui.color_edit3("Cloth Color", *self.renderer.cloth_color[:3])
        
        imgui.text("\nControls:")
        imgui.text("  Left drag: Orbit camera")
        imgui.text("  Right drag: Pan camera")
        imgui.text("  Scroll: Zoom")
        imgui.text("  H: Toggle GUI")
        imgui.text("  Shift+R: Reset simulation")
        
        imgui.end()
        
        imgui.render()
        self._impl.render(imgui.get_draw_data())
    
    def should_step(self) -> bool:
        if self._step_sim:
            self._step_sim = False
            return True
        return not self._paused
    
    def get_substeps(self) -> int:
        return self._substeps
    
    def show_grid(self) -> bool:
        return self._show_grid
    
    def handle_keypress(self, key):
        if key == pygame.K_h:
            self._show_gui = not self._show_gui
    
    def cleanup(self):
        self._impl.shutdown()
