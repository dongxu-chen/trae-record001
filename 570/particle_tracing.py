import numpy as np


class TracerParticle:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.prev_x = float(x)
        self.prev_y = float(y)
        self.age = 0.0
        self.max_age = 500.0
        self.active = True
        self.path_length = 0.0
        
        self.color = np.array([1.0, 1.0, 0.0], dtype=np.float32)
    
    def update(self, u, v, dt, dx=1.0, dy=1.0):
        if not self.active:
            return
        
        self.prev_x = self.x
        self.prev_y = self.y
        
        height, width = u.shape
        
        x0 = int(np.floor(self.x))
        y0 = int(np.floor(self.y))
        
        if x0 < 0 or x0 >= width - 1 or y0 < 0 or y0 >= height - 1:
            self.active = False
            return
        
        wx = self.x - x0
        wy = self.y - y0
        
        u_interp = (1-wx)*(1-wy)*u[y0, x0] + wx*(1-wy)*u[y0, x0+1] + \
                   (1-wx)*wy*u[y0+1, x0] + wx*wy*u[y0+1, x0+1]
        v_interp = (1-wx)*(1-wy)*v[y0, x0] + wx*(1-wy)*v[y0, x0+1] + \
                   (1-wx)*wy*v[y0+1, x0] + wx*wy*v[y0+1, x0+1]
        
        self.x += u_interp * dt / dx
        self.y += v_interp * dt / dy
        
        dx_p = self.x - self.prev_x
        dy_p = self.y - self.prev_y
        self.path_length += np.sqrt(dx_p**2 + dy_p**2)
        
        self.age += dt
        
        if self.age >= self.max_age:
            self.active = False
    
    def reset(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.prev_x = float(x)
        self.prev_y = float(y)
        self.age = 0.0
        self.active = True
        self.path_length = 0.0


class ParticleTracing:
    def __init__(self, width=512, height=512, max_particles=2000):
        self.width = width
        self.height = height
        self.max_particles = max_particles
        
        self.particles = []
        self.particle_positions = np.zeros((max_particles, 2), dtype=np.float32)
        self.particle_prev_positions = np.zeros((max_particles, 2), dtype=np.float32)
        self.particle_colors = np.zeros((max_particles, 3), dtype=np.float32)
        self.particle_active = np.zeros(max_particles, dtype=bool)
        
        self.trail_length = 100
        self.trail_buffer = np.zeros((max_particles, self.trail_length, 2), dtype=np.float32)
        self.trail_head = np.zeros(max_particles, dtype=np.int32)
        
        self.release_rate = 10
        self.release_interval = 5
        self.release_x = 10
        self.release_y_min = height // 4
        self.release_y_max = 3 * height // 4
        
        self.dt = 1.0
        self.step_counter = 0
        
        self.flow_mode = 'streamlines'
        
        self._initialize_particles()
    
    def _initialize_particles(self):
        for i in range(self.max_particles):
            x = np.random.uniform(0, self.width)
            y = np.random.uniform(0, self.height)
            p = TracerParticle(x, y)
            p.max_age = np.random.uniform(200, 800)
            hue = (y / self.height) * 0.3 + 0.5
            p.color = self._hsv_to_rgb(hue, 1.0, 1.0)
            self.particles.append(p)
        
        self._update_buffers()
    
    def _hsv_to_rgb(self, h, s, v):
        h = h % 1.0
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        
        i = i % 6
        if i == 0:
            return np.array([v, t, p], dtype=np.float32)
        elif i == 1:
            return np.array([q, v, p], dtype=np.float32)
        elif i == 2:
            return np.array([p, v, t], dtype=np.float32)
        elif i == 3:
            return np.array([p, q, v], dtype=np.float32)
        elif i == 4:
            return np.array([t, p, v], dtype=np.float32)
        else:
            return np.array([v, p, q], dtype=np.float32)
    
    def set_release_region(self, x, y_min, y_max):
        self.release_x = x
        self.release_y_min = y_min
        self.release_y_max = y_max
    
    def release_particles(self, count=None):
        if count is None:
            count = self.release_rate
        
        released = 0
        for i, p in enumerate(self.particles):
            if not p.active and released < count:
                y = np.random.uniform(self.release_y_min, self.release_y_max)
                p.reset(self.release_x, y)
                p.max_age = np.random.uniform(200, 800)
                hue = (y / self.height) * 0.3 + 0.5
                p.color = self._hsv_to_rgb(hue, 1.0, 1.0)
                self.trail_head[i] = 0
                released += 1
        
        if released < count:
            for _ in range(count - released):
                if len(self.particles) < self.max_particles:
                    y = np.random.uniform(self.release_y_min, self.release_y_max)
                    p = TracerParticle(self.release_x, y)
                    p.max_age = np.random.uniform(200, 800)
                    hue = (y / self.height) * 0.3 + 0.5
                    p.color = self._hsv_to_rgb(hue, 1.0, 1.0)
                    self.particles.append(p)
    
    def update(self, velocity_field, obstacles=None):
        self.step_counter += 1
        
        if self.step_counter % self.release_interval == 0:
            self.release_particles()
        
        u = velocity_field[:, :, 0]
        v = velocity_field[:, :, 1]
        
        for i, p in enumerate(self.particles):
            if not p.active:
                continue
            
            p.update(u, v, self.dt)
            
            if obstacles is not None:
                px = int(np.clip(p.x, 0, self.width - 1))
                py = int(np.clip(p.y, 0, self.height - 1))
                if obstacles[py, px]:
                    p.active = False
            
            if p.active:
                self.trail_buffer[i, self.trail_head[i], 0] = p.x
                self.trail_buffer[i, self.trail_head[i], 1] = p.y
                self.trail_head[i] = (self.trail_head[i] + 1) % self.trail_length
        
        self._update_buffers()
    
    def _update_buffers(self):
        for i, p in enumerate(self.particles):
            if i >= self.max_particles:
                break
            self.particle_positions[i, 0] = p.x
            self.particle_positions[i, 1] = p.y
            self.particle_prev_positions[i, 0] = p.prev_x
            self.particle_prev_positions[i, 1] = p.prev_y
            self.particle_colors[i] = p.color
            self.particle_active[i] = p.active
    
    def get_active_particles(self):
        positions = self.particle_positions[self.particle_active]
        colors = self.particle_colors[self.particle_active]
        return positions, colors
    
    def get_streamlines(self):
        lines = []
        line_colors = []
        
        for i in range(len(self.particles)):
            if not self.particle_active[i]:
                continue
            
            head = self.trail_head[i]
            trail = []
            
            for j in range(self.trail_length):
                idx = (head - j) % self.trail_length
                pos = self.trail_buffer[i, idx]
                if pos[0] != 0 or pos[1] != 0:
                    trail.append(pos.copy())
            
            if len(trail) > 1:
                lines.append(np.array(trail))
                line_colors.append(self.particle_colors[i])
        
        return lines, line_colors
    
    def reset(self):
        for p in self.particles:
            p.active = False
        self.particle_positions.fill(0)
        self.particle_prev_positions.fill(0)
        self.trail_buffer.fill(0)
        self.trail_head.fill(0)
        self.step_counter = 0
        self.release_particles(self.max_particles // 10)
    
    def clear(self):
        for p in self.particles:
            p.active = False
        self.trail_buffer.fill(0)
