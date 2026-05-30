import cv2
import numpy as np
from scipy import ndimage
from scipy.interpolate import splprep, splev
from scipy.ndimage import label, sum as ndi_sum
from sklearn.cluster import KMeans
import svgwrite
import warnings
warnings.filterwarnings('ignore')


class RasterToVector:
    def __init__(self, image_path):
        self.image_path = image_path
        self.original_image = None
        self.preprocessed_image = None
        self.edges = None
        self.contours = None
        self.svg_path = None
        
    def load_image(self):
        self.original_image = cv2.imread(self.image_path, cv2.IMREAD_COLOR)
        if self.original_image is None:
            raise ValueError(f"无法加载图像: {self.image_path}")
        self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        return self.original_image
    
    def denoise(self, image, method='bilateral', kernel_size=5, min_area=20):
        if method == 'bilateral':
            denoised = cv2.bilateralFilter(image, kernel_size, 75, 75)
        elif method == 'gaussian':
            denoised = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
        elif method == 'median':
            denoised = cv2.medianBlur(image, kernel_size)
        elif method == 'nl_means':
            denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        elif method == 'area_filter':
            return self.area_filter_denoise(image, min_area=min_area)
        else:
            denoised = image
        
        if min_area > 0 and method != 'area_filter':
            denoised = self.area_filter_denoise(denoised, min_area=min_area)
        
        return denoised
    
    def area_filter_denoise(self, image, min_area=20):
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        dilated = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
        
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            255 - dilated, connectivity=8
        )
        
        mask = np.zeros_like(gray, dtype=np.uint8)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= min_area:
                mask[labels == i] = 255
        
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        mask = mask.astype(np.float32) / 255.0
        mask_3d = np.stack([mask, mask, mask], axis=2)
        
        result = image.astype(np.float32) * mask_3d
        result = result.astype(np.uint8)
        
        return result
    
    def color_quantization(self, image, n_colors=8, edge_aware=True, smooth_sigma=1.5):
        if not edge_aware:
            pixels = image.reshape(-1, 3)
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)
            labels = kmeans.predict(pixels)
            quantized = kmeans.cluster_centers_[labels].astype(np.uint8)
            return quantized.reshape(image.shape)
        
        return self.edge_aware_color_quantization(image, n_colors, smooth_sigma)
    
    def edge_aware_color_quantization(self, image, n_colors=8, smooth_sigma=1.5):
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_strength = cv2.GaussianBlur(edges.astype(np.float32), (0, 0), sigmaX=smooth_sigma)
        edge_strength = edge_strength / edge_strength.max() if edge_strength.max() > 0 else edge_strength
        
        h, w = image.shape[:2]
        pixels = image.reshape(-1, 3).astype(np.float32)
        edge_weights = edge_strength.reshape(-1)
        
        coords = np.mgrid[0:h, 0:w].reshape(2, -1).T.astype(np.float32)
        coords_normalized = coords / np.array([h, w]) * 10
        
        features = np.concatenate([pixels / 255.0 * 5, coords_normalized], axis=1)
        
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        labels = kmeans.fit_predict(features)
        
        quantized = np.zeros_like(pixels)
        for i in range(n_colors):
            mask = labels == i
            if mask.sum() > 0:
                cluster_pixels = pixels[mask]
                cluster_edges = edge_weights[mask]
                weights = 1.0 / (1.0 + cluster_edges * 5)
                weights = weights / weights.sum()
                weighted_color = np.average(cluster_pixels, weights=weights, axis=0)
                quantized[mask] = weighted_color
        
        quantized = quantized.reshape(image.shape).astype(np.uint8)
        quantized = self.smooth_boundaries(quantized, edges, smooth_sigma)
        
        return quantized
    
    def smooth_boundaries(self, quantized_image, edges, sigma=1.5):
        blurred = cv2.GaussianBlur(quantized_image, (0, 0), sigmaX=sigma)
        
        edge_mask = edges > 50
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        edge_region = cv2.dilate(edge_mask.astype(np.uint8), kernel) > 0
        
        edge_region_3d = np.stack([edge_region, edge_region, edge_region], axis=2)
        
        result = np.where(edge_region_3d, blurred, quantized_image)
        return result.astype(np.uint8)
    
    def preprocess(self, denoise_method='bilateral', n_colors=8, 
                   denoise_min_area=20, edge_aware_quant=True, smooth_sigma=1.5):
        if self.original_image is None:
            self.load_image()
        
        denoised = self.denoise(self.original_image, method=denoise_method, min_area=denoise_min_area)
        self.preprocessed_image = self.color_quantization(
            denoised, n_colors=n_colors, edge_aware=edge_aware_quant, smooth_sigma=smooth_sigma
        )
        return self.preprocessed_image
    
    def detect_edges(self, method='canny', low_threshold=50, high_threshold=150):
        if self.preprocessed_image is None:
            self.preprocess()
        
        gray = cv2.cvtColor(self.preprocessed_image, cv2.COLOR_RGB2GRAY)
        
        if method == 'canny':
            self.edges = cv2.Canny(gray, low_threshold, high_threshold)
        elif method == 'sobel':
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            self.edges = np.sqrt(sobelx**2 + sobely**2).astype(np.uint8)
        elif method == 'laplacian':
            self.edges = cv2.Laplacian(gray, cv2.CV_64F)
            self.edges = np.absolute(self.edges).astype(np.uint8)
        
        return self.edges
    
    def extract_contours(self, min_area=10):
        if self.edges is None:
            self.detect_edges()
        
        contours, hierarchy = cv2.findContours(
            self.edges, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        self.contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
        return self.contours
    
    def detect_corners(self, contour, epsilon_factor=0.01):
        perimeter = cv2.arcLength(contour, True)
        epsilon = epsilon_factor * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)
        return approx
    
    def fit_curve(self, contour, n_points=100, smooth=100, max_iterations=5, error_threshold=1.0):
        contour = contour.reshape(-1, 2)
        if len(contour) < 4:
            return contour
        
        return self.iterative_curve_fitting(contour, n_points, smooth, max_iterations, error_threshold)
    
    def iterative_curve_fitting(self, contour, n_points=100, initial_smooth=100, max_iterations=5, error_threshold=1.0):
        current_smooth = initial_smooth
        best_fit = None
        best_error = float('inf')
        
        original_points = contour.astype(np.float64)
        
        for iteration in range(max_iterations):
            try:
                tck, u = splprep([original_points[:, 0], original_points[:, 1]], s=current_smooth, per=True)
                
                u_fit = np.linspace(u.min(), u.max(), len(original_points))
                x_fit, y_fit = splev(u_fit, tck)
                fitted_points = np.column_stack((x_fit, y_fit))
                
                error = self.calculate_fitting_error(original_points, fitted_points)
                
                if error < best_error:
                    best_error = error
                    best_fit = tck
                
                if error <= error_threshold:
                    break
                
                if error > best_error * 1.2:
                    current_smooth *= 0.5
                else:
                    current_smooth *= 0.8
                
            except Exception as e:
                break
        
        if best_fit is not None:
            try:
                u_new = np.linspace(0, 1, n_points)
                x_new, y_new = splev(u_new, best_fit)
                result = np.column_stack((x_new, y_new))
                
                result = self.correct_fitting_bias(original_points, result)
                
                return result.astype(np.int32)
            except:
                pass
        
        return contour.astype(np.int32)
    
    def calculate_fitting_error(self, original_points, fitted_points):
        distances = []
        for orig_point in original_points:
            dists = np.linalg.norm(fitted_points - orig_point, axis=1)
            distances.append(np.min(dists))
        return np.mean(distances)
    
    def correct_fitting_bias(self, original_points, fitted_curve):
        original_centroid = np.mean(original_points, axis=0)
        fitted_centroid = np.mean(fitted_curve, axis=0)
        
        translation = original_centroid - fitted_centroid
        corrected_curve = fitted_curve + translation
        
        original_scale = np.mean(np.linalg.norm(original_points - original_centroid, axis=1))
        fitted_scale = np.mean(np.linalg.norm(corrected_curve - original_centroid, axis=1))
        
        if fitted_scale > 0:
            scale_factor = original_scale / fitted_scale
            corrected_curve = original_centroid + (corrected_curve - original_centroid) * scale_factor
        
        return corrected_curve
    
    def simplify_contour(self, contour, tolerance=2.0):
        contour = contour.reshape(-1, 2)
        if len(contour) < 3:
            return contour
        
        simplified = [contour[0]]
        for point in contour[1:]:
            prev = simplified[-1]
            dist = np.linalg.norm(point - prev)
            if dist > tolerance:
                simplified.append(point)
        
        return np.array(simplified, dtype=np.int32)
    
    def get_contour_colors(self, contour):
        mask = np.zeros(self.original_image.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask, [contour], 0, 255, -1)
        
        masked_region = cv2.bitwise_and(self.preprocessed_image, self.preprocessed_image, mask=mask)
        pixels = masked_region[mask == 255]
        
        if len(pixels) == 0:
            return (128, 128, 128)
        
        mean_color = np.mean(pixels, axis=0).astype(int)
        return tuple(mean_color)
    
    def generate_svg(self, output_path, use_curve_fitting=True, stroke_width=1,
                     curve_max_iter=5, curve_error_threshold=1.0):
        if self.contours is None:
            self.extract_contours()
        
        height, width = self.original_image.shape[:2]
        dwg = svgwrite.Drawing(output_path, size=(width, height), profile='tiny')
        
        bg_color = np.median(self.preprocessed_image.reshape(-1, 3), axis=0).astype(int)
        dwg.add(dwg.rect(insert=(0, 0), size=(width, height), 
                         fill=f'rgb({bg_color[0]},{bg_color[1]},{bg_color[2]})'))
        
        for contour in self.contours:
            color = self.get_contour_colors(contour)
            
            if use_curve_fitting:
                try:
                    fitted = self.fit_curve(
                        contour, 
                        max_iterations=curve_max_iter,
                        error_threshold=curve_error_threshold
                    )
                    points = fitted.reshape(-1, 2)
                except:
                    approx = self.detect_corners(contour)
                    points = approx.reshape(-1, 2)
            else:
                approx = self.detect_corners(contour)
                points = approx.reshape(-1, 2)
            
            if len(points) >= 3:
                path_data = f"M {points[0][0]},{points[0][1]} "
                for i in range(1, len(points)):
                    path_data += f"L {points[i][0]},{points[i][1]} "
                path_data += "Z"
                
                dwg.add(dwg.path(d=path_data, 
                               fill=f'rgb({color[0]},{color[1]},{color[2]})',
                               stroke=f'rgb({color[0]},{color[1]},{color[2]})',
                               stroke_width=stroke_width))
        
        dwg.save()
        self.svg_path = output_path
        return output_path
    
    def convert(self, output_svg_path, 
                denoise_method='bilateral', 
                n_colors=8,
                edge_method='canny',
                low_threshold=50,
                high_threshold=150,
                min_contour_area=10,
                use_curve_fitting=True,
                stroke_width=1,
                denoise_min_area=20,
                edge_aware_quant=True,
                smooth_sigma=1.5,
                curve_max_iter=5,
                curve_error_threshold=1.0):
        
        self.load_image()
        self.preprocess(
            denoise_method=denoise_method, 
            n_colors=n_colors,
            denoise_min_area=denoise_min_area,
            edge_aware_quant=edge_aware_quant,
            smooth_sigma=smooth_sigma
        )
        self.detect_edges(method=edge_method, low_threshold=low_threshold, high_threshold=high_threshold)
        self.extract_contours(min_area=min_contour_area)
        self.generate_svg(
            output_svg_path, 
            use_curve_fitting=use_curve_fitting, 
            stroke_width=stroke_width,
            curve_max_iter=curve_max_iter,
            curve_error_threshold=curve_error_threshold
        )
        
        return self.svg_path
    
    def get_preview(self, scale=0.5):
        if self.edges is None:
            return None
        
        preview = cv2.cvtColor(self.edges, cv2.COLOR_GRAY2BGR)
        preview = cv2.drawContours(preview, self.contours, -1, (0, 255, 0), 2)
        preview = cv2.resize(preview, None, fx=scale, fy=scale)
        return preview
