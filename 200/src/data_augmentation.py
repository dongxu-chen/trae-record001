import cv2
import numpy as np
import albumentations as A
from typing import Tuple, Optional, Dict, Any
from functools import wraps


class XRayDataAugmentor:
    def __init__(self, image_size: Tuple[int, int] = (640, 640), use_gaussian_noise: bool = True,
                 use_geometric: bool = True, use_photometric: bool = True):
        self.image_size = image_size
        self.use_gaussian_noise = use_gaussian_noise
        self.use_geometric = use_geometric
        self.use_photometric = use_photometric
        self.transform = self._build_transform()

    def _build_transform(self) -> A.Compose:
        transforms = []

        if self.use_geometric:
            transforms.extend([
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(p=0.5),
                A.RandomRotate90(p=0.5),
                A.ShiftScaleRotate(
                    shift_limit=0.0625,
                    scale_limit=0.2,
                    rotate_limit=15,
                    interpolation=cv2.INTER_LINEAR,
                    border_mode=cv2.BORDER_CONSTANT,
                    value=0,
                    p=0.5
                ),
                A.Perspective(
                    scale=(0.05, 0.1),
                    p=0.3
                )
            ])

        if self.use_photometric:
            transforms.extend([
                A.RandomBrightnessContrast(
                    brightness_limit=0.2,
                    contrast_limit=0.2,
                    p=0.5
                ),
                A.GaussNoise(
                    var_limit=(10.0, 50.0),
                    p=0.3
                ),
                A.MotionBlur(
                    blur_limit=3,
                    p=0.2
                ),
                A.MedianBlur(
                    blur_limit=3,
                    p=0.2
                )
            ])

        if self.use_gaussian_noise:
            transforms.append(
                A.GaussianBlur(
                    blur_limit=(3, 5),
                    p=0.3
                )
            )

        transforms.append(
            A.Resize(
                height=self.image_size[0],
                width=self.image_size[1],
                always_apply=True
            )
        )

        return A.Compose(
            transforms=transforms,
            bbox_params=A.BboxParams(
                format='yolo',
                label_fields=['class_labels'],
                min_visibility=0.3
            )
        )

    def __call__(self, image: np.ndarray, bboxes: Optional[np.ndarray] = None,
                 class_labels: Optional[list] = None) -> Dict[str, Any]:
        if bboxes is not None and class_labels is not None:
            bboxes_list = bboxes.tolist() if isinstance(bboxes, np.ndarray) else bboxes
            transformed = self.transform(
                image=image,
                bboxes=bboxes_list,
                class_labels=class_labels
            )
            return {
                'image': transformed['image'],
                'bboxes': np.array(transformed['bboxes'], dtype=np.float32),
                'class_labels': transformed['class_labels']
            }
        else:
            transformed = self.transform(image=image)
            return {
                'image': transformed['image'],
                'bboxes': None,
                'class_labels': None
            }

    def augment_batch(self, images: list, bboxes_list: list, class_labels_list: list) -> list:
        results = []
        for img, bboxes, labels in zip(images, bboxes_list, class_labels_list):
            result = self(img, bboxes, labels)
            results.append(result)
        return results


class CutMix:
    def __init__(self, image_size: Tuple[int, int] = (640, 640), p: float = 0.5):
        self.image_size = image_size
        self.p = p

    def __call__(self, images: list, bboxes_list: list, class_labels_list: list) -> Dict[str, Any]:
        if len(images) < 4 or np.random.random() > self.p:
            return {
                'image': images[0],
                'bboxes': bboxes_list[0],
                'class_labels': class_labels_list[0]
            }

        h, w = self.image_size
        result_image = np.zeros((h, w, 3), dtype=np.uint8)
        if len(images[0].shape) == 2:
            result_image = np.zeros((h, w), dtype=np.uint8)

        cut_h = int(h * np.random.uniform(0.3, 0.7))
        cut_w = int(w * np.random.uniform(0.3, 0.7))

        cy = np.random.randint(cut_h // 2, h - cut_h // 2)
        cx = np.random.randint(cut_w // 2, w - cut_w // 2)

        bboxes_result = []
        labels_result = []

        for i in range(4):
            x1, y1, x2, y2 = self._get_corner(i, w, h, cx, cy, cut_w, cut_h)
            
            img = cv2.resize(images[i], (w, h)) if images[i].shape[:2] != (h, w) else images[i]
            if len(img.shape) == 2 and len(result_image.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            elif len(img.shape) == 3 and len(result_image.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            result_image[y1:y2, x1:x2] = img[y1:y2, x1:x2]

            if bboxes_list[i] is not None:
                scaled_bboxes = self._adjust_bboxes(
                    bboxes_list[i], class_labels_list[i],
                    x1, y1, x2, y2, w, h
                )
                bboxes_result.extend(scaled_bboxes['bboxes'])
                labels_result.extend(scaled_bboxes['labels'])

        return {
            'image': result_image,
            'bboxes': np.array(bboxes_result, dtype=np.float32) if bboxes_result else np.array([]),
            'class_labels': labels_result
        }

    def _get_corner(self, idx: int, w: int, h: int, cx: int, cy: int, cut_w: int, cut_h: int) -> Tuple[int, int, int, int]:
        if idx == 0:
            return 0, 0, cx, cy
        elif idx == 1:
            return cx, 0, w, cy
        elif idx == 2:
            return 0, cy, cx, h
        else:
            return cx, cy, w, h

    def _adjust_bboxes(self, bboxes: np.ndarray, labels: list, x1: int, y1: int, x2: int, y2: int,
                       w: int, h: int) -> Dict[str, list]:
        adjusted_bboxes = []
        adjusted_labels = []

        for bbox, label in zip(bboxes, labels):
            cx_bbox_center_x = bbox[0] * w
            bbox_center_y = bbox[1] * h
            bbox_w = bbox[2] * w
            bbox_h = bbox[3] * h

            bx1 = bbox_center_x - bbox_w / 2
            by1 = bbox_center_y - bbox_h / 2
            bx2 = bbox_center_x + bbox_w / 2
            by2 = bbox_center_y + bbox_h / 2

            ix1 = max(bx1, x1)
            iy1 = max(by1, y1)
            ix2 = min(bx2, x2)
            iy2 = min(by2, y2)

            if ix2 <= ix1 or iy2 <= iy1:
                continue

            inter_w = ix2 - ix1
            inter_h = iy2 - iy1
            inter_area = inter_w * inter_h
            bbox_area = bbox_w * bbox_h

            if inter_area / bbox_area < 0.3:
                continue

            new_cx = (ix1 + ix2) / 2 / w
            new_cy = (iy1 + iy2) / 2 / h
            new_w = inter_w / w
            new_h = inter_h / h

            adjusted_bboxes.append([new_cx, new_cy, new_w, new_h])
            adjusted_labels.append(label)

        return {'bboxes': adjusted_bboxes, 'labels': adjusted_labels}


class Mosaic:
    def __init__(self, image_size: Tuple[int, int] = (640, 640), p: float = 0.5):
        self.image_size = image_size
        self.p = p
        self.cutmix = CutMix(image_size, p)

    def __call__(self, images: list, bboxes_list: list, class_labels_list: list) -> Dict[str, Any]:
        return self.cutmix(images, bboxes_list, class_labels_list)


def augment_with_labels(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        augmentor = args[0] if len(args) > 0 else kwargs.get('augmentor')
        if augmentor and hasattr(augmentor, 'augment_enabled'):
            return augmentor(*args[1:], **kwargs)
        return func(*args, **kwargs)
    return wrapper
