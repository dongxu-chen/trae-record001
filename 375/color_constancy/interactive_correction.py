import numpy as np
import cv2
from .white_balance import correct_white_balance, estimate_gains
from .visualization import rgb_to_temperature


class InteractiveWhiteBalance:
    """
    Interactive white balance correction with manual white point selection.
    
    Allows users to:
    1. Click on a region of the image to set as the white reference
    2. Adjust RGB gains manually
    3. Adjust color temperature
    4. Preview corrected image in real-time
    5. Save final corrected image
    """
    
    def __init__(self, image=None, method='gray_world'):
        """
        Initialize interactive WB.
        
        Args:
            image: Input BGR image (H, W, 3) uint8 (optional)
            method: Default estimation method for initial guess
        """
        self.original = None
        self.corrected = None
        self.illuminant = None
        self.rgb_gains = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self.temperature = 6500.0
        self.tint = 0.0
        self._white_point_roi = None
        self._dragging = False
        self._drag_start = None
        self._roi_start = None
        
        if image is not None:
            self.load_image(image, method=method)
    
    def load_image(self, image, method='gray_world'):
        """
        Load an image and get initial illuminant estimate.
        
        Args:
            image: Input BGR image (H, W, 3) uint8
            method: Initial estimation method
        """
        self.original = image.copy()
        self.corrected = image.copy()
        
        from .algorithms import gray_world, perfect_reflection, shades_of_gray
        
        if method == 'gray_world':
            est = gray_world(image)
        elif method == 'perfect_reflection':
            est = perfect_reflection(image, percentile=99)
        elif method == 'shades_of_gray':
            est = shades_of_gray(image, p=6)
        else:
            est = gray_world(image)
        
        self.illuminant = est
        self.rgb_gains = estimate_gains(est)
        self.corrected = correct_white_balance(image, est)
        
        cct, _ = rgb_to_temperature(est)
        self.temperature = cct
        
        return self.corrected
    
    def set_white_point(self, x, y, patch_size=10):
        """
        Set white point from a pixel location.
        
        Args:
            x, y: Pixel coordinates (in original image)
            patch_size: Size of patch to average (pixels)
        
        Returns:
            corrected: Updated corrected image
        """
        h, w = self.original.shape[:2]
        
        y1 = max(0, y - patch_size // 2)
        y2 = min(h, y + patch_size // 2)
        x1 = max(0, x - patch_size // 2)
        x2 = min(w, x + patch_size // 2)
        
        patch = self.original[y1:y2, x1:x2].astype(np.float32)
        mean_rgb = np.mean(patch.reshape(-1, 3), axis=0)
        
        if np.sum(mean_rgb) < 1e-8:
            return self.corrected
        
        self.illuminant = mean_rgb / (np.linalg.norm(mean_rgb) + 1e-8)
        self.rgb_gains = estimate_gains(self.illuminant)
        self.corrected = correct_white_balance(self.original, self.illuminant)
        
        cct, _ = rgb_to_temperature(self.illuminant)
        self.temperature = cct
        
        self._white_point_roi = (x1, y1, x2, y2)
        
        return self.corrected
    
    def set_white_roi(self, x1, y1, x2, y2):
        """
        Set white point from a rectangular region.
        
        Args:
            x1, y1, x2, y2: Region coordinates
        
        Returns:
            corrected: Updated corrected image
        """
        h, w = self.original.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            return self.corrected
        
        patch = self.original[y1:y2, x1:x2].astype(np.float32)
        mean_rgb = np.mean(patch.reshape(-1, 3), axis=0)
        
        if np.sum(mean_rgb) < 1e-8:
            return self.corrected
        
        self.illuminant = mean_rgb / (np.linalg.norm(mean_rgb) + 1e-8)
        self.rgb_gains = estimate_gains(self.illuminant)
        self.corrected = correct_white_balance(self.original, self.illuminant)
        
        cct, _ = rgb_to_temperature(self.illuminant)
        self.temperature = cct
        
        self._white_point_roi = (x1, y1, x2, y2)
        
        return self.corrected
    
    def set_gains(self, r_gain=None, g_gain=None, b_gain=None):
        """
        Manually set RGB channel gains.
        
        Args:
            r_gain: Red gain (None to keep current)
            g_gain: Green gain
            b_gain: Blue gain
        
        Returns:
            corrected: Updated corrected image
        """
        if r_gain is not None:
            self.rgb_gains[0] = r_gain
        if g_gain is not None:
            self.rgb_gains[1] = g_gain
        if b_gain is not None:
            self.rgb_gains[2] = b_gain
        
        self.rgb_gains = np.clip(self.rgb_gains, 0.1, 10.0)
        
        img_float = self.original.astype(np.float32)
        self.corrected = np.clip(img_float * self.rgb_gains.reshape(1, 1, 3), 0, 255).astype(np.uint8)
        
        self.illuminant = 1.0 / (self.rgb_gains + 1e-8)
        self.illuminant = self.illuminant / (np.linalg.norm(self.illuminant) + 1e-8)
        
        cct, _ = rgb_to_temperature(self.illuminant)
        self.temperature = cct
        
        return self.corrected
    
    def set_temperature(self, temperature, tint=0.0):
        """
        Set color temperature and tint for WB correction.
        
        Args:
            temperature: Color temperature in Kelvin (2000-12000)
            tint: Green-magenta tint (-1.0 to 1.0)
        
        Returns:
            corrected: Updated corrected image
        """
        self.temperature = np.clip(temperature, 2000, 12000)
        self.tint = np.clip(tint, -1.0, 1.0)
        
        from .visualization import temperature_to_rgb
        
        target_white = temperature_to_rgb(self.temperature)
        
        if self.tint != 0.0:
            target_white[1] *= (1.0 + self.tint * 0.1)
            target_white = target_white / (np.linalg.norm(target_white) + 1e-8)
        
        self.illuminant = target_white
        self.rgb_gains = estimate_gains(target_white)
        self.corrected = correct_white_balance(self.original, target_white)
        
        return self.corrected
    
    def auto_white_balance(self, method='gray_world'):
        """
        Re-apply automatic WB estimation.
        
        Args:
            method: Estimation method
        
        Returns:
            corrected: Updated corrected image
        """
        if self.original is None:
            return None
        
        from .algorithms import gray_world, perfect_reflection, shades_of_gray
        
        if method == 'gray_world':
            est = gray_world(self.original)
        elif method == 'perfect_reflection':
            est = perfect_reflection(self.original, percentile=99)
        elif method == 'shades_of_gray':
            est = shades_of_gray(self.original, p=6)
        else:
            est = gray_world(self.original)
        
        self.illuminant = est
        self.rgb_gains = estimate_gains(est)
        self.corrected = correct_white_balance(self.original, est)
        
        cct, _ = rgb_to_temperature(est)
        self.temperature = cct
        
        return self.corrected
    
    def reset(self):
        self.corrected = self.original.copy()
        self.rgb_gains = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self.illuminant = None
        self.temperature = 6500.0
        self.tint = 0.0
        self._white_point_roi = None
        return self.corrected
    
    def get_preview_image(self, scale=1.0):
        if self.corrected is None:
            return None
        
        preview = self.corrected.copy()
        
        if self._white_point_roi is not None:
            x1, y1, x2, y2 = self._white_point_roi
            cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        if scale != 1.0:
            preview = cv2.resize(preview, None, fx=scale, fy=scale)
        
        return preview
    
    def get_info_text(self):
        lines = []
        lines.append(f"Temperature: {self.temperature:.0f} K")
        lines.append(f"RGB Gains: R={self.rgb_gains[0]:.3f}, G={self.rgb_gains[1]:.3f}, B={self.rgb_gains[2]:.3f}")
        
        if self.illuminant is not None:
            lines.append(f"Illuminant: [{self.illuminant[0]:.3f}, {self.illuminant[1]:.3f}, {self.illuminant[2]:.3f}]")
        
        return '\n'.join(lines)


def interactive_white_balance(image, window_name='White Balance Correction'):
    """
    Run interactive white balance correction GUI using OpenCV.
    
    Controls:
    - Click on image: Set white point at clicked location
    - Drag mouse: Select ROI for white point
    - 'w': Cycle through auto WB methods
    - 'r': Reset to original
    - 't': Increase temperature (warm)
    - 'y': Decrease temperature (cool)
    - '1'-'9': Set temperature from 2K to 10K
    - 'o': Increase red gain
    - 'p': Decrease red gain
    - 'k': Increase blue gain
    - 'l': Decrease blue gain
    - 's': Save corrected image
    - 'q': Quit
    
    Args:
        image: Input BGR image (H, W, 3) uint8
        window_name: Window title
    
    Returns:
        corrected: Final corrected image
        iwb: InteractiveWhiteBalance instance with settings
    """
    iwb = InteractiveWhiteBalance(image, method='gray_world')
    
    methods = ['gray_world', 'perfect_reflection', 'shades_of_gray']
    current_method_idx = 0
    
    h, w = image.shape[:2]
    max_display_size = 800
    scale = min(1.0, max_display_size / max(w, h))
    
    display_w = int(w * scale)
    display_h = int(h * scale)
    
    mouse_down = False
    start_x, start_y = -1, -1
    
    def mouse_callback(event, x, y, flags, param):
        nonlocal mouse_down, start_x, start_y
        
        orig_x = int(x / scale)
        orig_y = int(y / scale)
        
        if event == cv2.EVENT_LBUTTONDOWN:
            mouse_down = True
            start_x, start_y = orig_x, orig_y
            
        elif event == cv2.EVENT_MOUSEMOVE:
            if mouse_down:
                temp = iwb.corrected.copy()
                cv2.rectangle(temp, 
                             (int(start_x * scale), int(start_y * scale)),
                             (x, y), (0, 255, 0), 2)
                cv2.imshow(window_name, cv2.resize(temp, (display_w, display_h)))
                
        elif event == cv2.EVENT_LBUTTONUP:
            mouse_down = False
            end_x, end_y = orig_x, orig_y
            
            if abs(start_x - end_x) < 5 and abs(start_y - end_y) < 5:
                iwb.set_white_point(orig_x, orig_y, patch_size=10)
            else:
                x1, x2 = min(start_x, end_x), max(start_x, end_x)
                y1, y2 = min(start_y, end_y), max(start_y, end_y)
                iwb.set_white_roi(x1, y1, x2, y2)
            
            cv2.imshow(window_name, iwb.get_preview_image(scale))
    
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, display_w, display_h)
    cv2.setMouseCallback(window_name, mouse_callback)
    
    cv2.imshow(window_name, iwb.get_preview_image(scale))
    
    print("Interactive White Balance Controls:")
    print("  Click: Set white point at location")
    print("  Drag: Select ROI for white point")
    print("  w: Cycle auto WB method")
    print("  r: Reset")
    print("  t/y: Warm/Cool temperature")
    print("  1-9: Set temperature (2K-10K)")
    print("  o/p: +/- Red gain")
    print("  k/l: +/- Blue gain")
    print("  s: Save corrected image")
    print("  q: Quit")
    
    while True:
        key = cv2.waitKey(100) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('r'):
            iwb.reset()
        elif key == ord('w'):
            current_method_idx = (current_method_idx + 1) % len(methods)
            method = methods[current_method_idx]
            iwb.auto_white_balance(method)
            print(f"Method: {method}")
        elif key == ord('t'):
            iwb.set_temperature(iwb.temperature + 500)
        elif key == ord('y'):
            iwb.set_temperature(iwb.temperature - 500)
        elif ord('1') <= key <= ord('9'):
            temp = 2000 + (key - ord('1')) * 1000
            iwb.set_temperature(temp)
        elif key == ord('o'):
            iwb.set_gains(r_gain=iwb.rgb_gains[0] * 1.1)
        elif key == ord('p'):
            iwb.set_gains(r_gain=iwb.rgb_gains[0] / 1.1)
        elif key == ord('k'):
            iwb.set_gains(b_gain=iwb.rgb_gains[2] * 1.1)
        elif key == ord('l'):
            iwb.set_gains(b_gain=iwb.rgb_gains[2] / 1.1)
        elif key == ord('s'):
            save_path = 'corrected_image.png'
            cv2.imwrite(save_path, iwb.corrected)
            print(f"Saved to {save_path}")
        
        cv2.imshow(window_name, iwb.get_preview_image(scale))
    
    cv2.destroyWindow(window_name)
    
    return iwb.corrected, iwb


def manual_white_balance_selector(image, points=None):
    """
    Apply white balance correction using manually selected white points.
    
    Args:
        image: Input BGR image (H, W, 3) uint8
        points: List of (x, y) pixel coordinates to use as white reference.
                If None, returns the original image.
    
    Returns:
        corrected: White balanced image
        illuminant: Estimated illuminant from selected points
    """
    if points is None or len(points) == 0:
        return image, None
    
    h, w = image.shape[:2]
    patch_size = 10
    
    all_pixels = []
    
    for x, y in points:
        y1 = max(0, y - patch_size // 2)
        y2 = min(h, y + patch_size // 2)
        x1 = max(0, x - patch_size // 2)
        x2 = min(w, x + patch_size // 2)
        
        patch = image[y1:y2, x1:x2].astype(np.float32)
        pixels = patch.reshape(-1, 3)
        
        mask = np.all(pixels > 20, axis=1) & np.all(pixels < 240, axis=1)
        valid_pixels = pixels[mask]
        
        if len(valid_pixels) > 0:
            all_pixels.append(valid_pixels)
    
    if len(all_pixels) == 0:
        return image, None
    
    all_pixels = np.vstack(all_pixels)
    mean_rgb = np.mean(all_pixels, axis=0)
    
    if np.sum(mean_rgb) < 1e-8:
        return image, None
    
    illuminant = mean_rgb / (np.linalg.norm(mean_rgb) + 1e-8)
    corrected = correct_white_balance(image, illuminant)
    
    return corrected, illuminant


def apply_temperature_correction(image, temperature=6500, tint=0.0):
    """
    Apply white balance correction based on color temperature.
    
    Args:
        image: Input BGR image (H, W, 3) uint8
        temperature: Target color temperature in Kelvin (2000-12000)
        tint: Green-magenta tint adjustment (-1.0 to 1.0)
    
    Returns:
        corrected: Temperature-corrected image
        illuminant: Target illuminant based on temperature
    """
    from .visualization import temperature_to_rgb
    
    temperature = np.clip(temperature, 2000, 12000)
    tint = np.clip(tint, -1.0, 1.0)
    
    target_white = temperature_to_rgb(temperature)
    
    if tint != 0.0:
        target_white[1] *= (1.0 + tint * 0.1)
        target_white = target_white / (np.linalg.norm(target_white) + 1e-8)
    
    corrected = correct_white_balance(image, target_white)
    
    return corrected, target_white
