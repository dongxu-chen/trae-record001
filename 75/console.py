import imgui
import datetime
import threading
from typing import List, Dict
from collections import deque

MAX_LOGS = 2000
MAX_RENDER_LOGS = 500


class LogLevel:
    INFO = 0
    WARNING = 1
    ERROR = 2
    DEBUG = 3

    LEVEL_NAMES = {
        INFO: "信息",
        WARNING: "警告",
        ERROR: "错误",
        DEBUG: "调试"
    }

    LEVEL_COLORS = {
        INFO: (0.8, 0.8, 0.8, 1.0),
        WARNING: (1.0, 0.8, 0.2, 1.0),
        ERROR: (1.0, 0.3, 0.3, 1.0),
        DEBUG: (0.4, 0.7, 1.0, 1.0)
    }

    @classmethod
    def get_name(cls, level: int) -> str:
        return cls.LEVEL_NAMES.get(level, "未知")

    @classmethod
    def get_color(cls, level: int) -> tuple:
        return cls.LEVEL_COLORS.get(level, (1.0, 1.0, 1.0, 1.0))


class LogMessage:
    def __init__(self, level: int, source: str, message: str):
        self.level = level
        self.source = source
        self.message = message
        self.timestamp = datetime.datetime.now()
        self.count = 1

    def format(self) -> str:
        time_str = self.timestamp.strftime("%H:%M:%S.%f")[:-3]
        count_str = f" [{self.count}x]" if self.count > 1 else ""
        return f"[{time_str}] [{LogLevel.get_name(self.level)}] [{self.source}]: {self.message}{count_str}"


class Console:
    _instance = None
    _logs: deque = deque(maxlen=MAX_LOGS)
    _auto_scroll = True
    _scroll_to_bottom = False
    _filter = ""
    _level_filters: Dict[int, bool] = {
        LogLevel.INFO: True,
        LogLevel.WARNING: True,
        LogLevel.ERROR: True,
        LogLevel.DEBUG: True
    }
    _selected_log_index = -1
    _show_details = False
    _counters: Dict[int, int] = {
        LogLevel.INFO: 0,
        LogLevel.WARNING: 0,
        LogLevel.ERROR: 0,
        LogLevel.DEBUG: 0
    }
    _lock = threading.Lock()
    _pending_logs: List[LogMessage] = []
    _last_flush_time = 0.0
    _flush_interval = 0.05

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def log(cls, source: str, message: str):
        cls._add_log(LogLevel.INFO, source, message)

    @classmethod
    def warning(cls, source: str, message: str):
        cls._add_log(LogLevel.WARNING, source, message)

    @classmethod
    def error(cls, source: str, message: str):
        cls._add_log(LogLevel.ERROR, source, message)

    @classmethod
    def debug(cls, source: str, message: str):
        cls._add_log(LogLevel.DEBUG, source, message)

    @classmethod
    def _add_log(cls, level: int, source: str, message: str):
        with cls._lock:
            if cls._logs:
                last = cls._logs[-1]
                if (last.level == level and
                    last.source == source and
                    last.message == message):
                    last.count += 1
                    cls._counters[level] += 1
                    return

            cls._logs.append(LogMessage(level, source, message))
            cls._counters[level] += 1
            cls._scroll_to_bottom = True

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._logs.clear()
            cls._selected_log_index = -1
            for key in cls._counters:
                cls._counters[key] = 0

    @classmethod
    def get_filtered_logs(cls) -> List[LogMessage]:
        with cls._lock:
            logs_copy = list(cls._logs)

        filtered = []
        for log in logs_copy:
            if not cls._level_filters[log.level]:
                continue
            if cls._filter:
                filter_lower = cls._filter.lower()
                if (filter_lower not in log.message.lower() and
                    filter_lower not in log.source.lower() and
                    filter_lower not in LogLevel.get_name(log.level).lower()):
                    continue
            filtered.append(log)
        return filtered

    @classmethod
    def get_counters(cls) -> Dict[int, int]:
        with cls._lock:
            return dict(cls._counters)

    def render_toolbar(self):
        counters = Console.get_counters()

        if imgui.small_button("清除"):
            Console.clear()

        imgui.same_line()
        if imgui.small_button("复制") and Console._selected_log_index >= 0:
            filtered = Console.get_filtered_logs()
            if 0 <= Console._selected_log_index < len(filtered):
                log = filtered[Console._selected_log_index]
                pass

        imgui.same_line()
        changed, Console._auto_scroll = imgui.checkbox("自动滚动", Console._auto_scroll)

        imgui.same_line()
        imgui.separator()
        imgui.same_line()

        for level, enabled in list(Console._level_filters.items()):
            imgui.push_id(level)
            color = LogLevel.get_color(level)
            imgui.push_style_color(imgui.COLOR_TEXT, *color)
            changed, Console._level_filters[level] = imgui.checkbox(
                f"{LogLevel.get_name(level)}({counters.get(level, 0)})",
                enabled
            )
            imgui.pop_style_color()
            imgui.pop_id()
            if level != LogLevel.DEBUG:
                imgui.same_line()

        imgui.separator()

        imgui.push_item_width(300)
        changed, Console._filter = imgui.input_text("##filter", Console._filter, 256)
        imgui.pop_item_width()
        imgui.same_line()
        imgui.text("过滤")

        imgui.separator()

    def render_log_list(self):
        filtered = Console.get_filtered_logs()
        total_logs = len(filtered)

        flags = imgui.WINDOW_HORIZONTAL_SCROLLBAR
        imgui.begin_child("log_list_region", 0, 0, False, flags)

        if total_logs == 0:
            imgui.text("(没有日志)")
        else:
            start_idx = 0
            end_idx = total_logs

            if total_logs > MAX_RENDER_LOGS:
                if Console._auto_scroll:
                    start_idx = max(0, total_logs - MAX_RENDER_LOGS)
                    end_idx = total_logs
                else:
                    start_idx = 0
                    end_idx = min(MAX_RENDER_LOGS, total_logs)
                    imgui.text(f"显示 {end_idx}/{total_logs} 条日志 (滚动到底部查看最新)")

            for i in range(start_idx, end_idx):
                log = filtered[i]
                is_selected = (i == Console._selected_log_index)

                imgui.push_id(str(i))
                color = LogLevel.get_color(log.level)

                imgui.push_style_color(imgui.COLOR_TEXT, *color)
                clicked, _ = imgui.selectable(log.format(), is_selected, imgui.SELECTABLE_SPAN_ALL_COLUMNS)
                imgui.pop_style_color()

                if clicked:
                    Console._selected_log_index = i

                if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(0):
                    Console._show_details = True

                imgui.pop_id()

            if Console._scroll_to_bottom and Console._auto_scroll:
                Console._scroll_to_bottom = False
                imgui.set_scroll_here(1.0)

        imgui.end_child()

    def render_details_panel(self):
        if not Console._show_details:
            return

        filtered = Console.get_filtered_logs()
        if not (0 <= Console._selected_log_index < len(filtered)):
            return

        log = filtered[Console._selected_log_index]

        imgui.separator()
        imgui.text("日志详情")
        imgui.separator()

        imgui.indent()

        imgui.text("级别:")
        imgui.same_line()
        imgui.text_colored(*LogLevel.get_color(log.level), LogLevel.get_name(log.level))

        imgui.text(f"源: {log.source}")
        imgui.text(f"时间: {log.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')}")
        if log.count > 1:
            imgui.text(f"次数: {log.count}")

        imgui.text("消息:")
        imgui.indent()
        imgui.text_wrapped(log.message)
        imgui.unindent()

        imgui.unindent()

    def render(self):
        imgui.begin("控制台")

        self.render_toolbar()
        self.render_log_list()
        self.render_details_panel()

        if imgui.begin_popup_context_window():
            if imgui.menu_item("清除")[0]:
                Console.clear()
            if imgui.menu_item("显示详情")[0]:
                Console._show_details = not Console._show_details
            imgui.end_popup()

        imgui.end()
