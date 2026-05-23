import argparse
from lbm2d import LBM2D
from visualization import AsyncFluidVisualizer
from config import SimulationConfig


def create_simulation(config):
    lbm = LBM2D(nx=config.nx, ny=config.ny, tau=config.tau, force=config.force)
    
    if config.obstacle_type == 'circle':
        lbm.add_circle(**config.obstacle_params)
    elif config.obstacle_type == 'rectangle':
        lbm.add_rectangle(**config.obstacle_params)
    else:
        raise ValueError(f"Unknown obstacle type: {config.obstacle_type}")
    
    if config.reynolds is not None:
        char_length = config.obstacle_params.get('r', config.ny / 2) * 2
        lbm.set_reynolds(config.reynolds, char_length)
    
    return lbm


def run_interactive():
    config = SimulationConfig()
    
    print("=== Fluid Dynamics Simulation (LBM Method) ===")
    print("1. Default flow around a circle")
    print("2. Flow around a rectangle")
    print("3. Custom configuration")
    print("4. Exit")
    
    choice = input("Select an option (1-4): ")
    
    if choice == '1':
        config.set_obstacle('circle', cx=100, cy=50, r=15)
        config.set_reynolds(200)
        config.set_visualization('streamline')
    elif choice == '2':
        config.set_obstacle('rectangle', x0=80, y0=40, width=30, height=20)
        config.set_reynolds(150)
        config.set_visualization('streamline')
    elif choice == '3':
        nx = int(input("Grid width (nx): "))
        ny = int(input("Grid height (ny): "))
        config.set_grid(nx, ny)
        
        tau = float(input("Relaxation time tau (0.55-1.0): "))
        config.set_viscosity(tau)
        
        re = float(input("Reynolds number: "))
        config.set_reynolds(re)
        
        obs_type = input("Obstacle type (circle/rectangle): ")
        if obs_type == 'circle':
            cx = int(input("Center x: "))
            cy = int(input("Center y: "))
            r = int(input("Radius: "))
            config.set_obstacle('circle', cx=cx, cy=cy, r=r)
        elif obs_type == 'rectangle':
            x0 = int(input("Top-left x: "))
            y0 = int(input("Top-left y: "))
            w = int(input("Width: "))
            h = int(input("Height: "))
            config.set_obstacle('rectangle', x0=x0, y0=y0, width=w, height=h)
        
        mode = input("Visualization mode (full/streamline): ")
        config.set_visualization(mode)
    elif choice == '4':
        return
    
    print(config)
    print("\nStarting simulation...")
    print("Click on the plot to pause/resume.")
    
    lbm = create_simulation(config)
    viz = FluidVisualizer(lbm, interval=config.animation_interval)
    viz.animate(mode=config.visualization_mode)


def run_demo():
    config = SimulationConfig()
    config.set_grid(400, 100)
    config.set_viscosity(0.6)
    config.set_obstacle('circle', cx=100, cy=50, r=15)
    config.set_reynolds(200)
    config.set_visualization('streamline', interval=30)
    
    print("Demo: Flow around a circle")
    print(config)
    
    lbm = create_simulation(config)
    viz = FluidVisualizer(lbm, interval=config.animation_interval)
    viz.animate(mode=config.visualization_mode)


def main():
    parser = argparse.ArgumentParser(description='2D LBM Fluid Simulation')
    parser.add_argument('--mode', type=str, default='interactive',
                        choices=['interactive', 'demo'],
                        help='Run mode')
    parser.add_argument('--nx', type=int, default=400, help='Grid width')
    parser.add_argument('--ny', type=int, default=100, help='Grid height')
    parser.add_argument('--tau', type=float, default=0.6, help='Relaxation time')
    parser.add_argument('--re', type=float, default=None, help='Reynolds number')
    parser.add_argument('--obstacle', type=str, default='circle',
                        choices=['circle', 'rectangle'], help='Obstacle type')
    parser.add_argument('--viz', type=str, default='streamline',
                        choices=['full', 'streamline'], help='Visualization mode')
    
    args = parser.parse_args()
    
    if args.mode == 'interactive':
        run_interactive()
    elif args.mode == 'demo':
        run_demo()


if __name__ == '__main__':
    main()
