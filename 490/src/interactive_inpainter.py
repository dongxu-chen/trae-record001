import numpy as np
import cv2
from typing import Optional, Tuple, List


class InteractiveMaskPainter:
    def __init__(self, image: np.ndarray, window_name: str = 'Draw Mask (Inpainting)'):
        self.original_image = image.copy()
        self.display_image = image.copy()
        self.mask = np.zeros(image.shape[:2], dtype=np.float32)
        self.window_name = window_name
        self.drawing = False
        self.brush_size = 15
        self.brush_color = (255, 255, 255)
        self.erasing = False
        self.history = []
        self.max_history = 50
        
        if self.original_image.max() <= 1.0:
            self.orig_uint8 = (self.original_image * 255).astype(np.uint8)
        else:
            self.orig_uint8 = self.original_image.astype(np.uint8)
        
        if len(self.orig_uint8.shape) == 2:
            self.orig_uint8 = cv2.cvtColor(self.orig_uint8, cv2.COLOR_GRAY2BGR)
        elif self.orig_uint8.shape[2] == 3:
            self.orig_uint8 = cv2.cvtColor(self.orig_uint8, cv2.COLOR_RGB2BGR)
        
        self._update_display()
    
    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self._save_history()
            self._paint(x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            self._paint(x, y)
        elif event == cv2.EVENT_RBUTTONDOWN:
            self.drawing = True
            self.erasing = True
            self._save_history()
            self._paint(x, y, erase=True)
        elif event == cv2.EVENT_RBUTTONUP:
            self.drawing = False
            self.erasing = False
    
    def _paint(self, x, y, erase=False):
        h, w = self.mask.shape
        radius = self.brush_size
        
        y_start = max(0, y - radius)
        y_end = min(h, y + radius + 1)
        x_start = max(0, x - radius)
        x_end = min(w, x + radius + 1)
        
        yy, xx = np.ogrid[y_start:y_end, x_start:x_end]
        circle = ((xx - x) ** 2 + (yy - y) ** 2) <= radius ** 2
        
        if erase:
            self.mask[y_start:y_end, x_start:x_end][circle] = 0.0
        else:
            self.mask[y_start:y_end, x_start:x_end][circle] = 1.0
        
        self._update_display()
    
    def _save_history(self):
        self.history.append(self.mask.copy())
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def _undo(self):
        if self.history:
            self.mask = self.history.pop()
            self._update_display()
    
    def _clear_mask(self):
        self._save_history()
        self.mask = np.zeros(self.mask.shape, dtype=np.float32)
        self._update_display()
    
    def _fill_mask(self):
        self._save_history()
        self.mask = np.ones(self.mask.shape, dtype=np.float32)
        self._update_display()
    
    def _update_display(self):
        display = self.orig_uint8.copy()
        
        mask_colored = np.zeros_like(display)
        mask_colored[:, :, 2] = (self.mask * 180).astype(np.uint8)
        mask_colored[:, :, 1] = (self.mask * 60).astype(np.uint8)
        
        display = cv2.addWeighted(display, 1.0, mask_colored, 0.5, 0)
        
        mask_uint8 = (self.mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(display, contours, -1, (0, 255, 0), 1)
        
        h, w = display.shape[:2]
        info_bar = np.zeros((60, w, 3), dtype=np.uint8)
        cv2.putText(info_bar, f"Brush:{self.brush_size} | L:Draw R:Erase | C:Clear F:Fill | Z:Undo | S:Save Q:Quit",
                     (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 1)
        cv2.putText(info_bar, f"Mask coverage: {self.mask.mean()*100:.1f}%",
                     (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 255), 1)
        
        combined = np.vstack([info_bar, display])
        
        cv2.imshow(self.window_name, combined)
    
    def run(self) -> np.ndarray:
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)
        
        print("\n" + "=" * 60)
        print("Interactive Mask Painter")
        print("=" * 60)
        print("Controls:")
        print("  Left Mouse Button  : Draw mask (paint region to repair)")
        print("  Right Mouse Button : Erase mask")
        print("  +/- or Scroll      : Increase/decrease brush size")
        print("  C                  : Clear all mask")
        print("  F                  : Fill entire mask")
        print("  Z                  : Undo last stroke")
        print("  S                  : Save mask and continue to repair")
        print("  Q / ESC            : Quit without repairing")
        print("=" * 60)
        
        while True:
            key = cv2.waitKey(30) & 0xFF
            
            if key == 27 or key == ord('q'):
                cv2.destroyAllWindows()
                return None
            
            elif key == ord('s'):
                cv2.destroyAllWindows()
                return self.mask
            
            elif key == ord('c'):
                self._clear_mask()
            
            elif key == ord('f'):
                self._fill_mask()
            
            elif key == ord('z'):
                self._undo()
            
            elif key == ord('+') or key == ord('='):
                self.brush_size = min(self.brush_size + 2, 100)
                self._update_display()
            
            elif key == ord('-') or key == ord('_'):
                self.brush_size = max(self.brush_size - 2, 1)
                self._update_display()
    
    def get_mask(self) -> np.ndarray:
        return self.mask.copy()


class InteractiveInpainter:
    def __init__(self, model_name: str = 'partialconv',
                 device: str = None,
                 image_size: Tuple[int, int] = (256, 256),
                 poisson_blend_method: str = 'mixed'):
        
        from .inpainter import ImageInpainter
        self.inpainter = ImageInpainter(
            model_name=model_name,
            device=device,
            image_size=image_size,
            poisson_blend_method=poisson_blend_method,
            enable_poisson_blend=True
        )
    
    def inpaint_interactive(self, image_path: str,
                             output_path: Optional[str] = None,
                             show_result: bool = True) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        
        from .utils import load_image, save_image
        
        image = load_image(image_path, normalize=True)
        
        h, w = image.shape[:2]
        
        painter = InteractiveMaskPainter(image, window_name=f'Draw Mask: {image_path}')
        mask = painter.run()
        
        if mask is None:
            print("Mask painting cancelled.")
            return image, np.zeros((h, w), dtype=np.float32), image
        
        if mask.ndim == 2:
            mask_3d = mask[:, :, np.newaxis]
        else:
            mask_3d = mask
        
        print(f"\nMask coverage: {mask.mean()*100:.1f}%")
        print("Running inpainting...")
        
        result = self.inpainter.inpaint(image, mask_3d)
        
        if show_result:
            self._show_result(image, mask_3d, result)
        
        if output_path:
            save_image(result, output_path)
            print(f"Result saved to: {output_path}")
        
        return image, mask, result
    
    def inpaint_interactive_array(self, image: np.ndarray,
                                    show_result: bool = True) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        
        painter = InteractiveMaskPainter(image, window_name='Draw Mask')
        mask = painter.run()
        
        if mask is None:
            print("Mask painting cancelled.")
            return image, np.zeros(image.shape[:2], dtype=np.float32), image
        
        if mask.ndim == 2:
            mask_3d = mask[:, :, np.newaxis]
        else:
            mask_3d = mask
        
        print("Running inpainting...")
        result = self.inpainter.inpaint(image, mask_3d)
        
        if show_result:
            self._show_result(image, mask_3d, result)
        
        return image, mask, result
    
    def _show_result(self, original, mask, result, window_name='Result'):
        if original.max() <= 1.0:
            orig_disp = (original * 255).astype(np.uint8)
        else:
            orig_disp = original.astype(np.uint8)
        
        if result.max() <= 1.0:
            result_disp = (result * 255).astype(np.uint8)
        else:
            result_disp = result.astype(np.uint8)
        
        if len(orig_disp.shape) == 3 and orig_disp.shape[2] == 3:
            orig_disp = cv2.cvtColor(orig_disp, cv2.COLOR_RGB2BGR)
            result_disp = cv2.cvtColor(result_disp, cv2.COLOR_RGB2BGR)
        
        mask_disp = (mask * 255).astype(np.uint8)
        if mask_disp.ndim == 3:
            mask_disp = mask_disp[:, :, 0]
        mask_color = cv2.cvtColor(mask_disp, cv2.COLOR_GRAY2BGR)
        
        h, w = orig_disp.shape[:2]
        combined = np.zeros((h, w * 3, 3), dtype=np.uint8)
        combined[:, :w] = orig_disp
        combined[:, w:w*2] = mask_color
        combined[:, w*2:] = result_disp
        
        cv2.putText(combined, 'Original', (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(combined, 'Mask', (w + 10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(combined, 'Result', (w*2 + 10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, combined)
        
        print("Press any key to close result, or 'R' to re-draw mask...")
        key = cv2.waitKey(0) & 0xFF
        cv2.destroyAllWindows()
        
        return key == ord('r')
    
    def interactive_loop(self, image_path: str, output_path: Optional[str] = None):
        from .utils import load_image, save_image
        
        image = load_image(image_path, normalize=True)
        
        while True:
            painter = InteractiveMaskPainter(image, window_name='Draw Mask (Interactive)')
            mask = painter.run()
            
            if mask is None:
                print("Exiting interactive mode.")
                return None, None, None
            
            if mask.ndim == 2:
                mask_3d = mask[:, :, np.newaxis]
            else:
                mask_3d = mask
            
            print("Running inpainting...")
            result = self.inpainter.inpaint(image, mask_3d)
            
            redo = self._show_result(image, mask_3d, result)
            
            if not redo:
                if output_path:
                    save_image(result, output_path)
                    print(f"Result saved to: {output_path}")
                return image, mask, result
