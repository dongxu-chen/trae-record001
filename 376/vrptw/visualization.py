import folium
from typing import List, Optional, Dict

from .models import Solution, ProblemData, Customer, Depot


class RouteVisualizer:
    COLOR_SCHEMES = [
        {
            "name": "红色系",
            "main": "#e53935",
            "light": "#ffcdd2",
            "dark": "#b71c1c",
            "gradient": ["#ff5252", "#e53935", "#d32f2f", "#c62828"]
        },
        {
            "name": "橙色系",
            "main": "#fb8c00",
            "light": "#ffe0b2",
            "dark": "#e65100",
            "gradient": ["#ffa726", "#fb8c00", "#f57c00", "#ef6c00"]
        },
        {
            "name": "黄色系",
            "main": "#fdd835",
            "light": "#fff9c4",
            "dark": "#f57f17",
            "gradient": ["#ffee58", "#fdd835", "#fbc02d", "#f9a825"]
        },
        {
            "name": "绿色系",
            "main": "#43a047",
            "light": "#c8e6c9",
            "dark": "#1b5e20",
            "gradient": ["#66bb6a", "#43a047", "#388e3c", "#2e7d32"]
        },
        {
            "name": "青色系",
            "main": "#00acc1",
            "light": "#b2ebf2",
            "dark": "#006064",
            "gradient": ["#26c6da", "#00acc1", "#0097a7", "#00838f"]
        },
        {
            "name": "蓝色系",
            "main": "#1e88e5",
            "light": "#bbdefb",
            "dark": "#0d47a1",
            "gradient": ["#42a5f5", "#1e88e5", "#1976d2", "#1565c0"]
        },
        {
            "name": "紫色系",
            "main": "#8e24aa",
            "light": "#e1bee7",
            "dark": "#4a148c",
            "gradient": ["#ab47bc", "#8e24aa", "#7b1fa2", "#6a1b9a"]
        },
        {
            "name": "粉色系",
            "main": "#ec407a",
            "light": "#f8bbd0",
            "dark": "#880e4f",
            "gradient": ["#f06292", "#ec407a", "#e91e63", "#d81b60"]
        },
        {
            "name": "棕色系",
            "main": "#6d4c41",
            "light": "#d7ccc8",
            "dark": "#3e2723",
            "gradient": ["#8d6e63", "#6d4c41", "#5d4037", "#4e342e"]
        },
        {
            "name": "灰色系",
            "main": "#546e7a",
            "light": "#cfd8dc",
            "dark": "#263238",
            "gradient": ["#78909c", "#546e7a", "#455a64", "#37474f"]
        },
    ]

    DEPOT_COLORS = [
        {"main": "#2c3e50", "icon": "🏭", "name": "仓库A"},
        {"main": "#27ae60", "icon": "🏬", "name": "仓库B"},
        {"main": "#8e44ad", "icon": "🏢", "name": "仓库C"},
        {"main": "#d35400", "icon": "🏪", "name": "仓库D"},
        {"main": "#16a085", "icon": "🏘️", "name": "仓库E"},
    ]

    def __init__(self, data: ProblemData, solution: Solution):
        self.data = data
        self.solution = solution
        self._customer_map = {c.id: c for c in data.customers}
        self._depot_map = {d.id: d for d in data.depots}

    def get_route_color(self, route_idx: int) -> Dict[str, str]:
        scheme = self.COLOR_SCHEMES[route_idx % len(self.COLOR_SCHEMES)]
        return scheme

    def get_depot_color(self, depot_id: int) -> Dict[str, str]:
        return self.DEPOT_COLORS[depot_id % len(self.DEPOT_COLORS)]

    def create_map(self, zoom_start: int = 13) -> str:
        if self.data.depots:
            center_depot = self.data.depots[0]
            center_lat, center_lon = center_depot.y, center_depot.x
        else:
            center_lat, center_lon = 39.904, 116.407

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles="OpenStreetMap",
        )

        for depot in self.data.depots:
            self._add_depot_marker(m, depot)

        for cust in self.data.customers:
            self._add_customer_marker(m, cust)

        for idx, route in enumerate(self.solution.routes):
            color_scheme = self.get_route_color(idx)
            self._add_route(m, route, color_scheme, idx + 1)

        self._add_legend(m)

        map_html = m._repr_html_()
        return map_html

    def _add_depot_marker(self, m: folium.Map, depot: Depot):
        depot_color = self.get_depot_color(depot.id)
        icon_html = f"""
        <div style="
            background: linear-gradient(135deg, {depot_color['main']} 0%, #34495e 100%);
            color: white;
            border-radius: 50%;
            width: 38px;
            height: 38px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            border: 3px solid #fff;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3), 0 0 0 3px rgba(52, 73, 94, 0.3);
        ">
            {depot_color['icon']}
        </div>
        """
        icon = folium.DivIcon(html=icon_html, icon_size=(38, 38))
        folium.Marker(
            location=[depot.y, depot.x],
            popup=folium.Popup(
                f"<b>{depot_color['name']} (仓库 #{depot.id})</b><br>"
                f"坐标: ({depot.x:.4f}, {depot.y:.4f})<br>"
                f"车辆数: {depot.num_vehicles}<br>"
                f"容量: {depot.vehicle_capacity}",
                max_width=220,
            ),
            icon=icon,
            z_index_offset=1000,
        ).add_to(m)

    def _add_customer_marker(self, m: folium.Map, cust: Customer):
        depot_id = cust.assigned_depot or 0
        depot_color = self.get_depot_color(depot_id)
        
        icon_html = f"""
        <div style="
            background: {depot_color['main']};
            color: white;
            border-radius: 50%;
            width: 26px;
            height: 26px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: bold;
            border: 2px solid #fff;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        ">
            {cust.id}
        </div>
        """
        icon = folium.DivIcon(html=icon_html, icon_size=(26, 26))

        popup_html = f"""
        <b>客户 #{cust.id}</b><br>
        坐标: ({cust.x:.4f}, {cust.y:.4f})<br>
        需求: {cust.demand:.1f}<br>
        时间窗: [{cust.ready_time:.0f}, {cust.due_time:.0f}]<br>
        服务时长: {cust.service_time:.0f}<br>
        分配仓库: {self.get_depot_color(depot_id)['name']}
        """
        folium.Marker(
            location=[cust.y, cust.x],
            popup=folium.Popup(popup_html, max_width=280),
            icon=icon,
        ).add_to(m)

    def _add_route(
        self, m: folium.Map, route, color_scheme: Dict[str, str], route_id: int
    ):
        depot_id = route.depot_id
        depot = self._depot_map.get(depot_id)
        if not depot:
            return

        points = [(depot.y, depot.x)]

        for cust_id in route.customer_ids:
            cust = self._customer_map.get(cust_id)
            if cust:
                points.append((cust.y, cust.x))

        points.append((depot.y, depot.x))

        main_color = color_scheme["main"]
        dark_color = color_scheme["dark"]
        scheme_name = color_scheme["name"]

        if len(points) >= 2:
            line = folium.PolyLine(
                locations=points,
                color=main_color,
                weight=5,
                opacity=0.85,
                popup=folium.Popup(
                    f"<div style='font-family: Arial, sans-serif;'>"
                    f"<b style='color: {main_color}; font-size: 14px;'>{scheme_name} - 车辆 #{route.vehicle_id}</b><br>"
                    f"<hr style='margin: 4px 0;'>"
                    f"<b>仓库:</b> {self.get_depot_color(depot_id)['name']}<br>"
                    f"<b>距离:</b> {route.total_distance:.2f} km<br>"
                    f"<b>装载:</b> {route.total_demand:.1f}/{depot.vehicle_capacity}<br>"
                    f"<b>等待:</b> {route.waiting_time:.0f} min<br>"
                    f"<b>迟到:</b> {route.lateness:.0f} min<br>"
                    f"<b>CO₂排放:</b> {route.carbon_emission:.2f} kg<br>"
                    f"<b>途经:</b> {len(route.customer_ids)} 个客户"
                    f"</div>",
                    max_width=300,
                ),
            )
            line.add_to(m)

            arrow_markers = []
            for i in range(len(points) - 1):
                mid_lat = (points[i][0] + points[i + 1][0]) / 2
                mid_lon = (points[i][1] + points[i + 1][1]) / 2
                arrow_markers.append((mid_lat, mid_lon))

            for i, (lat, lon) in enumerate(arrow_markers):
                arrow_icon = folium.DivIcon(
                    html=f"""
                    <div style="
                        color: {dark_color};
                        font-size: 18px;
                        font-weight: bold;
                        text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white, 0 0 4px white;
                    ">
                        ➤
                    </div>
                    """,
                    icon_size=(18, 18),
                )
                folium.Marker(
                    location=[lat, lon],
                    icon=arrow_icon,
                    tooltip=f"{scheme_name} - 车辆 #{route.vehicle_id} 段 {i + 1}",
                ).add_to(m)

    def _add_legend(self, m: folium.Map):
        legend_html = """
        <div style="
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
            background: white;
            padding: 16px;
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05);
            font-size: 12px;
            font-family: Arial, sans-serif;
            max-width: 300px;
            max-height: 450px;
            overflow-y: auto;
        ">
        """

        legend_html += """
            <div style="border-bottom: 2px solid #3498db; padding-bottom: 8px; margin-bottom: 12px;">
                <b style="font-size: 14px; color: #2c3e50;">📊 路径规划结果</b>
            </div>
        """

        for depot in self.data.depots:
            depot_color = self.get_depot_color(depot.id)
            legend_html += f"""
            <div style="margin-bottom: 6px; display: flex; align-items: center;">
                <div style="width: 18px; height: 18px; background: {depot_color['main']}; 
                     border-radius: 50%; margin-right: 8px; border: 2px solid #fff;
                     box-shadow: 0 1px 3px rgba(0,0,0,0.3);"></div>
                <span style="color: #555;">{depot_color['icon']} {depot_color['name']} (#{depot.id})</span>
            </div>
            """

        legend_html += """
            <div style="margin-bottom: 8px; display: flex; align-items: center; padding-left: 4px;">
                <div style="width: 14px; height: 14px; background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); 
                     border-radius: 50%; margin-right: 8px; border: 2px solid #fff;
                     box-shadow: 0 1px 3px rgba(0,0,0,0.3);"></div>
                <span style="color: #555;">🔵 客户位置</span>
            </div>
        """

        legend_html += """
            <div style="border-top: 1px dashed #ddd; padding-top: 10px; margin-bottom: 10px;">
                <b style="color: #2c3e50;">🚛 车辆路线</b>
            </div>
        """

        for idx, route in enumerate(self.solution.routes):
            color_scheme = self.get_route_color(idx)
            main_color = color_scheme["main"]
            dark_color = color_scheme["dark"]
            scheme_name = color_scheme["name"]
            depot_color = self.get_depot_color(route.depot_id)
            
            legend_html += f"""
            <div style="
                margin-bottom: 10px;
                padding: 8px;
                background: {color_scheme['light']};
                border-radius: 8px;
                border-left: 4px solid {main_color};
            ">
                <div style="display: flex; align-items: center; margin-bottom: 4px;">
                    <div style="width: 16px; height: 16px; background: {main_color}; 
                         border-radius: 50%; margin-right: 6px;"></div>
                    <b style="color: {dark_color};">{scheme_name} #{route.vehicle_id}</b>
                    <span style="margin-left: 4px; color: #888; font-size: 10px;">
                        ({depot_color['name']})
                    </span>
                </div>
                <div style="font-size: 11px; color: #555; padding-left: 22px;">
                    📏 {route.total_distance:.2f}km | 🌱 {route.carbon_emission:.1f}kg CO₂
                </div>
            </div>
            """

        legend_html += f"""
            <div style="border-top: 2px solid #3498db; padding-top: 10px; margin-top: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: #666;">总距离:</span>
                    <b>{self.solution.total_distance:.2f} km</b>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: #666;">使用车辆:</span>
                    <b>{self.solution.used_vehicles} 辆</b>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: #666;">平均装载率:</span>
                    <b>{self.solution.avg_load_rate * 100:.1f}%</b>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: #666;">🌱 CO₂排放:</span>
                    <b style="color: #27ae60;">{self.solution.total_carbon_emission:.2f} kg</b>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: #666;">💰 碳成本:</span>
                    <b>¥{self.solution.carbon_cost:.2f}</b>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #666;">可行性:</span>
                    <b style="color: {'#27ae60' if self.solution.is_feasible else '#e74c3c'};">
                        {'✅ 可行' if self.solution.is_feasible else '⚠ 有迟到'}
                    </b>
                </div>
            </div>
        </div>
        """

        m.get_root().html.add_child(folium.Element(legend_html))

    def save_map(self, filepath: str):
        map_html = self.create_map()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(map_html)

    def get_map_html(self) -> str:
        return self.create_map()