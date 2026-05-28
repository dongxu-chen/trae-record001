import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtOpenGL import QGLWidget
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import trimesh


class GLViewer3D(QGLWidget):
    vertices_selected = pyqtSignal(set)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mesh = None
        self.uv = None
        self.texture = None
        self.texture_id = None

        self.rot_x = 30.0
        self.rot_y = 45.0
        self.zoom = 5.0
        self.pan_x = 0.0
        self.pan_y = 0.0

        self.last_pos = QPoint()
        self.mouse_button = None

        self.display_mode = 'solid'
        self.show_wireframe = False

        self.selection_mode = False
        self.selected_vertices = set()
        self.select_radius = 10

        self.highlighted_vertices = set()

    def set_mesh(self, mesh):
        self.mesh = mesh
        self.selected_vertices.clear()
        self.highlighted_vertices.clear()
        self.update()

    def set_uv(self, uv):
        self.uv = uv
        self.update()

    def set_texture(self, texture):
        self.texture = texture
        if texture is not None:
            self.load_texture()
        self.update()

    def set_highlighted_vertices(self, vertices):
        self.highlighted_vertices = set(vertices) if vertices else set()
        self.update()

    def set_selection_mode(self, enabled):
        self.selection_mode = enabled
        if not enabled:
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    def load_texture(self):
        if self.texture_id is not None:
            glDeleteTextures([self.texture_id])

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        tex_data = np.flipud(self.texture)
        h, w = tex_data.shape[:2]

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, tex_data)
        glBindTexture(GL_TEXTURE_2D, 0)

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glShadeModel(GL_SMOOTH)
        glClearColor(0.3, 0.3, 0.3, 1.0)

        light_pos = [1.0, 1.0, 1.0, 0.0]
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w / h if h > 0 else 1.0, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        glTranslatef(self.pan_x, self.pan_y, -self.zoom)
        glRotatef(self.rot_x, 1.0, 0.0, 0.0)
        glRotatef(self.rot_y, 0.0, 1.0, 0.0)

        if self.mesh is not None:
            self.draw_mesh()
            self.draw_highlighted_vertices()
            self.draw_selected_vertices()

        self.draw_axes()

    def draw_axes(self):
        glDisable(GL_LIGHTING)
        glLineWidth(2.0)

        glBegin(GL_LINES)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(1.0, 0.0, 0.0)

        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 1.0, 0.0)

        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 0.0, 1.0)
        glEnd()

        glEnable(GL_LIGHTING)

    def get_scaled_vertices(self):
        if self.mesh is None:
            return None
        vertices = self.mesh.vertices
        center = np.mean(vertices, axis=0)
        scale = np.max(np.linalg.norm(vertices - center, axis=1))
        if scale == 0:
            scale = 1
        return (vertices - center) / scale

    def draw_mesh(self):
        vertices = self.mesh.vertices
        faces = self.mesh.faces
        normals = self.mesh.vertex_normals

        center = np.mean(vertices, axis=0)
        scale = np.max(np.linalg.norm(vertices - center, axis=1))
        if scale == 0:
            scale = 1

        vertices_scaled = (vertices - center) / scale

        if self.display_mode == 'solid' and self.texture is not None and self.uv is not None:
            self.draw_textured_mesh(vertices_scaled, faces, normals)
        elif self.display_mode == 'solid':
            self.draw_solid_mesh(vertices_scaled, faces, normals)
        elif self.display_mode == 'wireframe':
            self.draw_wireframe_mesh(vertices_scaled, faces)
        elif self.display_mode == 'points':
            self.draw_points_mesh(vertices_scaled)

        if self.show_wireframe and self.display_mode == 'solid':
            glPolygonOffset(1.0, 1.0)
            glEnable(GL_POLYGON_OFFSET_LINE)
            self.draw_wireframe_mesh(vertices_scaled, faces, color=(0, 0, 0))
            glDisable(GL_POLYGON_OFFSET_LINE)

    def draw_textured_mesh(self, vertices, faces, normals):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        glBegin(GL_TRIANGLES)
        for face in faces:
            for v_idx in face:
                glTexCoord2f(self.uv[v_idx, 0], self.uv[v_idx, 1])
                glNormal3f(*normals[v_idx])
                glVertex3f(*vertices[v_idx])
        glEnd()

        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)

    def draw_solid_mesh(self, vertices, faces, normals):
        glColor3f(0.8, 0.8, 0.8)
        glBegin(GL_TRIANGLES)
        for face in faces:
            for v_idx in face:
                glNormal3f(*normals[v_idx])
                glVertex3f(*vertices[v_idx])
        glEnd()

    def draw_wireframe_mesh(self, vertices, faces, color=None):
        glDisable(GL_LIGHTING)
        if color is None:
            glColor3f(0.2, 0.2, 0.2)
        else:
            glColor3f(*color)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        glBegin(GL_TRIANGLES)
        for face in faces:
            for v_idx in face:
                glVertex3f(*vertices[v_idx])
        glEnd()

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glEnable(GL_LIGHTING)

    def draw_points_mesh(self, vertices):
        glDisable(GL_LIGHTING)
        glColor3f(0.6, 0.6, 0.6)
        glPointSize(3.0)

        glBegin(GL_POINTS)
        for v in vertices:
            glVertex3f(*v)
        glEnd()

        glEnable(GL_LIGHTING)

    def draw_highlighted_vertices(self):
        if not self.highlighted_vertices or self.mesh is None:
            return

        vertices_scaled = self.get_scaled_vertices()

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glPointSize(12.0)

        glBegin(GL_POINTS)
        glColor3f(0.0, 1.0, 1.0)
        for v_idx in self.highlighted_vertices:
            if v_idx < len(vertices_scaled):
                glVertex3f(*vertices_scaled[v_idx])
        glEnd()

        glPointSize(8.0)
        glBegin(GL_POINTS)
        glColor3f(1.0, 1.0, 0.0)
        for v_idx in self.highlighted_vertices:
            if v_idx < len(vertices_scaled):
                glVertex3f(*vertices_scaled[v_idx])
        glEnd()

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

    def draw_selected_vertices(self):
        if not self.selected_vertices or self.mesh is None:
            return

        vertices_scaled = self.get_scaled_vertices()

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glPointSize(14.0)

        glBegin(GL_POINTS)
        glColor3f(1.0, 0.0, 1.0)
        for v_idx in self.selected_vertices:
            if v_idx < len(vertices_scaled):
                glVertex3f(*vertices_scaled[v_idx])
        glEnd()

        glPointSize(10.0)
        glBegin(GL_POINTS)
        glColor3f(0.0, 1.0, 0.0)
        for v_idx in self.selected_vertices:
            if v_idx < len(vertices_scaled):
                glVertex3f(*vertices_scaled[v_idx])
        glEnd()

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

    def project_vertex(self, v_idx):
        if self.mesh is None:
            return None

        vertices_scaled = self.get_scaled_vertices()
        if v_idx >= len(vertices_scaled):
            return None

        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)

        v = vertices_scaled[v_idx]
        screen_pos = gluProject(v[0], v[1], v[2], modelview, projection, viewport)
        if screen_pos:
            return np.array([screen_pos[0], viewport[3] - screen_pos[1]])
        return None

    def pick_vertex(self, screen_x, screen_y):
        if self.mesh is None:
            return None

        closest_v = None
        min_dist = float('inf')

        for v_idx in range(len(self.mesh.vertices)):
            screen_pos = self.project_vertex(v_idx)
            if screen_pos is not None:
                dist = np.linalg.norm(screen_pos - np.array([screen_x, screen_y]))
                if dist < min_dist and dist < self.select_radius:
                    min_dist = dist
                    closest_v = v_idx

        return closest_v

    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        self.mouse_button = event.button()

        if self.selection_mode and event.button() == Qt.LeftButton:
            v_idx = self.pick_vertex(event.x(), event.y())
            if v_idx is not None:
                if event.modifiers() & Qt.ShiftModifier:
                    if v_idx in self.selected_vertices:
                        self.selected_vertices.remove(v_idx)
                    else:
                        self.selected_vertices.add(v_idx)
                else:
                    self.selected_vertices.clear()
                    self.selected_vertices.add(v_idx)
                self.vertices_selected.emit(self.selected_vertices)
                self.update()
            return

    def mouseMoveEvent(self, event):
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()

        if self.selection_mode and self.mouse_button == Qt.LeftButton:
            pass
        elif self.mouse_button == Qt.LeftButton:
            self.rot_y += dx * 0.5
            self.rot_x += dy * 0.5
        elif self.mouse_button == Qt.MidButton:
            self.pan_x += dx * 0.01
            self.pan_y -= dy * 0.01
        elif self.mouse_button == Qt.RightButton:
            self.zoom += dy * 0.05
            self.zoom = max(1.0, min(self.zoom, 50.0))

        self.last_pos = event.pos()
        self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.zoom -= delta * 0.005
        self.zoom = max(1.0, min(self.zoom, 50.0))
        self.update()

    def set_display_mode(self, mode):
        self.display_mode = mode
        self.update()

    def toggle_wireframe(self, show):
        self.show_wireframe = show
        self.update()

    def clear_selection(self):
        self.selected_vertices.clear()
        self.highlighted_vertices.clear()
        self.update()
