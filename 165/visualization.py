import math
from matrix import Matrix


def _rgb_to_hex(r, g, b):
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def _get_color(value, vmin, vmax, cmap='viridis'):
    normalized = (value - vmin) / (vmax - vmin) if vmax > vmin else 0.5
    normalized = max(0.0, min(1.0, normalized))
    
    colormaps = {
        'viridis': [
            (0.267004, 0.004874, 0.329415),
            (0.282623, 0.140926, 0.457517),
            (0.253935, 0.265254, 0.529983),
            (0.206756, 0.371758, 0.553117),
            (0.163625, 0.471133, 0.558148),
            (0.127568, 0.566949, 0.550556),
            (0.134692, 0.658636, 0.517649),
            (0.266941, 0.748751, 0.440573),
            (0.477504, 0.821444, 0.318195),
            (0.741388, 0.873449, 0.149561),
            (0.993248, 0.906157, 0.143936)
        ],
        'coolwarm': [
            (0.2298057, 0.298717966, 0.753683153),
            (0.535663421, 0.578169578, 0.87374046),
            (0.845579125, 0.857964421, 0.936129507),
            (0.967316515, 0.807971582, 0.768786961),
            (0.890882381, 0.511538244, 0.436082518),
            (0.705673185, 0.015556155, 0.150232805)
        ],
        'jet': [
            (0.0, 0.0, 0.5),
            (0.0, 0.0, 1.0),
            (0.0, 0.5, 1.0),
            (0.0, 1.0, 1.0),
            (0.5, 1.0, 0.5),
            (1.0, 1.0, 0.0),
            (1.0, 0.5, 0.0),
            (1.0, 0.0, 0.0),
            (0.5, 0.0, 0.0)
        ],
        'gray': [
            (0.0, 0.0, 0.0),
            (1.0, 1.0, 1.0)
        ],
        'hot': [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (1.0, 1.0, 1.0)
        ]
    }
    
    colors = colormaps.get(cmap, colormaps['viridis'])
    n = len(colors) - 1
    idx = normalized * n
    i = int(idx)
    t = idx - i
    
    if i >= n:
        r, g, b = colors[-1]
    else:
        c1 = colors[i]
        c2 = colors[i + 1]
        r = c1[0] + t * (c2[0] - c1[0])
        g = c1[1] + t * (c2[1] - c1[1])
        b = c1[2] + t * (c2[2] - c1[2])
    
    return _rgb_to_hex(r, g, b)


def heatmap(matrix, filename=None, title=None, cmap='viridis', 
            show_values=True, figsize=(800, 600), dpi=100):
    
    if not isinstance(matrix, Matrix):
        matrix = Matrix(matrix)
    
    data = matrix.data
    rows, cols = matrix.rows, matrix.cols
    
    all_values = [elem for row in data for elem in row]
    vmin = min(all_values)
    vmax = max(all_values)
    
    padding = 80
    cell_width = (figsize[0] - 2 * padding) / cols
    cell_height = (figsize[1] - 2 * padding) / rows
    
    svg_lines = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{figsize[0]}" height="{figsize[1]}" viewBox="0 0 {figsize[0]} {figsize[1]}">')
    
    svg_lines.append('<rect width="100%" height="100%" fill="white"/>')
    
    if title:
        svg_lines.append(f'<text x="{figsize[0]/2}" y="35" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" font-weight="bold">{title}</text>')
    
    for i in range(rows):
        for j in range(cols):
            x = padding + j * cell_width
            y = padding + i * cell_height
            color = _get_color(data[i][j], vmin, vmax, cmap)
            
            svg_lines.append(f'<rect x="{x}" y="{y}" width="{cell_width}" height="{cell_height}" fill="{color}" stroke="white" stroke-width="1"/>')
            
            if show_values:
                text_color = "white" if abs(data[i][j] - vmin) < (vmax - vmin) / 2 else "black"
                font_size = min(cell_width, cell_height) * 0.3
                value_str = f"{data[i][j]:.2f}" if abs(data[i][j]) >= 0.01 else f"{data[i][j]:.2e}"
                text_x = x + cell_width / 2
                text_y = y + cell_height / 2 + font_size / 3
                svg_lines.append(f'<text x="{text_x}" y="{text_y}" text-anchor="middle" font-family="monospace" font-size="{font_size}" fill="{text_color}">{value_str}</text>')
    
    bar_width = 30
    bar_height = figsize[1] - 2 * padding
    bar_x = figsize[0] - padding + 20
    bar_y = padding
    
    n_ticks = 5
    for i in range(100):
        y = bar_y + bar_height * (1 - i / 100)
        color = _get_color(vmin + (vmax - vmin) * i / 100, vmin, vmax, cmap)
        svg_lines.append(f'<rect x="{bar_x}" y="{y}" width="{bar_width}" height="{bar_height/100 + 1}" fill="{color}"/>')
    
    svg_lines.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" fill="none" stroke="black" stroke-width="1"/>')
    
    for tick in range(n_ticks + 1):
        value = vmin + (vmax - vmin) * tick / n_ticks
        y = bar_y + bar_height * (1 - tick / n_ticks)
        value_str = f"{value:.2f}" if abs(value) >= 0.01 else f"{value:.2e}"
        svg_lines.append(f'<line x1="{bar_x}" y1="{y}" x2="{bar_x - 8}" y2="{y}" stroke="black" stroke-width="1"/>')
        svg_lines.append(f'<text x="{bar_x - 12}" y="{y + 4}" text-anchor="end" font-family="Arial, sans-serif" font-size="12">{value_str}</text>')
    
    x_label_y = figsize[1] - 30
    svg_lines.append(f'<text x="{figsize[0]/2}" y="{x_label_y}" text-anchor="middle" font-family="Arial, sans-serif" font-size="14">列索引</text>')
    
    for j in range(min(10, cols)):
        x = padding + (j + 0.5) * cell_width
        svg_lines.append(f'<text x="{x}" y="{padding - 10}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">{j}</text>')
    
    for i in range(min(10, rows)):
        y = padding + (i + 0.5) * cell_height + 4
        svg_lines.append(f'<text x="{padding - 10}" y="{y}" text-anchor="end" font-family="Arial, sans-serif" font-size="12">{i}</text>')
    
    svg_lines.append('</svg>')
    svg_content = '\n'.join(svg_lines)
    
    if filename:
        if filename.lower().endswith('.svg'):
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            print(f"热力图已保存为: {filename}")
        else:
            svg_filename = filename.rsplit('.', 1)[0] + '.svg'
            with open(svg_filename, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            print(f"热力图已保存为: {svg_filename} (建议使用SVG格式)")
    else:
        return svg_content


def save_heatmap_png(matrix, filename, **kwargs):
    svg_filename = filename.rsplit('.', 1)[0] + '.svg'
    heatmap(matrix, svg_filename, **kwargs)
    print(f"SVG文件已生成: {svg_filename}")
    print("提示: 如需PNG格式，可使用浏览器或SVG编辑器打开SVG文件后导出。")


def spy(matrix, filename=None, precision=1e-10, figsize=(600, 600)):
    if not isinstance(matrix, Matrix):
        matrix = Matrix(matrix)
    
    rows, cols = matrix.rows, matrix.cols
    padding = 60
    cell_width = (figsize[0] - 2 * padding) / cols
    cell_height = (figsize[1] - 2 * padding) / rows
    
    svg_lines = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{figsize[0]}" height="{figsize[1]}" viewBox="0 0 {figsize[0]} {figsize[1]}">')
    svg_lines.append('<rect width="100%" height="100%" fill="white"/>')
    svg_lines.append(f'<text x="{figsize[0]/2}" y="35" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="bold">矩阵非零元素分布</text>')
    
    for i in range(rows):
        for j in range(cols):
            x = padding + j * cell_width
            y = padding + i * cell_height
            
            if abs(matrix[i][j]) > precision:
                svg_lines.append(f'<rect x="{x + 1}" y="{y + 1}" width="{cell_width - 2}" height="{cell_height - 2}" fill="darkblue"/>')
            else:
                svg_lines.append(f'<rect x="{x + 1}" y="{y + 1}" width="{cell_width - 2}" height="{cell_height - 2}" fill="#f0f0f0"/>')
    
    svg_lines.append('</svg>')
    svg_content = '\n'.join(svg_lines)
    
    if filename:
        svg_filename = filename.rsplit('.', 1)[0] + '.svg'
        with open(svg_filename, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        print(f"Spy图已保存为: {svg_filename}")
    else:
        return svg_content
