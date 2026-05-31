import numpy as np
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import QTimer, Qt, QPoint
from OpenGL.GL import *
from OpenGL.GL import shaders

from fft_water import FFTWave
from camera import Camera
from ship import Ship


class WaterGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.wave_params = {
            'wind_speed': 30.0,
            'wind_angle': 0.0,
            'wave_amplitude': 0.0002,
            'choppy_factor': 1.5,
            'foam_threshold': 0.7,
            'foam_intensity': 1.0,
            'spectrum_type': 'phillips'
        }

        self.light_params = {
            'light_dir': np.array([0.5, -0.8, 0.3], dtype=np.float32),
            'light_color': np.array([1.0, 0.98, 0.9], dtype=np.float32),
            'water_color': np.array([0.0, 0.3, 0.5], dtype=np.float32),
            'specular_strength': 0.8,
            'shininess': 128.0,
            'reflectivity': 0.8
        }

        self.grid_size = 128
        self.patch_size = 100.0

        self.animation_time = 0.0
        self.time_scale = 1.0
        self.is_playing = True

        self.camera = Camera()
        self._last_mouse_pos = QPoint()
        self._mouse_buttons = Qt.NoButton

        self._vao = None
        self._vbo = None
        self._ebo = None
        self._shader_program = None
        self._indices_count = 0

        self.ship = Ship(position=np.array([15.0, 0.0, 10.0], dtype=np.float32), scale=1.0)
        self.ship_visible = True

        self._current_heights = None

        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_animation)

    def initializeGL(self):
        glClearColor(0.1, 0.2, 0.3, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self._init_shaders()
        self._init_wave()
        self._init_mesh()
        self.ship.init_gl()

        self._update_timer.start(16)

    def _init_shaders(self):
        with open('shaders/water_vert.glsl', 'r') as f:
            vert_source = f.read()

        with open('shaders/water_frag.glsl', 'r') as f:
            frag_source = f.read()

        vert_shader = shaders.compileShader(vert_source, GL_VERTEX_SHADER)
        frag_shader = shaders.compileShader(frag_source, GL_FRAGMENT_SHADER)
        self._shader_program = shaders.compileProgram(vert_shader, frag_shader)

    def _init_wave(self):
        self.fft_wave = FFTWave(
            self.grid_size, self.patch_size,
            spectrum_type=self.wave_params['spectrum_type']
        )
        self._update_wave_params()

    def _update_wave_params(self):
        wind_angle_rad = np.radians(self.wave_params['wind_angle'])
        self.fft_wave.wind_direction = np.array([
            np.cos(wind_angle_rad),
            np.sin(wind_angle_rad)
        ])
        self.fft_wave.wind_speed = self.wave_params['wind_speed']
        self.fft_wave.wave_amplitude = self.wave_params['wave_amplitude']
        self.fft_wave.choppy_factor = self.wave_params['choppy_factor']

    def _init_mesh(self):
        self._vao = glGenVertexArrays(1)
        self._vbo = glGenBuffers(1)
        self._ebo = glGenBuffers(1)

        glBindVertexArray(self._vao)

        indices = []
        for y in range(self.grid_size - 1):
            for x in range(self.grid_size - 1):
                idx = y * self.grid_size + x
                indices.extend([idx, idx + self.grid_size, idx + 1])
                indices.extend([idx + 1, idx + self.grid_size, idx + self.grid_size + 1])

        self._indices_count = len(indices)
        indices = np.array(indices, dtype=np.uint32)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        self._update_mesh()

        glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
        stride = 9 * 4

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)

        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
        glEnableVertexAttribArray(2)

        glVertexAttribPointer(3, 1, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(32))
        glEnableVertexAttribArray(3)

        glBindVertexArray(0)

    def _update_mesh(self):
        heights = self.fft_wave.compute_wave_height(self.animation_time)
        dx, dz = self.fft_wave.compute_choppy_displacement(self.animation_time)
        normals = self.fft_wave.compute_normals(heights)
        foam = self.fft_wave.compute_foam(heights, self.wave_params['foam_threshold'], self.animation_time)

        self._current_heights = heights

        half_grid = self.grid_size / 2
        scale = self.patch_size / self.grid_size

        vertices = []
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                px = (x - half_grid) * scale + dx[y, x]
                py = heights[y, x]
                pz = (y - half_grid) * scale + dz[y, x]

                nx, ny, nz = normals[y, x]
                tx = x / self.grid_size
                ty = y / self.grid_size
                fm = foam[y, x]

                vertices.extend([px, py, pz, nx, ny, nz, tx, ty, fm])

        vertices = np.array(vertices, dtype=np.float32)

        glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)

        if self.ship_visible and self._current_heights is not None:
            self.ship.update(heights, self.patch_size, self.grid_size, self.animation_time)

    def _update_animation(self):
        if self.is_playing:
            self.animation_time += 0.016 * self.time_scale

        self._update_mesh()
        self.update()

    def paintGL(self):
        self.camera.update_underwater_state(water_y=0.0)

        if self.camera.is_underwater:
            glClearColor(0.0, 0.05, 0.1, 1.0)
        else:
            glClearColor(0.1, 0.2, 0.3, 1.0)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self._shader_program)

        view = self.camera.get_view_matrix()
        proj = self.camera.get_projection_matrix(self.width(), self.height())
        model = np.eye(4, dtype=np.float32)

        view_loc = glGetUniformLocation(self._shader_program, 'view')
        proj_loc = glGetUniformLocation(self._shader_program, 'projection')
        model_loc = glGetUniformLocation(self._shader_program, 'model')
        camera_loc = glGetUniformLocation(self._shader_program, 'cameraPos')
        underwater_loc = glGetUniformLocation(self._shader_program, 'underwater')

        glUniformMatrix4fv(view_loc, 1, GL_FALSE, view)
        glUniformMatrix4fv(proj_loc, 1, GL_FALSE, proj)
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, model)
        glUniform3fv(camera_loc, 1, self.camera.position)
        glUniform1i(underwater_loc, 1 if self.camera.is_underwater else 0)

        light_dir_loc = glGetUniformLocation(self._shader_program, 'lightDir')
        light_color_loc = glGetUniformLocation(self._shader_program, 'lightColor')
        water_color_loc = glGetUniformLocation(self._shader_program, 'waterColor')
        spec_strength_loc = glGetUniformLocation(self._shader_program, 'specularStrength')
        shininess_loc = glGetUniformLocation(self._shader_program, 'shininess')
        reflectivity_loc = glGetUniformLocation(self._shader_program, 'reflectivity')
        time_loc = glGetUniformLocation(self._shader_program, 'time')
        foam_intensity_loc = glGetUniformLocation(self._shader_program, 'foamIntensity')
        screen_size_loc = glGetUniformLocation(self._shader_program, 'screenSize')

        glUniform3fv(light_dir_loc, 1, self.light_params['light_dir'])
        glUniform3fv(light_color_loc, 1, self.light_params['light_color'])
        glUniform3fv(water_color_loc, 1, self.light_params['water_color'])
        glUniform1f(spec_strength_loc, self.light_params['specular_strength'])
        glUniform1f(shininess_loc, self.light_params['shininess'])
        glUniform1f(reflectivity_loc, self.light_params['reflectivity'])
        glUniform1f(time_loc, self.animation_time)
        glUniform1f(foam_intensity_loc, self.wave_params['foam_intensity'])
        glUniform2f(screen_size_loc, float(self.width()), float(self.height()))

        glBindVertexArray(self._vao)
        glDrawElements(GL_TRIANGLES, self._indices_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        glUseProgram(0)

        if self.ship_visible and not self.camera.is_underwater:
            self.ship.render(
                view, proj,
                self.light_params['light_dir'],
                self.light_params['light_color']
            )

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)

    def mousePressEvent(self, event):
        self._last_mouse_pos = event.pos()
        self._mouse_buttons = event.buttons()

    def mouseMoveEvent(self, event):
        delta = event.pos() - self._last_mouse_pos

        if self._mouse_buttons & Qt.LeftButton:
            self.camera.rotate(delta.x() * 0.5, delta.y() * 0.5)
        elif self._mouse_buttons & Qt.MiddleButton:
            self.camera.pan(-delta.x() * 0.01, delta.y() * 0.01)
        elif self._mouse_buttons & Qt.RightButton:
            self.camera.move_vertical(delta.y() * 0.05)

        self._last_mouse_pos = event.pos()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        self.camera.zoom(-delta * 5.0)

    def set_wind_speed(self, value):
        self.wave_params['wind_speed'] = value
        self._update_wave_params()

    def set_wind_angle(self, value):
        self.wave_params['wind_angle'] = value
        self._update_wave_params()

    def set_wave_amplitude(self, value):
        self.wave_params['wave_amplitude'] = value
        self._update_wave_params()

    def set_choppy_factor(self, value):
        self.wave_params['choppy_factor'] = value
        self._update_wave_params()

    def set_foam_threshold(self, value):
        self.wave_params['foam_threshold'] = value

    def set_foam_intensity(self, value):
        self.wave_params['foam_intensity'] = value

    def set_time_scale(self, value):
        self.time_scale = value

    def set_spectrum_type(self, spectrum_type):
        self.wave_params['spectrum_type'] = spectrum_type
        self.fft_wave.set_spectrum_type(spectrum_type)
        self._update_wave_params()

    def set_ship_visible(self, visible):
        self.ship_visible = visible

    def toggle_play(self):
        self.is_playing = not self.is_playing
        return self.is_playing

    def reset_view(self):
        self.camera = Camera()

    def is_underwater(self):
        return self.camera.is_underwater

    def get_framebuffer(self):
        width, height = self.width(), self.height()
        glReadBuffer(GL_FRONT)
        pixels = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
        image = np.frombuffer(pixels, dtype=np.uint8).reshape((height, width, 3))
        image = np.flip(image, axis=0)
        return image
