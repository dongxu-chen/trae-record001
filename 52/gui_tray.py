import pystray
from PIL import Image, ImageDraw
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
import os
import sys
import platform
import json
import time

from screenshot import (
    capture_full_screen, 
    capture_region, 
    get_default_save_dir, 
    generate_filename, 
    list_monitors,
    interactive_select_region,
    get_virtual_screen_bounds
)
from ocr import (
    recognize_text, 
    configure_tesseract, 
    get_languages,
    check_training_data,
    translate_text,
    set_baidu_config,
    is_baidu_configured
)
from clipboard import copy_text, copy_image
from hotkey import HotkeyManager


CONFIG_FILE = os.path.join(
    os.path.expanduser("~"), 
    ".ocr_screenshot_config.json"
)


def get_tray_backend():
    system = platform.system()
    if system == "Windows":
        return "default"
    elif system == "Darwin":
        return "default"
    else:
        try:
            from pystray._linux import AppIndicatorIcon
            return "appindicator"
        except ImportError:
            try:
                from pystray._gtk import Icon
                return "gtk"
            except ImportError:
                return "default"


def setup_tray_backend():
    backend = get_tray_backend()
    if backend == "appindicator":
        try:
            os.environ["PYSTRAY_BACKEND"] = "appindicator"
        except Exception:
            pass
    elif backend == "gtk":
        try:
            os.environ["PYSTRAY_BACKEND"] = "gtk"
        except Exception:
            pass
    return backend


def create_tray_icon():
    icon_size = 64
    icon_image = Image.new('RGB', (icon_size, icon_size), color=(52, 152, 219))
    draw = ImageDraw.Draw(icon_image)
    
    draw.rectangle([10, 20, 54, 40], fill=(255, 255, 255), outline=(41, 128, 185), width=2)
    draw.rectangle([14, 24, 30, 36], fill=(46, 204, 113))
    draw.line([34, 26, 50, 26], fill=(149, 165, 166), width=2)
    draw.line([34, 30, 48, 30], fill=(149, 165, 166), width=2)
    draw.line([34, 34, 44, 34], fill=(149, 165, 166), width=2)
    
    return icon_image


def load_config():
    default_config = {
        "languages": ["chi_sim+eng", "eng", "chi_sim", "chi_tra", "jpn", "kor"],
        "current_lang": "chi_sim+eng",
        "translate_to": "zh",
        "translate_from": "auto",
        "use_baidu_translate": False,
        "baidu_app_id": "",
        "baidu_app_key": "",
        "baidu_secret_key": "",
        "hotkeys": {
            "fullscreen": "<ctrl>+<alt>+a",
            "region": "<ctrl>+<alt>+s",
            "translate_selected": "<ctrl>+<alt>+t"
        },
        "show_magnifier": True,
        "auto_translate": False
    }
    
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                default_config.update(loaded)
    except Exception:
        pass
        
    return default_config


def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


class OCRApp:
    def __init__(self):
        self.icon = None
        self.config = load_config()
        self.languages = self.config["languages"]
        self.current_lang = self.config["current_lang"]
        self.translate_to = self.config["translate_to"]
        self.translate_from = self.config["translate_from"]
        self.use_baidu_translate = self.config["use_baidu_translate"]
        self.show_magnifier = self.config["show_magnifier"]
        self.auto_translate = self.config["auto_translate"]
        self.tesseract_configured = False
        self.result_window = None
        self.hotkey_manager = None
        self._setup_baidu()
        
    def _setup_baidu(self):
        if self.config.get("baidu_app_key") and self.config.get("baidu_secret_key"):
            set_baidu_config(
                self.config.get("baidu_app_id", ""),
                self.config["baidu_app_key"],
                self.config["baidu_secret_key"]
            )
            self.use_baidu_translate = True
        
    def ensure_tesseract_configured(self):
        if not self.tesseract_configured:
            configure_tesseract()
            self.tesseract_configured = True
            
    def setup_hotkeys(self):
        try:
            self.hotkey_manager = HotkeyManager()
            
            hotkeys = self.config.get("hotkeys", {})
            
            if hotkeys.get("fullscreen"):
                self.hotkey_manager.register(
                    hotkeys["fullscreen"],
                    lambda: threading.Thread(target=self.capture_and_ocr, daemon=True).start()
                )
                
            if hotkeys.get("region"):
                self.hotkey_manager.register(
                    hotkeys["region"],
                    lambda: threading.Thread(target=self.capture_region_ocr, daemon=True).start()
                )
                
            self.hotkey_manager.start()
            return True
        except Exception as e:
            print(f"快捷键注册失败: {e}")
            return False
            
    def stop_hotkeys(self):
        if self.hotkey_manager:
            self.hotkey_manager.stop()
            self.hotkey_manager = None
    
    def show_message(self, title, message):
        def show():
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(title, message)
            root.destroy()
        
        thread = threading.Thread(target=show)
        thread.daemon = True
        thread.start()
    
    def show_error(self, title, message):
        def show():
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(title, message)
            root.destroy()
        
        thread = threading.Thread(target=show)
        thread.daemon = True
        thread.start()
        
    def show_yes_no(self, title, message):
        root = tk.Tk()
        root.withdraw()
        result = messagebox.askyesno(title, message)
        root.destroy()
        return result
    
    def show_result(self, title, text, translated=None, image=None):
        if self.result_window:
            try:
                self.result_window.destroy()
            except:
                pass
        
        def show():
            self.result_window = tk.Tk()
            self.result_window.title(title)
            self.result_window.geometry("700x500")
            
            main_frame = tk.Frame(self.result_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            if translated:
                paned = tk.PanedWindow(main_frame, orient=tk.VERTICAL, sashrelief=tk.RAISED)
                paned.pack(fill=tk.BOTH, expand=True)
                
                original_frame = tk.LabelFrame(paned, text="原文", padx=5, pady=5)
                original_text = scrolledtext.ScrolledText(original_frame, wrap=tk.WORD, font=("Arial", 11))
                original_text.pack(fill=tk.BOTH, expand=True)
                original_text.insert(tk.END, text)
                original_text.config(state=tk.DISABLED)
                paned.add(original_frame, minsize=150)
                
                translated_frame = tk.LabelFrame(paned, text="翻译", padx=5, pady=5)
                translated_text = scrolledtext.ScrolledText(translated_frame, wrap=tk.WORD, font=("Arial", 11))
                translated_text.pack(fill=tk.BOTH, expand=True)
                translated_text.insert(tk.END, translated)
                translated_text.config(state=tk.DISABLED)
                paned.add(translated_frame, minsize=150)
            else:
                text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, font=("Arial", 11))
                text_area.pack(fill=tk.BOTH, expand=True)
                text_area.insert(tk.END, text)
                text_area.config(state=tk.DISABLED)
            
            button_frame = tk.Frame(self.result_window)
            button_frame.pack(fill=tk.X, padx=10, pady=5)
            
            def copy_original():
                try:
                    copy_text(text)
                    self.show_message("成功", "原文已复制到剪贴板！")
                except Exception as e:
                    self.show_error("错误", f"复制失败: {str(e)}")
            
            copy_btn = tk.Button(button_frame, text="复制原文", command=copy_original, width=12)
            copy_btn.pack(side=tk.LEFT, padx=5)
            
            if translated:
                def copy_translated():
                    try:
                        copy_text(translated)
                        self.show_message("成功", "译文已复制到剪贴板！")
                    except Exception as e:
                        self.show_error("错误", f"复制失败: {str(e)}")
                
                copy_trans_btn = tk.Button(button_frame, text="复制译文", command=copy_translated, width=12)
                copy_trans_btn.pack(side=tk.LEFT, padx=5)
                
                def translate_again():
                    try:
                        new_translated = translate_text(
                            text, 
                            from_lang=self.translate_from,
                            to_lang=self.translate_to,
                            use_baidu=self.use_baidu_translate
                        )
                        if new_translated:
                            translated_text.config(state=tk.NORMAL)
                            translated_text.delete('1.0', tk.END)
                            translated_text.insert(tk.END, new_translated)
                            translated_text.config(state=tk.DISABLED)
                    except Exception as e:
                        self.show_error("翻译失败", str(e))
                
                trans_again_btn = tk.Button(button_frame, text="重新翻译", command=translate_again, width=12)
                trans_again_btn.pack(side=tk.LEFT, padx=5)
            
            if image:
                def copy_image_to_clipboard():
                    try:
                        copy_image(image)
                        self.show_message("成功", "图片已复制到剪贴板！")
                    except Exception as e:
                        self.show_error("错误", f"复制失败: {str(e)}")
                
                copy_img_btn = tk.Button(button_frame, text="复制图片", command=copy_image_to_clipboard, width=12)
                copy_img_btn.pack(side=tk.LEFT, padx=5)
            
            close_btn = tk.Button(button_frame, text="关闭", command=self.result_window.destroy, width=10)
            close_btn.pack(side=tk.RIGHT, padx=5)
            
            self.result_window.mainloop()
        
        thread = threading.Thread(target=show)
        thread.daemon = True
        thread.start()
    
    def capture_and_ocr(self, monitor_index=1):
        try:
            save_dir = get_default_save_dir()
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            filename = generate_filename()
            save_path = os.path.join(save_dir, filename)
            
            img, saved = capture_full_screen(monitor_index, save_path)
            
            self.ensure_tesseract_configured()
            
            available, msg = check_training_data(self.current_lang)
            if not available:
                self.show_error("语言包缺失", msg or "请安装对应的 Tesseract 语言包")
                return
            
            text = recognize_text(img, lang=self.current_lang)
            
            if text:
                if self.auto_translate:
                    try:
                        translated = translate_text(
                            text, 
                            from_lang=self.translate_from,
                            to_lang=self.translate_to,
                            use_baidu=self.use_baidu_translate
                        )
                        self.show_result(
                            f"OCR识别结果 ({self.current_lang})", 
                            text, 
                            translated=translated,
                            image=img
                        )
                    except Exception as e:
                        self.show_result(
                            f"OCR识别结果 ({self.current_lang})", 
                            text,
                            image=img
                        )
                        self.show_error("翻译失败", str(e))
                else:
                    self.show_result(
                        f"OCR识别结果 ({self.current_lang})", 
                        text,
                        image=img
                    )
            else:
                self.show_message("提示", "未识别到文字")
        except Exception as e:
            self.show_error("错误", f"操作失败: {str(e)}")
    
    def capture_region_ocr(self):
        try:
            selection = interactive_select_region()
            
            if not selection:
                return
                
            left, top, width, height = selection
            
            save_dir = get_default_save_dir()
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            filename = generate_filename("region")
            save_path = os.path.join(save_dir, filename)
            
            img, saved = capture_region(left, top, width, height, save_path, use_absolute_coords=True)
            
            self.ensure_tesseract_configured()
            
            available, msg = check_training_data(self.current_lang)
            if not available:
                self.show_error("语言包缺失", msg or "请安装对应的 Tesseract 语言包")
                return
            
            text = recognize_text(img, lang=self.current_lang)
            
            if text:
                if self.auto_translate:
                    try:
                        translated = translate_text(
                            text, 
                            from_lang=self.translate_from,
                            to_lang=self.translate_to,
                            use_baidu=self.use_baidu_translate
                        )
                        self.show_result(
                            f"区域OCR识别结果 ({self.current_lang})", 
                            text, 
                            translated=translated,
                            image=img
                        )
                    except Exception as e:
                        self.show_result(
                            f"区域OCR识别结果 ({self.current_lang})", 
                            text,
                            image=img
                        )
                        self.show_error("翻译失败", str(e))
                else:
                    self.show_result(
                        f"区域OCR识别结果 ({self.current_lang})", 
                        text,
                        image=img
                    )
            else:
                self.show_message("提示", "未识别到文字")
        except Exception as e:
            self.show_error("错误", f"操作失败: {str(e)}")
    
    def set_language(self, lang):
        self.current_lang = lang
        self.config["current_lang"] = lang
        save_config(self.config)
        self.show_message("语言设置", f"已设置识别语言: {lang}")
        
    def set_translate_to(self, lang):
        self.translate_to = lang
        self.config["translate_to"] = lang
        save_config(self.config)
        
    def set_translate_from(self, lang):
        self.translate_from = lang
        self.config["translate_from"] = lang
        save_config(self.config)
        
    def toggle_auto_translate(self):
        self.auto_translate = not self.auto_translate
        self.config["auto_translate"] = self.auto_translate
        save_config(self.config)
        status = "已启用" if self.auto_translate else "已禁用"
        self.show_message("自动翻译", f"自动翻译功能{status}")
        
    def toggle_magnifier(self):
        self.show_magnifier = not self.show_magnifier
        self.config["show_magnifier"] = self.show_magnifier
        save_config(self.config)
        status = "已启用" if self.show_magnifier else "已禁用"
        self.show_message("放大镜", f"选区放大镜{status}")
        
    def toggle_baidu_translate(self):
        if self.use_baidu_translate:
            self.use_baidu_translate = False
            self.config["use_baidu_translate"] = False
            save_config(self.config)
            self.show_message("翻译服务", "已切换到免费翻译服务")
        else:
            if is_baidu_configured() or (self.config.get("baidu_app_key") and self.config.get("baidu_secret_key")):
                self.use_baidu_translate = True
                self.config["use_baidu_translate"] = True
                save_config(self.config)
                self.show_message("翻译服务", "已切换到百度翻译")
            else:
                self.show_error("未配置", "请先在设置中配置百度翻译 API")
                
    def configure_baidu_translate(self):
        def show_config_dialog():
            dialog = tk.Tk()
            dialog.title("百度翻译 API 配置")
            dialog.geometry("450x250")
            dialog.resizable(False, False)
            
            tk.Label(dialog, text="APP ID（可选）:").pack(anchor='w', padx=20, pady=(15, 5))
            app_id_entry = tk.Entry(dialog, width=50)
            app_id_entry.pack(padx=20)
            app_id_entry.insert(0, self.config.get("baidu_app_id", ""))
            
            tk.Label(dialog, text="API Key:").pack(anchor='w', padx=20, pady=(10, 5))
            app_key_entry = tk.Entry(dialog, width=50)
            app_key_entry.pack(padx=20)
            app_key_entry.insert(0, self.config.get("baidu_app_key", ""))
            
            tk.Label(dialog, text="Secret Key:").pack(anchor='w', padx=20, pady=(10, 5))
            secret_entry = tk.Entry(dialog, width=50, show='*')
            secret_entry.pack(padx=20)
            secret_entry.insert(0, self.config.get("baidu_secret_key", ""))
            
            def on_save():
                app_id = app_id_entry.get().strip()
                app_key = app_key_entry.get().strip()
                secret = secret_entry.get().strip()
                
                if not app_key or not secret:
                    messagebox.showwarning("提示", "请填写 API Key 和 Secret Key")
                    return
                    
                self.config["baidu_app_id"] = app_id
                self.config["baidu_app_key"] = app_key
                self.config["baidu_secret_key"] = secret
                
                set_baidu_config(app_id, app_key, secret)
                self.use_baidu_translate = True
                self.config["use_baidu_translate"] = True
                
                save_config(self.config)
                messagebox.showinfo("成功", "百度翻译配置已保存")
                dialog.destroy()
                
            def on_test():
                app_id = app_id_entry.get().strip()
                app_key = app_key_entry.get().strip()
                secret = secret_entry.get().strip()
                
                if not app_key or not secret:
                    messagebox.showwarning("提示", "请填写 API Key 和 Secret Key")
                    return
                    
                try:
                    temp_config = {"baidu_app_id": app_id, "baidu_app_key": app_key, "baidu_secret_key": secret}
                    set_baidu_config(app_id, app_key, secret)
                    result = translate_text("Hello", from_lang="en", to_lang="zh", use_baidu=True)
                    messagebox.showinfo("测试成功", f"翻译结果: {result}")
                except Exception as e:
                    messagebox.showerror("测试失败", str(e))
                    
            btn_frame = tk.Frame(dialog)
            btn_frame.pack(pady=20)
            
            tk.Button(btn_frame, text="测试连接", command=on_test, width=10).pack(side=tk.LEFT, padx=10)
            tk.Button(btn_frame, text="保存", command=on_save, width=10).pack(side=tk.LEFT, padx=10)
            tk.Button(btn_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=10)
            
            dialog.mainloop()
            
        threading.Thread(target=show_config_dialog, daemon=True).start()
    
    def show_help(self):
        help_text = """截图OCR工具使用说明:

【功能介绍】
1. 全屏截图OCR: 识别当前屏幕的所有文字
2. 区域截图OCR: 拖动鼠标选择区域进行识别
   • 选择时鼠标附近会显示放大镜
   • 绿色虚线框显示选择区域
   • 按 ESC 取消选择
3. 自动翻译: 识别后自动翻译到目标语言
4. 全局快捷键:
   • Ctrl+Alt+A: 全屏截图OCR
   • Ctrl+Alt+S: 区域截图OCR

【语言包安装】
- 中文简体: tesseract-ocr-chi-sim
- 中文繁体: tesseract-ocr-chi-tra
- 英文: 默认自带
- 日文: tesseract-ocr-jpn
- 韩文: tesseract-ocr-kor

【百度翻译配置】
1. 访问 https://fanyi-api.baidu.com/
2. 注册开发者账号
3. 创建应用获取 API Key 和 Secret Key
4. 在设置中填入配置信息

【默认保存位置】
- Windows: 图片\\Screenshots
- Mac: 桌面
- Linux: 图片文件夹
"""
        self.show_message("使用说明", help_text)
    
    def on_exit(self, icon, item):
        self.stop_hotkeys()
        if self.result_window:
            try:
                self.result_window.destroy()
            except:
                pass
        icon.stop()
    
    def create_menu(self):
        monitors = list_monitors()
        monitor_items = []
        
        if len(monitors) > 1:
            for i in range(1, len(monitors)):
                mon = monitors[i]
                monitor_items.append(
                    pystray.MenuItem(
                        f"显示器 {i}: {mon['width']}x{mon['height']}",
                        lambda checked, idx=i: threading.Thread(
                            target=self.capture_and_ocr, 
                            args=(idx,),
                            daemon=True
                        ).start()
                    )
                )
        
        lang_items = [
            pystray.MenuItem(
                lang,
                lambda checked, l=lang: self.set_language(l),
                checked=lambda item, l=lang: self.current_lang == l
            )
            for lang in self.languages
        ]
        
        translate_to_items = [
            pystray.MenuItem("中文", lambda: self.set_translate_to("zh"), checked=lambda item: self.translate_to == "zh"),
            pystray.MenuItem("英文", lambda: self.set_translate_to("en"), checked=lambda item: self.translate_to == "en"),
            pystray.MenuItem("日文", lambda: self.set_translate_to("jp"), checked=lambda item: self.translate_to == "jp"),
            pystray.MenuItem("韩文", lambda: self.set_translate_to("kor"), checked=lambda item: self.translate_to == "kor"),
        ]
        
        translate_from_items = [
            pystray.MenuItem("自动检测", lambda: self.set_translate_from("auto"), checked=lambda item: self.translate_from == "auto"),
            pystray.MenuItem("中文", lambda: self.set_translate_from("zh"), checked=lambda item: self.translate_from == "zh"),
            pystray.MenuItem("英文", lambda: self.set_translate_from("en"), checked=lambda item: self.translate_from == "en"),
            pystray.MenuItem("日文", lambda: self.set_translate_from("jp"), checked=lambda item: self.translate_from == "jp"),
        ]
        
        menu = pystray.Menu(
            pystray.MenuItem("全屏截图OCR", lambda: threading.Thread(
                target=self.capture_and_ocr,
                daemon=True
            ).start()),
            pystray.MenuItem("区域截图OCR", lambda: threading.Thread(
                target=self.capture_region_ocr,
                daemon=True
            ).start()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "选择显示器",
                pystray.Menu(*monitor_items)
            ) if monitor_items else pystray.MenuItem("单显示器", None, enabled=False),
            pystray.MenuItem(
                "识别语言",
                pystray.Menu(*lang_items)
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "自动翻译",
                self.toggle_auto_translate,
                checked=lambda item: self.auto_translate
            ),
            pystray.MenuItem(
                "翻译目标语言",
                pystray.Menu(*translate_to_items)
            ),
            pystray.MenuItem(
                "翻译源语言",
                pystray.Menu(*translate_from_items)
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "使用百度翻译",
                self.toggle_baidu_translate,
                checked=lambda item: self.use_baidu_translate
            ),
            pystray.MenuItem(
                "配置百度翻译",
                lambda: threading.Thread(target=self.configure_baidu_translate, daemon=True).start()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "选区放大镜",
                self.toggle_magnifier,
                checked=lambda item: self.show_magnifier
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("使用说明", self.show_help),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self.on_exit)
        )
        
        return menu
    
    def run(self):
        backend = setup_tray_backend()
        
        self.setup_hotkeys()
        
        try:
            self.icon = pystray.Icon(
                "ocr_screenshot",
                create_tray_icon(),
                "截图OCR工具",
                self.create_menu()
            )
            
            self.icon.run()
        except Exception as e:
            if platform.system() == "Linux":
                print(f"托盘图标初始化失败，尝试备用方案。错误: {e}")
                print("提示: 请确保安装了 libappindicator 或 gtk3")
            self.stop_hotkeys()
            raise


def main():
    try:
        app = OCRApp()
        app.run()
    except KeyboardInterrupt:
        print("\n程序已退出")
    except Exception as e:
        print(f"程序运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
