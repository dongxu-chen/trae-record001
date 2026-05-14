import threading
import platform
import time


class HotkeyManager:
    def __init__(self):
        self.hotkeys = {}
        self.listener = None
        self.is_running = False
        self.system = platform.system()
        
    def register(self, hotkey, callback):
        self.hotkeys[hotkey.lower()] = callback
        
    def unregister(self, hotkey):
        if hotkey.lower() in self.hotkeys:
            del self.hotkeys[hotkey.lower()]
            
    def clear(self):
        self.hotkeys.clear()
        
    def start(self):
        if self.is_running:
            return
            
        self.is_running = True
        
        if self.system == "Windows":
            self._start_windows()
        elif self.system == "Darwin":
            self._start_mac()
        else:
            self._start_linux()
            
    def stop(self):
        if not self.is_running:
            return
            
        self.is_running = False
        
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None
            
    def _start_windows(self):
        try:
            from pynput import keyboard
            
            current_keys = set()
            
            def parse_hotkey(hotkey):
                parts = hotkey.lower().split('+')
                key_set = set()
                for part in parts:
                    part = part.strip()
                    if part == 'ctrl':
                        key_set.add(keyboard.Key.ctrl_l)
                        key_set.add(keyboard.Key.ctrl_r)
                    elif part == 'alt':
                        key_set.add(keyboard.Key.alt_l)
                        key_set.add(keyboard.Key.alt_r)
                    elif part == 'shift':
                        key_set.add(keyboard.Key.shift_l)
                        key_set.add(keyboard.Key.shift_r)
                    elif part == 'win' or part == 'cmd' or part == 'super':
                        key_set.add(keyboard.Key.cmd_l)
                        key_set.add(keyboard.Key.cmd_r)
                    else:
                        try:
                            key_set.add(keyboard.KeyCode.from_char(part))
                        except Exception:
                            try:
                                key_set.add(getattr(keyboard.Key, part, part))
                            except Exception:
                                pass
                return key_set
            
            parsed_hotkeys = {}
            for hotkey, callback in self.hotkeys.items():
                parsed_hotkeys[hotkey] = (parse_hotkey(hotkey), callback)
            
            def on_press(key):
                current_keys.add(key)
                
                for hotkey, (required_keys, callback) in parsed_hotkeys.items():
                    matched_modifiers = all(
                        any(k in current_keys for k in required_keys if hasattr(k, 'name') and 'key.' in str(k).lower()) or
                        k in current_keys
                        for k in required_keys
                    )
                    
                    has_modifier = any(
                        k in current_keys
                        for k in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                                 keyboard.Key.alt_l, keyboard.Key.alt_r,
                                 keyboard.Key.shift_l, keyboard.Key.shift_r,
                                 keyboard.Key.cmd_l, keyboard.Key.cmd_r]
                    )
                    
                    if has_modifier:
                        for required_key in required_keys:
                            if str(key).lower() == str(required_key).lower():
                                try:
                                    threading.Thread(target=callback, daemon=True).start()
                                except Exception:
                                    pass
                                break
            
            def on_release(key):
                if key in current_keys:
                    current_keys.remove(key)
            
            self.listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release
            )
            self.listener.start()
            
        except ImportError:
            print("请安装 pynput: pip install pynput")
        except Exception as e:
            print(f"Windows 快捷键注册失败: {e}")
            
    def _start_mac(self):
        try:
            from pynput import keyboard
            
            current_keys = set()
            
            def on_press(key):
                current_keys.add(key)
                
                for hotkey, callback in self.hotkeys.items():
                    parts = hotkey.lower().split('+')
                    if 'ctrl' in parts:
                        if not any(k in current_keys for k in [keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r]):
                            continue
                    if 'cmd' in parts:
                        if not any(k in current_keys for k in [keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r]):
                            continue
                    if 'alt' in parts:
                        if not any(k in current_keys for k in [keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r]):
                            continue
                    if 'shift' in parts:
                        if not any(k in current_keys for k in [keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r]):
                            continue
                    
                    try:
                        threading.Thread(target=callback, daemon=True).start()
                    except Exception:
                        pass
            
            def on_release(key):
                if key in current_keys:
                    current_keys.remove(key)
            
            self.listener = keyboard.GlobalHotKeys(self.hotkeys)
            self.listener.start()
            
        except ImportError:
            print("请安装 pynput: pip install pynput")
        except Exception as e:
            print(f"Mac 快捷键注册失败: {e}")
            
    def _start_linux(self):
        try:
            from pynput import keyboard
            
            self.listener = keyboard.GlobalHotKeys(self.hotkeys)
            self.listener.start()
            
        except ImportError:
            print("请安装 pynput: pip install pynput")
        except Exception as e:
            print(f"Linux 快捷键注册失败: {e}")


_default_manager = None


def get_manager():
    global _default_manager
    if _default_manager is None:
        _default_manager = HotkeyManager()
    return _default_manager


def register_hotkey(hotkey, callback):
    manager = get_manager()
    manager.register(hotkey, callback)


def unregister_hotkey(hotkey):
    manager = get_manager()
    manager.unregister(hotkey)


def start_hotkeys():
    manager = get_manager()
    manager.start()


def stop_hotkeys():
    manager = get_manager()
    manager.stop()


if __name__ == "__main__":
    import sys
    
    def on_fullscreen():
        print("全屏截图快捷键触发")
        
    def on_region():
        print("区域截图快捷键触发")
        
    def on_quit():
        print("退出")
        stop_hotkeys()
        sys.exit(0)
    
    register_hotkey('<ctrl>+<alt>+a', on_fullscreen)
    register_hotkey('<ctrl>+<alt>+s', on_region)
    register_hotkey('<ctrl>+<alt>+q', on_quit)
    
    print("快捷键监听中:")
    print("  Ctrl+Alt+A: 全屏截图")
    print("  Ctrl+Alt+S: 区域截图")
    print("  Ctrl+Alt+Q: 退出")
    
    start_hotkeys()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop_hotkeys()
