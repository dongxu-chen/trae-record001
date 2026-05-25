import sys
import time
import threading
from typing import Optional, Callable, List, Dict, Tuple
from collections import deque
from datetime import datetime

from config import config


class MultiMonitorDetector:
    def __init__(self):
        self._monitor_count = 1
        self._monitor_info: List[Dict[str, Any]] = []
        self._last_monitor_count = 1
        self._monitor_change_events: List[Dict[str, Any]] = []
        self._on_monitor_change_callback: Optional[Callable[[int, int], None]] = None
    
    def set_on_monitor_change_callback(self, callback: Callable[[int, int], None]) -> None:
        self._on_monitor_change_callback = callback
    
    def _detect_monitors_windows(self) -> Tuple[int, List[Dict[str, Any]]]:
        try:
            import win32api
            monitors = win32api.EnumDisplayMonitors()
            monitor_info = []
            
            for i, (hMonitor, hdcMonitor, lprcMonitor) in enumerate(monitors):
                left, top, right, bottom = lprcMonitor
                width = right - left
                height = bottom - top
                
                info = {
                    'monitor_id': i,
                    'left': left,
                    'top': top,
                    'right': right,
                    'bottom': bottom,
                    'width': width,
                    'height': height,
                    'is_primary': i == 0
                }
                monitor_info.append(info)
            
            return len(monitors), monitor_info
            
        except ImportError:
            print("pywin32 not installed for monitor detection")
            return 1, []
        except Exception as e:
            print(f"Error detecting monitors (Windows): {e}")
            return 1, []
    
    def _detect_monitors_linux(self) -> Tuple[int, List[Dict[str, Any]]]:
        try:
            import subprocess
            result = subprocess.run(
                ['xrandr', '--query'],
                capture_output=True, text=True
            )
            
            monitor_info = []
            for line in result.stdout.split('\n'):
                if ' connected' in line:
                    parts = line.split()
                    name = parts[0]
                    
                    for i, part in enumerate(parts):
                        if 'x' in part and '+' in part:
                            try:
                                size_pos = part.split('+')
                                width, height = size_pos[0].split('x')
                                pos_x, pos_y = int(size_pos[1]), int(size_pos[2])
                                
                                info = {
                                    'monitor_id': len(monitor_info),
                                    'name': name,
                                    'left': pos_x,
                                    'top': pos_y,
                                    'right': pos_x + int(width),
                                    'bottom': pos_y + int(height),
                                    'width': int(width),
                                    'height': int(height),
                                    'is_primary': 'primary' in line
                                }
                                monitor_info.append(info)
                            except:
                                pass
            
            return max(1, len(monitor_info)), monitor_info
            
        except Exception as e:
            print(f"Error detecting monitors (Linux): {e}")
            return 1, []
    
    def _detect_monitors_macos(self) -> Tuple[int, List[Dict[str, Any]]]:
        try:
            import subprocess
            script = '''
            tell application "System Events"
                set displayInfo to {}
                repeat with d in displays
                    set dBounds to bounds of d
                    set end of displayInfo to dBounds
                end repeat
                return displayInfo
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True
            )
            
            monitor_info = []
            output = result.stdout.strip()
            if output:
                bounds_list = output.split(', ')
                for i in range(0, len(bounds_list), 4):
                    if i + 3 < len(bounds_list):
                        try:
                            left = int(bounds_list[i])
                            top = int(bounds_list[i+1])
                            right = int(bounds_list[i+2])
                            bottom = int(bounds_list[i+3])
                            
                            info = {
                                'monitor_id': len(monitor_info),
                                'left': left,
                                'top': top,
                                'right': right,
                                'bottom': bottom,
                                'width': right - left,
                                'height': bottom - top,
                                'is_primary': len(monitor_info) == 0
                            }
                            monitor_info.append(info)
                        except:
                            pass
            
            return max(1, len(monitor_info)), monitor_info
            
        except Exception as e:
            print(f"Error detecting monitors (macOS): {e}")
            return 1, []
    
    def detect_monitors(self) -> Tuple[int, List[Dict[str, Any]]]:
        platform = sys.platform
        if platform.startswith('win'):
            return self._detect_monitors_windows()
        elif platform.startswith('linux'):
            return self._detect_monitors_linux()
        elif platform == 'darwin':
            return self._detect_monitors_macos()
        else:
            return 1, []
    
    def check_monitor_change(self) -> Optional[Dict[str, Any]]:
        monitor_count, monitor_info = self.detect_monitors()
        
        if monitor_count != self._last_monitor_count:
            event = {
                'timestamp': datetime.now().isoformat(),
                'old_count': self._last_monitor_count,
                'new_count': monitor_count,
                'monitors': monitor_info,
                'message': f"显示器数量从 {self._last_monitor_count} 变为 {monitor_count}"
            }
            
            self._monitor_change_events.append(event)
            
            if self._on_monitor_change_callback is not None:
                try:
                    self._on_monitor_change_callback(self._last_monitor_count, monitor_count)
                except Exception as e:
                    print(f"Error in monitor change callback: {e}")
            
            self._last_monitor_count = monitor_count
            self._monitor_info = monitor_info
            
            return event
        
        self._monitor_info = monitor_info
        return None
    
    def get_active_window_monitor(self, window_title: Optional[str] = None) -> Optional[int]:
        if len(self._monitor_info) <= 1:
            return 0
        
        try:
            if sys.platform.startswith('win'):
                import win32gui
                import win32api
                
                hwnd = win32gui.GetForegroundWindow()
                if hwnd == 0:
                    return None
                
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                center_x = (left + right) // 2
                center_y = (top + bottom) // 2
                
                for i, monitor in enumerate(self._monitor_info):
                    if (monitor['left'] <= center_x <= monitor['right'] and
                        monitor['top'] <= center_y <= monitor['bottom']):
                        return i
            
            return 0
        except Exception as e:
            print(f"Error getting active window monitor: {e}")
            return 0
    
    def is_window_on_secondary_monitor(self) -> Tuple[bool, int]:
        monitor_id = self.get_active_window_monitor()
        if monitor_id is not None and monitor_id > 0:
            return True, monitor_id
        return False, monitor_id or 0
    
    def get_monitor_info(self) -> List[Dict[str, Any]]:
        return self._monitor_info.copy()
    
    def get_monitor_count(self) -> int:
        return self._last_monitor_count
    
    def get_monitor_change_events(self) -> List[Dict[str, Any]]:
        return self._monitor_change_events.copy()
    
    def clear_events(self) -> None:
        self._monitor_change_events.clear()


class FullscreenDetector:
    def __init__(self):
        self._is_fullscreen = False
        self._fullscreen_start_time: Optional[float] = None
        self._fullscreen_history: List[Dict[str, Any]] = []
        self._on_fullscreen_callback: Optional[Callable[[bool], None]] = None
    
    def set_on_fullscreen_callback(self, callback: Callable[[bool], None]) -> None:
        self._on_fullscreen_callback = callback
    
    def _is_fullscreen_windows(self) -> Tuple[bool, Optional[str]]:
        try:
            import win32gui
            import win32con
            
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return False, None
            
            title = win32gui.GetWindowText(hwnd)
            
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMAXIMIZED:
                return True, title
            
            screen_width = win32api.GetSystemMetrics(0)
            screen_height = win32api.GetSystemMetrics(1)
            
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            if width >= screen_width * 0.95 and height >= screen_height * 0.95:
                return True, title
            
            return False, title
            
        except ImportError:
            return False, None
        except Exception as e:
            print(f"Error detecting fullscreen (Windows): {e}")
            return False, None
    
    def _is_fullscreen_linux(self) -> Tuple[bool, Optional[str]]:
        try:
            import subprocess
            
            result = subprocess.run(
                ['xdotool', 'getactivewindow', 'getwindowname'],
                capture_output=True, text=True
            )
            title = result.stdout.strip() if result.stdout else None
            
            result = subprocess.run(
                ['xprop', '-id', subprocess.check_output(['xdotool', 'getactivewindow']).decode().strip(),
                 '_NET_WM_STATE'],
                capture_output=True, text=True
            )
            
            if '_NET_WM_STATE_FULLSCREEN' in result.stdout or '_NET_WM_STATE_MAXIMIZED' in result.stdout:
                return True, title
            
            return False, title
            
        except Exception as e:
            print(f"Error detecting fullscreen (Linux): {e}")
            return False, None
    
    def _is_fullscreen_macos(self) -> Tuple[bool, Optional[str]]:
        try:
            import subprocess
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set frontWindow to first window of frontApp
                set isFullscreen to value of attribute "AXFullScreen" of frontWindow
                set windowName to name of frontWindow
                return {isFullscreen, windowName}
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True
            )
            
            output = result.stdout.strip()
            if output:
                parts = output.split(', ', 1)
                is_fullscreen = parts[0].lower() == 'true'
                title = parts[1] if len(parts) > 1 else None
                return is_fullscreen, title
            
            return False, None
            
        except Exception as e:
            print(f"Error detecting fullscreen (macOS): {e}")
            return False, None
    
    def check_fullscreen(self) -> Tuple[bool, Optional[str], float]:
        platform = sys.platform
        if platform.startswith('win'):
            is_full, title = self._is_fullscreen_windows()
        elif platform.startswith('linux'):
            is_full, title = self._is_fullscreen_linux()
        elif platform == 'darwin':
            is_full, title = self._is_fullscreen_macos()
        else:
            is_full, title = False, None
        
        duration = 0.0
        if is_full != self._is_fullscreen:
            if is_full:
                self._fullscreen_start_time = time.time()
                event = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'fullscreen_start',
                    'window_title': title
                }
                self._fullscreen_history.append(event)
            else:
                if self._fullscreen_start_time:
                    duration = time.time() - self._fullscreen_start_time
                event = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'fullscreen_end',
                    'window_title': title,
                    'duration_seconds': duration
                }
                self._fullscreen_history.append(event)
                self._fullscreen_start_time = None
            
            self._is_fullscreen = is_full
            
            if self._on_fullscreen_callback is not None:
                try:
                    self._on_fullscreen_callback(is_full)
                except Exception as e:
                    print(f"Error in fullscreen callback: {e}")
        
        if is_full and self._fullscreen_start_time:
            duration = time.time() - self._fullscreen_start_time
        
        return is_full, title, duration
    
    def is_fullscreen(self) -> bool:
        return self._is_fullscreen
    
    def get_fullscreen_duration(self) -> float:
        if self._is_fullscreen and self._fullscreen_start_time:
            return time.time() - self._fullscreen_start_time
        return 0.0
    
    def get_fullscreen_history(self) -> List[Dict[str, Any]]:
        return self._fullscreen_history.copy()
    
    def get_fullscreen_count(self) -> int:
        return len([e for e in self._fullscreen_history if e['type'] == 'fullscreen_start'])
    
    def get_total_fullscreen_time(self) -> float:
        total = 0.0
        for e in self._fullscreen_history:
            if e['type'] == 'fullscreen_end' and 'duration_seconds' in e:
                total += e['duration_seconds']
        if self._is_fullscreen and self._fullscreen_start_time:
            total += time.time() - self._fullscreen_start_time
        return total
    
    def clear_history(self) -> None:
        self._fullscreen_history.clear()
        self._fullscreen_start_time = None
        self._is_fullscreen = False


class TabSwitchDetector:
    def __init__(self):
        self._is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self._current_window: Optional[str] = None
        self._last_window: Optional[str] = None
        self._switch_count = 0
        self._switch_history: deque = deque(maxlen=100)
        self._switch_timestamps: deque = deque(maxlen=config.TAB_SWITCH_WINDOW)
        
        self._allowed_windows: List[str] = []
        self._exam_window_title: Optional[str] = None
        
        self._on_switch_callback: Optional[Callable[[str, str, str], None]] = None
        self._on_suspicious_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        
        self._suspicious_events: List[Dict] = []
        self._platform = sys.platform
        
        self._fullscreen_detector = FullscreenDetector()
        self._monitor_detector = MultiMonitorDetector()
        
        self._on_fullscreen_callback: Optional[Callable[[bool, str, float], None]] = None
        self._on_monitor_change_callback: Optional[Callable[[int, int], None]] = None
        
        self._setup_callbacks()
    
    def _setup_callbacks(self) -> None:
        self._fullscreen_detector.set_on_fullscreen_callback(self._on_fullscreen)
        self._monitor_detector.set_on_monitor_change_callback(self._on_monitor_change)
    
    def set_allowed_windows(self, windows: List[str]) -> None:
        self._allowed_windows = windows
    
    def set_exam_window_title(self, title: str) -> None:
        self._exam_window_title = title
        if title not in self._allowed_windows:
            self._allowed_windows.append(title)
    
    def set_on_switch_callback(self, callback: Callable[[str, str, str], None]) -> None:
        self._on_switch_callback = callback
    
    def set_on_suspicious_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        self._on_suspicious_callback = callback
    
    def set_on_fullscreen_callback(self, callback: Callable[[bool, str, float], None]) -> None:
        self._on_fullscreen_callback = callback
    
    def set_on_monitor_change_callback(self, callback: Callable[[int, int], None]) -> None:
        self._on_monitor_change_callback = callback
    
    def _on_fullscreen(self, is_fullscreen: bool) -> None:
        if not self._is_monitoring:
            return
        
        if is_fullscreen:
            current_window = self._get_active_window_title()
            if not self._is_window_allowed(current_window):
                event = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'suspicious_fullscreen',
                    'window_title': current_window,
                    'message': f'非允许窗口进入全屏: {current_window}'
                }
                self._suspicious_events.append(event)
                
                if self._on_suspicious_callback is not None:
                    try:
                        self._on_suspicious_callback('suspicious_fullscreen', event)
                    except Exception as e:
                        print(f"Error in suspicious callback: {e}")
        
        if self._on_fullscreen_callback is not None:
            is_full, title, duration = self._fullscreen_detector.check_fullscreen()
            try:
                self._on_fullscreen_callback(is_full, title or '', duration)
            except Exception as e:
                print(f"Error in fullscreen callback: {e}")
    
    def _on_monitor_change(self, old_count: int, new_count: int) -> None:
        if not self._is_monitoring:
            return
        
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': 'monitor_change',
            'old_count': old_count,
            'new_count': new_count,
            'message': f'显示器数量变化: {old_count} -> {new_count}'
        }
        self._suspicious_events.append(event)
        
        if self._on_suspicious_callback is not None:
            try:
                self._on_suspicious_callback('monitor_change', event)
            except Exception as e:
                print(f"Error in suspicious callback: {e}")
        
        if self._on_monitor_change_callback is not None:
            try:
                self._on_monitor_change_callback(old_count, new_count)
            except Exception as e:
                print(f"Error in monitor change callback: {e}")
    
    def _get_active_window_title_windows(self) -> Optional[str]:
        try:
            import win32gui
            import win32process
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return None
            title = win32gui.GetWindowText(hwnd)
            return title
        except ImportError:
            print("pywin32 not installed, cannot detect window on Windows")
            return None
        except Exception as e:
            print(f"Error getting active window (Windows): {e}")
            return None
    
    def _get_active_window_title_linux(self) -> Optional[str]:
        try:
            import subprocess
            result = subprocess.run(
                ['xdotool', 'getactivewindow', 'getwindowname'],
                capture_output=True, text=True
            )
            return result.stdout.strip() if result.stdout else None
        except Exception as e:
            print(f"Error getting active window (Linux): {e}")
            return None
    
    def _get_active_window_title_macos(self) -> Optional[str]:
        try:
            import subprocess
            script = '''
            tell application "System Events"
                get name of first application process whose frontmost is true
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True
            )
            return result.stdout.strip() if result.stdout else None
        except Exception as e:
            print(f"Error getting active window (macOS): {e}")
            return None
    
    def _get_active_window_title(self) -> Optional[str]:
        if self._platform.startswith('win'):
            return self._get_active_window_title_windows()
        elif self._platform.startswith('linux'):
            return self._get_active_window_title_linux()
        elif self._platform == 'darwin':
            return self._get_active_window_title_macos()
        else:
            return None
    
    def _is_window_allowed(self, window_title: str) -> bool:
        if not window_title:
            return False
        
        for allowed in self._allowed_windows:
            if allowed.lower() in window_title.lower():
                return True
        
        return False
    
    def _check_recent_switches(self) -> Tuple[int, float]:
        now = time.time()
        recent_switches = [
            ts for ts in self._switch_timestamps
            if now - ts <= config.TAB_SWITCH_WINDOW
        ]
        return len(recent_switches), config.TAB_SWITCH_WINDOW
    
    def _monitor_loop(self, check_interval: float = 0.5) -> None:
        self._monitor_detector.detect_monitors()
        
        while not self._stop_event.is_set():
            current_window = self._get_active_window_title()
            
            if current_window != self._current_window:
                previous_window = self._current_window
                self._current_window = current_window
                
                if previous_window is not None and current_window is not None:
                    self._switch_count += 1
                    self._switch_timestamps.append(time.time())
                    self._switch_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'from': previous_window,
                        'to': current_window
                    })
                    
                    if self._on_switch_callback is not None:
                        try:
                            self._on_switch_callback(previous_window, current_window, '')
                        except Exception as e:
                            print(f"Error in switch callback: {e}")
                    
                    if not self._is_window_allowed(current_window):
                        event = {
                            'timestamp': datetime.now().isoformat(),
                            'type': 'suspicious_window',
                            'window_title': current_window,
                            'message': f'切换到非允许窗口: {current_window}'
                        }
                        self._suspicious_events.append(event)
                        
                        if self._on_suspicious_callback is not None:
                            try:
                                self._on_suspicious_callback('suspicious_window', event)
                            except Exception as e:
                                print(f"Error in suspicious callback: {e}")
                    
                    recent_count, window_size = self._check_recent_switches()
                    if recent_count >= config.TAB_SWITCH_THRESHOLD:
                        if self._on_suspicious_callback is not None:
                            try:
                                event = {
                                    'timestamp': datetime.now().isoformat(),
                                    'type': 'excessive_switching',
                                    'switch_count': recent_count,
                                    'window_seconds': window_size,
                                    'message': f'在{window_size}秒内切换窗口{recent_count}次'
                                }
                                self._on_suspicious_callback('excessive_switching', event)
                            except Exception as e:
                                print(f"Error in suspicious callback: {e}")
                        
                        event = {
                            'timestamp': datetime.now().isoformat(),
                            'type': 'excessive_switching',
                            'switch_count': recent_count,
                            'window_seconds': window_size,
                            'message': f'在{window_size}秒内切换窗口{recent_count}次'
                        }
                        self._suspicious_events.append(event)
            
            if config.ENABLE_FULLSCREEN_DETECTION:
                is_full, title, duration = self._fullscreen_detector.check_fullscreen()
                if is_full and not self._is_window_allowed(title):
                    event = {
                        'timestamp': datetime.now().isoformat(),
                        'type': 'suspicious_fullscreen_active',
                        'window_title': title,
                        'duration_seconds': duration,
                        'message': f'非允许窗口全屏: {title}, 持续 {duration:.1f} 秒'
                    }
                    self._suspicious_events.append(event)
            
            if config.ENABLE_MULTI_MONITOR_DETECTION:
                monitor_event = self._monitor_detector.check_monitor_change()
                if monitor_event:
                    pass
                
                is_secondary, monitor_id = self._monitor_detector.is_window_on_secondary_monitor()
                if is_secondary:
                    event = {
                        'timestamp': datetime.now().isoformat(),
                        'type': 'secondary_monitor',
                        'monitor_id': monitor_id,
                        'window_title': current_window,
                        'message': f'窗口在副显示器 #{monitor_id} 上'
                    }
                    self._suspicious_events.append(event)
            
            time.sleep(check_interval)
    
    def start(self, check_interval: float = 0.5) -> bool:
        if self._is_monitoring:
            return False
        
        self._stop_event.clear()
        self._is_monitoring = True
        self._current_window = self._get_active_window_title()
        
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(check_interval,), daemon=True
        )
        self._monitor_thread.start()
        
        print(f"Started tab switch detection. Current window: {self._current_window}")
        print(f"Fullscreen detection: {'ENABLED' if config.ENABLE_FULLSCREEN_DETECTION else 'DISABLED'}")
        print(f"Multi-monitor detection: {'ENABLED' if config.ENABLE_MULTI_MONITOR_DETECTION else 'DISABLED'}")
        return True
    
    def stop(self) -> None:
        if not self._is_monitoring:
            return
        
        self._stop_event.set()
        
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=3.0)
        
        self._is_monitoring = False
        print("Stopped tab switch detection")
    
    def get_current_window(self) -> Optional[str]:
        return self._current_window
    
    def get_switch_count(self) -> int:
        return self._switch_count
    
    def get_switch_history(self) -> List[Dict]:
        return list(self._switch_history)
    
    def get_suspicious_events(self) -> List[Dict]:
        return self._suspicious_events.copy()
    
    def clear_suspicious_events(self) -> None:
        self._suspicious_events.clear()
    
    def is_current_window_allowed(self) -> bool:
        current = self._get_active_window_title()
        return self._is_window_allowed(current) if current else False
    
    def is_fullscreen(self) -> bool:
        return self._fullscreen_detector.is_fullscreen()
    
    def get_fullscreen_info(self) -> Dict[str, Any]:
        is_full, title, duration = self._fullscreen_detector.check_fullscreen()
        return {
            'is_fullscreen': is_full,
            'window_title': title,
            'duration_seconds': duration,
            'total_fullscreen_seconds': self._fullscreen_detector.get_total_fullscreen_time(),
            'fullscreen_count': self._fullscreen_detector.get_fullscreen_count()
        }
    
    def get_monitor_info(self) -> Dict[str, Any]:
        monitor_count, monitor_info = self._monitor_detector.detect_monitors()
        is_secondary, active_monitor = self._monitor_detector.is_window_on_secondary_monitor()
        
        return {
            'monitor_count': monitor_count,
            'monitors': monitor_info,
            'active_monitor_id': active_monitor,
            'is_on_secondary_monitor': is_secondary,
            'monitor_change_events': self._monitor_detector.get_monitor_change_events()
        }
    
    def get_stats(self) -> Dict:
        recent_count, window_size = self._check_recent_switches()
        fullscreen_info = self.get_fullscreen_info()
        monitor_info = self.get_monitor_info()
        
        return {
            'total_switches': self._switch_count,
            'current_window': self._current_window,
            'is_current_allowed': self.is_current_window_allowed(),
            'recent_switches': recent_count,
            'recent_window_seconds': window_size,
            'suspicious_events_count': len(self._suspicious_events),
            'is_monitoring': self._is_monitoring,
            'fullscreen': fullscreen_info,
            'monitor': monitor_info,
            'features': {
                'fullscreen_detection': config.ENABLE_FULLSCREEN_DETECTION,
                'multi_monitor_detection': config.ENABLE_MULTI_MONITOR_DETECTION
            }
        }


class BrowserTabDetector:
    def __init__(self):
        self._tab_visibility_events: List[Dict] = []
        self._blur_events: List[Dict] = []
        self._focus_events: List[Dict] = []
        self._last_blur_time: Optional[float] = None
        self._total_background_time = 0.0
        
        self._on_visibility_change_callback: Optional[Callable[[bool, float], None]] = None
        self._on_suspicious_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    
    def set_on_visibility_change_callback(self, callback: Callable[[bool, float], None]) -> None:
        self._on_visibility_change_callback = callback
    
    def set_on_suspicious_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        self._on_suspicious_callback = callback
    
    def on_visibility_change(self, is_visible: bool) -> None:
        duration = 0.0
        event = {
            'timestamp': datetime.now().isoformat(),
            'is_visible': is_visible
        }
        self._tab_visibility_events.append(event)
        
        if not is_visible:
            self._last_blur_time = time.time()
            blur_event = {
                'timestamp': datetime.now().isoformat(),
                'type': 'tab_hidden'
            }
            self._blur_events.append(blur_event)
            
            suspicious_event = {
                'timestamp': datetime.now().isoformat(),
                'type': 'tab_hidden',
                'message': '考试页面被隐藏'
            }
            
            if self._on_suspicious_callback is not None:
                try:
                    self._on_suspicious_callback('tab_hidden', suspicious_event)
                except Exception as e:
                    print(f"Error in suspicious callback: {e}")
        else:
            if self._last_blur_time is not None:
                duration = time.time() - self._last_blur_time
                self._total_background_time += duration
                self._last_blur_time = None
            
            focus_event = {
                'timestamp': datetime.now().isoformat(),
                'type': 'tab_shown',
                'background_duration_seconds': duration
            }
            self._focus_events.append(focus_event)
        
        if self._on_visibility_change_callback is not None:
            try:
                self._on_visibility_change_callback(is_visible, duration)
            except Exception as e:
                print(f"Error in visibility callback: {e}")
    
    def on_blur(self) -> None:
        self.on_visibility_change(False)
    
    def on_focus(self) -> None:
        self.on_visibility_change(True)
    
    def get_background_events_count(self) -> int:
        return len(self._blur_events)
    
    def get_total_background_time(self) -> float:
        if self._last_blur_time is not None:
            return self._total_background_time + (time.time() - self._last_blur_time)
        return self._total_background_time
    
    def get_stats(self) -> Dict:
        return {
            'background_events': len(self._blur_events),
            'total_background_seconds': self.get_total_background_time(),
            'is_visible_now': self._last_blur_time is None,
            'visibility_events_count': len(self._tab_visibility_events)
        }
    
    def get_all_events(self) -> List[Dict]:
        all_events = []
        all_events.extend(self._blur_events)
        all_events.extend(self._focus_events)
        all_events.sort(key=lambda x: x['timestamp'])
        return all_events
