import os
import io
import numpy as np
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from config import DATA_DIR, AQI_LEVELS

REPORT_DIR = os.path.join(DATA_DIR, 'reports')
os.makedirs(REPORT_DIR, exist_ok=True)


class ReportGenerator:
    def __init__(self):
        self.page_width = 595
        self.page_height = 842
        self.margin = 50
        self.content_width = self.page_width - 2 * self.margin
        self.content_height = self.page_height - 2 * self.margin
        self.current_y = self.margin

    def generate_png_report(self, data_service, time_idx=0):
        img = Image.new('RGB', (self.page_width, self.page_height), 'white')
        draw = ImageDraw.Draw(img)
        
        self.current_y = self.margin
        
        self._draw_header(draw)
        self.current_y += 40
        
        self._draw_cover_info(draw, time_idx)
        self.current_y += 60
        
        self._draw_aqi_distribution(draw, data_service, time_idx)
        self.current_y += 220
        
        self._draw_time_series(draw, data_service)
        self.current_y += 180
        
        self._draw_stats_table(draw, data_service, time_idx)
        self.current_y += 30
        
        self._draw_footer(draw)
        
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()

    def _draw_header(self, draw):
        try:
            title_font = ImageFont.truetype("arial.ttf", 20)
        except:
            title_font = ImageFont.load_default()
        
        draw.rectangle([self.margin, self.current_y, 
                        self.page_width - self.margin, self.current_y + 40],
                       fill=(22, 93, 255))
        
        draw.text((self.margin + 10, self.current_y + 8), 
                  '空气质量预报评估报告', 
                  fill='white', font=title_font)
        
        self.current_y += 10

    def _draw_cover_info(self, draw, time_idx):
        try:
            normal_font = ImageFont.truetype("arial.ttf", 12)
            label_font = ImageFont.truetype("arial.ttf", 10)
        except:
            normal_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
        
        info_items = [
            ('预报起报时间', datetime.now().strftime('%Y-%m-%d %H:00:00')),
            ('预报时效', f'{time_idx}小时至{time_idx + 24}小时'),
            ('预报区域', '中国东部地区 (105°E-125°E, 20°N-40°N)'),
            ('生成时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ]
        
        for label, value in info_items:
            draw.text((self.margin, self.current_y), label + ':', fill=(100, 100, 100), font=label_font)
            draw.text((self.margin + 100, self.current_y), value, fill=(50, 50, 50), font=normal_font)
            self.current_y += 18

    def _draw_aqi_distribution(self, draw, data_service, time_idx):
        try:
            section_font = ImageFont.truetype("arial.ttf", 14)
        except:
            section_font = ImageFont.load_default()
        
        draw.text((self.margin, self.current_y), 'AQI空间分布', 
                  fill=(22, 93, 255), font=section_font)
        self.current_y += 25
        
        map_width = self.content_width
        map_height = 160
        
        draw.rectangle([self.margin, self.current_y, 
                        self.margin + map_width, self.current_y + map_height],
                       fill=(240, 245, 255), outline=(200, 200, 200))
        
        aqi_data = data_service.get_aqi_data(time_idx)
        if aqi_data and 'aqi_data' in aqi_data:
            self._draw_heatmap(draw, aqi_data['aqi_data'], 
                              self.margin, self.current_y, map_width, map_height)
        
        self._draw_colorbar(draw, self.margin, self.current_y + map_height + 10, map_width, 15)

    def _draw_heatmap(self, draw, aqi_data, x, y, w, h):
        aqi_array = np.array(aqi_data)
        ny, nx = aqi_array.shape
        
        color_map = {
            (0, 50): (0, 228, 0),
            (51, 100): (255, 255, 0),
            (101, 150): (255, 126, 0),
            (151, 200): (255, 0, 0),
            (201, 300): (153, 0, 76),
            (301, 500): (126, 0, 35),
        }
        
        def get_color(aqi):
            for (low, high), color in color_map.items():
                if low <= aqi <= high:
                    return color
            return (126, 0, 35)
        
        step_x = max(1, nx // 100)
        step_y = max(1, ny // 80)
        
        for j in range(0, ny, step_y):
            for i in range(0, nx, step_x):
                aqi = aqi_array[j, i]
                color = get_color(aqi)
                px = x + int(i / nx * w)
                py = y + int(j / ny * h)
                draw.rectangle([px, py, px + step_x * 2, py + step_y * 2], 
                              fill=color)

    def _draw_colorbar(self, draw, x, y, w, h):
        colors = ['#00E400', '#FFFF00', '#FF7E00', '#FF0000', '#99004C', '#7E0023']
        labels = ['优', '良', '轻度', '中度', '重度', '严重']
        
        segment_w = w // len(colors)
        
        for i, color in enumerate(colors):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            draw.rectangle([x + i * segment_w, y, x + (i + 1) * segment_w, y + h],
                          fill=(r, g, b))
        
        try:
            small_font = ImageFont.truetype("arial.ttf", 9)
        except:
            small_font = ImageFont.load_default()
        
        for i, label in enumerate(labels):
            draw.text((x + i * segment_w + segment_w // 2 - 10, y + h + 3), 
                      label, fill=(80, 80, 80), font=small_font)

    def _draw_time_series(self, draw, data_service):
        try:
            section_font = ImageFont.truetype("arial.ttf", 14)
            small_font = ImageFont.truetype("arial.ttf", 10)
        except:
            section_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        draw.text((self.margin, self.current_y), '区域平均AQI时间序列', 
                  fill=(22, 93, 255), font=section_font)
        self.current_y += 25
        
        chart_width = self.content_width
        chart_height = 140
        
        draw.rectangle([self.margin, self.current_y, 
                        self.margin + chart_width, self.current_y + chart_height],
                       fill=(248, 250, 252), outline=(220, 220, 220))
        
        hours = list(range(0, 72, 6))
        aqi_values = []
        for h in hours:
            try:
                data = data_service.get_aqi_data(h)
                if data and 'aqi_data' in data:
                    avg_aqi = np.mean(data['aqi_data'])
                    aqi_values.append(avg_aqi)
                else:
                    aqi_values.append(80)
            except:
                aqi_values.append(80)
        
        max_aqi = max(aqi_values) * 1.2 if aqi_values else 200
        
        points = []
        for i, (h, aqi) in enumerate(zip(hours, aqi_values)):
            px = self.margin + int(i / (len(hours) - 1) * (chart_width - 20)) + 10
            py = self.current_y + chart_height - int(aqi / max_aqi * (chart_height - 20)) - 10
            points.append((px, py))
        
        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]], fill=(22, 93, 255), width=2)
        
        for px, py in points:
            draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(22, 93, 255))
        
        for i, h in enumerate(hours):
            px = self.margin + int(i / (len(hours) - 1) * (chart_width - 20)) + 10
            draw.text((px - 10, self.current_y + chart_height + 5), 
                      f'T{h}', fill=(100, 100, 100), font=small_font)
        
        self.current_y += 20

    def _draw_stats_table(self, draw, data_service, time_idx):
        try:
            section_font = ImageFont.truetype("arial.ttf", 14)
            table_font = ImageFont.truetype("arial.ttf", 10)
        except:
            section_font = ImageFont.load_default()
            table_font = ImageFont.load_default()
        
        draw.text((self.margin, self.current_y), '预报统计摘要', 
                  fill=(22, 93, 255), font=section_font)
        self.current_y += 25
        
        col_widths = [80, 70, 70, 70, 70, 70]
        row_height = 20
        
        headers = ['AQI等级', '格点数', '占比(%)', '平均AQI', '最大值', '最小值']
        
        x = self.margin
        y = self.current_y
        
        for i, header in enumerate(headers):
            draw.rectangle([x, y, x + col_widths[i], y + row_height],
                          fill=(22, 93, 255))
            draw.text((x + 5, y + 4), header, fill='white', font=table_font)
            x += col_widths[i]
        
        y += row_height
        
        aqi_data = data_service.get_aqi_data(time_idx)
        if aqi_data and 'aqi_data' in aqi_data:
            aqi_array = np.array(aqi_data['aqi_data'])
            
            level_ranges = [
                ('优', 0, 50),
                ('良', 51, 100),
                ('轻度', 101, 150),
                ('中度', 151, 200),
                ('重度', 201, 300),
                ('严重', 301, 500),
            ]
            
            total = aqi_array.size
            
            for level_name, low, high in level_ranges:
                mask = (aqi_array >= low) & (aqi_array <= high)
                count = mask.sum()
                if count == 0:
                    continue
                
                level_data = aqi_array[mask]
                row_data = [
                    level_name,
                    str(count),
                    f'{count/total*100:.1f}',
                    f'{np.mean(level_data):.0f}',
                    f'{np.max(level_data):.0f}',
                    f'{np.min(level_data):.0f}',
                ]
                
                x = self.margin
                for i, cell in enumerate(row_data):
                    bg_color = (245, 248, 252) if y % 40 == row_height else 'white'
                    draw.rectangle([x, y, x + col_widths[i], y + row_height],
                                  fill=bg_color, outline=(220, 220, 220))
                    draw.text((x + 5, y + 4), cell, fill=(60, 60, 60), font=table_font)
                    x += col_widths[i]
                y += row_height

    def _draw_footer(self, draw):
        try:
            small_font = ImageFont.truetype("arial.ttf", 9)
        except:
            small_font = ImageFont.load_default()
        
        draw.line([self.margin, self.page_height - 40, 
                   self.page_width - self.margin, self.page_height - 40],
                  fill=(200, 200, 200))
        
        draw.text((self.margin, self.page_height - 30), 
                  '空气质量数值预报系统 | 自动生成报告', 
                  fill=(150, 150, 150), font=small_font)
        
        draw.text((self.page_width - self.margin - 100, self.page_height - 30), 
                  f'第 1 页', 
                  fill=(150, 150, 150), font=small_font)


report_generator = ReportGenerator()
