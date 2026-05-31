import numpy as np


class RigidBody:
    def __init__(self, cx, cy, radius, density=1.0, fixed=False):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.density = density
        self.fixed = fixed
        
        self.velocity = np.array([0.0, 0.0], dtype=np.float32)
        self.angular_velocity = 0.0
        self.angle = 0.0
        
        self.force = np.array([0.0, 0.0], dtype=np.float32)
        self.torque = 0.0
        
        self.mass = np.pi * radius**2 * density
        self.inertia = 0.5 * self.mass * radius**2
        
        self.collision_damping = 0.8
    
    def update(self, dt, domain_width, domain_height):
        if self.fixed:
            return
        
        self.velocity += self.force / self.mass * dt
        self.angular_velocity += self.torque / self.inertia * dt
        
        self.cx += self.velocity[0] * dt
        self.cy += self.velocity[1] * dt
        self.angle += self.angular_velocity * dt
        
        min_x = self.radius
        max_x = domain_width - self.radius
        min_y = self.radius
        max_y = domain_height - self.radius
        
        if self.cx < min_x:
            self.cx = min_x
            self.velocity[0] *= -self.collision_damping
        elif self.cx > max_x:
            self.cx = max_x
            self.velocity[0] *= -self.collision_damping
        
        if self.cy < min_y:
            self.cy = min_y
            self.velocity[1] *= -self.collision_damping
        elif self.cy > max_y:
            self.cy = max_y
            self.velocity[1] *= -self.collision_damping
        
        self.force[:] = 0
        self.torque = 0
    
    def apply_force(self, fx, fy, rx=0, ry=0):
        self.force[0] += fx
        self.force[1] += fy
        self.torque += rx * fy - ry * fx
    
    def reset(self):
        self.velocity[:] = 0
        self.angular_velocity = 0
        self.force[:] = 0
        self.torque = 0
    
    def get_mask(self, width, height):
        y, x = np.ogrid[:height, :width]
        dist = np.sqrt((x - self.cx)**2 + (y - self.cy)**2)
        return dist <= self.radius


class FluidStructureCoupling:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.bodies = []
        self.dt = 1.0
        
        self.stress_tensor = np.zeros((height, width, 2, 2), dtype=np.float32)
        
        self.cx = np.array([-1, 0, 1, -1, 0, 1, -1, 0, 1], dtype=np.int32)
        self.cy = np.array([-1, -1, -1, 0, 0, 0, 1, 1, 1], dtype=np.int32)
        self.w = np.array([1/36, 1/9, 1/36, 1/9, 4/9, 1/9, 1/36, 1/9, 1/36], dtype=np.float32)
    
    def add_body(self, body):
        self.bodies.append(body)
    
    def clear_bodies(self):
        self.bodies.clear()
    
    def get_obstacle_mask(self):
        mask = np.zeros((self.height, self.width), dtype=bool)
        for body in self.bodies:
            mask |= body.get_mask(self.width, self.height)
        return mask
    
    def compute_forces(self, f, rho, u, tau):
        omega = 1.0 / max(tau, 0.51)
        
        for body in self.bodies:
            if body.fixed:
                continue
            
            y, x = np.ogrid[:self.height, :self.width]
            dx = x - body.cx
            dy = y - body.cy
            dist = np.sqrt(dx**2 + dy**2)
            
            ring = (dist > body.radius - 3) & (dist <= body.radius + 3)
            
            if not np.any(ring):
                continue
            
            body_mask = ring
            
            for i in range(9):
                cxi = self.cx[i]
                cyi = self.cy[i]
                
                nx = dx[body_mask] / (dist[body_mask] + 1e-10)
                ny = dy[body_mask] / (dist[body_mask] + 1e-10)
                
                mom_x = f[body_mask, i] * cxi
                mom_y = f[body_mask, i] * cyi
                
                force_x = np.sum((1 - omega) * (mom_x - mom_y))
                force_y = np.sum((1 - omega) * (mom_y + mom_x))
                
                rx = dx[body_mask]
                ry = dy[body_mask]
                
                body.force[0] += force_x * 0.01
                body.force[1] += force_y * 0.01
                body.torque += np.sum(rx * force_y - ry * force_x) * 0.01
    
    def compute_forces_momentum_exchange(self, f, f_post, tau):
        omega = 1.0 / max(tau, 0.51)
        
        for body in self.bodies:
            if body.fixed:
                continue
            
            body_mask = body.get_mask(self.width, self.height)
            
            if not np.any(body_mask):
                continue
            
            delta_f = (f - f_post) * omega
            
            total_force_x = 0.0
            total_force_y = 0.0
            total_torque = 0.0
            
            y_idx, x_idx = np.where(body_mask)
            
            for y, x in zip(y_idx, x_idx):
                rx = x - body.cx
                ry = y - body.cy
                
                for i in range(9):
                    cxi = self.cx[i]
                    cyi = self.cy[i]
                    
                    df = delta_f[y, x, i]
                    fx = df * cxi
                    fy = df * cyi
                    
                    total_force_x += fx
                    total_force_y += fy
                    total_torque += rx * fy - ry * fx
            
            body.force[0] += total_force_x * 0.1
            body.force[1] += total_force_y * 0.1
            body.torque += total_torque * 0.01
    
    def update_bodies(self):
        for body in self.bodies:
            body.update(self.dt, self.width, self.height)
    
    def update_body_velocity(self, f, rho, tau):
        omega = 1.0 / max(tau, 0.51)
        
        for body in self.bodies:
            if body.fixed:
                continue
            
            body_mask = body.get_mask(self.width, self.height)
            
            if not np.any(body_mask):
                continue
            
            y_idx, x_idx = np.where(body_mask)
            
            for y, x in zip(y_idx, x_idx):
                for i in range(9):
                    opp_i = 8 - i
                    
                    rx = self.cx[opp_i]
                    ry = self.cy[opp_i]
                    
                    rel_vel_x = body.velocity[0] - body.angular_velocity * ry
                    rel_vel_y = body.velocity[1] + body.angular_velocity * rx
                    
                    vel_dot = rx * rel_vel_x + ry * rel_vel_y
                    
                    rho_local = rho[y, x] if rho[y, x] > 0 else 1.0
                    
                    f_eq = self.w[i] * rho_local * (1 + 3 * vel_dot + 4.5 * vel_dot**2 - 1.5 * (rel_vel_x**2 + rel_vel_y**2))
                    
                    f[y, x, i] = f_eq + (1 - omega) * (f[y, x, opp_i] - f_eq)
    
    def step_coupling(self, f, rho, u, tau):
        f_old = f.copy()
        
        self.compute_forces_momentum_exchange(f_old, f, tau)
        self.update_bodies()
        self.update_body_velocity(f, rho, tau)
        
        return self.get_obstacle_mask()
    
    def get_body_states(self):
        states = []
        for body in self.bodies:
            states.append({
                'cx': body.cx,
                'cy': body.cy,
                'radius': body.radius,
                'velocity': body.velocity.copy(),
                'angular_velocity': body.angular_velocity,
                'angle': body.angle,
                'force': body.force.copy(),
                'torque': body.torque,
                'fixed': body.fixed
            })
        return states
