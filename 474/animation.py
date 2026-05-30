import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, Circle
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from warehouse import Warehouse, ZoneType
import io
import base64
from pathlib import Path


@dataclass
class AnimationFrame:
    frame_number: int
    picker_position: Tuple[float, float]
    current_item: Optional[str]
    picked_items: List[str]
    remaining_items: List[str]
    distance_traveled: float


@dataclass
class AnimationResult:
    gif_path: str
    total_distance: float
    total_frames: int
    duration: float
    html_video: str


class PickingPathAnimator:
    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse
        self.depot_position = (-1.0, -1.0)
        self.fig = None
        self.ax = None
        self.frames: List[AnimationFrame] = []

    def _calculate_path_with_order(self, order_items: List[str],
                                   assignment: Dict[str, str]) -> Tuple[List[Tuple[float, float, str]], float]:
        if not order_items:
            return [], 0.0

        waypoints = []
        for item in order_items:
            if item in assignment:
                loc = self.warehouse.locations[assignment[item]]
                waypoints.append((loc.x, loc.y, item))

        if not waypoints:
            return [], 0.0

        path = []
        current_x, current_y = self.depot_position
        total_distance = 0.0

        remaining = waypoints[:]
        while remaining:
            nearest_idx = 0
            nearest_dist = float('inf')
            for i, (x, y, item) in enumerate(remaining):
                dist = np.sqrt((x - current_x) ** 2 + (y - current_y) ** 2)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i

            total_distance += nearest_dist
            x, y, item = remaining.pop(nearest_idx)
            path.append((x, y, item))
            current_x, current_y = x, y

        total_distance += np.sqrt(
            (current_x - self.depot_position[0]) ** 2 +
            (current_y - self.depot_position[1]) ** 2
        )

        return path, total_distance

    def _generate_frames(self, path: List[Tuple[float, float, str]],
                         steps_per_segment: int = 10) -> List[AnimationFrame]:
        frames = []
        picked_items = []
        remaining_items = [item for (_, _, item) in path]
        distance_traveled = 0.0

        prev_x, prev_y = self.depot_position

        for target_x, target_y, item in path:
            dx = (target_x - prev_x) / steps_per_segment
            dy = (target_y - prev_y) / steps_per_segment
            segment_dist = np.sqrt((target_x - prev_x) ** 2 + (target_y - prev_y) ** 2)
            dist_per_step = segment_dist / steps_per_segment

            for step in range(steps_per_segment):
                current_x = prev_x + dx * step
                current_y = prev_y + dy * step

                frames.append(AnimationFrame(
                    frame_number=len(frames),
                    picker_position=(current_x, current_y),
                    current_item=None,
                    picked_items=picked_items.copy(),
                    remaining_items=remaining_items.copy(),
                    distance_traveled=distance_traveled + dist_per_step * step
                ))

            distance_traveled += segment_dist
            picked_items.append(item)
            if item in remaining_items:
                remaining_items.remove(item)

            frames.append(AnimationFrame(
                frame_number=len(frames),
                picker_position=(target_x, target_y),
                current_item=item,
                picked_items=picked_items.copy(),
                remaining_items=remaining_items.copy(),
                distance_traveled=distance_traveled
            ))

            prev_x, prev_y = target_x, target_y

        return_x, return_y = self.depot_position
        dx = (return_x - prev_x) / steps_per_segment
        dy = (return_y - prev_y) / steps_per_segment
        segment_dist = np.sqrt((return_x - prev_x) ** 2 + (return_y - prev_y) ** 2)
        dist_per_step = segment_dist / steps_per_segment

        for step in range(steps_per_segment):
            current_x = prev_x + dx * step
            current_y = prev_y + dy * step

            frames.append(AnimationFrame(
                frame_number=len(frames),
                picker_position=(current_x, current_y),
                current_item=None,
                picked_items=picked_items.copy(),
                remaining_items=remaining_items.copy(),
                distance_traveled=distance_traveled + dist_per_step * step
            ))

        return frames

    def _setup_plot(self, title: str):
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.fig.patch.set_facecolor('#f0f2f6')
        self.ax.set_facecolor('#ffffff')
        self.ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        self.ax.set_xlabel('X 坐标 (米)', fontsize=11)
        self.ax.set_ylabel('Y 坐标 (米)', fontsize=11)

    def _draw_warehouse_layout(self):
        zone_colors = {
            ZoneType.GOLD: '#FFD700',
            ZoneType.SILVER: '#C0C0C0',
            ZoneType.BRONZE: '#CD7F32',
            ZoneType.STORAGE: '#E8E8E8'
        }

        for loc_id, loc in self.warehouse.locations.items():
            rect = Rectangle(
                (loc.x - 0.8, loc.y - 0.8), 1.6, 1.6,
                facecolor=zone_colors.get(loc.zone, '#E8E8E8'),
                edgecolor='#333333',
                linewidth=0.5,
                alpha=0.6
            )
            self.ax.add_patch(rect)

        depot_circle = Circle(
            self.depot_position, 1.0,
            facecolor='#FF4B4B',
            edgecolor='#CC0000',
            linewidth=2,
            alpha=0.8
        )
        self.ax.add_patch(depot_circle)
        self.ax.text(self.depot_position[0], self.depot_position[1], '出库台',
                     ha='center', va='center', fontsize=9, fontweight='bold')

        all_x = [loc.x for loc in self.warehouse.locations.values()] + [self.depot_position[0]]
        all_y = [loc.y for loc in self.warehouse.locations.values()] + [self.depot_position[1]]
        self.ax.set_xlim(min(all_x) - 2, max(all_x) + 2)
        self.ax.set_ylim(min(all_y) - 2, max(all_y) + 2)

        legend_elements = [
            Rectangle((0, 0), 1, 1, facecolor='#FFD700', label='黄金区 (A类)'),
            Rectangle((0, 0), 1, 1, facecolor='#C0C0C0', label='白银区 (A/B类)'),
            Rectangle((0, 0), 1, 1, facecolor='#CD7F32', label='青铜区 (A/B/C类)'),
            Rectangle((0, 0), 1, 1, facecolor='#E8E8E8', label='存储区 (B/C类)'),
            Circle((0, 0), 0.5, facecolor='#FF4B4B', label='出库台')
        ]
        self.ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

    def _create_animation_frame(self, frame_data: AnimationFrame,
                                path_waypoints: List[Tuple[float, float, str]],
                                assignment: Dict[str, str]):
        for artist in self.ax.artists + self.ax.texts + self.ax.patches:
            if hasattr(artist, '_is_animated'):
                artist.remove()

        for x, y, item in path_waypoints:
            if item in frame_data.picked_items:
                color = '#00CC00'
            elif item in frame_data.remaining_items:
                color = '#FF6B6B'
            else:
                color = '#888888'

            marker = Circle((x, y), 0.4, facecolor=color, edgecolor='#333333',
                           linewidth=1.5, alpha=0.8)
            marker._is_animated = True
            self.ax.add_patch(marker)

            item_name = item[:8] if len(item) > 8 else item
            text = self.ax.text(x, y + 0.6, item_name, ha='center', va='bottom',
                               fontsize=7, fontweight='bold')
            text._is_animated = True
            self.ax.add_artist(text)

        picker = Circle(frame_data.picker_position, 0.6,
                       facecolor='#4B8BFF', edgecolor='#0047CC',
                       linewidth=2.5, alpha=0.9)
        picker._is_animated = True
        self.ax.add_patch(picker)

        if frame_data.current_item:
            item_name = frame_data.current_item[:12]
            status_text = self.ax.text(0.02, 0.98,
                                      f'正在拣货: {item_name}\n'
                                      f'已完成: {len(frame_data.picked_items)}/{len(path_waypoints)}\n'
                                      f'已行驶: {frame_data.distance_traveled:.1f}m',
                                      transform=self.ax.transAxes,
                                      verticalalignment='top',
                                      bbox=dict(boxstyle='round,pad=0.5',
                                               facecolor='#FFF9C4',
                                               edgecolor='#FBC02D',
                                               alpha=0.9),
                                      fontsize=10)
        else:
            status_text = self.ax.text(0.02, 0.98,
                                      f'移动中...\n'
                                      f'已完成: {len(frame_data.picked_items)}/{len(path_waypoints)}\n'
                                      f'已行驶: {frame_data.distance_traveled:.1f}m',
                                      transform=self.ax.transAxes,
                                      verticalalignment='top',
                                      bbox=dict(boxstyle='round,pad=0.5',
                                               facecolor='#E3F2FD',
                                               edgecolor='#1976D2',
                                               alpha=0.9),
                                      fontsize=10)
        status_text._is_animated = True
        self.ax.add_artist(status_text)

        return picker,

    def create_picking_animation(self, order_items: List[str],
                                 assignment: Dict[str, str],
                                 title: str = "拣货路径仿真",
                                 output_path: str = "picking_animation.gif",
                                 fps: int = 10) -> AnimationResult:
        path_waypoints, total_distance = self._calculate_path_with_order(order_items, assignment)

        if not path_waypoints:
            raise ValueError("未能生成拣货路径")

        self.frames = self._generate_frames(path_waypoints)
        self._setup_plot(title)
        self._draw_warehouse_layout()

        def animate(frame_idx):
            frame = self.frames[frame_idx]
            return self._create_animation_frame(frame, path_waypoints, assignment)

        ani = animation.FuncAnimation(
            self.fig, animate,
            frames=len(self.frames),
            interval=1000 // fps,
            blit=False,
            repeat=True
        )

        writer = animation.PillowWriter(fps=fps)
        ani.save(output_path, writer=writer, dpi=100)
        plt.close(self.fig)

        with open(output_path, 'rb') as f:
            gif_data = f.read()
            gif_base64 = base64.b64encode(gif_data).decode()

        html_video = f'''
        <div style="text-align: center; padding: 10px;">
            <img src="data:image/gif;base64,{gif_base64}" 
                 alt="拣货路径动画" 
                 style="max-width: 100%; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="margin-top: 10px; font-size: 14px; color: #666;">
                总距离: <strong>{total_distance:.1f}米</strong> | 
                总步骤: <strong>{len(self.frames)}</strong>帧
            </div>
        </div>
        '''

        return AnimationResult(
            gif_path=output_path,
            total_distance=total_distance,
            total_frames=len(self.frames),
            duration=len(self.frames) / fps,
            html_video=html_video
        )


class ComparisonAnimator:
    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse
        self.animator = PickingPathAnimator(warehouse)

    def create_comparison_animation(self, order_items: List[str],
                                     assignment_before: Dict[str, str],
                                     assignment_after: Dict[str, str],
                                     output_path: str = "comparison_animation.gif",
                                     fps: int = 10) -> AnimationResult:
        path_before, dist_before = self.animator._calculate_path_with_order(order_items, assignment_before)
        path_after, dist_after = self.animator._calculate_path_with_order(order_items, assignment_after)

        frames_before = self.animator._generate_frames(path_before)
        frames_after = self.animator._generate_frames(path_after)

        max_frames = max(len(frames_before), len(frames_after))

        while len(frames_before) < max_frames:
            frames_before.append(frames_before[-1])
        while len(frames_after) < max_frames:
            frames_after.append(frames_after[-1])

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        fig.patch.set_facecolor('#f0f2f6')

        zone_colors = {
            ZoneType.GOLD: '#FFD700',
            ZoneType.SILVER: '#C0C0C0',
            ZoneType.BRONZE: '#CD7F32',
            ZoneType.STORAGE: '#E8E8E8'
        }

        for ax, title in [(ax1, '优化前'), (ax2, '优化后')]:
            ax.set_facecolor('#ffffff')
            ax.set_title(title, fontsize=12, fontweight='bold', pad=15)
            ax.set_xlabel('X 坐标')
            ax.set_ylabel('Y 坐标')

            for loc_id, loc in self.warehouse.locations.items():
                rect = Rectangle(
                    (loc.x - 0.8, loc.y - 0.8), 1.6, 1.6,
                    facecolor=zone_colors.get(loc.zone, '#E8E8E8'),
                    edgecolor='#333333',
                    linewidth=0.3,
                    alpha=0.5
                )
                ax.add_patch(rect)

            depot_circle = Circle((-1.0, -1.0), 0.8, facecolor='#FF4B4B',
                                 edgecolor='#CC0000', alpha=0.8)
            ax.add_patch(depot_circle)

            all_x = [loc.x for loc in self.warehouse.locations.values()] + [-1.0]
            all_y = [loc.y for loc in self.warehouse.locations.values()] + [-1.0]
            ax.set_xlim(min(all_x) - 2, max(all_x) + 2)
            ax.set_ylim(min(all_y) - 2, max(all_y) + 2)

        def animate(frame_idx):
            for ax in [ax1, ax2]:
                for artist in ax.artists + ax.texts:
                    if hasattr(artist, '_is_animated'):
                        artist.remove()

            frame_b = frames_before[min(frame_idx, len(frames_before) - 1)]
            frame_a = frames_after[min(frame_idx, len(frames_after) - 1)]

            picker_b = Circle(frame_b.picker_position, 0.5,
                             facecolor='#FF6B6B', edgecolor='#CC0000',
                             linewidth=2, alpha=0.9)
            picker_b._is_animated = True
            ax1.add_patch(picker_b)

            picker_a = Circle(frame_a.picker_position, 0.5,
                             facecolor='#00CC00', edgecolor='#008800',
                             linewidth=2, alpha=0.9)
            picker_a._is_animated = True
            ax2.add_patch(picker_a)

            text_b = ax1.text(0.02, 0.98,
                             f'距离: {frame_b.distance_traveled:.1f}m\n'
                             f'完成: {len(frame_b.picked_items)}/{len(path_before)}',
                             transform=ax1.transAxes,
                             verticalalignment='top',
                             bbox=dict(boxstyle='round,pad=0.3',
                                      facecolor='#FFEBEE',
                                      edgecolor='#E57373'),
                             fontsize=9)
            text_b._is_animated = True
            ax1.add_artist(text_b)

            text_a = ax2.text(0.02, 0.98,
                             f'距离: {frame_a.distance_traveled:.1f}m\n'
                             f'完成: {len(frame_a.picked_items)}/{len(path_after)}',
                             transform=ax2.transAxes,
                             verticalalignment='top',
                             bbox=dict(boxstyle='round,pad=0.3',
                                      facecolor='#E8F5E9',
                                      edgecolor='#81C784'),
                             fontsize=9)
            text_a._is_animated = True
            ax2.add_artist(text_a)

            improvement = (dist_before - dist_after) / dist_before * 100 if dist_before > 0 else 0
            title_text = fig.suptitle(
                f'拣货路径优化对比 | 优化前: {dist_before:.1f}m → 优化后: {dist_after:.1f}m | 提升: {improvement:.1f}%',
                fontsize=14, fontweight='bold', y=0.98
            )
            title_text._is_animated = True

            return picker_b, picker_a

        ani = animation.FuncAnimation(
            fig, animate,
            frames=max_frames,
            interval=1000 // fps,
            blit=False,
            repeat=True
        )

        writer = animation.PillowWriter(fps=fps)
        ani.save(output_path, writer=writer, dpi=100)
        plt.close(fig)

        with open(output_path, 'rb') as f:
            gif_data = f.read()
            gif_base64 = base64.b64encode(gif_data).decode()

        improvement = (dist_before - dist_after) / dist_before * 100 if dist_before > 0 else 0

        html_video = f'''
        <div style="text-align: center; padding: 10px;">
            <div style="margin-bottom: 15px; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        border-radius: 10px; color: white;">
                <h3 style="margin: 0;">🎯 优化效果对比</h3>
                <div style="display: flex; justify-content: center; gap: 40px; margin-top: 10px;">
                    <div>
                        <div style="font-size: 24px; font-weight: bold;">{dist_before:.1f}m</div>
                        <div style="font-size: 12px; opacity: 0.8;">优化前</div>
                    </div>
                    <div style="font-size: 30px;">→</div>
                    <div>
                        <div style="font-size: 24px; font-weight: bold;">{dist_after:.1f}m</div>
                        <div style="font-size: 12px; opacity: 0.8;">优化后</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.2); padding: 10px 20px; border-radius: 8px;">
                        <div style="font-size: 24px; font-weight: bold;">{improvement:+.1f}%</div>
                        <div style="font-size: 12px;">效率提升</div>
                    </div>
                </div>
            </div>
            <img src="data:image/gif;base64,{gif_base64}" 
                 alt="优化对比动画" 
                 style="max-width: 100%; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        </div>
        '''

        return AnimationResult(
            gif_path=output_path,
            total_distance=dist_after,
            total_frames=max_frames,
            duration=max_frames / fps,
            html_video=html_video
        )
