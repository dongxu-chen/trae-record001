import time
import imgui
from collections import deque
from typing import Deque, Dict, List


class PerformanceStats:
    def __init__(self, max_samples: int = 60):
        self.max_samples = max_samples
        self.frame_times: Deque[float] = deque(maxlen=max_samples)
        self.render_times: Deque[float] = deque(maxlen=max_samples)
        self.update_times: Deque[float] = deque(maxlen=max_samples)
        self._frame_start_time = 0.0
        self._render_start_time = 0.0
        self._update_start_time = 0.0

        self.draw_calls: Dict[str, int] = {
            "triangles": 0,
            "lines": 0,
            "points": 0,
            "textures_bound": 0,
            "shader_switches": 0,
            "vao_binds": 0,
        }

        self._draw_call_history: Deque[Dict[str, int]] = deque(maxlen=max_samples)

    def begin_frame(self):
        self._frame_start_time = time.perf_counter()

    def begin_update(self):
        self._update_start_time = time.perf_counter()

    def end_update(self):
        elapsed = (time.perf_counter() - self._update_start_time) * 1000.0
        self.update_times.append(elapsed)

    def begin_render(self):
        self._render_start_time = time.perf_counter()

    def end_render(self):
        elapsed = (time.perf_counter() - self._render_start_time) * 1000.0
        self.render_times.append(elapsed)

    def end_frame(self):
        elapsed = (time.perf_counter() - self._frame_start_time) * 1000.0
        self.frame_times.append(elapsed)
        self._draw_call_history.append(dict(self.draw_calls))

    def record_draw_call(self, call_type: str, count: int = 1):
        if call_type in self.draw_calls:
            self.draw_calls[call_type] += count

    def reset_draw_calls(self):
        for key in self.draw_calls:
            self.draw_calls[key] = 0

    def get_avg_frame_time(self) -> float:
        if not self.frame_times:
            return 0.0
        return sum(self.frame_times) / len(self.frame_times)

    def get_avg_render_time(self) -> float:
        if not self.render_times:
            return 0.0
        return sum(self.render_times) / len(self.render_times)

    def get_avg_update_time(self) -> float:
        if not self.update_times:
            return 0.0
        return sum(self.update_times) / len(self.update_times)

    def get_fps(self) -> float:
        avg = self.get_avg_frame_time()
        if avg <= 0.0:
            return 0.0
        return 1000.0 / avg

    def get_min_frame_time(self) -> float:
        if not self.frame_times:
            return 0.0
        return min(self.frame_times)

    def get_max_frame_time(self) -> float:
        if not self.frame_times:
            return 0.0
        return max(self.frame_times)

    def get_total_draw_calls(self) -> int:
        return sum(self.draw_calls.values())

    def render(self):
        imgui.begin("性能统计")

        fps = self.get_fps()
        avg_frame = self.get_avg_frame_time()
        avg_render = self.get_avg_render_time()
        avg_update = self.get_avg_update_time()
        min_frame = self.get_min_frame_time()
        max_frame = self.get_max_frame_time()

        if fps >= 55.0:
            fps_color = (0.3, 1.0, 0.3, 1.0)
        elif fps >= 30.0:
            fps_color = (1.0, 0.8, 0.2, 1.0)
        else:
            fps_color = (1.0, 0.3, 0.3, 1.0)

        imgui.text_colored(*fps_color, f"FPS: {fps:.1f}")
        imgui.same_line()
        imgui.text(f"| 帧时间: {avg_frame:.2f}ms")

        imgui.separator()

        if imgui.collapsing_header("时序统计", flags=imgui.TREE_NODE_DEFAULT_OPEN):
            imgui.indent()
            imgui.text(f"平均更新: {avg_update:.3f} ms")
            imgui.text(f"平均渲染: {avg_render:.3f} ms")
            imgui.text(f"平均帧:   {avg_frame:.3f} ms")
            imgui.text(f"最小帧:   {min_frame:.3f} ms")
            imgui.text(f"最大帧:   {max_frame:.3f} ms")
            imgui.unindent()

        imgui.separator()

        if imgui.collapsing_header("绘制调用统计", flags=imgui.TREE_NODE_DEFAULT_OPEN):
            imgui.indent()
            total = self.get_total_draw_calls()

            if total > 0:
                for name, count in self.draw_calls.items():
                    percentage = (count / total * 100) if total > 0 else 0
                    imgui.progress_bar(
                        count / max(total, 1),
                        imgui.Vec2(-1, 0),
                        f"{name}: {count} ({percentage:.1f}%)"
                    )
            else:
                imgui.text("(没有记录绘制调用)")
            imgui.unindent()

        imgui.separator()

        if imgui.collapsing_header("帧时间图"):
            imgui.indent()
            if len(self.frame_times) >= 2:
                times_list = list(self.frame_times)
                min_t = min(times_list)
                max_t = max(times_list)
                range_t = max(max_t - min_t, 0.01)

                imgui.plot_lines(
                    "##frametime_plot",
                    times_list,
                    scale_min=0.0,
                    scale_max=max_t * 1.1,
                    graph_size=imgui.Vec2(-1, 100)
                )

                imgui.text(f"范围: {min_t:.2f} - {max_t:.2f} ms")
            else:
                imgui.text("(需要更多帧数据)")
            imgui.unindent()

        imgui.separator()

        if imgui.small_button("重置统计"):
            self.frame_times.clear()
            self.render_times.clear()
            self.update_times.clear()
            self._draw_call_history.clear()
            self.reset_draw_calls()

        imgui.end()

    def get_draw_calls_summary(self) -> Dict[str, int]:
        return dict(self.draw_calls)
