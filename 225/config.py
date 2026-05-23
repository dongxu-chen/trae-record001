class SimulationConfig:
    def __init__(self):
        self.nx = 400
        self.ny = 100
        self.tau = 0.6
        self.force = 1e-6
        self.reynolds = None
        
        self.obstacle_type = 'circle'
        self.obstacle_params = {
            'cx': 100,
            'cy': 50,
            'r': 15
        }
        
        self.visualization_mode = 'streamline'
        self.animation_interval = 30
    
    def set_grid(self, nx, ny):
        self.nx = nx
        self.ny = ny
    
    def set_viscosity(self, tau):
        self.tau = tau
    
    def set_force(self, force):
        self.force = force
    
    def set_reynolds(self, re):
        self.reynolds = re
    
    def set_obstacle(self, obstacle_type, **kwargs):
        self.obstacle_type = obstacle_type
        self.obstacle_params = kwargs
    
    def set_visualization(self, mode='streamline', interval=30):
        self.visualization_mode = mode
        self.animation_interval = interval
    
    def __str__(self):
        return (
            f"Simulation Configuration:\n"
            f"  Grid: {self.nx} x {self.ny}\n"
            f"  Tau: {self.tau}\n"
            f"  Force: {self.force}\n"
            f"  Reynolds: {self.reynolds}\n"
            f"  Obstacle: {self.obstacle_type} - {self.obstacle_params}\n"
            f"  Visualization: {self.visualization_mode}\n"
        )
