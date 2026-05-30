import os
import re
import tempfile
import xml.etree.ElementTree as ET
from typing import Optional


class FormatExporter:
    def __init__(self, svg_path: str):
        self.svg_path = svg_path
        if not os.path.exists(svg_path):
            raise FileNotFoundError(f"SVG文件不存在: {svg_path}")

    def export(self, output_path: str, format: str = None):
        format = format or self._detect_format(output_path)
        format = format.lower().lstrip('.')

        exporters = {
            'svg': self._export_svg,
            'pdf': self._export_pdf,
            'eps': self._export_eps,
            'ai': self._export_ai,
        }

        if format not in exporters:
            raise ValueError(f"不支持的格式: {format}，支持: {list(exporters.keys())}")

        return exporters[format](output_path)

    @staticmethod
    def _detect_format(path: str) -> str:
        _, ext = os.path.splitext(path)
        return ext.lower().lstrip('.') or 'svg'

    def _export_svg(self, output_path: str) -> str:
        import shutil
        shutil.copy2(self.svg_path, output_path)
        return output_path

    def _export_pdf(self, output_path: str) -> str:
        try:
            import cairosvg
            cairosvg.svg2pdf(url=self.svg_path, write_to=output_path)
            return output_path
        except (ImportError, OSError):
            return self._export_pdf_reportlab(output_path)

    def _export_pdf_reportlab(self, output_path: str) -> str:
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.colors import Color

            width, height, paths_data = self._parse_svg_content()
            c = rl_canvas.Canvas(output_path, pagesize=(width, height))

            for path_info in paths_data:
                d = path_info['d']
                fill = path_info['fill']
                stroke = path_info['stroke']
                stroke_width = path_info.get('stroke_width', 1)

                if not d:
                    continue

                coords = self._parse_path_coords(d)
                if len(coords) < 2:
                    continue

                c.saveState()

                if fill and fill != 'none':
                    color = self._parse_rgb_for_reportlab(fill)
                    if color:
                        c.setFillColor(color)

                if stroke and stroke != 'none':
                    color = self._parse_rgb_for_reportlab(stroke)
                    if color:
                        c.setStrokeColor(color)
                    c.setLineWidth(stroke_width)

                p = c.beginPath()
                p.moveTo(coords[0][0], height - coords[0][1])
                for x, y in coords[1:]:
                    p.lineTo(x, height - y)
                p.close()

                c.drawPath(p, fill=1, stroke=1)
                c.restoreState()

            c.save()
            return output_path

        except ImportError:
            return self._export_pdf_fallback(output_path)

    def _export_pdf_fallback(self, output_path: str) -> str:
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPDF

            drawing = svg2rlg(self.svg_path)
            if drawing:
                renderPDF.drawToFile(drawing, output_path)
                return output_path
        except ImportError:
            pass

        width, height, paths_data = self._parse_svg_content()

        with open(output_path, 'wb') as f:
            objects = []
            obj_offset = 5

            content_lines = []
            for path_info in paths_data:
                d = path_info['d']
                fill = path_info['fill']
                stroke = path_info['stroke']

                if not d:
                    continue

                coords = self._parse_path_coords(d)
                if len(coords) < 2:
                    continue

                if fill and fill != 'none':
                    r, g, b = self._parse_rgb_for_eps(fill)
                    content_lines.append(f'{r:.4f} {g:.4f} {b:.4f} rg')

                if stroke and stroke != 'none':
                    r, g, b = self._parse_rgb_for_eps(stroke)
                    content_lines.append(f'{r:.4f} {g:.4f} {b:.4f} RG')
                    content_lines.append(f'{path_info.get("stroke_width", 1)} w')

                content_lines.append(f'{coords[0][0]:.2f} {height - coords[0][1]:.2f} m')
                for x, y in coords[1:]:
                    content_lines.append(f'{x:.2f} {height - y:.2f} l')
                content_lines.append('h f')

            content_str = '\n'.join(content_lines)

            f.write(b'%PDF-1.4\n')

            f.write(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
            f.write(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')

            page_obj = (
                f'3 0 obj\n'
                f'<< /Type /Page /Parent 2 0 R '
                f'/MediaBox [0 0 {width:.0f} {height:.0f}] '
                f'/Contents 4 0 R /Resources << >> >>\n'
                f'endobj\n'
            )
            f.write(page_obj.encode('latin-1'))

            content_bytes = content_str.encode('latin-1')
            content_obj = f'4 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n'
            f.write(content_obj.encode('latin-1'))
            f.write(content_bytes)
            f.write(b'\nendstream\nendobj\n')

            f.write(b'xref\n')
            f.write(b'0 5\n')
            f.write(b'0000000000 65535 f \n')
            for i in range(1, 5):
                f.write(f'{"0" * 9}{i} 00000 n \n'.encode('latin-1'))

            f.write(b'trailer\n<< /Size 5 /Root 1 0 R >>\n')
            f.write(b'startxref\n0\n%%EOF\n')

        return output_path

    @staticmethod
    def _parse_rgb_for_reportlab(color_str: str):
        match = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color_str)
        if match:
            try:
                from reportlab.lib.colors import Color
                r = int(match.group(1)) / 255.0
                g = int(match.group(2)) / 255.0
                b = int(match.group(3)) / 255.0
                return Color(r, g, b)
            except ImportError:
                return None
        return None

    def _export_eps(self, output_path: str) -> str:
        width, height, paths_data = self._parse_svg_content()

        with open(output_path, 'w', encoding='latin-1') as f:
            f.write('%!PS-Adobe-3.0 EPSF-3.0\n')
            f.write(f'%%BoundingBox: 0 0 {int(width)} {int(height)}\n')
            f.write('%%EndComments\n')
            f.write('%%BeginProlog\n')
            f.write('%%EndProlog\n')
            f.write('%%BeginSetup\n')
            f.write('%%EndSetup\n')
            f.write('%%Page: 1 1\n')

            for path_info in paths_data:
                d = path_info['d']
                fill = path_info['fill']
                stroke = path_info['stroke']
                stroke_width = path_info.get('stroke_width', 1)

                self._write_eps_path(f, d, fill, stroke, stroke_width)

            f.write('showpage\n')
            f.write('%%Trailer\n')
            f.write('%%EOF\n')

        return output_path

    def _export_ai(self, output_path: str) -> str:
        tmp_eps = output_path + '.tmp.eps'
        self._export_eps(tmp_eps)

        with open(tmp_eps, 'r', encoding='latin-1') as f:
            eps_content = f.read()
        os.remove(tmp_eps)

        width, height, _ = self._parse_svg_content()

        with open(output_path, 'w', encoding='latin-1') as f:
            f.write('%!PS-Adobe-3.0\n')
            f.write('%%Creator: RasterToVector AI Export\n')
            f.write(f'%%BoundingBox: 0 0 {int(width)} {int(height)}\n')
            f.write('%%HIResBoundingBox: 0 0 {:.4f} {:.4f}\n'.format(width, height))
            f.write('%%DocumentProcessColors: Cyan Magenta Yellow Black\n')
            f.write('%%DocumentCustomColors:\n')
            f.write('%%CMYKCustomColor:\n')
            f.write('%%EndComments\n')
            f.write('%%BeginProlog\n')
            f.write('/AI3_ReadAI8_Prolog {}\n')
            f.write('%%EndProlog\n')
            f.write('%%BeginSetup\n')
            f.write('%%EndSetup\n')
            f.write('%%Page: 1 1\n')
            f.write('%%BeginPageSetup\n')
            f.write('%%EndPageSetup\n')

            body_start = eps_content.find('%%Page: 1 1\n')
            if body_start != -1:
                body = eps_content[body_start + len('%%Page: 1 1\n'):]
                body_end = body.find('%%Trailer')
                if body_end != -1:
                    body = body[:body_end]
                f.write(body)
            else:
                f.write(eps_content)

            f.write('%%PageTrailer\n')
            f.write('%%Trailer\n')
            f.write('%%EOF\n')

        return output_path

    def _parse_svg_content(self):
        tree = ET.parse(self.svg_path)
        root = tree.getroot()
        ns = {'svg': 'http://www.w3.org/2000/svg'}

        try:
            width = float(root.get('width', 800))
            height = float(root.get('height', 600))
        except (ValueError, TypeError):
            width, height = 800, 600

        vb = root.get('viewBox')
        if vb:
            parts = vb.split()
            if len(parts) >= 4:
                width = float(parts[2])
                height = float(parts[3])

        path_elements = root.findall('.//svg:path', ns)
        if not path_elements:
            path_elements = root.findall('.//{http://www.w3.org/2000/svg}path')
        if not path_elements:
            path_elements = root.iter('path')

        paths = []
        for path_elem in path_elements:
            paths.append({
                'd': path_elem.get('d', ''),
                'fill': path_elem.get('fill', 'none'),
                'stroke': path_elem.get('stroke', 'none'),
                'stroke_width': float(path_elem.get('stroke-width', '1'))
            })

        return width, height, paths

    @staticmethod
    def _parse_path_coords(d: str):
        coords = []
        d = d.replace(',', ' ')
        tokens = d.strip().split()
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token in ('M', 'L', 'm', 'l'):
                i += 1
                if i + 1 < len(tokens):
                    try:
                        x = float(tokens[i])
                        y = float(tokens[i + 1])
                        coords.append((x, y))
                        i += 2
                    except ValueError:
                        i += 1
            elif token.upper() == 'Z':
                i += 1
            else:
                try:
                    x = float(token)
                    if i + 1 < len(tokens):
                        y = float(tokens[i + 1])
                        coords.append((x, y))
                        i += 2
                    else:
                        i += 1
                except ValueError:
                    i += 1
        return coords

    def _write_eps_path(self, f, d: str, fill: str, stroke: str, stroke_width: float):
        coords = self._parse_path_coords(d)
        if len(coords) < 2:
            return

        if fill and fill != 'none':
            r, g, b = self._parse_rgb_for_eps(fill)
            f.write(f'{r:.4f} {g:.4f} {b:.4f} setrgbcolor\n')

            f.write(f'newpath\n')
            f.write(f'{coords[0][0]:.2f} {coords[0][1]:.2f} moveto\n')
            for x, y in coords[1:]:
                f.write(f'{x:.2f} {y:.2f} lineto\n')
            f.write('closepath\n')
            f.write('fill\n')

        if stroke and stroke != 'none':
            r, g, b = self._parse_rgb_for_eps(stroke)
            f.write(f'{r:.4f} {g:.4f} {b:.4f} setrgbcolor\n')
            f.write(f'{stroke_width:.2f} setlinewidth\n')

            f.write(f'newpath\n')
            f.write(f'{coords[0][0]:.2f} {coords[0][1]:.2f} moveto\n')
            for x, y in coords[1:]:
                f.write(f'{x:.2f} {y:.2f} lineto\n')
            f.write('closepath\n')
            f.write('stroke\n')

    @staticmethod
    def _parse_rgb_for_eps(color_str: str):
        match = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color_str)
        if match:
            r = int(match.group(1)) / 255.0
            g = int(match.group(2)) / 255.0
            b = int(match.group(3)) / 255.0
            return r, g, b
        return 0.5, 0.5, 0.5

    @staticmethod
    def get_supported_formats():
        return ['svg', 'pdf', 'eps', 'ai']
