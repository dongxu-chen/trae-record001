import mss
from PIL import Image
import os
import platform
from datetime import datetime


def get_default_save_dir():
    if platform.system() == "Windows":
        return os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
    elif platform.system() == "Darwin":
        return os.path.join(os.path.expanduser("~"), "Desktop")
    else:
        return os.path.join(os.path.expanduser("~"), "Pictures")


def get_virtual_screen_bounds():
    with mss.mss() as sct:
        all_monitors = sct.monitors
        if len(all_monitors) <= 1:
            return all_monitors[0] if all_monitors else {"left": 0, "top": 0, "width": 1920, "height": 1080}
        return all_monitors[0]


def get_monitor_at(x, y):
    with mss.mss() as sct:
        all_monitors = sct.monitors
        for i in range(1, len(all_monitors)):
            mon = all_monitors[i]
            if (mon["left"] <= x < mon["left"] + mon["width"] and 
                mon["top"] <= y < mon["top"] + mon["height"]):
                return mon, i
        return all_monitors[1], 1


def normalize_region(left, top, width, height):
    virtual = get_virtual_screen_bounds()
    return {
        "left": virtual["left"] + left,
        "top": virtual["top"] + top,
        "width": width,
        "height": height
    }


def capture_full_screen(monitor_index=1, save_path=None):
    with mss.mss() as sct:
        monitors = sct.monitors
        if monitor_index < 1 or monitor_index >= len(monitors):
            monitor_index = 1
        monitor = monitors[monitor_index]
        
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        
        if save_path:
            save_dir = os.path.dirname(save_path)
            if save_dir and not os.path.exists(save_dir):
                os.makedirs(save_dir)
            img.save(save_path)
        
        return img, save_path


def capture_region(left, top, width, height, save_path=None, use_absolute_coords=True):
    with mss.mss() as sct:
        if use_absolute_coords:
            monitor = {"left": left, "top": top, "width": width, "height": height}
        else:
            monitor = normalize_region(left, top, width, height)
        
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        
        if save_path:
            save_dir = os.path.dirname(save_path)
            if save_dir and not os.path.exists(save_dir):
                os.makedirs(save_dir)
            img.save(save_path)
        
        return img, save_path


def generate_filename(prefix="screenshot", ext="png"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{ext}"


def list_monitors():
    with mss.mss() as sct:
        return sct.monitors


class InteractiveSelector:
    def __init__(self, on_select=None, on_cancel=None, show_magnifier=True):
        self.on_select = on_select
        self.on_cancel = on_cancel
        self.show_magnifier = show_magnifier
        self.root = None
        self.canvas = None
        self.rect_id = None
        self.coord_text_id = None
        self.dim_text_id = None
        self.start_x = 0
        self.start_y = 0
        self.magnifier = None
        self.selection = None
        self.cancelled = False
        
    def start(self):
        import tkinter as tk
        from magnifier import SelectionMagnifier
        
        self.root = tk.Tk()
        
        virtual = get_virtual_screen_bounds()
        self.root.geometry(f"{virtual['width']}x{virtual['height']}+{virtual['left']}+{virtual['top']}")
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.attributes('-alpha', 0.25)
        self.root.configure(bg='black')
        self.root.configure(cursor='cross')
        
        self.canvas = tk.Canvas(
            self.root,
            bg='black',
            highlightthickness=0,
            cursor='cross'
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        if self.show_magnifier:
            self.magnifier = SelectionMagnifier(scale=3, size=150)
            self.magnifier.start(self.root)
        
        self._bind_events()
        
        self.root.mainloop()
        
        return self.selection, self.cancelled
        
    def _bind_events(self):
        self.canvas.bind('<Button-1>', self._on_mouse_down)
        self.canvas.bind('<B1-Motion>', self._on_mouse_move)
        self.canvas.bind('<ButtonRelease-1>', self._on_mouse_up)
        self.canvas.bind('<Motion>', self._on_mouse_track)
        self.root.bind('<Escape>', self._on_escape)
        self.root.bind('<KeyPress-F1>', self._on_help)
        self.root.bind('<FocusOut>', self._on_focus_out)
        
    def _on_mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y
        
        abs_x = self.root.winfo_x() + event.x
        abs_y = self.root.winfo_y() + event.y
        
        self.rect_id = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline='#00FF00',
            width=2,
            dash=(5, 3)
        )
        
        self.coord_text_id = self.canvas.create_text(
            event.x, event.y - 20,
            text=f"起点: ({abs_x}, {abs_y})",
            fill='yellow',
            font=('Arial', 11, 'bold'),
            anchor=tk.SW
        )
        
    def _on_mouse_track(self, event):
        if self.magnifier:
            abs_x = self.root.winfo_x() + event.x
            abs_y = self.root.winfo_y() + event.y
            self.magnifier.update(abs_x, abs_y)
            
    def _on_mouse_move(self, event):
        if self.rect_id:
            self.canvas.coords(
                self.rect_id,
                self.start_x, self.start_y,
                event.x, event.y
            )
            
            abs_x1 = self.root.winfo_x() + min(self.start_x, event.x)
            abs_y1 = self.root.winfo_y() + min(self.start_y, event.y)
            abs_x2 = self.root.winfo_x() + max(self.start_x, event.x)
            abs_y2 = self.root.winfo_y() + max(self.start_y, event.y)
            width = abs_x2 - abs_x1
            height = abs_y2 - abs_y1
            
            if self.coord_text_id:
                self.canvas.itemconfig(
                    self.coord_text_id,
                    text=f"选择: ({abs_x1}, {abs_y1}) - ({abs_x2}, {abs_y2})"
                )
                text_x = min(self.start_x, event.x)
                text_y = min(self.start_y, event.y) - 20
                self.canvas.coords(self.coord_text_id, text_x, text_y)
            
            if self.dim_text_id:
                self.canvas.itemconfig(
                    self.dim_text_id,
                    text=f"大小: {width} x {height}"
                )
            else:
                self.dim_text_id = self.canvas.create_text(
                    max(self.start_x, event.x),
                    max(self.start_y, event.y) + 5,
                    text=f"大小: {width} x {height}",
                    fill='#00FF00',
                    font=('Arial', 10, 'bold'),
                    anchor=tk.NE
                )
            
            if self.dim_text_id:
                dim_text_x = max(self.start_x, event.x)
                dim_text_y = max(self.start_y, event.y) + 5
                self.canvas.coords(self.dim_text_id, dim_text_x, dim_text_y)
            
            if self.magnifier:
                abs_x = self.root.winfo_x() + event.x
                abs_y = self.root.winfo_y() + event.y
                self.magnifier.update(abs_x, abs_y)
                
    def _on_mouse_up(self, event):
        if self.rect_id is None:
            return
            
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
            
        width = x2 - x1
        height = y2 - y1
        
        if width < 10 or height < 10:
            self._cleanup()
            self.cancelled = True
            if self.on_cancel:
                self.on_cancel()
            return
            
        abs_left = self.root.winfo_x() + x1
        abs_top = self.root.winfo_y() + y1
        
        self.selection = (abs_left, abs_top, width, height)
        
        self._cleanup()
        
        if self.on_select:
            self.on_select(self.selection)
            
    def _on_escape(self, event):
        self.cancelled = True
        self._cleanup()
        if self.on_cancel:
            self.on_cancel()
            
    def _on_help(self, event):
        import tkinter.messagebox as messagebox
        messagebox.showinfo(
            "选区帮助",
            "操作说明:\n\n"
            "• 按住鼠标左键拖动选择区域\n"
            "• 按 ESC 取消选择\n"
            "• 绿色虚线框显示选择区域\n"
            "• 右下角显示选区大小"
        )
        
    def _on_focus_out(self, event):
        self.root.lift()
        
    def _cleanup(self):
        if self.magnifier:
            self.magnifier.stop()
            self.magnifier = None
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except Exception:
                pass
            self.root = None


def interactive_capture(save_path=None, show_magnifier=True):
    selector = InteractiveSelector(show_magnifier=show_magnifier)
    selection, cancelled = selector.start()
    
    if cancelled or not selection:
        return None, None
        
    left, top, width, height = selection
    
    img, saved = capture_region(
        left, top, width, height,
        save_path=save_path,
        use_absolute_coords=True
    )
    
    return img, saved


def interactive_select_region():
    selector = InteractiveSelector()
    selection, cancelled = selector.start()
    
    if cancelled or not selection:
        return None
        
    return selection


if __name__ == "__main__":
    import sys
    
    save_dir = get_default_save_dir()
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    filename = generate_filename()
    save_path = os.path.join(save_dir, filename)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--region":
            if len(sys.argv) >= 6:
                left = int(sys.argv[2])
                top = int(sys.argv[3])
                width = int(sys.argv[4])
                height = int(sys.argv[5])
                img, saved = capture_region(left, top, width, height, save_path)
            else:
                print("Usage: python screenshot.py --region <left> <top> <width> <height>")
                print("   or: python screenshot.py --interactive")
                sys.exit(1)
        elif sys.argv[1] == "--interactive":
            img, saved = interactive_capture(save_path)
            if not img:
                print("用户取消了选择")
                sys.exit(0)
        else:
            monitor_index = int(sys.argv[1])
            img, saved = capture_full_screen(monitor_index, save_path)
    else:
        img, saved = capture_full_screen(1, save_path)
    
    if saved:
        print(f"截图已保存到: {saved}")
