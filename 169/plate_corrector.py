import cv2
import numpy as np
from scipy import ndimage
from scipy.spatial import distance as dist


class PlateCorrector:
    def __init__(self, target_width=440, target_height=140):
        self.target_width = target_width
        self.target_height = target_height
        self.max_angle = 70

    def correct(self, image, plate_info):
        if image is None or plate_info is None:
            return None
        
        plate_image = plate_info.get('plate_image')
        if plate_image is None or plate_image.size == 0:
            return None
        
        rect = plate_info.get('rect')
        rotated_box = plate_info.get('rotated_box')
        
        corrected = None
        
        if rotated_box is not None and len(rotated_box) == 4:
            corrected = self._perspective_transform_from_box(image, rotated_box)
        
        if corrected is None and rect is not None:
            corrected = self._affine_transform_large_angle(image, rect)
        
        if corrected is None:
            corrected = self._hybrid_correction(plate_image)
        
        if corrected is not None:
            corrected = self._orientation_correction(corrected)
            corrected = self._fine_tune(corrected)
        
        return corrected

    def _perspective_transform_from_box(self, image, box):
        try:
            box = np.array(box, dtype=np.float32)
            
            if len(box) != 4:
                return None
            
            ordered_box = self._order_points(box)
            
            width_top = dist.euclidean(ordered_box[0], ordered_box[1])
            width_bottom = dist.euclidean(ordered_box[3], ordered_box[2])
            max_width = max(int(width_top), int(width_bottom))
            
            height_left = dist.euclidean(ordered_box[0], ordered_box[3])
            height_right = dist.euclidean(ordered_box[1], ordered_box[2])
            max_height = max(int(height_left), int(height_right))
            
            if max_width < 10 or max_height < 10:
                return None
            
            aspect_ratio = max_width / max_height if max_height > 0 else 1
            
            if aspect_ratio < 1:
                max_width, max_height = max_height, max_width
                ordered_box = np.roll(ordered_box, 1, axis=0)
            
            dst_points = np.array([
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1]
            ], dtype=np.float32)
            
            M = cv2.getPerspectiveTransform(ordered_box, dst_points)
            warped = cv2.warpPerspective(
                image,
                M,
                (max_width, max_height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            
            resized = cv2.resize(
                warped,
                (self.target_width, self.target_height),
                interpolation=cv2.INTER_CUBIC
            )
            
            return resized
            
        except Exception as e:
            print(f"Perspective transform error: {e}")
            return None

    def _affine_transform_large_angle(self, image, rect):
        try:
            (center_x, center_y), (width, height), angle = rect
            
            if width < height:
                width, height = height, width
                angle += 90
            
            angle = self._normalize_angle(angle)
            
            if abs(angle) > self.max_angle:
                return self._extreme_angle_correction(image, rect)
            
            rotation_matrix = cv2.getRotationMatrix2D((center_x, center_y), angle, 1.0)
            
            abs_cos = abs(rotation_matrix[0, 0])
            abs_sin = abs(rotation_matrix[0, 1])
            
            new_width = int(height * abs_sin + width * abs_cos)
            new_height = int(height * abs_cos + width * abs_sin)
            
            rotation_matrix[0, 2] += new_width / 2 - center_x
            rotation_matrix[1, 2] += new_height / 2 - center_y
            
            rotated = cv2.warpAffine(
                image,
                rotation_matrix,
                (new_width, new_height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            
            x1 = int(new_width / 2 - width / 2)
            y1 = int(new_height / 2 - height / 2)
            x2 = int(new_width / 2 + width / 2)
            y2 = int(new_height / 2 + height / 2)
            
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(new_width, x2), min(new_height, y2)
            
            cropped = rotated[y1:y2, x1:x2]
            
            if cropped.size == 0:
                return None
            
            resized = cv2.resize(
                cropped,
                (self.target_width, self.target_height),
                interpolation=cv2.INTER_CUBIC
            )
            
            return resized
            
        except Exception as e:
            print(f"Affine transform error: {e}")
            return None

    def _normalize_angle(self, angle):
        while angle > 90:
            angle -= 180
        while angle < -90:
            angle += 180
        
        if angle > 45:
            angle -= 90
        elif angle < -45:
            angle += 90
        
        return angle

    def _extreme_angle_correction(self, image, rect):
        try:
            (center_x, center_y), (width, height), angle = rect
            
            if abs(angle) > 135:
                angle = angle - 180 if angle > 0 else angle + 180
            
            if width < height:
                width, height = height, width
            
            plate_region = self._extract_plate_region(image, rect)
            
            if plate_region is None or plate_region.size == 0:
                return None
            
            gray = cv2.cvtColor(plate_region, cv2.COLOR_BGR2GRAY)
            
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=30,
                minLineLength=20,
                maxLineGap=10
            )
            
            if lines is not None and len(lines) > 0:
                angles = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    line_angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                    if abs(line_angle) < 80:
                        angles.append(line_angle)
                
                if len(angles) > 0:
                    median_angle = np.median(angles)
                    rotated = ndimage.rotate(plate_region, median_angle, reshape=True)
                    
                    resized = cv2.resize(
                        rotated,
                        (self.target_width, self.target_height),
                        interpolation=cv2.INTER_CUBIC
                    )
                    return resized
            
            resized = cv2.resize(
                plate_region,
                (self.target_width, self.target_height),
                interpolation=cv2.INTER_CUBIC
            )
            return resized
            
        except Exception as e:
            print(f"Extreme angle correction error: {e}")
            return None

    def _extract_plate_region(self, image, rect):
        try:
            (center_x, center_y), (width, height), angle = rect
            
            if width < height:
                width, height = height, width
            
            x1 = int(center_x - width / 2)
            y1 = int(center_y - height / 2)
            x2 = int(center_x + width / 2)
            y2 = int(center_y + height / 2)
            
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
            
            if x2 <= x1 or y2 <= y1:
                return None
            
            return image[y1:y2, x1:x2]
            
        except Exception as e:
            print(f"Extract plate region error: {e}")
            return None

    def _hybrid_correction(self, plate_image):
        try:
            gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
            
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            contours, _ = cv2.findContours(
                thresh,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                epsilon = 0.02 * cv2.arcLength(largest_contour, True)
                approx = cv2.approxPolyDP(largest_contour, epsilon, True)
                
                if len(approx) == 4:
                    points = approx.reshape(4, 2).astype(np.float32)
                    return self.correct_perspective(plate_image, points)
            
            return self._correct_without_rotation(plate_image)
            
        except Exception as e:
            print(f"Hybrid correction error: {e}")
            return self._correct_without_rotation(plate_image)

    def _correct_without_rotation(self, plate_image):
        try:
            gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
            
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=50)
            
            if lines is not None and len(lines) > 0:
                angles = []
                for line in lines:
                    rho, theta = line[0]
                    angle = (theta * 180 / np.pi) - 90
                    
                    if abs(angle) < 80:
                        angles.append(angle)
                
                if len(angles) > 0:
                    median_angle = np.median(angles)
                    rotated = ndimage.rotate(plate_image, median_angle, reshape=True)
                    
                    resized = cv2.resize(
                        rotated,
                        (self.target_width, self.target_height),
                        interpolation=cv2.INTER_CUBIC
                    )
                    return resized
            
            resized = cv2.resize(
                plate_image,
                (self.target_width, self.target_height),
                interpolation=cv2.INTER_CUBIC
            )
            return resized
            
        except Exception as e:
            print(f"Correct without rotation error: {e}")
            return plate_image

    def _orientation_correction(self, image):
        try:
            if image is None or image.size == 0:
                return image
            
            h, w = image.shape[:2]
            
            rotations = [0, 180, 90, 270]
            scores = []
            
            for angle in rotations:
                if angle == 0:
                    rotated = image.copy()
                elif angle == 180:
                    rotated = cv2.rotate(image, cv2.ROTATE_180)
                elif angle == 90:
                    rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
                elif angle == 270:
                    rotated = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                
                score = self._evaluate_orientation(rotated)
                scores.append((angle, score, rotated))
            
            scores.sort(key=lambda x: x[1], reverse=True)
            
            best_angle, best_score, best_image = scores[0]
            
            if best_angle != 0 and best_score > 0.3:
                return cv2.resize(
                    best_image,
                    (self.target_width, self.target_height),
                    interpolation=cv2.INTER_CUBIC
                )
            
            return image
            
        except Exception as e:
            print(f"Orientation correction error: {e}")
            return image

    def _evaluate_orientation(self, image):
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            edge_magnitude = np.sqrt(sobelx**2 + sobely**2)
            horizontal_edges = np.sum(np.abs(sobelx) > 50)
            vertical_edges = np.sum(np.abs(sobely) > 50)
            
            total_edges = horizontal_edges + vertical_edges
            if total_edges == 0:
                return 0
            
            ratio = vertical_edges / total_edges if total_edges > 0 else 0
            
            h, w = gray.shape
            aspect_ratio_score = 1 - abs(w / h - 3.14) / 3.14 if h > 0 else 0
            
            combined_score = 0.6 * ratio + 0.4 * max(0, aspect_ratio_score)
            
            return max(0, min(1, combined_score))
            
        except Exception as e:
            print(f"Evaluate orientation error: {e}")
            return 0

    def _fine_tune(self, image):
        if image is None or image.size == 0:
            return image
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            _, thresh = cv2.threshold(
                gray,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            
            coords = cv2.findNonZero(thresh)
            if coords is not None:
                x, y, w, h = cv2.boundingRect(coords)
                
                h_margin = int(h * 0.05)
                w_margin = int(w * 0.02)
                
                x1 = max(0, x - w_margin)
                y1 = max(0, y - h_margin)
                x2 = min(image.shape[1], x + w + w_margin)
                y2 = min(image.shape[0], y + h + h_margin)
                
                cropped = image[y1:y2, x1:x2]
                
                if cropped.size > 0:
                    resized = cv2.resize(
                        cropped,
                        (self.target_width, self.target_height),
                        interpolation=cv2.INTER_CUBIC
                    )
                    return resized
        except Exception as e:
            print(f"Fine tune error: {e}")
        
        return image

    def correct_perspective(self, image, points):
        if len(points) != 4:
            return None
        
        try:
            points = np.array(points, dtype=np.float32)
            points = self._order_points(points)
            
            dst_points = np.array([
                [0, 0],
                [self.target_width - 1, 0],
                [self.target_width - 1, self.target_height - 1],
                [0, self.target_height - 1]
            ], dtype=np.float32)
            
            M = cv2.getPerspectiveTransform(points, dst_points)
            corrected = cv2.warpPerspective(
                image,
                M,
                (self.target_width, self.target_height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            
            return corrected
            
        except Exception as e:
            print(f"Correct perspective error: {e}")
            return None

    def _order_points(self, points):
        rect = np.zeros((4, 2), dtype=np.float32)
        
        s = points.sum(axis=1)
        rect[0] = points[np.argmin(s)]
        rect[2] = points[np.argmax(s)]
        
        diff = np.diff(points, axis=1)
        rect[1] = points[np.argmin(diff)]
        rect[3] = points[np.argmax(diff)]
        
        return rect

    def deskew(self, image):
        if image is None or image.size == 0:
            return image
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            gray = cv2.bitwise_not(gray)
            
            thresh = cv2.threshold(
                gray,
                0,
                255,
                cv2.THRESH_BINARY | cv2.THRESH_OTSU
            )[1]
            
            coords = np.column_stack(np.where(thresh > 0))
            
            if len(coords) < 10:
                return image
            
            angle = cv2.minAreaRect(coords)[-1]
            
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image,
                M,
                (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            
            return rotated
            
        except Exception as e:
            print(f"Deskew error: {e}")
            return image
