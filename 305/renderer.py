import numpy as np
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from typing import List, Tuple
from cloth import Cloth
from collision import SphereCollider, PlaneCollider
from rigid_body import RigidBody, RigidSphere, RigidBox


class Camera:
    def __init__(self, position: Tuple[float, float, float] = (0.0, 3.0, 10.0),
                 target: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 fov: float = 45.0,
                 near: float = 0.1,
                 far: float = 100.0):
        
        self.position = np.array(position, dtype=np.float64)
        self.target = np.array(target, dtype=np.float64)
        self.up = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        self.fov = fov
        self.near = near
        self.far = far
        
        self.yaw = -np.pi / 2.0
        self.pitch = -0.3
        self.distance = 10.0
        
        self._update_position_from_angles()
    
    def _update_position_from_angles(self):
        x = self.target[0] + self.distance * np.cos(self.pitch) * np.sin(self.yaw)
        y = self.target[1] + self.distance * np.sin(self.pitch)
        z = self.target[2] + self.distance * np.cos(self.pitch) * np.cos(self.yaw)
        self.position = np.array([x, y, z], dtype=np.float64)
    
    def orbit(self, dx: float, dy: float):
        self.yaw += dx * 0.01
        self.pitch += dy * 0.01
        self.pitch = max(-np.pi / 2.0 + 0.1, min(np.pi / 2.0 - 0.1, self.pitch))
        self._update_position_from_angles()
    
    def zoom(self, delta: float):
        self.distance += delta * 0.5
        self.distance = max(2.0, min(50.0, self.distance))
        self._update_position_from_angles()
    
    def pan(self, dx: float, dy: float):
        forward = self.target - self.position
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, self.up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)
        
        self.target += right * dx * 0.02
        self.target += up * dy * 0.02
        self._update_position_from_angles()
    
    def apply_projection(self, width: int, height: int):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fov, width / height, self.near, self.far)
    
    def apply_modelview(self):
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(
            self.position[0], self.position[1], self.position[2],
            self.target[0], self.target[1], self.target[2],
            self.up[0], self.up[1], self.up[2]
        )


class Renderer:
    def __init__(self, width: int = 1280, height: int = 720, title: str = "Cloth Simulation"):
        self.width = width
        self.height = height
        self.title = title
        
        self.window = None
        self.camera = Camera()
        
        self.show_wireframe = False
        self.show_points = False
        self.show_broken_edges = True
        self.color_by_stress = False
        self.cloth_color = (0.3, 0.6, 0.9, 1.0)
        self.wireframe_color = (0.1, 0.1, 0.1, 1.0)
        self.point_color = (1.0, 0.0, 0.0, 1.0)
        self.broken_edge_color = (1.0, 0.0, 0.0, 1.0)
        self.background_color = (0.95, 0.95, 0.95, 1.0)
        self.max_stress = 0.5
        
        self._mouse_down = False
        self._right_mouse_down = False
        self._last_mouse_pos = (0, 0)
        
        self._init_gl()
    
    def _init_gl(self):
        pygame.init()
        pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL | RESIZABLE)
        pygame.display.set_caption(self.title)
        
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glShadeModel(GL_SMOOTH)
        
        light_pos = [5.0, 10.0, 5.0, 1.0]
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
        
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50.0)
        
        self.camera.apply_projection(self.width, self.height)
    
    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == QUIT:
                return False
            
            if event.type == VIDEORESIZE:
                self.width = event.w
                self.height = event.h
                pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL | RESIZABLE)
                glViewport(0, 0, self.width, self.height)
                self.camera.apply_projection(self.width, self.height)
            
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._mouse_down = True
                    self._last_mouse_pos = pygame.mouse.get_pos()
                elif event.button == 3:
                    self._right_mouse_down = True
                    self._last_mouse_pos = pygame.mouse.get_pos()
                elif event.button == 4:
                    self.camera.zoom(-1.0)
                elif event.button == 5:
                    self.camera.zoom(1.0)
            
            if event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    self._mouse_down = False
                elif event.button == 3:
                    self._right_mouse_down = False
            
            if event.type == MOUSEMOTION:
                if self._mouse_down:
                    mx, my = pygame.mouse.get_pos()
                    dx = mx - self._last_mouse_pos[0]
                    dy = my - self._last_mouse_pos[1]
                    self.camera.orbit(dx, dy)
                    self._last_mouse_pos = (mx, my)
                elif self._right_mouse_down:
                    mx, my = pygame.mouse.get_pos()
                    dx = mx - self._last_mouse_pos[0]
                    dy = my - self._last_mouse_pos[1]
                    self.camera.pan(-dx, dy)
                    self._last_mouse_pos = (mx, my)
        
        return True
    
    def clear(self):
        glClearColor(*self.background_color)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.camera.apply_projection(self.width, self.height)
        self.camera.apply_modelview()
    
    def draw_grid(self, size: float = 10.0, steps: int = 20):
        glDisable(GL_LIGHTING)
        glColor3f(0.7, 0.7, 0.7)
        glLineWidth(0.5)
        
        step_size = size / steps
        
        glBegin(GL_LINES)
        for i in range(steps + 1):
            x = -size / 2.0 + i * step_size
            glVertex3f(x, 0.0, -size / 2.0)
            glVertex3f(x, 0.0, size / 2.0)
            
            z = -size / 2.0 + i * step_size
            glVertex3f(-size / 2.0, 0.0, z)
            glVertex3f(size / 2.0, 0.0, z)
        glEnd()
        
        glEnable(GL_LIGHTING)
    
    def _stress_to_color(self, stress: float, max_stress: float) -> Tuple[float, float, float]:
        ratio = min(stress / max_stress, 1.0)
        if ratio < 0.5:
            t = ratio * 2.0
            r = 0.0
            g = t
            b = 1.0 - t
        else:
            t = (ratio - 0.5) * 2.0
            r = t
            g = 1.0 - t
            b = 0.0
        return (r, g, b)
    
    def draw_cloth(self, cloth: Cloth):
        positions = cloth.get_position_array()
        triangles = cloth.get_triangles()
        edges = cloth.get_wireframe_edges()
        broken_edges = cloth.get_broken_edges()
        pinned_mask = cloth.get_pinned_mask()
        
        stress = None
        if self.color_by_stress:
            stress = cloth.get_stress_array()
        
        normals = self._compute_normals(positions, triangles)
        
        if not self.show_wireframe:
            glBegin(GL_TRIANGLES)
            if self.color_by_stress and stress is not None:
                for tri in triangles:
                    for idx in tri:
                        glNormal3f(*normals[idx])
                        color = self._stress_to_color(stress[idx], self.max_stress)
                        glColor3f(*color)
                        glVertex3f(*positions[idx])
            else:
                glColor4f(*self.cloth_color)
                for tri in triangles:
                    for idx in tri:
                        glNormal3f(*normals[idx])
                        glVertex3f(*positions[idx])
            glEnd()
        
        if self.show_wireframe or True:
            glDisable(GL_LIGHTING)
            glColor4f(*self.wireframe_color)
            glLineWidth(1.0)
            glBegin(GL_LINES)
            for edge in edges:
                glVertex3f(*positions[edge[0]])
                glVertex3f(*positions[edge[1]])
            glEnd()
            
            if self.show_broken_edges and len(broken_edges) > 0:
                glColor4f(*self.broken_edge_color)
                glLineWidth(2.0)
                glEnable(GL_LINE_STIPPLE)
                glLineStipple(2, 0x00FF)
                glBegin(GL_LINES)
                for edge in broken_edges:
                    glVertex3f(*positions[edge[0]])
                    glVertex3f(*positions[edge[1]])
                glEnd()
                glDisable(GL_LINE_STIPPLE)
            
            glEnable(GL_LIGHTING)
        
        if self.show_points:
            glDisable(GL_LIGHTING)
            glPointSize(4.0)
            glBegin(GL_POINTS)
            for i, pos in enumerate(positions):
                if pinned_mask[i]:
                    glColor3f(1.0, 0.0, 0.0)
                elif self.color_by_stress and stress is not None:
                    color = self._stress_to_color(stress[i], self.max_stress)
                    glColor3f(*color)
                else:
                    glColor4f(*self.point_color)
                glVertex3f(*pos)
            glEnd()
            glEnable(GL_LIGHTING)
    
    def draw_rigid_body(self, body: RigidBody):
        if not body.enabled:
            return
        
        glDisable(GL_LIGHTING)
        
        if isinstance(body, RigidSphere):
            glColor4f(0.8, 0.5, 0.2, 0.6)
            
            quad = gluNewQuadric()
            gluQuadricNormals(quad, GLU_SMOOTH)
            gluQuadricTexture(quad, GL_FALSE)
            
            glPushMatrix()
            glTranslatef(body.state.position[0], body.state.position[1], body.state.position[2])
            q = body.state.orientation
            angle = 2.0 * np.arccos(q[0])
            if abs(angle) > 1e-6:
                axis = q[1:] / np.sin(angle / 2.0)
                glRotatef(angle * 180.0 / np.pi, axis[0], axis[1], axis[2])
            gluSphere(quad, body.radius, 32, 32)
            glPopMatrix()
            
            gluDeleteQuadric(quad)
        
        elif isinstance(body, RigidBox):
            glColor4f(0.2, 0.6, 0.8, 0.6)
            
            half_size = body.size * 0.5
            
            vertices = np.array([
                [-half_size[0], -half_size[1], -half_size[2]],
                [ half_size[0], -half_size[1], -half_size[2]],
                [ half_size[0],  half_size[1], -half_size[2]],
                [-half_size[0],  half_size[1], -half_size[2]],
                [-half_size[0], -half_size[1],  half_size[2]],
                [ half_size[0], -half_size[1],  half_size[2]],
                [ half_size[0],  half_size[1],  half_size[2]],
                [-half_size[0],  half_size[1],  half_size[2]],
            ])
            
            q = body.state.orientation
            w, x, y, z = q
            rot_mat = np.array([
                [1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
                [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
                [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)]
            ])
            
            rotated_vertices = vertices @ rot_mat.T + body.state.position
            
            faces = [
                [0, 1, 2, 3],
                [5, 4, 7, 6],
                [4, 0, 3, 7],
                [1, 5, 6, 2],
                [3, 2, 6, 7],
                [4, 5, 1, 0],
            ]
            
            glBegin(GL_QUADS)
            for face in faces:
                for idx in face:
                    glVertex3f(*rotated_vertices[idx])
            glEnd()
            
            glColor3f(0.1, 0.1, 0.1)
            glLineWidth(1.5)
            edges = [
                [0, 1], [1, 2], [2, 3], [3, 0],
                [4, 5], [5, 6], [6, 7], [7, 4],
                [0, 4], [1, 5], [2, 6], [3, 7],
            ]
            glBegin(GL_LINES)
            for edge in edges:
                glVertex3f(*rotated_vertices[edge[0]])
                glVertex3f(*rotated_vertices[edge[1]])
            glEnd()
        
        glEnable(GL_LIGHTING)
    
    def _compute_normals(self, positions: np.ndarray, triangles: np.ndarray) -> np.ndarray:
        normals = np.zeros_like(positions)
        
        for tri in triangles:
            v0 = positions[tri[0]]
            v1 = positions[tri[1]]
            v2 = positions[tri[2]]
            
            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = np.cross(edge1, edge2)
            normal_len = np.linalg.norm(normal)
            if normal_len > 1e-6:
                normal = normal / normal_len
            
            normals[tri[0]] += normal
            normals[tri[1]] += normal
            normals[tri[2]] += normal
        
        for i in range(len(normals)):
            normal_len = np.linalg.norm(normals[i])
            if normal_len > 1e-6:
                normals[i] = normals[i] / normal_len
        
        return normals
    
    def draw_sphere(self, collider: SphereCollider):
        if not collider.enabled:
            return
        
        glDisable(GL_LIGHTING)
        glColor4f(0.8, 0.3, 0.3, 0.5)
        
        quad = gluNewQuadric()
        gluQuadricNormals(quad, GLU_SMOOTH)
        gluQuadricTexture(quad, GL_FALSE)
        
        glPushMatrix()
        glTranslatef(collider.center[0], collider.center[1], collider.center[2])
        gluSphere(quad, collider.radius, 32, 32)
        glPopMatrix()
        
        gluDeleteQuadric(quad)
        glEnable(GL_LIGHTING)
    
    def draw_plane(self, collider: PlaneCollider):
        if not collider.enabled:
            return
        
        glDisable(GL_LIGHTING)
        glColor4f(0.5, 0.5, 0.5, 0.8)
        
        center = collider.point
        normal = collider.normal
        
        tangent = np.array([1.0, 0.0, 0.0])
        if abs(np.dot(tangent, normal)) > 0.9:
            tangent = np.array([0.0, 1.0, 0.0])
        
        bitangent = np.cross(normal, tangent)
        bitangent = bitangent / np.linalg.norm(bitangent)
        tangent = np.cross(bitangent, normal)
        tangent = tangent / np.linalg.norm(tangent)
        
        size = 10.0
        v0 = center - tangent * size - bitangent * size
        v1 = center + tangent * size - bitangent * size
        v2 = center + tangent * size + bitangent * size
        v3 = center - tangent * size + bitangent * size
        
        glBegin(GL_QUADS)
        glNormal3f(*normal)
        glVertex3f(*v0)
        glVertex3f(*v1)
        glVertex3f(*v2)
        glVertex3f(*v3)
        glEnd()
        
        glEnable(GL_LIGHTING)
    
    def swap_buffers(self):
        pygame.display.flip()
    
    def get_delta_time(self) -> float:
        return pygame.time.get_ticks() / 1000.0
    
    def cleanup(self):
        pygame.quit()
