import numpy as np
import cv2
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QPoint, QRectF, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush, QPolygonF
from PyQt5.QtCore import QPointF


class UVEditor(QGraphicsView):
    vertices_selected = pyqtSignal(set)
    vertices_highlighted = pyqtSignal(set)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)

        self.uv = None
        self.faces = None
        self.texture = None
        self.texture_pixmap = None
        self.texture_item = None

        self.selected_vertices = set()
        self.highlighted_vertices = set()
        self.uv_items = []
        self.edge_items = []
        self.face_items = []

        self.last_pos = QPoint()
        self.dragging = False
        self.selecting = False
        self.selection_rect = None
        self.selection_start = QPoint()

        self.scale_factor = 1.0

        self.setMinimumSize(400, 400)

    def set_uv(self, uv, faces):
        self.uv = uv.copy()
        self.faces = faces
        self.selected_vertices.clear()
        self.highlighted_vertices.clear()
        self.update_view()

    def set_texture(self, texture):
        self.texture = texture
        if texture is not None:
            h, w = texture.shape[:2]
            qimage = QImage(texture.data, w, h, 3 * w, QImage.Format_RGB888)
            self.texture_pixmap = QPixmap.fromImage(qimage.rgbSwapped())
        else:
            self.texture_pixmap = None
        self.update_view()

    def set_highlighted_vertices(self, vertices):
        self.highlighted_vertices = set(vertices) if vertices else set()
        self.update_vertex_colors()

    def set_selected_vertices(self, vertices):
        self.selected_vertices = set(vertices) if vertices else set()
        self.update_vertex_colors()

    def update_view(self):
        self.scene.clear()
        self.uv_items = []
        self.edge_items = []
        self.face_items = []

        if self.texture_pixmap is not None:
            self.texture_item = self.scene.addPixmap(self.texture_pixmap)
            self.texture_item.setZValue(-1)
            self.scene.setSceneRect(0, 0, self.texture_pixmap.width(), self.texture_pixmap.height())
        else:
            self.scene.setSceneRect(0, 0, 512, 512)

        if self.uv is None or self.faces is None:
            return

        tex_h = self.texture_pixmap.height() if self.texture_pixmap is not None else 512
        tex_w = self.texture_pixmap.width() if self.texture_pixmap is not None else 512

        for face in self.faces:
            face_uv = self.uv[face]
            points = []
            for uv in face_uv:
                x = uv[0] * tex_w
                y = (1 - uv[1]) * tex_h
                points.append(QPointF(x, y))
            polygon = QPolygonF(points)
            item = self.scene.addPolygon(polygon, QPen(QColor(100, 100, 100, 100), 1))
            item.setBrush(QBrush(QColor(200, 200, 200, 50)))
            self.face_items.append(item)

        for face in self.faces:
            for i in range(3):
                v1 = face[i]
                v2 = face[(i + 1) % 3]
                uv1 = self.uv[v1]
                uv2 = self.uv[v2]
                x1 = uv1[0] * tex_w
                y1 = (1 - uv1[1]) * tex_h
                x2 = uv2[0] * tex_w
                y2 = (1 - uv2[1]) * tex_h
                item = self.scene.addLine(x1, y1, x2, y2, QPen(QColor(0, 0, 0), 1))
                self.edge_items.append((v1, v2, item))

        for i, uv in enumerate(self.uv):
            x = uv[0] * tex_w
            y = (1 - uv[1]) * tex_h

            if i in self.highlighted_vertices and i in self.selected_vertices:
                brush = QBrush(QColor(255, 0, 255, 200))
                pen = QPen(QColor(128, 0, 128), 2)
                size = 12
            elif i in self.highlighted_vertices:
                brush = QBrush(QColor(0, 255, 255, 200))
                pen = QPen(QColor(0, 128, 128), 2)
                size = 10
            elif i in self.selected_vertices:
                brush = QBrush(QColor(0, 255, 0, 200))
                pen = QPen(QColor(0, 128, 0), 2)
                size = 10
            else:
                brush = QBrush(QColor(255, 0, 0, 150))
                pen = QPen(QColor(255, 0, 0), 1)
                size = 8

            item = self.scene.addEllipse(x - size / 2, y - size / 2, size, size, pen, brush)
            item.setData(0, i)
            self.uv_items.append(item)

    def update_vertex_colors(self):
        for i, item in enumerate(self.uv_items):
            if self.uv is None or i >= len(self.uv):
                continue

            tex_h = self.texture_pixmap.height() if self.texture_pixmap is not None else 512
            tex_w = self.texture_pixmap.width() if self.texture_pixmap is not None else 512
            x = self.uv[i, 0] * tex_w
            y = (1 - self.uv[i, 1]) * tex_h

            if i in self.highlighted_vertices and i in self.selected_vertices:
                item.setBrush(QBrush(QColor(255, 0, 255, 200)))
                item.setPen(QPen(QColor(128, 0, 128), 2))
                item.setRect(x - 6, y - 6, 12, 12)
            elif i in self.highlighted_vertices:
                item.setBrush(QBrush(QColor(0, 255, 255, 200)))
                item.setPen(QPen(QColor(0, 128, 128), 2))
                item.setRect(x - 5, y - 5, 10, 10)
            elif i in self.selected_vertices:
                item.setBrush(QBrush(QColor(0, 255, 0, 200)))
                item.setPen(QPen(QColor(0, 128, 0), 2))
                item.setRect(x - 5, y - 5, 10, 10)
            else:
                item.setBrush(QBrush(QColor(255, 0, 0, 150)))
                item.setPen(QPen(QColor(255, 0, 0), 1))
                item.setRect(x - 4, y - 4, 8, 8)

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        self.last_pos = event.pos()

        if event.button() == Qt.LeftButton:
            item = self.scene.itemAt(scene_pos, self.transform())
            if item in self.uv_items:
                v_idx = item.data(0)
                if event.modifiers() & Qt.ShiftModifier:
                    if v_idx in self.selected_vertices:
                        self.selected_vertices.remove(v_idx)
                    else:
                        self.selected_vertices.add(v_idx)
                else:
                    self.selected_vertices.clear()
                    self.selected_vertices.add(v_idx)
                self.update_vertex_colors()
                self.vertices_selected.emit(self.selected_vertices)
                self.dragging = True
            else:
                self.selecting = True
                self.selection_start = scene_pos
                if self.selection_rect is None:
                    self.selection_rect = self.scene.addRect(QRectF(), QPen(QColor(0, 0, 255), 1, Qt.DashLine))
                self.selection_rect.setRect(QRectF(scene_pos, scene_pos))
                if not (event.modifiers() & Qt.ShiftModifier):
                    self.selected_vertices.clear()
                    self.update_vertex_colors()

        elif event.button() == Qt.MidButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)

        elif event.button() == Qt.RightButton:
            pass

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())

        if self.dragging and len(self.selected_vertices) > 0:
            dx = (event.pos() - self.last_pos).x() / self.scale_factor
            dy = (event.pos() - self.last_pos).y() / self.scale_factor

            tex_h = self.texture_pixmap.height() if self.texture_pixmap is not None else 512
            tex_w = self.texture_pixmap.width() if self.texture_pixmap is not None else 512

            for v_idx in self.selected_vertices:
                self.uv[v_idx, 0] += dx / tex_w
                self.uv[v_idx, 1] -= dy / tex_h
                self.uv[v_idx] = np.clip(self.uv[v_idx], 0, 1)

            self.update_uv_positions()
            self.vertices_highlighted.emit(self.selected_vertices)

        elif self.selecting and self.selection_rect is not None:
            rect = QRectF(self.selection_start, scene_pos).normalized()
            self.selection_rect.setRect(rect)

            new_selected = set()
            for item in self.uv_items:
                v_idx = item.data(0)
                if rect.contains(item.scenePos()):
                    new_selected.add(v_idx)

            if event.modifiers() & Qt.ShiftModifier:
                self.selected_vertices.update(new_selected)
            else:
                self.selected_vertices = new_selected

            self.update_vertex_colors()
            self.vertices_selected.emit(self.selected_vertices)

        self.last_pos = event.pos()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.selecting = False
            if self.selection_rect is not None:
                self.scene.removeItem(self.selection_rect)
                self.selection_rect = None
            self.vertices_highlighted.emit(set())
        elif event.button() == Qt.MidButton:
            self.setDragMode(QGraphicsView.NoDrag)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 1 / 1.1
            self.scale(factor, factor)
            self.scale_factor *= factor
        else:
            super().wheelEvent(event)

    def update_uv_positions(self):
        if self.uv is None:
            return

        tex_h = self.texture_pixmap.height() if self.texture_pixmap is not None else 512
        tex_w = self.texture_pixmap.width() if self.texture_pixmap is not None else 512

        for i, item in enumerate(self.uv_items):
            x = self.uv[i, 0] * tex_w
            y = (1 - self.uv[i, 1]) * tex_h

            if i in self.highlighted_vertices and i in self.selected_vertices:
                item.setRect(x - 6, y - 6, 12, 12)
            elif i in self.highlighted_vertices or i in self.selected_vertices:
                item.setRect(x - 5, y - 5, 10, 10)
            else:
                item.setRect(x - 4, y - 4, 8, 8)

        for (v1, v2, item) in self.edge_items:
            uv1 = self.uv[v1]
            uv2 = self.uv[v2]
            x1 = uv1[0] * tex_w
            y1 = (1 - uv1[1]) * tex_h
            x2 = uv2[0] * tex_w
            y2 = (1 - uv2[1]) * tex_h
            item.setLine(x1, y1, x2, y2)

        for i, face in enumerate(self.faces):
            face_uv = self.uv[face]
            points = []
            for uv in face_uv:
                x = uv[0] * tex_w
                y = (1 - uv[1]) * tex_h
                points.append(QPointF(x, y))
            polygon = QPolygonF(points)
            self.face_items[i].setPolygon(polygon)

    def clear_selection(self):
        self.selected_vertices.clear()
        self.highlighted_vertices.clear()
        self.update_vertex_colors()

    def select_all(self):
        self.selected_vertices.clear()
        for i, item in enumerate(self.uv_items):
            self.selected_vertices.add(i)
        self.update_vertex_colors()
        self.vertices_selected.emit(self.selected_vertices)

    def get_uv(self):
        return self.uv.copy()

    def transform_uv(self, matrix):
        if self.uv is None or len(self.selected_vertices) == 0:
            return

        for v_idx in self.selected_vertices:
            uv = self.uv[v_idx]
            uv_h = np.append(uv, 1)
            transformed = matrix @ uv_h
            self.uv[v_idx] = transformed[:2] / transformed[2]

        self.update_uv_positions()

    def scale_uv(self, sx, sy):
        if len(self.selected_vertices) == 0:
            return

        indices = list(self.selected_vertices)
        selected_uvs = self.uv[indices]
        center = np.mean(selected_uvs, axis=0)

        for v_idx in indices:
            self.uv[v_idx] = center + (self.uv[v_idx] - center) * np.array([sx, sy])

        self.update_uv_positions()

    def rotate_uv(self, angle_deg):
        if len(self.selected_vertices) == 0:
            return

        angle_rad = np.radians(angle_deg)
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        rot_matrix = np.array([[cos_a, -sin_a], [sin_a, cos_a]])

        indices = list(self.selected_vertices)
        selected_uvs = self.uv[indices]
        center = np.mean(selected_uvs, axis=0)

        for v_idx in indices:
            offset = self.uv[v_idx] - center
            self.uv[v_idx] = center + rot_matrix @ offset

        self.update_uv_positions()

    def flip_uv(self, horizontal=True, vertical=False):
        if len(self.selected_vertices) == 0:
            return

        indices = list(self.selected_vertices)
        selected_uvs = self.uv[indices]
        center = np.mean(selected_uvs, axis=0)

        for v_idx in indices:
            if horizontal:
                self.uv[v_idx, 0] = 2 * center[0] - self.uv[v_idx, 0]
            if vertical:
                self.uv[v_idx, 1] = 2 * center[1] - self.uv[v_idx, 1]

        self.update_uv_positions()

    def pack_uv(self, padding=0.01):
        if self.uv is None:
            return

        min_uv = np.min(self.uv, axis=0)
        max_uv = np.max(self.uv, axis=0)
        range_uv = max_uv - min_uv
        range_uv[range_uv == 0] = 1

        self.uv = (self.uv - min_uv) / range_uv
        self.uv = self.uv * (1 - 2 * padding) + padding

        self.update_view()
