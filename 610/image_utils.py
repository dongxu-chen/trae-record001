import numpy as np
import cv2
from scipy.signal import fftconvolve


class ImageProcessor:
    @staticmethod
    def load_image(filepath, grayscale=True):
        if grayscale:
            img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
        else:
            img = cv2.imread(filepath, cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img.astype(np.float64) / 255.0

    @staticmethod
    def save_image(filepath, image):
        img = (image * 255).astype(np.uint8)
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        cv2.imwrite(filepath, img)

    @staticmethod
    def normalize(image):
        img_min = np.min(image)
        img_max = np.max(image)
        if img_max - img_min < 1e-10:
            return np.zeros_like(image)
        return (image - img_min) / (img_max - img_min)

    @staticmethod
    def adjust_contrast(image, alpha=1.0, beta=0.0):
        return np.clip(alpha * image + beta, 0, 1)

    @staticmethod
    def apply_gaussian_filter(image, sigma=1.0):
        return cv2.GaussianBlur(image, (0, 0), sigma)

    @staticmethod
    def apply_median_filter(image, ksize=3):
        img = (image * 255).astype(np.uint8)
        img = cv2.medianBlur(img, ksize)
        return img.astype(np.float64) / 255.0

    @staticmethod
    def apply_unsharp_mask(image, sigma=1.0, amount=1.5):
        blurred = cv2.GaussianBlur(image, (0, 0), sigma)
        sharpened = cv2.addWeighted(image, 1 + amount, blurred, -amount, 0)
        return np.clip(sharpened, 0, 1)

    @staticmethod
    def resize_image(image, scale):
        h, w = image.shape[:2]
        new_h, new_w = int(h * scale), int(w * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    @staticmethod
    def generate_test_image(size=256, num_spots=20):
        img = np.zeros((size, size), dtype=np.float64)
        for _ in range(num_spots):
            x, y = np.random.randint(20, size - 20, 2)
            r = np.random.randint(2, 8)
            img = cv2.circle(img, (x, y), r, 1.0, -1)
        from scipy.ndimage import gaussian_filter
        img = gaussian_filter(img, sigma=0.8)
        return img

    @staticmethod
    def generate_blurred_image(image, psf, noise_std=0.01):
        blurred = fftconvolve(image, psf, mode='same')
        if noise_std > 0:
            blurred += np.random.normal(0, noise_std, blurred.shape)
        return np.clip(blurred, 0, 1)

    @staticmethod
    def compute_image_gradient(image):
        grad_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)
        return magnitude

    @staticmethod
    def to_qimage(image):
        from PyQt5.QtGui import QImage, qRgb
        if len(image.shape) == 2:
            img = (image * 255).astype(np.uint8)
            h, w = img.shape
            q_img = QImage(w, h, QImage.Format_Grayscale8)
            for y in range(h):
                for x in range(w):
                    q_img.setPixel(x, y, img[y, x])
            return q_img
        else:
            img = (image * 255).astype(np.uint8)
            h, w, c = img.shape
            q_img = QImage(w, h, QImage.Format_RGB888)
            for y in range(h):
                for x in range(w):
                    r, g, b = img[y, x]
                    q_img.setPixel(x, y, qRgb(r, g, b))
            return q_img
