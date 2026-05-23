from lbm2d import LBM2D, ParticleTracer
from visualization import AsyncFluidVisualizer


def example_thermal_convection():
    print("Example 1: Thermal Convection with Heated Obstacle")
    print("  - Heated cylinder in channel flow")
    print("  - Temperature field visualization")
    print("  - Particle tracer enabled")
    print()
    
    lbm = LBM2D(nx=400, ny=100, tau=0.6, force=1e-6,
                enable_temperature=True, tau_T=0.7)
    
    lbm.add_circle(cx=100, cy=50, r=15, temperature=1.0)
    
    lbm.set_reynolds(200, 30)
    
    tracer = ParticleTracer(lbm, n_particles=300)
    
    viz = AsyncFluidVisualizer(
        lbm, interval=30, steps_per_update=10,
        tracer=tracer, show_particles=True, show_temperature=True
    )
    viz.animate(mode='streamline')


def example_particle_streamlines():
    print("Example 2: Particle Streamlines")
    print("  - Flow around a cylinder")
    print("  - 500 tracer particles")
    print("  - Particle trails shown")
    print()
    
    lbm = LBM2D(nx=400, ny=100, tau=0.6, force=1e-6,
                enable_temperature=False)
    
    lbm.add_circle(cx=100, cy=50, r=15)
    lbm.set_reynolds(250, 30)
    
    tracer = ParticleTracer(lbm, n_particles=500)
    
    viz = AsyncFluidVisualizer(
        lbm, interval=30, steps_per_update=10,
        tracer=tracer, show_particles=True, show_temperature=False
    )
    viz.animate(mode='streamline')


def example_rectangle_thermal():
    print("Example 3: Flow around heated rectangle")
    print("  - Full thermal visualization")
    print("  - Velocity, vorticity, temperature")
    print()
    
    lbm = LBM2D(nx=400, ny=100, tau=0.65, force=1e-6,
                enable_temperature=True, tau_T=0.8)
    
    lbm.add_rectangle(x0=80, y0=40, width=30, height=20, temperature=0.8)
    lbm.set_reynolds(150, 20)
    
    tracer = ParticleTracer(lbm, n_particles=200)
    
    viz = AsyncFluidVisualizer(
        lbm, interval=40, steps_per_update=8,
        tracer=tracer, show_particles=True, show_temperature=True
    )
    viz.animate(mode='thermal')


def example_von_karman_street():
    print("Example 4: Von Karman Vortex Street")
    print("  - Higher Reynolds number (350)")
    print("  - Vortex shedding")
    print("  - Particle trails show vortices")
    print()
    
    lbm = LBM2D(nx=500, ny=120, tau=0.55, force=1e-6,
                enable_temperature=False)
    
    lbm.add_circle(cx=120, cy=60, r=18)
    lbm.set_reynolds(350, 36)
    
    tracer = ParticleTracer(lbm, n_particles=400)
    
    viz = AsyncFluidVisualizer(
        lbm, interval=25, steps_per_update=12,
        tracer=tracer, show_particles=True, show_temperature=False
    )
    viz.animate(mode='streamline')


def example_natural_convection():
    print("Example 5: Natural Convection (Rayleigh-Bénard)")
    print("  - Heated bottom, cooled top")
    print("  - Buoyancy-driven flow")
    print("  - Temperature coupled to velocity")
    print()
    
    lbm = LBM2D(nx=200, ny=150, tau=0.7, force=0.0,
                enable_temperature=True, tau_T=0.8,
                rayleigh=10000)
    
    lbm.set_temperature_boundary(bottom_temp=1.0, top_temp=0.0)
    
    tracer = ParticleTracer(lbm, n_particles=300)
    
    viz = AsyncFluidVisualizer(
        lbm, interval=50, steps_per_update=5,
        tracer=tracer, show_particles=True, show_temperature=True
    )
    viz.animate(mode='thermal')


def run_parameter_scan():
    print("Example 6: Parameter Scan")
    print("  - Scan tau and Reynolds combinations")
    print("  - Classify flow regimes (Steady/Transitional/Unsteady)")
    print("  - Generate phase diagram")
    print()
    
    from param_scan import ParameterScanner
    import numpy as np
    
    scanner = ParameterScanner()
    
    tau_values = np.linspace(0.55, 0.8, 4)
    re_values = np.linspace(80, 400, 8)
    
    print("This may take several minutes...")
    confirm = input("Continue? (y/n): ")
    if confirm.lower() != 'y':
        return
    
    results = scanner.run_scan(
        tau_values, re_values,
        nx=150, ny=75,
        obstacle_type='circle',
        obstacle_params={'cx': 40, 'cy': 37, 'r': 10},
        n_steps=2000,
        sample_interval=2000
    )
    
    scanner.print_summary()
    scanner.plot_phase_diagram()
    print(f"Results saved to: {scanner.output_dir}/")


if __name__ == '__main__':
    import sys
    
    examples = [
        ("Thermal Convection with Heated Obstacle", example_thermal_convection),
        ("Particle Streamlines", example_particle_streamlines),
        ("Flow around Heated Rectangle (Full View)", example_rectangle_thermal),
        ("Von Karman Vortex Street", example_von_karman_street),
        ("Natural Convection", example_natural_convection),
        ("Parameter Scan (Batch)", run_parameter_scan),
    ]
    
    if len(sys.argv) > 1:
        example_num = int(sys.argv[1]) - 1
        if 0 <= example_num < len(examples):
            examples[example_num][1]()
        else:
            print(f"Invalid example number. Select 1-{len(examples)}")
    else:
        print("Available examples:")
        for i, (name, _) in enumerate(examples, 1):
            print(f"  {i} - {name}")
        
        example_num = int(input(f"Select example (1-{len(examples)}): ")) - 1
        
        if 0 <= example_num < len(examples):
            examples[example_num][1]()
        else:
            print("Invalid example number")
