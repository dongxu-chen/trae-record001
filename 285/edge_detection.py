import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor


class EdgeDetection:
    def __init__(self):
        pass

    @staticmethod
    def gaussian_kernel_1d(kernel_size=5, sigma=1.4):
        kernel = np.fromfunction(
            lambda x: (1 / (np.sqrt(2 * np.pi) * sigma)) * 
            np.exp(-((x - (kernel_size - 1) / 2) ** 2) / (2 * sigma ** 2)),
            (kernel_size,)
        )
        return kernel / np.sum(kernel)

    @staticmethod
    def gaussian_blur_separable(image, kernel_size=5, sigma=1.4):
        kernel_1d = EdgeDetection.gaussian_kernel_1d(kernel_size, sigma)
        kernel_1d = kernel_1d.reshape(1, -1).astype(np.float32)
        img_float = image.astype(np.float32)
        blurred_rows = cv2.filter2D(img_float, -1, kernel_1d)
        blurred = cv2.filter2D(blurred_rows, -1, kernel_1d.T)
        return blurred.astype(np.uint8)

    @staticmethod
    def gaussian_blur(image, kernel_size=5, sigma=1.4, use_separable=True):
        if use_separable:
            return EdgeDetection.gaussian_blur_separable(image, kernel_size, sigma)
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)

    @staticmethod
    def median_blur(image, kernel_size=5):
        return cv2.medianBlur(image, kernel_size)

    @staticmethod
    def sobel(image, ksize=3, threshold=100, dx=1, dy=1):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, dx, 0, ksize=ksize)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, dy, ksize=ksize)
        
        magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        magnitude = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        _, edges = cv2.threshold(magnitude, threshold, 255, cv2.THRESH_BINARY)
        return edges

    @staticmethod
    def laplacian(image, ksize=3, threshold=100):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)
        laplacian = cv2.normalize(laplacian, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        _, edges = cv2.threshold(laplacian, threshold, 255, cv2.THRESH_BINARY)
        return edges

    @staticmethod
    def compute_gradients(image, ksize=3):
        sobel_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=ksize)
        sobel_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=ksize)
        magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        direction = np.arctan2(sobel_y, sobel_x) * 180 / np.pi
        direction[direction < 0] += 180
        return magnitude, direction

    @staticmethod
    def non_maximum_suppression_parallel(magnitude, direction, num_workers=4):
        rows, cols = magnitude.shape
        nms = np.zeros_like(magnitude, dtype=np.float64)
        direction = np.round(direction / 45) * 45
        direction = np.where(direction == 180, 0, direction)
        
        def process_block(start_row, end_row):
            block_result = np.zeros((end_row - start_row, cols), dtype=np.float64)
            for i in range(start_row, end_row):
                for j in range(1, cols - 1):
                    if i == 0 or i == rows - 1:
                        continue
                    angle = direction[i, j]
                    if angle == 0:
                        q, r = magnitude[i, j+1], magnitude[i, j-1]
                    elif angle == 45:
                        q, r = magnitude[i+1, j-1], magnitude[i-1, j+1]
                    elif angle == 90:
                        q, r = magnitude[i+1, j], magnitude[i-1, j]
                    elif angle == 135:
                        q, r = magnitude[i-1, j-1], magnitude[i+1, j+1]
                    else:
                        q, r = magnitude[i, j+1], magnitude[i, j-1]
                    
                    if magnitude[i, j] >= q and magnitude[i, j] >= r:
                        block_result[i - start_row, j] = magnitude[i, j]
            return start_row, block_result
        
        block_size = (rows + num_workers - 1) // num_workers
        blocks = [(i * block_size, min((i + 1) * block_size, rows)) for i in range(num_workers)]
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            results = list(executor.map(lambda b: process_block(b[0], b[1]), blocks))
        
        for start_row, block_result in results:
            end_row = min(start_row + block_result.shape[0], rows)
            nms[start_row:end_row, :] = block_result[:end_row-start_row, :]
        
        return nms

    @staticmethod
    def double_threshold_edge_linking(nms, low_threshold, high_threshold):
        strong = 255
        weak = 75
        
        strong_edges = (nms >= high_threshold)
        weak_edges = (nms >= low_threshold) & (nms < high_threshold)
        
        edge_map = np.zeros_like(nms, dtype=np.uint8)
        edge_map[strong_edges] = strong
        edge_map[weak_edges] = weak
        
        rows, cols = edge_map.shape
        visited = np.zeros_like(edge_map, dtype=bool)
        
        def find_neighbors(r, c):
            return [(r+dr, c+dc) for dr in [-1, 0, 1] for dc in [-1, 0, 1]
                    if 0 <= r+dr < rows and 0 <= c+dc < cols and not (dr == 0 and dc == 0)]
        
        for r in range(rows):
            for c in range(cols):
                if edge_map[r, c] == strong and not visited[r, c]:
                    stack = [(r, c)]
                    visited[r, c] = True
                    while stack:
                        cr, cc = stack.pop()
                        for nr, nc in find_neighbors(cr, cc):
                            if edge_map[nr, nc] == weak and not visited[nr, nc]:
                                edge_map[nr, nc] = strong
                                visited[nr, nc] = True
                                stack.append((nr, nc))
        
        edge_map[edge_map == weak] = 0
        return edge_map

    @staticmethod
    def canny_optimized(image, low_threshold=50, high_threshold=150, ksize=3, 
                        gaussian_kernel=5, gaussian_sigma=1.4, num_workers=4):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        blurred = EdgeDetection.gaussian_blur_separable(gray, gaussian_kernel, gaussian_sigma)
        magnitude, direction = EdgeDetection.compute_gradients(blurred, ksize)
        nms = EdgeDetection.non_maximum_suppression_parallel(magnitude, direction, num_workers)
        edges = EdgeDetection.double_threshold_edge_linking(nms, low_threshold, high_threshold)
        
        return edges

    @staticmethod
    def canny(image, low_threshold=50, high_threshold=150, aperture_size=3, l2_gradient=False, use_optimized=True):
        if use_optimized:
            return EdgeDetection.canny_optimized(image, low_threshold, high_threshold, aperture_size)
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        edges = cv2.Canny(gray, low_threshold, high_threshold, apertureSize=aperture_size, L2gradient=l2_gradient)
        return edges

    @staticmethod
    def edge_connect(edges, min_edge_length=10):
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(edges, connectivity=8)
        result = np.zeros_like(edges)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= min_edge_length:
                result[labels == i] = 255
        return result

    def detect_edges(self, image, method='canny', preprocess=None, 
                     sobel_ksize=3, sobel_threshold=100,
                     laplacian_ksize=3, laplacian_threshold=100,
                     canny_low=50, canny_high=150,
                     gaussian_kernel=5, gaussian_sigma=1.4,
                     median_kernel=5,
                     connect_edges=False, min_edge_length=10,
                     use_optimized_canny=True):
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        if preprocess == 'gaussian':
            gray = self.gaussian_blur(gray, gaussian_kernel, gaussian_sigma)
        elif preprocess == 'median':
            gray = self.median_blur(gray, median_kernel)

        if method == 'sobel':
            edges = self.sobel(gray, sobel_ksize, sobel_threshold)
        elif method == 'laplacian':
            edges = self.laplacian(gray, laplacian_ksize, laplacian_threshold)
        elif method == 'canny':
            if use_optimized_canny:
                edges = self.canny_optimized(gray, canny_low, canny_high)
            else:
                edges = self.canny(gray, canny_low, canny_high, use_optimized=False)
        else:
            raise ValueError(f"Unknown method: {method}. Use 'sobel', 'laplacian', or 'canny'")

        if connect_edges:
            edges = self.edge_connect(edges, min_edge_length)

        return edges
