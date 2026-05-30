import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from typing import Dict, List, Tuple, Optional
from warehouse import Warehouse, Location, SeasonalityType
from path_simulator import PickingPath
from dataclasses import dataclass
from enum import Enum


class LODLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class LODSettings:
    distance_threshold_near: float = 10.0
    distance_threshold_medium: float = 25.0
    size_high: int = 10
    size_medium: int = 6
    size_low: int = 3
    opacity_high: float = 0.9
    opacity_medium: float = 0.7
    opacity_low: float = 0.4


class LODRenderer:
    def __init__(self, settings: LODSettings = None):
        self.settings = settings or LODSettings()
        self.camera_position = np.array([15.0, 10.0, 10.0])

    def update_camera(self, eye_x: float, eye_y: float, eye_z: float):
        self.camera_position = np.array([eye_x, eye_y, eye_z])

    def get_lod_level(self, point: Tuple[float, float, float]) -> LODLevel:
        distance = np.linalg.norm(np.array(point) - self.camera_position)
        if distance < self.settings.distance_threshold_near:
            return LODLevel.HIGH
        elif distance < self.settings.distance_threshold_medium:
            return LODLevel.MEDIUM
        else:
            return LODLevel.LOW

    def get_marker_props(self, lod_level: LODLevel) -> Dict:
        if lod_level == LODLevel.HIGH:
            return {
                'size': self.settings.size_high,
                'opacity': self.settings.opacity_high,
                'symbol': 'cube'
            }
        elif lod_level == LODLevel.MEDIUM:
            return {
                'size': self.settings.size_medium,
                'opacity': self.settings.opacity_medium,
                'symbol': 'circle'
            }
        else:
            return {
                'size': self.settings.size_low,
                'opacity': self.settings.opacity_low,
                'symbol': 'square-open'
            }


class WarehouseVisualizer:
    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse
        self.lod_renderer = LODRenderer()
        self.category_colors = {
            '电子产品': '#1f77b4',
            '日用品': '#ff7f0e',
            '食品': '#2ca02c',
            '服装': '#d62728',
            '工具': '#9467bd',
            '玩具': '#8c564b'
        }
        self.season_colors = {
            SeasonalityType.SPRING: '#98FB98',
            SeasonalityType.SUMMER: '#FFD700',
            SeasonalityType.AUTUMN: '#CD853F',
            SeasonalityType.WINTER: '#87CEEB',
            SeasonalityType.HOLIDAY: '#FF69B4',
            SeasonalityType.NONE: '#808080',
            SeasonalityType.WEEKEND: '#DDA0DD',
            SeasonalityType.MONTH_END: '#20B2AA'
        }

    def create_3d_warehouse_plot(self, product_locations: Dict[str, str] = None,
                                  title: str = "仓库货位布局",
                                  use_lod: bool = False,
                                  camera_eye: Tuple[float, float, float] = None) -> go.Figure:
        fig = go.Figure()

        if camera_eye:
            self.lod_renderer.update_camera(*camera_eye)

        self._add_warehouse_structure(fig)

        if product_locations:
            if use_lod:
                self._add_products_lod(fig, product_locations)
            else:
                self._add_products(fig, product_locations)
        else:
            if use_lod:
                self._add_empty_locations_lod(fig)
            else:
                self._add_empty_locations(fig)

        self._add_depot(fig)
        self._update_layout(fig, title)

        return fig

    def create_3d_warehouse_lod_plot(self, product_locations: Dict[str, str] = None,
                                      title: str = "仓库货位布局 (LOD渲染)") -> go.Figure:
        fig = go.Figure()

        self._add_warehouse_structure_lod(fig)

        if product_locations:
            self._add_products_lod(fig, product_locations)
        else:
            self._add_empty_locations_lod(fig)

        self._add_depot(fig)
        self._add_lod_legend(fig)
        self._update_layout(fig, title)

        return fig

    def _add_warehouse_structure_lod(self, fig: go.Figure):
        max_x = max(loc.x for loc in self.warehouse.locations.values()) + 2
        max_y = max(loc.y for loc in self.warehouse.locations.values()) + 2
        max_z = max(loc.z for loc in self.warehouse.locations.values()) + 2

        for aisle in range(1, self.warehouse.num_aisles + 1):
            x = (aisle - 1) * 5.0
            lod_level = self.lod_renderer.get_lod_level((x, max_y / 2, 0))

            if lod_level == LODLevel.HIGH:
                line_width = 5
                opacity = 0.4
            elif lod_level == LODLevel.MEDIUM:
                line_width = 3
                opacity = 0.25
            else:
                line_width = 1
                opacity = 0.1

            fig.add_trace(go.Scatter3d(
                x=[x, x], y=[0, max_y - 2], z=[0, 0],
                mode='lines',
                line=dict(color=f'rgba(100,100,100,{opacity})', width=line_width),
                name=f'通道 {aisle}',
                showlegend=False,
                hoverinfo='skip'
            ))

    def _add_empty_locations_lod(self, fig: go.Figure):
        lod_groups = {LODLevel.HIGH: [], LODLevel.MEDIUM: [], LODLevel.LOW: []}

        for loc in self.warehouse.locations.values():
            lod_level = self.lod_renderer.get_lod_level((loc.x, loc.y, loc.z))
            lod_groups[lod_level].append(loc)

        for lod_level, locations in lod_groups.items():
            if not locations:
                continue

            props = self.lod_renderer.get_marker_props(lod_level)
            x_coords = [loc.x for loc in locations]
            y_coords = [loc.y for loc in locations]
            z_coords = [loc.z for loc in locations]

            hover_texts = [f'货位: {loc.id}<br>位置: ({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f})'
                           for loc in locations]

            fig.add_trace(go.Scatter3d(
                x=x_coords, y=y_coords, z=z_coords,
                mode='markers',
                marker=dict(
                    size=props['size'] // 2,
                    color='lightgray',
                    opacity=props['opacity'] * 0.8,
                    symbol=props['symbol']
                ),
                text=hover_texts,
                hoverinfo='text' if lod_level != LODLevel.LOW else 'skip',
                name=f'空闲货位 ({lod_level.value})',
                showlegend=lod_level != LODLevel.LOW
            ))

    def _add_products_lod(self, fig: go.Figure, product_locations: Dict[str, str]):
        lod_groups = {
            LODLevel.HIGH: {'x': [], 'y': [], 'z': [], 'text': [], 'colors': []},
            LODLevel.MEDIUM: {'x': [], 'y': [], 'z': [], 'text': [], 'colors': []},
            LODLevel.LOW: {'x': [], 'y': [], 'z': [], 'text': [], 'colors': []}
        }

        for prod_id, loc_id in product_locations.items():
            prod = self.warehouse.products.get(prod_id)
            loc = self.warehouse.locations.get(loc_id)
            if not prod or not loc:
                continue

            lod_level = self.lod_renderer.get_lod_level((loc.x, loc.y, loc.z))
            color = self.category_colors.get(prod.category, '#7f7f7f')

            lod_groups[lod_level]['x'].append(loc.x)
            lod_groups[lod_level]['y'].append(loc.y)
            lod_groups[lod_level]['z'].append(loc.z)
            lod_groups[lod_level]['colors'].append(color)

            if lod_level != LODLevel.LOW:
                lod_groups[lod_level]['text'].append(
                    f'商品: {prod.name} ({prod.id})<br>'
                    f'货位: {loc_id}<br>'
                    f'分类: {prod.category}<br>'
                    f'周转率: {prod.turnover_rate:.2f}'
                )

        for lod_level, data in lod_groups.items():
            if not data['x']:
                continue

            props = self.lod_renderer.get_marker_props(lod_level)

            fig.add_trace(go.Scatter3d(
                x=data['x'], y=data['y'], z=data['z'],
                mode='markers',
                marker=dict(
                    size=props['size'],
                    color=data['colors'],
                    opacity=props['opacity'],
                    symbol=props['symbol']
                ),
                text=data['text'] if data['text'] else None,
                hoverinfo='text' if lod_level != LODLevel.LOW else 'skip',
                name=f'商品 ({lod_level.value})',
                showlegend=lod_level != LODLevel.LOW
            ))

        all_loc_ids = set(self.warehouse.locations.keys())
        used_loc_ids = set(product_locations.values())
        empty_loc_ids = all_loc_ids - used_loc_ids

        if empty_loc_ids:
            empty_lod_groups = {LODLevel.HIGH: [], LODLevel.MEDIUM: [], LODLevel.LOW: []}
            for loc_id in empty_loc_ids:
                loc = self.warehouse.locations[loc_id]
                lod_level = self.lod_renderer.get_lod_level((loc.x, loc.y, loc.z))
                empty_lod_groups[lod_level].append(loc)

            for lod_level, locations in empty_lod_groups.items():
                if not locations:
                    continue
                props = self.lod_renderer.get_marker_props(lod_level)
                fig.add_trace(go.Scatter3d(
                    x=[loc.x for loc in locations],
                    y=[loc.y for loc in locations],
                    z=[loc.z for loc in locations],
                    mode='markers',
                    marker=dict(
                        size=props['size'] // 2,
                        color='lightgray',
                        opacity=props['opacity'] * 0.5,
                        symbol=props['symbol']
                    ),
                    hoverinfo='skip',
                    showlegend=False
                ))

    def _add_lod_legend(self, fig: go.Figure):
        for lod_level in [LODLevel.HIGH, LODLevel.MEDIUM, LODLevel.LOW]:
            props = self.lod_renderer.get_marker_props(lod_level)
            fig.add_trace(go.Scatter3d(
                x=[None], y=[None], z=[None],
                mode='markers',
                marker=dict(
                    size=props['size'],
                    color='blue',
                    opacity=props['opacity'],
                    symbol=props['symbol']
                ),
                name=f'LOD: {lod_level.value}',
                showlegend=True
            ))

    def _add_warehouse_structure(self, fig: go.Figure):
        max_x = max(loc.x for loc in self.warehouse.locations.values()) + 2
        max_y = max(loc.y for loc in self.warehouse.locations.values()) + 2
        max_z = max(loc.z for loc in self.warehouse.locations.values()) + 2

        for aisle in range(1, self.warehouse.num_aisles + 1):
            x = (aisle - 1) * 5.0
            fig.add_trace(go.Scatter3d(
                x=[x, x], y=[0, max_y - 2], z=[0, 0],
                mode='lines',
                line=dict(color='rgba(100,100,100,0.3)', width=5),
                name=f'通道 {aisle}',
                showlegend=False,
                hoverinfo='skip'
            ))

        for bay in range(1, self.warehouse.bays_per_aisle + 1):
            y = (bay - 1) * 2.0
            fig.add_trace(go.Scatter3d(
                x=[0, max_x - 2], y=[y, y], z=[0, 0],
                mode='lines',
                line=dict(color='rgba(100,100,100,0.2)', width=2),
                showlegend=False,
                hoverinfo='skip'
            ))

    def _add_empty_locations(self, fig: go.Figure):
        x_coords, y_coords, z_coords, hover_texts = [], [], [], []

        for loc in self.warehouse.locations.values():
            x_coords.append(loc.x)
            y_coords.append(loc.y)
            z_coords.append(loc.z)
            hover_texts.append(f'货位: {loc.id}<br>位置: ({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f})')

        fig.add_trace(go.Scatter3d(
            x=x_coords, y=y_coords, z=z_coords,
            mode='markers',
            marker=dict(
                size=4,
                color='lightgray',
                opacity=0.6,
                symbol='square'
            ),
            text=hover_texts,
            hoverinfo='text',
            name='空闲货位'
        ))

    def _add_products(self, fig: go.Figure, product_locations: Dict[str, str]):
        category_data = {}

        for prod_id, loc_id in product_locations.items():
            prod = self.warehouse.products.get(prod_id)
            loc = self.warehouse.locations.get(loc_id)
            if not prod or not loc:
                continue

            category = prod.category
            if category not in category_data:
                category_data[category] = {'x': [], 'y': [], 'z': [], 'text': []}

            category_data[category]['x'].append(loc.x)
            category_data[category]['y'].append(loc.y)
            category_data[category]['z'].append(loc.z)
            category_data[category]['text'].append(
                f'商品: {prod.name} ({prod.id})<br>'
                f'货位: {loc_id}<br>'
                f'分类: {category}<br>'
                f'周转率: {prod.turnover_rate:.2f}<br>'
                f'尺寸: {prod.width:.2f}x{prod.depth:.2f}x{prod.height:.2f}m'
            )

        for category, data in category_data.items():
            color = self.category_colors.get(category, '#7f7f7f')
            fig.add_trace(go.Scatter3d(
                x=data['x'], y=data['y'], z=data['z'],
                mode='markers',
                marker=dict(
                    size=8,
                    color=color,
                    opacity=0.8,
                    symbol='cube'
                ),
                text=data['text'],
                hoverinfo='text',
                name=category
            ))

        all_loc_ids = set(self.warehouse.locations.keys())
        used_loc_ids = set(product_locations.values())
        empty_loc_ids = all_loc_ids - used_loc_ids

        if empty_loc_ids:
            x_coords, y_coords, z_coords, hover_texts = [], [], [], []
            for loc_id in empty_loc_ids:
                loc = self.warehouse.locations[loc_id]
                x_coords.append(loc.x)
                y_coords.append(loc.y)
                z_coords.append(loc.z)
                hover_texts.append(f'货位: {loc.id}<br>状态: 空闲')

            fig.add_trace(go.Scatter3d(
                x=x_coords, y=y_coords, z=z_coords,
                mode='markers',
                marker=dict(
                    size=4,
                    color='lightgray',
                    opacity=0.4,
                    symbol='square'
                ),
                text=hover_texts,
                hoverinfo='text',
                name='空闲货位'
            ))

    def _add_depot(self, fig: go.Figure):
        fig.add_trace(go.Scatter3d(
            x=[-1.0], y=[-1.0], z=[0.0],
            mode='markers',
            marker=dict(
                size=12,
                color='red',
                symbol='diamond',
                line=dict(width=2, color='darkred')
            ),
            text='出库台 (起点/终点)',
            hoverinfo='text',
            name='出库台'
        ))

    def _update_layout(self, fig: go.Figure, title: str):
        max_x = max(loc.x for loc in self.warehouse.locations.values()) + 3
        max_y = max(loc.y for loc in self.warehouse.locations.values()) + 3
        max_z = max(loc.z for loc in self.warehouse.locations.values()) + 1

        fig.update_layout(
            title=dict(
                text=title,
                x=0.5,
                font=dict(size=18)
            ),
            scene=dict(
                xaxis=dict(title='X (通道方向)', range=[-2, max_x]),
                yaxis=dict(title='Y (货位方向)', range=[-2, max_y]),
                zaxis=dict(title='Z (高度)', range=[-0.5, max_z]),
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.0)
                )
            ),
            width=800,
            height=600,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            ),
            margin=dict(l=0, r=0, t=40, b=0)
        )

    def create_picking_path_plot(self, picking_path: PickingPath,
                                  title: str = "拣货路径可视化") -> go.Figure:
        fig = self.create_3d_warehouse_plot(title=title)

        path = picking_path.path
        path_x = [p[0] for p in path]
        path_y = [p[1] for p in path]
        path_z = [p[2] for p in path]

        fig.add_trace(go.Scatter3d(
            x=path_x, y=path_y, z=path_z,
            mode='lines',
            line=dict(
                color='rgba(255, 0, 0, 0.8)',
                width=4
            ),
            name=f'拣货路径 (总距离: {picking_path.total_distance:.2f}m)',
            hoverinfo='name'
        ))

        for i, (x, y, z) in enumerate(path[1:-1], 1):
            fig.add_trace(go.Scatter3d(
                x=[x], y=[y], z=[z],
                mode='text',
                text=[str(i)],
                textfont=dict(size=12, color='white'),
                showlegend=False,
                hoverinfo='skip'
            ))

        return fig

    def create_turnover_heatmap(self, product_locations: Dict[str, str],
                                 title: str = "货位周转率热力图") -> go.Figure:
        fig = go.Figure()

        turnover_values = []
        x_coords, y_coords, z_coords = [], [], []
        hover_texts = []

        for prod_id, loc_id in product_locations.items():
            prod = self.warehouse.products.get(prod_id)
            loc = self.warehouse.locations.get(loc_id)
            if prod and loc:
                turnover_values.append(prod.turnover_rate)
                x_coords.append(loc.x)
                y_coords.append(loc.y)
                z_coords.append(loc.z)
                hover_texts.append(
                    f'商品: {prod.name}<br>'
                    f'货位: {loc_id}<br>'
                    f'周转率: {prod.turnover_rate:.2f}'
                )

        fig.add_trace(go.Scatter3d(
            x=x_coords, y=y_coords, z=z_coords,
            mode='markers',
            marker=dict(
                size=8,
                color=turnover_values,
                colorscale='Viridis',
                opacity=0.8,
                colorbar=dict(
                    title='周转率',
                    x=0.9
                )
            ),
            text=hover_texts,
            hoverinfo='text',
            name='商品'
        ))

        self._add_depot(fig)
        self._update_layout(fig, title)

        return fig

    def create_comparison_bar_chart(self, comparison_data: Dict[str, Dict],
                                     title: str = "拣货路径优化对比") -> go.Figure:
        fig = go.Figure()

        names = list(comparison_data.keys())
        mean_distances = [comparison_data[name]['mean_distance'] for name in names]
        std_distances = [comparison_data[name]['std_distance'] for name in names]

        colors = ['#ff7f0e', '#1f77b4', '#2ca02c'][:len(names)]

        fig.add_trace(go.Bar(
            x=names,
            y=mean_distances,
            error_y=dict(type='data', array=std_distances, visible=True),
            marker_color=colors,
            text=[f'{d:.2f}m' for d in mean_distances],
            textposition='auto',
        ))

        fig.update_layout(
            title=dict(text=title, x=0.5, font=dict(size=16)),
            xaxis_title='货位分配策略',
            yaxis_title='平均拣货距离 (m)',
            width=700,
            height=450,
            showlegend=False,
            template='plotly_white'
        )

        return fig

    def create_ga_convergence_plot(self, logbook) -> go.Figure:
        gen = logbook.select("gen")
        fit_max = logbook.select("max")
        fit_avg = logbook.select("avg")

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=gen,
            y=fit_max,
            mode='lines+markers',
            name='最优适应度',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=6)
        ))

        fig.add_trace(go.Scatter(
            x=gen,
            y=fit_avg,
            mode='lines',
            name='平均适应度',
            line=dict(color='#ff7f0e', width=2, dash='dash')
        ))

        fig.update_layout(
            title=dict(text='遗传算法收敛曲线', x=0.5, font=dict(size=16)),
            xaxis_title='迭代次数',
            yaxis_title='适应度值',
            width=700,
            height=450,
            showlegend=True,
            template='plotly_white',
            hovermode='x unified'
        )

        return fig

    def create_boxplot_comparison(self, comparison_data: Dict[str, Dict],
                                   title: str = "拣货距离分布对比") -> go.Figure:
        fig = go.Figure()

        colors = ['#ff7f0e', '#1f77b4', '#2ca02c']

        for i, (name, data) in enumerate(comparison_data.items()):
            fig.add_trace(go.Box(
                y=data['distances'],
                name=name,
                boxmean=True,
                marker_color=colors[i % len(colors)]
            ))

        fig.update_layout(
            title=dict(text=title, x=0.5, font=dict(size=16)),
            xaxis_title='货位分配策略',
            yaxis_title='拣货距离 (m)',
            width=700,
            height=450,
            showlegend=False,
            template='plotly_white'
        )

        return fig

    def create_seasonality_3d_plot(self, product_locations: Dict[str, str],
                                      current_month: int = 1,
                                      title: str = "季节性商品分布") -> go.Figure:
        fig = go.Figure()

        self._add_warehouse_structure(fig)

        season_groups = {st: {'x': [], 'y': [], 'z': [], 'text': []}
                      for st in SeasonalityType}

        for prod_id, loc_id in product_locations.items():
            prod = self.warehouse.products.get(prod_id)
            loc = self.warehouse.locations.get(loc_id)
            if not prod or not loc:
                continue

            if prod.seasonal_pattern:
                st = prod.seasonal_pattern.seasonality_type
            else:
                st = SeasonalityType.NONE

            is_peak = False
            if prod.seasonal_pattern and current_month in prod.seasonal_pattern.peak_seasons:
                is_peak = True

            season_groups[st]['x'].append(loc.x)
            season_groups[st]['y'].append(loc.y)
            season_groups[st]['z'].append(loc.z)
            season_groups[st]['text'].append(
                f'商品: {prod.name}<br>'
                f'季节性: {st.value}<br>'
                f'强度: {prod.seasonal_pattern.seasonality_strength:.2f}'
            )

        for st, data in season_groups.items():
            if not data['x']:
                continue

            color = self.season_colors.get(st, '#808080')
            fig.add_trace(go.Scatter3d(
                x=data['x'], y=data['y'], z=data['z'],
                mode='markers',
                marker=dict(
                    size=10,
                    color=color,
                    opacity=0.8,
                    symbol='cube'
                ),
                text=data['text'],
                hoverinfo='text',
                name=st.value
            ))

        self._add_depot(fig)
        self._update_layout(fig, title)

        return fig

    def create_time_series_decomposition_plot(self, original: np.ndarray,
                                              trend: np.ndarray,
                                              seasonal: np.ndarray,
                                              title: str = "时间序列分解") -> go.Figure:
        fig = go.Figure()

        days = list(range(len(original)))

        fig.add_trace(go.Scatter(
            x=days, y=original,
            mode='lines',
            name='原始数据',
            line=dict(color='gray', width=1),
            opacity=0.5
        ))

        fig.add_trace(go.Scatter(
            x=days, y=trend,
            mode='lines',
            name='趋势项',
            line=dict(color='red', width=2)
        ))

        fig.add_trace(go.Scatter(
            x=days, y=seasonal,
            mode='lines',
            name='季节项',
            line=dict(color='blue', width=2)
        ))

        fig.update_layout(
            title=dict(text=title, x=0.5, font=dict(size=16)),
            xaxis_title='天数',
            yaxis_title='销量',
            width=800,
            height=400,
            template='plotly_white'
        )

        return fig

    def create_seasonality_distribution_chart(self, product_locations: Dict[str, str],
                                          title: str = "季节性分类分布") -> go.Figure:
        season_counts = {}

        for prod_id in product_locations.keys():
            prod = self.warehouse.products.get(prod_id)
            if prod and prod.seasonal_pattern:
                st = prod.seasonal_pattern.seasonality_type.value
                season_counts[st] = season_counts.get(st, 0) + 1

        fig = go.Figure(data=[go.Pie(
            labels=list(season_counts.keys()),
            values=list(season_counts.values()),
            hole=0.4,
            marker=dict(
                colors=[self.season_colors.get(SeasonalityType(st), '#7f7f7f')
                        for st in season_counts.keys()]
            )
        )])

        fig.update_layout(
            title=dict(text=title, x=0.5, font=dict(size=16)),
            width=500,
            height=450,
            showlegend=True
        )

        return fig

    def create_category_distribution_chart(self, product_locations: Dict[str, str],
                                            title: str = "商品分类分布") -> go.Figure:
        category_counts = {}

        for prod_id in product_locations.keys():
            prod = self.warehouse.products.get(prod_id)
            if prod:
                cat = prod.category
                category_counts[cat] = category_counts.get(cat, 0) + 1

        fig = go.Figure(data=[go.Pie(
            labels=list(category_counts.keys()),
            values=list(category_counts.values()),
            hole=0.4,
            marker=dict(
                colors=[self.category_colors.get(cat, '#7f7f7f')
                        for cat in category_counts.keys()]
            )
        )])

        fig.update_layout(
            title=dict(text=title, x=0.5, font=dict(size=16)),
            width=500,
            height=450,
            showlegend=True
        )

        return fig
