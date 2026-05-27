import os
import io
import json
import uuid
import numpy as np
from typing import List, Optional, Tuple, Dict
from pathlib import Path
from datetime import datetime
from PIL import Image
import cv2
import xml.etree.ElementTree as ET
from xml.dom import minidom

from schemas import ImageInfo, Annotation


class ImageService:
    _instance = None
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        self.images_meta: dict = {}
        self.label_map: Dict[str, int] = {}
        self.next_label_id = 0
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def save_image(self, file_content: bytes, filename: str) -> ImageInfo:
        image_id = str(uuid.uuid4())
        
        ext = Path(filename).suffix.lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff']:
            ext = '.png'
        
        saved_filename = f"{image_id}{ext}"
        filepath = self.upload_dir / saved_filename
        
        with open(filepath, 'wb') as f:
            f.write(file_content)
        
        img = Image.open(io.BytesIO(file_content))
        width, height = img.size
        
        image_info = ImageInfo(
            id=image_id,
            filename=filename,
            width=width,
            height=height,
            uploadedAt=int(datetime.now().timestamp() * 1000)
        )
        
        self.images_meta[image_id] = {
            'filepath': str(filepath),
            'info': image_info
        }
        
        return image_info
    
    def get_image_info(self, image_id: str) -> Optional[ImageInfo]:
        if image_id in self.images_meta:
            return self.images_meta[image_id]['info']
        return None
    
    def list_images(self) -> List[ImageInfo]:
        return [meta['info'] for meta in self.images_meta.values()]
    
    def get_image_path(self, image_id: str) -> Optional[str]:
        if image_id in self.images_meta:
            return self.images_meta[image_id]['filepath']
        return None
    
    def get_image_array(self, image_id: str) -> Optional[np.ndarray]:
        filepath = self.get_image_path(image_id)
        if not filepath or not os.path.exists(filepath):
            return None
        
        img = cv2.imread(filepath)
        if img is None:
            return None
        
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    def delete_image(self, image_id: str) -> bool:
        if image_id not in self.images_meta:
            return False
        
        filepath = self.images_meta[image_id]['filepath']
        if os.path.exists(filepath):
            os.remove(filepath)
        
        del self.images_meta[image_id]
        return True
    
    def get_or_create_label_id(self, label_name: str) -> int:
        if label_name not in self.label_map:
            self.label_map[label_name] = self.next_label_id
            self.next_label_id += 1
        return self.label_map[label_name]
    
    def annotation_to_bbox(self, annotation: dict, width: int, height: int) -> Optional[Tuple[float, float, float, float]]:
        ann_type = annotation.get('type')
        
        if ann_type == 'rectangle':
            x = annotation.get('x', 0)
            y = annotation.get('y', 0)
            w = annotation.get('width', 0)
            h = annotation.get('height', 0)
            return (x, y, x + w, y + h)
        
        elif ann_type == 'polygon':
            points = annotation.get('points', [])
            if len(points) < 3:
                return None
            xs = [p['x'] for p in points]
            ys = [p['y'] for p in points]
            return (min(xs), min(ys), max(xs), max(ys))
        
        elif ann_type == 'point':
            pos = annotation.get('position', {})
            r = annotation.get('radius', 5)
            x = pos.get('x', 0)
            y = pos.get('y', 0)
            return (x - r, y - r, x + r, y + r)
        
        elif ann_type == 'brush':
            points = annotation.get('points', [])
            if len(points) < 2:
                return None
            xs = [p['x'] for p in points]
            ys = [p['y'] for p in points]
            stroke = annotation.get('strokeWidth', 5)
            return (min(xs) - stroke, min(ys) - stroke, max(xs) + stroke, max(ys) + stroke)
        
        elif ann_type == 'sam':
            mask = np.array(annotation.get('mask', []), dtype=np.uint8)
            w = annotation.get('width', width)
            h = annotation.get('height', height)
            if len(mask) == w * h:
                mask = mask.reshape((h, w))
                rows = np.any(mask > 127, axis=1)
                cols = np.any(mask > 127, axis=0)
                if rows.any() and cols.any():
                    y_indices = np.where(rows)[0]
                    x_indices = np.where(cols)[0]
                    return (float(x_indices[0]), float(y_indices[0]), 
                            float(x_indices[-1]), float(y_indices[-1]))
        
        return None
    
    def export_yolo_format(
        self,
        image_id: str,
        annotations: List[dict],
        width: int,
        height: int
    ) -> str:
        lines = []
        
        for ann in annotations:
            label = ann.get('label', 'object')
            label_id = self.get_or_create_label_id(label)
            
            bbox = self.annotation_to_bbox(ann, width, height)
            if bbox is None:
                continue
            
            x1, y1, x2, y2 = bbox
            
            center_x = ((x1 + x2) / 2) / width
            center_y = ((y1 + y2) / 2) / height
            bbox_width = (x2 - x1) / width
            bbox_height = (y2 - y1) / height
            
            center_x = max(0, min(1, center_x))
            center_y = max(0, min(1, center_y))
            bbox_width = max(0, min(1, bbox_width))
            bbox_height = max(0, min(1, bbox_height))
            
            lines.append(f"{label_id} {center_x:.6f} {center_y:.6f} {bbox_width:.6f} {bbox_height:.6f}")
        
        return "\n".join(lines)
    
    def export_labelme_format(
        self,
        image_id: str,
        annotations: List[dict],
        width: int,
        height: int,
        image_filename: str
    ) -> dict:
        shapes = []
        
        for ann in annotations:
            label = ann.get('label', 'object')
            ann_type = ann.get('type')
            shape_type = 'polygon'
            points = []
            
            if ann_type == 'polygon':
                points = [[p['x'], p['y']] for p in ann.get('points', [])]
                shape_type = 'polygon'
            
            elif ann_type == 'rectangle':
                x = ann.get('x', 0)
                y = ann.get('y', 0)
                w = ann.get('width', 0)
                h = ann.get('height', 0)
                points = [[x, y], [x + w, y + h]]
                shape_type = 'rectangle'
            
            elif ann_type == 'point':
                pos = ann.get('position', {})
                points = [[pos.get('x', 0), pos.get('y', 0)]]
                shape_type = 'point'
            
            elif ann_type == 'brush':
                points = [[p['x'], p['y']] for p in ann.get('points', [])]
                shape_type = 'linestrip'
            
            elif ann_type == 'sam':
                mask = np.array(ann.get('mask', []), dtype=np.uint8)
                w = ann.get('width', width)
                h = ann.get('height', height)
                if len(mask) == w * h:
                    mask = mask.reshape((h, w))
                    mask_uint8 = (mask > 127).astype(np.uint8) * 255
                    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        epsilon = 0.005 * cv2.arcLength(contours[0], True)
                        approx = cv2.approxPolyDP(contours[0], epsilon, True)
                        points = [[float(p[0][0]), float(p[0][1])] for p in approx]
                        shape_type = 'polygon'
            
            if points:
                shapes.append({
                    'label': label,
                    'points': points,
                    'group_id': None,
                    'description': '',
                    'shape_type': shape_type,
                    'flags': {}
                })
        
        return {
            'version': '5.0.1',
            'flags': {},
            'shapes': shapes,
            'imagePath': image_filename,
            'imageData': None,
            'imageHeight': height,
            'imageWidth': width
        }
    
    def export_voc_format(
        self,
        image_id: str,
        annotations: List[dict],
        width: int,
        height: int,
        image_filename: str
    ) -> str:
        root = ET.Element('annotation')
        
        folder = ET.SubElement(root, 'folder')
        folder.text = 'images'
        
        filename_elem = ET.SubElement(root, 'filename')
        filename_elem.text = image_filename
        
        path = ET.SubElement(root, 'path')
        path.text = image_filename
        
        source = ET.SubElement(root, 'source')
        database = ET.SubElement(source, 'database')
        database.text = 'Unknown'
        
        size_elem = ET.SubElement(root, 'size')
        w_elem = ET.SubElement(size_elem, 'width')
        w_elem.text = str(width)
        h_elem = ET.SubElement(size_elem, 'height')
        h_elem.text = str(height)
        d_elem = ET.SubElement(size_elem, 'depth')
        d_elem.text = '3'
        
        segmented = ET.SubElement(root, 'segmented')
        segmented.text = '0'
        
        for ann in annotations:
            label = ann.get('label', 'object')
            bbox = self.annotation_to_bbox(ann, width, height)
            
            if bbox is None:
                continue
            
            x1, y1, x2, y2 = bbox
            
            obj = ET.SubElement(root, 'object')
            name = ET.SubElement(obj, 'name')
            name.text = label
            
            pose = ET.SubElement(obj, 'pose')
            pose.text = 'Unspecified'
            
            truncated = ET.SubElement(obj, 'truncated')
            truncated.text = '0'
            
            difficult = ET.SubElement(obj, 'difficult')
            difficult.text = '0'
            
            bndbox = ET.SubElement(obj, 'bndbox')
            xmin = ET.SubElement(bndbox, 'xmin')
            xmin.text = str(int(max(0, x1)))
            ymin = ET.SubElement(bndbox, 'ymin')
            ymin.text = str(int(max(0, y1)))
            xmax = ET.SubElement(bndbox, 'xmax')
            xmax.text = str(int(min(width, x2)))
            ymax = ET.SubElement(bndbox, 'ymax')
            ymax.text = str(int(min(height, y2)))
        
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent='\t')
        return xml_str
    
    def export_coco_format(
        self,
        image_id: str,
        annotations: List[dict],
        width: int,
        height: int,
        image_filename: str
    ) -> dict:
        coco_annotations = []
        coco_categories = []
        category_map = {}
        
        for ann in annotations:
            label = ann.get('label', 'object')
            if label not in category_map:
                cat_id = len(category_map) + 1
                category_map[label] = cat_id
                coco_categories.append({
                    'id': cat_id,
                    'name': label,
                    'supercategory': 'object'
                })
            
            bbox = self.annotation_to_bbox(ann, width, height)
            if bbox is None:
                continue
            
            x1, y1, x2, y2 = bbox
            bbox_width = x2 - x1
            bbox_height = y2 - y1
            
            ann_id = len(coco_annotations) + 1
            coco_annotations.append({
                'id': ann_id,
                'image_id': 1,
                'category_id': category_map[label],
                'bbox': [float(x1), float(y1), float(bbox_width), float(bbox_height)],
                'area': float(bbox_width * bbox_height),
                'iscrowd': 0,
                'segmentation': []
            })
        
        return {
            'info': {
                'description': 'Exported from Image Segmentation Annotation Tool',
                'version': '1.0',
                'date_created': datetime.now().isoformat()
            },
            'licenses': [],
            'images': [{
                'id': 1,
                'file_name': image_filename,
                'width': width,
                'height': height
            }],
            'annotations': coco_annotations,
            'categories': coco_categories
        }
    
    def calculate_polygon_area(self, points: List[dict], width: int, height: int) -> int:
        if len(points) < 3:
            return 0
        
        np_points = np.array([(p['x'], p['y']) for p in points], dtype=np.int32)
        
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask, [np_points], 255)
        
        return int(np.sum(mask > 0))
    
    def calculate_sam_area(self, mask: List[int]) -> int:
        return sum(1 for m in mask if m > 127)
    
    def generate_annotation_mask(
        self,
        annotations: List[dict],
        width: int,
        height: int
    ) -> np.ndarray:
        mask = np.zeros((height, width), dtype=np.uint8)
        
        for idx, ann in enumerate(annotations, start=1):
            ann_mask = self.annotation_to_mask(ann, width, height)
            mask[ann_mask > 0] = idx
        
        return mask
    
    def annotation_to_mask(
        self,
        annotation: dict,
        width: int,
        height: int
    ) -> np.ndarray:
        mask = np.zeros((height, width), dtype=np.uint8)
        ann_type = annotation.get('type')
        
        if ann_type == 'polygon':
            points = np.array(
                [(p['x'], p['y']) for p in annotation.get('points', [])],
                dtype=np.int32
            )
            if len(points) >= 3:
                cv2.fillPoly(mask, [points], 255)
        
        elif ann_type == 'rectangle':
            x = int(annotation.get('x', 0))
            y = int(annotation.get('y', 0))
            w = int(annotation.get('width', 0))
            h = int(annotation.get('height', 0))
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)
        
        elif ann_type == 'point':
            pos = annotation.get('position', {})
            cx = int(pos.get('x', 0))
            cy = int(pos.get('y', 0))
            r = int(annotation.get('radius', 5))
            cv2.circle(mask, (cx, cy), r, 255, -1)
        
        elif ann_type == 'brush':
            points = np.array(
                [(p['x'], p['y']) for p in annotation.get('points', [])],
                dtype=np.int32
            )
            stroke = int(annotation.get('strokeWidth', 5))
            if len(points) >= 2:
                cv2.polylines(mask, [points], False, 255, stroke)
        
        elif ann_type == 'sam':
            sam_mask = np.array(annotation.get('mask', []), dtype=np.uint8)
            w = annotation.get('width', width)
            h = annotation.get('height', height)
            if len(sam_mask) == w * h:
                sam_mask = sam_mask.reshape((h, w))
                mask[:h, :w] = np.where(sam_mask > 127, 255, 0)
        
        return mask
    
    def export_mask_to_png(
        self,
        annotations: List[dict],
        width: int,
        height: int
    ) -> bytes:
        mask = self.generate_annotation_mask(annotations, width, height)
        
        colored_mask = np.zeros((height, width, 3), dtype=np.uint8)
        
        colors = [
            [239, 68, 68], [249, 115, 22], [234, 179, 8], [34, 197, 94],
            [6, 182, 212], [59, 130, 246], [139, 92, 246], [236, 72, 153]
        ]
        
        for idx in range(1, len(annotations) + 1):
            color = colors[(idx - 1) % len(colors)]
            colored_mask[mask == idx] = color
        
        img = Image.fromarray(colored_mask)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    
    def export_annotations_to_json(
        self,
        image_id: str,
        annotations: List[dict]
    ) -> dict:
        image_info = self.get_image_info(image_id)
        
        return {
            "version": "1.0",
            "image": image_info.model_dump() if image_info else {"id": image_id},
            "annotations": annotations,
            "exportedAt": int(datetime.now().timestamp() * 1000)
        }
    
    def export_label_map(self) -> str:
        lines = []
        for label, label_id in sorted(self.label_map.items(), key=lambda x: x[1]):
            lines.append(f"{label_id} {label}")
        return "\n".join(lines)


image_service = ImageService.get_instance()
