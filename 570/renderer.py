import numpy as np
from OpenGL.GL import *
from OpenGL.GL import shaders
from PIL import Image
import ctypes


class FluidRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
        self.vao = None
        self.vbo = None
        self.ebo = None
        self.texture = None
        self.shader_program = None
        
        self.particle_vao = None
        self.particle_vbo = None
        
        self.body_vao = None
        self.body_vbo = None
        
        self._init_buffers()
        self._init_shaders()
        self._init_texture()
    
    def _init_buffers(self):
        vertices = np.array([
            -1.0, -1.0, 0.0, 0.0, 1.0,
             1.0, -1.0, 0.0, 1.0, 1.0,
             1.0,  1.0, 0.0, 1.0, 0.0,
            -1.0,  1.0, 0.0, 0.0, 0.0,
        ], dtype=np.float32)
        
        indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32)
        
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        
        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(3 * 4))
        glEnableVertexAttribArray(1)
        
        glBindVertexArray(0)
        
        self.particle_vao = glGenVertexArrays(1)
        glBindVertexArray(self.particle_vao)
        self.particle_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.particle_vbo)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(2 * 4))
        glEnableVertexAttribArray(1)
        glBindVertexArray(0)
        
        self.body_vao = glGenVertexArrays(1)
        glBindVertexArray(self.body_vao)
        self.body_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.body_vbo)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 6 * 4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, 6 * 4, ctypes.c_void_p(2 * 4))
        glEnableVertexAttribArray(1)
        glBindVertexArray(0)
    
    def _init_shaders(self):
        vertex_shader = """
        #version 330 core
        layout (location = 0) in vec3 aPos;
        layout (location = 1) in vec2 aTexCoord;
        
        out vec2 TexCoord;
        
        void main() {
            gl_Position = vec4(aPos, 1.0);
            TexCoord = aTexCoord;
        }
        """
        
        fragment_shader = """
        #version 330 core
        out vec4 FragColor;
        
        in vec2 TexCoord;
        
        uniform sampler2D ourTexture;
        uniform int displayMode;
        uniform float colorScale;
        uniform int showPhase;
        uniform sampler2D phaseTexture;
        
        vec3 hsv2rgb(vec3 c) {
            vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
            vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
            return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
        }
        
        void main() {
            vec4 texColor = texture(ourTexture, TexCoord);
            vec4 phaseColor = texture(phaseTexture, TexCoord);
            
            vec4 baseColor;
            
            if (displayMode == 0) {
                float vel = length(texColor.xy);
                float angle = atan(texColor.y, texColor.x);
                float hue = (angle + 3.14159) / (2.0 * 3.14159);
                vec3 color = hsv2rgb(vec3(hue, 1.0, min(vel * colorScale, 1.0)));
                baseColor = vec4(color, 1.0);
            } else if (displayMode == 1) {
                float p = texColor.x * colorScale;
                baseColor = vec4(p, p, p, 1.0);
            } else if (displayMode == 2) {
                float vort = texColor.x * colorScale;
                float abs_vort = abs(vort);
                if (vort > 0.0) {
                    baseColor = vec4(0.0, min(abs_vort, 1.0), 0.0, 1.0);
                } else {
                    baseColor = vec4(min(abs_vort, 1.0), 0.0, 0.0, 1.0);
                }
            } else if (displayMode == 3) {
                float vel = length(texColor.xy) * colorScale;
                baseColor = vec4(0.0, 0.0, min(vel, 1.0), 1.0);
            } else {
                baseColor = vec4(0.2, 0.2, 0.2, 1.0);
            }
            
            if (showPhase > 0 && phaseColor.x > 0.0) {
                float phase = phaseColor.x;
                vec3 liquidColor = vec3(0.0, 0.4, 0.8);
                vec3 gasColor = vec3(0.9, 0.9, 1.0);
                vec3 phaseColorMix = mix(gasColor, liquidColor, phase);
                
                float interface = phaseColor.y;
                if (interface > 0.1) {
                    baseColor = mix(baseColor, vec4(1.0, 1.0, 0.0, 1.0), min(interface * 5.0, 1.0));
                } else {
                    baseColor = mix(baseColor, vec4(phaseColorMix, 1.0), 0.6);
                }
            }
            
            FragColor = baseColor;
        }
        """
        
        vs = shaders.compileShader(vertex_shader, GL_VERTEX_SHADER)
        fs = shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
        self.shader_program = shaders.compileProgram(vs, fs)
        
        particle_vs = """
        #version 330 core
        layout (location = 0) in vec2 aPos;
        layout (location = 1) in vec3 aColor;
        
        uniform vec2 viewportScale;
        
        out vec3 vColor;
        
        void main() {
            vec2 pos = aPos * viewportScale * 2.0 - 1.0;
            pos.y = -pos.y;
            gl_Position = vec4(pos, 0.0, 1.0);
            gl_PointSize = 3.0;
            vColor = aColor;
        }
        """
        
        particle_fs = """
        #version 330 core
        out vec4 FragColor;
        
        in vec3 vColor;
        
        void main() {
            vec2 coord = gl_PointCoord - vec2(0.5);
            if (length(coord) > 0.5) discard;
            FragColor = vec4(vColor, 1.0);
        }
        """
        
        p_vs = shaders.compileShader(particle_vs, GL_VERTEX_SHADER)
        p_fs = shaders.compileShader(particle_fs, GL_FRAGMENT_SHADER)
        self.particle_shader = shaders.compileProgram(p_vs, p_fs)
        
        body_vs = """
        #version 330 core
        layout (location = 0) in vec2 aPos;
        layout (location = 1) in vec4 aColor;
        
        uniform vec2 viewportScale;
        
        out vec4 vColor;
        
        void main() {
            vec2 pos = aPos * viewportScale * 2.0 - 1.0;
            pos.y = -pos.y;
            gl_Position = vec4(pos, 0.0, 1.0);
            vColor = aColor;
        }
        """
        
        body_fs = """
        #version 330 core
        out vec4 FragColor;
        
        in vec4 vColor;
        
        void main() {
            FragColor = vColor;
        }
        """
        
        b_vs = shaders.compileShader(body_vs, GL_VERTEX_SHADER)
        b_fs = shaders.compileShader(body_fs, GL_FRAGMENT_SHADER)
        self.body_shader = shaders.compileProgram(b_vs, b_fs)
    
    def _init_texture(self):
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        data = np.zeros((self.height, self.width, 4), dtype=np.float32)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, self.width, self.height, 0, GL_RGBA, GL_FLOAT, data)
        glBindTexture(GL_TEXTURE_2D, 0)
        
        self.phase_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.phase_texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RG32F, self.width, self.height, 0, GL_RG, GL_FLOAT, data[:, :, :2])
        glBindTexture(GL_TEXTURE_2D, 0)
    
    def update_texture(self, data):
        glBindTexture(GL_TEXTURE_2D, self.texture)
        
        if len(data.shape) == 2:
            rgba_data = np.zeros((self.height, self.width, 4), dtype=np.float32)
            rgba_data[:, :, 0] = data
            rgba_data[:, :, 1] = data
            rgba_data[:, :, 2] = data
            rgba_data[:, :, 3] = 1.0
        elif data.shape[2] == 2:
            rgba_data = np.zeros((self.height, self.width, 4), dtype=np.float32)
            rgba_data[:, :, 0:2] = data
            rgba_data[:, :, 3] = 1.0
        else:
            rgba_data = data.astype(np.float32)
        
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, self.width, self.height, GL_RGBA, GL_FLOAT, rgba_data)
        glBindTexture(GL_TEXTURE_2D, 0)
    
    def update_phase_texture(self, phase, interface):
        glBindTexture(GL_TEXTURE_2D, self.phase_texture)
        data = np.zeros((self.height, self.width, 2), dtype=np.float32)
        data[:, :, 0] = phase
        data[:, :, 1] = interface
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, self.width, self.height, GL_RG, GL_FLOAT, data)
        glBindTexture(GL_TEXTURE_2D, 0)
    
    def update_particles(self, positions, colors):
        if len(positions) == 0:
            self.particle_count = 0
            return
        
        self.particle_count = len(positions)
        
        particle_data = np.zeros((len(positions), 5), dtype=np.float32)
        particle_data[:, 0:2] = positions
        particle_data[:, 2:5] = colors
        
        glBindBuffer(GL_ARRAY_BUFFER, self.particle_vbo)
        glBufferData(GL_ARRAY_BUFFER, particle_data.nbytes, particle_data, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    def update_streamlines(self, lines, colors):
        self.streamline_data = []
        self.streamline_count = 0
        
        for line, color in zip(lines, colors):
            if len(line) < 2:
                continue
            
            line_data = np.zeros((len(line) - 1, 10), dtype=np.float32)
            for i in range(len(line) - 1):
                alpha = i / max(len(line) - 1, 1)
                line_data[i, 0:2] = line[i]
                line_data[i, 2:5] = color * alpha
                line_data[i, 5:7] = line[i + 1]
                line_data[i, 7:10] = color * (alpha + 0.1)
            
            self.streamline_data.append(line_data)
            self.streamline_count += (len(line) - 1)
        
        if self.streamline_count > 0:
            all_data = np.vstack(self.streamline_data)
            glBindBuffer(GL_ARRAY_BUFFER, self.particle_vbo)
            glBufferData(GL_ARRAY_BUFFER, all_data.nbytes, all_data, GL_DYNAMIC_DRAW)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    def update_bodies(self, body_states):
        body_vertices = []
        
        for body in body_states:
            cx = body['cx']
            cy = body['cy']
            r = body['radius']
            angle = body['angle']
            fixed = body['fixed']
            
            color = [0.8, 0.3, 0.3, 1.0] if fixed else [0.3, 0.8, 0.3, 1.0]
            
            segments = 32
            for i in range(segments):
                theta1 = 2.0 * np.pi * i / segments + angle
                theta2 = 2.0 * np.pi * (i + 1) / segments + angle
                
                x1 = cx + r * np.cos(theta1)
                y1 = cy + r * np.sin(theta1)
                x2 = cx + r * np.cos(theta2)
                y2 = cy + r * np.sin(theta2)
                
                body_vertices.extend([cx, cy] + color)
                body_vertices.extend([x1, y1] + color)
                body_vertices.extend([x2, y2] + color)
                
                dir_x = np.cos(angle)
                dir_y = np.sin(angle)
                body_vertices.extend([cx, cy] + [1.0, 1.0, 0.0, 1.0])
                body_vertices.extend([cx + r * dir_x, cy + r * dir_y] + [1.0, 1.0, 0.0, 1.0])
                body_vertices.extend([cx + r * 0.8 * dir_x, cy + r * 0.8 * dir_y] + [1.0, 1.0, 0.0, 1.0])
        
        self.body_count = len(body_vertices) // 6
        
        if self.body_count > 0:
            body_data = np.array(body_vertices, dtype=np.float32).reshape(-1, 6)
            glBindBuffer(GL_ARRAY_BUFFER, self.body_vbo)
            glBufferData(GL_ARRAY_BUFFER, body_data.nbytes, body_data, GL_DYNAMIC_DRAW)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
        else:
            self.body_count = 0
    
    def render(self, display_mode=0, color_scale=10.0, show_phase=False, show_particles=False, 
               show_streamlines=False, show_bodies=False):
        glUseProgram(self.shader_program)
        
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glUniform1i(glGetUniformLocation(self.shader_program, "ourTexture"), 0)
        
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.phase_texture)
        glUniform1i(glGetUniformLocation(self.shader_program, "phaseTexture"), 1)
        
        glUniform1i(glGetUniformLocation(self.shader_program, "displayMode"), display_mode)
        glUniform1f(glGetUniformLocation(self.shader_program, "colorScale"), color_scale)
        glUniform1i(glGetUniformLocation(self.shader_program, "showPhase"), 1 if show_phase else 0)
        
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
        
        if show_bodies and self.body_count > 0:
            self._render_bodies()
        
        if show_streamlines and self.streamline_count > 0:
            self._render_streamlines()
        
        if show_particles and self.particle_count > 0:
            self._render_particles()
    
    def _render_particles(self):
        glUseProgram(self.particle_shader)
        glUniform2f(glGetUniformLocation(self.particle_shader, "viewportScale"), 
                   1.0 / self.width, 1.0 / self.height)
        
        glEnable(GL_POINT_SMOOTH)
        glBindVertexArray(self.particle_vao)
        glDrawArrays(GL_POINTS, 0, self.particle_count)
        glBindVertexArray(0)
        glDisable(GL_POINT_SMOOTH)
    
    def _render_streamlines(self):
        if self.streamline_count == 0:
            return
        
        glUseProgram(self.particle_shader)
        glUniform2f(glGetUniformLocation(self.particle_shader, "viewportScale"), 
                   1.0 / self.width, 1.0 / self.height)
        
        glEnable(GL_LINE_SMOOTH)
        glBindVertexArray(self.particle_vao)
        glDrawArrays(GL_LINES, 0, self.streamline_count * 2)
        glBindVertexArray(0)
        glDisable(GL_LINE_SMOOTH)
    
    def _render_bodies(self):
        glUseProgram(self.body_shader)
        glUniform2f(glGetUniformLocation(self.body_shader, "viewportScale"), 
                   1.0 / self.width, 1.0 / self.height)
        
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glBindVertexArray(self.body_vao)
        glDrawArrays(GL_TRIANGLES, 0, self.body_count)
        glBindVertexArray(0)
        
        glDisable(GL_BLEND)
    
    def cleanup(self):
        glDeleteVertexArrays(1, [self.vao])
        glDeleteBuffers(1, [self.vbo])
        glDeleteBuffers(1, [self.ebo])
        glDeleteTextures(1, [self.texture])
        glDeleteTextures(1, [self.phase_texture])
        glDeleteProgram(self.shader_program)
        glDeleteProgram(self.particle_shader)
        glDeleteProgram(self.body_shader)
        glDeleteVertexArrays(1, [self.particle_vao])
        glDeleteBuffers(1, [self.particle_vbo])
        glDeleteVertexArrays(1, [self.body_vao])
        glDeleteBuffers(1, [self.body_vbo])
