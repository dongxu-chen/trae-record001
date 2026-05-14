import tkinter as tk
from PIL import Image, ImageTk, ImageGrab
import platform
import mss


class ScreenMagnifier:
    def __init__(self, scale=3, size=200, show_crosshair=True, show_info=True):
        self.scale = scale
        self.size = size
        self.show_crosshair = show_crosshair
        self.show_info = show_info
        self.window = None
        self.canvas = None
        self.running = False
        self.last_pos = (0, 0)
        self.sct = None
        
    def start(self):
        if self.running:
            return
            
        self.running = True
        self.sct = mss.mss()
        
        self.window = tk.Toplevel()
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.configure(bg='black', cursor='none')
        
        self.canvas = tk.Canvas(
            self.window,
            width=self.size,
            height=self.size,
            bg='black',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self._update_position()
        self._capture_loop()
        
    def stop(self):
        self.running = False
        if self.sct:
            try:
                self.sct.close()
            except Exception:
                pass
            self.sct = None
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
        self.canvas = None
            
    def _update_position(self):
        if not self.running or not self.window:
            return
            
        try:
            x = self.window.winfo_pointerx()
            y = self.window.winfo_pointery()
            
            offset_x = self.size // 2 + 20
            offset_y = self.size // 2 + 20
            
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            
            pos_x = x + offset_x
            pos_y = y - offset_y
            
            if pos_x + self.size > screen_width:
                pos_x = x - offset_x - self.size
            if pos_y < 0:
                pos_y = y + 20
            if pos_y + self.size > screen_height:
                pos_y = y - self.size - 20
                
            self.window.geometry(f"{self.size}x{self.size}+{max(0, pos_x)}+{max(0, pos_y)}")
            
            if (x, y) != self.last_pos:
                self.last_pos = (x, y)
                self._refresh_magnifier(x, y)
                
        except Exception:
            pass
            
        if self.running and self.window:
            self.window.after(30, self._update_position)
            
    def _capture_loop(self):
        if not self.running or not self.window:
            return
            
        try:
            x = self.window.winfo_pointerx()
            y = self.window.winfo_pointery()
            
            if (x, y) != self.last_pos:
                self.last_pos = (x, y)
                self._refresh_magnifier(x, y)
                
        except Exception:
            pass
            
        if self.running and self.window:
            self.window.after(50, self._capture_loop)
            
    def _refresh_magnifier(self, x, y):
        if not self.running or not self.canvas:
            return
            
        try:
            half = self.size // 2 // self.scale
            
            monitor = {
                "left": x - half,
                "top": y - half,
                "width": half * 2,
                "height": half * 2
            }
            
            screenshot = self.sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            
            new_size = self.size
            img = img.resize((new_size, new_size), Image.LANCZOS)
            
            self.photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            
            if self.show_crosshair:
                center = self.size // 2
                self.canvas.create_line(
                    center, 0, center, self.size,
                    fill='red', width=1
                )
                self.canvas.create_line(
                    0, center, self.size, center,
                    fill='red', width=1
                )
                self.canvas.create_oval(
                    center - 3, center - 3,
                    center + 3, center + 3,
                    outline='red', width=1
                )
                
            if self.show_info:
                info_text = f"X:{x} Y:{y}"
                self.canvas.create_text(
                    10, 10,
                    anchor=tk.NW,
                    text=info_text,
                    fill='white',
                    font=('Arial', 9, 'bold')
                )
                
        except Exception:
            pass
            
    def update_scale(self, scale):
        self.scale = max(1, min(scale, 8))
        
    def update_size(self, size):
        self.size = max(100, min(size, 500))


class SelectionMagnifier:
    def __init__(self, scale=3, size=150):
        self.scale = scale
        self.size = size
        self.window = None
        self.canvas = None
        self.running = False
        self.sct = None
        
    def start(self, parent_root=None):
        if self.running:
            return
            
        self.running = True
        self.sct = mss.mss()
        
        if parent_root:
            self.window = tk.Toplevel(parent_root)
        else:
            self.window = tk.Toplevel()
            
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.configure(bg='black')
        
        self.canvas = tk.Canvas(
            self.window,
            width=self.size,
            height=self.size,
            bg='black',
            highlightthickness=2,
            highlightbackground='blue'
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
    def stop(self):
        self.running = False
        if self.sct:
            try:
                self.sct.close()
            except Exception:
                pass
            self.sct = None
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
        self.canvas = None
        
    def update(self, x, y):
        if not self.running or not self.window or not self.canvas:
            return
            
        try:
            half = self.size // 2 // self.scale
            
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            
            pos_x = x + 30
            pos_y = y - self.size - 30
            
            if pos_x + self.size > screen_width:
                pos_x = x - self.size - 30
            if pos_y < 0:
                pos_y = y + 30
                
            self.window.geometry(
                f"{self.size}x{self.size}+{max(0, pos_x)}+{max(0, pos_y)}"
            )
            
            left = max(0, x - half)
            top = max(0, y - half)
            
            monitor = {
                "left": left,
                "top": top,
                "width": min(half * 2, screen_width - left),
                "height": min(half * 2, screen_height - top)
            }
            
            screenshot = self.sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            img = img.resize((self.size, self.size), Image.LANCZOS)
            
            self.photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            
            center = self.size // 2
            self.canvas.create_line(center, 0, center, self.size, fill='red', width=1)
            self.canvas.create_line(0, center, self.size, center, fill='red', width=1)
            
            self.canvas.create_text(
                10, 10,
                anchor=tk.NW,
                text=f"({x}, {y})",
                fill='white',
                font=('Arial', 8, 'bold')
            )
            
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    import time
    import threading
    
    root = tk.Tk()
    root.withdraw()
    
    magnifier = ScreenMagnifier(scale=4, size=250)
    
    def stop_magnifier():
        magnifier.stop()
        root.destroy()
        sys.exit(0)
    
    magnifier.start()
    
    print("放大镜已启动，10秒后自动关闭...")
    print("按 Ctrl+C 强制退出")
    
    try:
        root.after(10000, stop_magnifier)
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        magnifier.stop()
