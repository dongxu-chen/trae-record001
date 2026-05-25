import numpy as np


class PerlinNoise3D:
    def __init__(self, seed: int = None, octaves: int = 4, persistence: float = 0.5, lacunarity: float = 2.0):
        self.octaves = octaves
        self.persistence = persistence
        self.lacunarity = lacunarity
        
        if seed is not None:
            rng = np.random.RandomState(seed)
        else:
            rng = np.random.RandomState()
        
        self.permutation = rng.permutation(512)
        self.gradients = rng.randn(512, 3)
        
        for i in range(len(self.gradients)):
            norm = np.linalg.norm(self.gradients[i])
            if norm > 0:
                self.gradients[i] /= norm
    
    def _fade(self, t: np.ndarray) -> np.ndarray:
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + t * (b - a)
    
    def _dot_gradient(self, xi: int, yi: int, zi: int, x: float, y: float, z: float) -> float:
        idx = self.permutation[xi + self.permutation[yi + self.permutation[zi % 256] % 256] % 256] % 512
        grad = self.gradients[idx]
        dx = x - xi
        dy = y - yi
        dz = z - zi
        return grad[0] * dx + grad[1] * dy + grad[2] * dz
    
    def _noise(self, x: float, y: float, z: float) -> float:
        xi = int(np.floor(x)) & 255
        yi = int(np.floor(y)) & 255
        zi = int(np.floor(z)) & 255
        
        xf = x - np.floor(x)
        yf = y - np.floor(y)
        zf = z - np.floor(z)
        
        u = self._fade(np.array([xf]))[0]
        v = self._fade(np.array([yf]))[0]
        w = self._fade(np.array([zf]))[0]
        
        x0 = xi
        x1 = xi + 1
        y0 = yi
        y1 = yi + 1
        z0 = zi
        z1 = zi + 1
        
        p000 = self._dot_gradient(x0, y0, z0, x, y, z)
        p100 = self._dot_gradient(x1, y0, z0, x, y, z)
        p010 = self._dot_gradient(x0, y1, z0, x, y, z)
        p110 = self._dot_gradient(x1, y1, z0, x, y, z)
        p001 = self._dot_gradient(x0, y0, z1, x, y, z)
        p101 = self._dot_gradient(x1, y0, z1, x, y, z)
        p011 = self._dot_gradient(x0, y1, z1, x, y, z)
        p111 = self._dot_gradient(x1, y1, z1, x, y, z)
        
        x00 = self._lerp(p000, p100, u)
        x10 = self._lerp(p010, p110, u)
        x01 = self._lerp(p001, p101, u)
        x11 = self._lerp(p011, p111, u)
        
        y0 = self._lerp(x00, x10, v)
        y1 = self._lerp(x01, x11, v)
        
        z = self._lerp(y0, y1, w)
        
        return z
    
    def noise(self, x: float, y: float, z: float) -> float:
        total = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0
        
        for _ in range(self.octaves):
            total += self._noise(x * frequency, y * frequency, z * frequency) * amplitude
            max_value += amplitude
            amplitude *= self.persistence
            frequency *= self.lacunarity
        
        return total / max_value if max_value > 0 else 0.0
    
    def noise_vec3(self, x: float, y: float, z: float) -> np.ndarray:
        nx = self.noise(x, y, z)
        ny = self.noise(x + 100.0, y + 100.0, z + 100.0)
        nz = self.noise(x + 200.0, y + 200.0, z + 200.0)
        return np.array([nx, ny, nz])


class WindTurbulence:
    def __init__(self, seed: int = 42, scale: float = 0.5, speed: float = 1.0, strength: float = 1.0):
        self.noise_x = PerlinNoise3D(seed=seed, octaves=4, persistence=0.5, lacunarity=2.0)
        self.noise_y = PerlinNoise3D(seed=seed + 1, octaves=4, persistence=0.5, lacunarity=2.0)
        self.noise_z = PerlinNoise3D(seed=seed + 2, octaves=4, persistence=0.5, lacunarity=2.0)
        self.scale = scale
        self.speed = speed
        self.strength = strength
        self._time = 0.0
    
    def update_time(self, dt: float):
        self._time += dt * self.speed
    
    def sample(self, position: np.ndarray) -> np.ndarray:
        x = position[0] * self.scale + self._time
        y = position[1] * self.scale
        z = position[2] * self.scale + self._time * 0.5
        
        nx = self.noise_x.noise(x, y, z)
        ny = self.noise_y.noise(x + 100.0, y + 100.0, z + 100.0)
        nz = self.noise_z.noise(x + 200.0, y + 200.0, z + 200.0)
        
        turbulence = np.array([nx, ny * 0.5, nz]) * self.strength
        return turbulence
