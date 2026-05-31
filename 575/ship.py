import numpy as np
from OpenGL.GL import *
from OpenGL.GL import shaders


BOAT_VERT = """
#version 330 core
layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;

out vec3 fragNormal;
out vec3 fragPos;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

void main() {
    vec4 worldPos = model * vec4(position, 1.0);
    fragPos = worldPos.xyz;
    fragNormal = mat3(transpose(inverse(model))) * normal;
    gl_Position = projection * view * worldPos;
}
"""

BOAT_FRAG = """
#version 330 core
in vec3 fragNormal;
in vec3 fragPos;

out vec4 finalColor;

uniform vec3 lightDir;
uniform vec3 lightColor;
uniform vec3 hullColor;
uniform vec3 cabinColor;

void main() {
    vec3 N = normalize(fragNormal);
    vec3 L = normalize(-lightDir);
    
    float diff = max(dot(N, L), 0.0);
    vec3 diffuse = diff * lightColor;
    
    vec3 V = normalize(-fragPos);
    vec3 H = normalize(V + L);
    float spec = pow(max(dot(N, H), 0.0), 32.0);
    vec3 specular = 0.3 * spec * lightColor;
    
    vec3 baseColor = mix(hullColor, cabinColor, step(fragPos.y, 1.5));
    
    vec3 ambient = 0.2 * baseColor;
    vec3 result = ambient + diffuse * baseColor + specular;
    
    finalColor = vec4(result, 1.0);
}
"""


class Ship:
    def __init__(self, position=(0.0, 0.0, 0.0), scale=1.0):
        self.position = np.array(position, dtype=np.float32)
        self.scale = scale
        self.ship_length = 8.0 * scale
        self.ship_width = 3.0 * scale
        self.ship_height = 2.0 * scale

        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.height_offset = 0.0

        self._vao = None
        self._vbo = None
        self._ebo = None
        self._shader = None
        self._indices_count = 0

    def init_gl(self):
        self._shader = shaders.compileProgram(
            shaders.compileShader(BOAT_VERT, GL_VERTEX_SHADER),
            shaders.compileShader(BOAT_FRAG, GL_FRAGMENT_SHADER)
        )
        self._build_mesh()

    def _build_mesh(self):
        L = self.ship_length
        W = self.ship_width
        H = self.ship_height
        D = H * 0.6

        vertices = np.array([
            -L/2, 0, 0,
            -L/2, 0, W/2,
            -L/2, 0, -W/2,

            L/2, 0, 0,
            L/4, 0, W/2,
            L/4, 0, -W/2,

            -L/2, -D, 0,
            -L/2, -D, W/3,
            -L/2, -D, -W/3,

            L/3, -D, 0,
            L/4, -D, W/3,
            L/4, -D, -W/3,

            -L/2, 0, W/2,
            -L/2, -D, W/3,
            L/4, -D, W/3,
            L/4, 0, W/2,

            -L/2, 0, -W/2,
            -L/2, -D, -W/3,
            L/4, -D, -W/3,
            L/4, 0, -W/2,

            -L/2, 0, W/2,
            L/4, 0, W/2,
            L/2, 0, 0,

            -L/2, 0, -W/2,
            L/4, 0, -W/2,
            L/2, 0, 0,

            L/4, -D, W/3,
            L/4, -D, -W/3,
            L/3, -D, 0,

            -L/2, -D, W/3,
            -L/2, -D, -W/3,
            L/3, -D, 0,

            -L/3, 0, -W/2.5,
            L/4, 0, -W/2.5,
            L/4, H, -W/2.5,
            -L/3, H, -W/2.5,

            -L/3, 0, W/2.5,
            L/4, 0, W/2.5,
            L/4, H, W/2.5,
            -L/3, H, W/2.5,

            -L/3, H, -W/2.5,
            L/4, H, -W/2.5,
            L/4, H, W/2.5,
            -L/3, H, W/2.5,
        ], dtype=np.float32)

        normals = np.zeros_like(vertices)
        num_tris = len(vertices) // 9
        for i in range(num_tris):
            idx = i * 9
            v0 = vertices[idx:idx+3]
            v1 = vertices[idx+3:idx+6]
            v2 = vertices[idx+6:idx+9]
            e1 = v1 - v0
            e2 = v2 - v0
            n = np.cross(e1, e2)
            length = np.linalg.norm(n)
            if length > 1e-6:
                n = n / length
            normals[idx:idx+3] = n
            normals[idx+3:idx+6] = n
            normals[idx+6:idx+9] = n

        interleaved = np.zeros(len(vertices) // 3 * 6, dtype=np.float32)
        for i in range(len(vertices) // 3):
            interleaved[i*6:i*6+3] = vertices[i*3:i*3+3]
            interleaved[i*6+3:i*6+6] = normals[i*3:i*3+3]

        self._indices_count = len(vertices) // 3

        self._vao = glGenVertexArrays(1)
        self._vbo = glGenBuffers(1)

        glBindVertexArray(self._vao)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
        glBufferData(GL_ARRAY_BUFFER, interleaved.nbytes, interleaved, GL_STATIC_DRAW)

        stride = 6 * 4
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)

        glBindVertexArray(0)

    def update(self, heights, patch_size, grid_size, time):
        half_grid = grid_size / 2
        scale = patch_size / grid_size

        ship_x = self.position[0]
        ship_z = self.position[2]

        bow_x = ship_x + self.ship_length * 0.4 * np.cos(np.radians(self.yaw))
        bow_z = ship_z + self.ship_length * 0.4 * np.sin(np.radians(self.yaw))
        stern_x = ship_x - self.ship_length * 0.4 * np.cos(np.radians(self.yaw))
        stern_z = ship_z - self.ship_length * 0.4 * np.sin(np.radians(self.yaw))

        port_x = ship_x + self.ship_width * 0.4 * np.cos(np.radians(self.yaw + 90))
        port_z = ship_z + self.ship_width * 0.4 * np.sin(np.radians(self.yaw + 90))

        h_center = self._sample_height(ship_x, ship_z, heights, half_grid, scale)
        h_bow = self._sample_height(bow_x, bow_z, heights, half_grid, scale)
        h_stern = self._sample_height(stern_x, stern_z, heights, half_grid, scale)
        h_port = self._sample_height(port_x, port_z, heights, half_grid, scale)

        self.height_offset = h_center
        self.position[1] = h_center

        dx_bow_stern = h_bow - h_stern
        dist_bow_stern = self.ship_length * 0.8
        if dist_bow_stern > 1e-6:
            self.pitch = np.degrees(np.arctan2(dx_bow_stern, dist_bow_stern))

        dx_port = h_port - h_center
        dist_port = self.ship_width * 0.4
        if dist_port > 1e-6:
            self.roll = -np.degrees(np.arctan2(dx_port, dist_port))

    def _sample_height(self, wx, wz, heights, half_grid, scale):
        gx = int(wx / scale + half_grid)
        gz = int(wz / scale + half_grid)
        gs = heights.shape[0]
        gx = np.clip(gx, 0, gs - 2)
        gz = np.clip(gz, 0, gs - 2)
        return heights[gz, gx]

    def get_model_matrix(self):
        c = np.cos
        s = np.sin

        roll_r = np.radians(self.roll)
        pitch_r = np.radians(self.pitch)
        yaw_r = np.radians(self.yaw)

        Rx = np.array([
            [1, 0, 0, 0],
            [0, c(roll_r), -s(roll_r), 0],
            [0, s(roll_r), c(roll_r), 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        Ry = np.array([
            [c(pitch_r), 0, s(pitch_r), 0],
            [0, 1, 0, 0],
            [-s(pitch_r), 0, c(pitch_r), 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        Rz = np.array([
            [c(yaw_r), -s(yaw_r), 0, 0],
            [s(yaw_r), c(yaw_r), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        T = np.array([
            [1, 0, 0, self.position[0]],
            [0, 1, 0, self.position[1]],
            [0, 0, 1, self.position[2]],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        return T @ Rz @ Ry @ Rx

    def render(self, view, proj, light_dir, light_color):
        if self._shader is None:
            return

        glUseProgram(self._shader)

        model = self.get_model_matrix()

        glUniformMatrix4fv(glGetUniformLocation(self._shader, 'model'), 1, GL_FALSE, model)
        glUniformMatrix4fv(glGetUniformLocation(self._shader, 'view'), 1, GL_FALSE, view)
        glUniformMatrix4fv(glGetUniformLocation(self._shader, 'projection'), 1, GL_FALSE, proj)
        glUniform3fv(glGetUniformLocation(self._shader, 'lightDir'), 1, light_dir)
        glUniform3fv(glGetUniformLocation(self._shader, 'lightColor'), 1, light_color)
        glUniform3f(glGetUniformLocation(self._shader, 'hullColor'), 0.35, 0.2, 0.1)
        glUniform3f(glGetUniformLocation(self._shader, 'cabinColor'), 0.85, 0.82, 0.75)

        glBindVertexArray(self._vao)
        glDrawArrays(GL_TRIANGLES, 0, self._indices_count)
        glBindVertexArray(0)

        glUseProgram(0)
