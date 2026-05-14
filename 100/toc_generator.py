import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class NavPoint:
    label: str
    href: str
    order: int
    children: list['NavPoint'] = field(default_factory=list)


class TOCGenerator:
    def __init__(self, calibre_path: Optional[str] = None):
        self.calibre_path = calibre_path

    def _get_ebook_convert_path(self) -> str:
        if self.calibre_path:
            return str(Path(self.calibre_path) / 'ebook-convert')
        return 'ebook-convert'

    def _get_ebook_meta_path(self) -> str:
        if self.calibre_path:
            return str(Path(self.calibre_path) / 'ebook-meta')
        return 'ebook-meta'

    def generate_from_headings(self, epub_path: str, output_epub_path: Optional[str] = None) -> str:
        input_path = Path(epub_path)
        if not input_path.exists():
            raise FileNotFoundError(f'EPUB not found: {epub_path}')

        if output_epub_path is None:
            output_epub_path = str(input_path)

        cmd = [
            self._get_ebook_convert_path(),
            str(input_path),
            output_epub_path,
            '--level1-toc', '//h:h1',
            '--level2-toc', '//h:h2',
            '--level3-toc', '//h:h3',
            '--use-auto-toc'
        ]

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=True
            )
            return output_epub_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Failed to generate TOC: {e.stderr}') from e

    def parse_ncx(self, epub_path: str) -> list[NavPoint]:
        import zipfile

        input_path = Path(epub_path)
        if not input_path.exists():
            raise FileNotFoundError(f'EPUB not found: {epub_path}')

        nav_points: list[NavPoint] = []

        try:
            with zipfile.ZipFile(input_path, 'r') as zf:
                ncx_path = None
                for name in zf.namelist():
                    if name.lower().endswith('.ncx'):
                        ncx_path = name
                        break

                if ncx_path is None:
                    return nav_points

                with zf.open(ncx_path) as f:
                    tree = ET.parse(f)
                    root = tree.getroot()

                ns = {'n': 'http://www.daisy.org/z3986/2005/ncx/'}
                nav_map = root.find('.//n:navMap', ns)

                if nav_map is None:
                    return nav_points

                def parse_nav_point(element, order_start=1):
                    label_elem = element.find('n:navLabel/n:text', ns)
                    content_elem = element.find('n:content', ns)

                    label = label_elem.text if label_elem is not None else ''
                    href = content_elem.get('src') if content_elem is not None else ''
                    order = int(element.get('playOrder', order_start))

                    np = NavPoint(label=label, href=href, order=order)

                    for child in element.findall('n:navPoint', ns):
                        np.children.append(parse_nav_point(child))

                    return np

                for np_elem in nav_map.findall('n:navPoint', ns):
                    nav_points.append(parse_nav_point(np_elem))

        except Exception as e:
            raise RuntimeError(f'Failed to parse NCX: {e}') from e

        return nav_points

    def add_custom_toc(self, epub_path: str, nav_points: list[NavPoint],
                       output_epub_path: Optional[str] = None) -> str:
        input_path = Path(epub_path)
        if not input_path.exists():
            raise FileNotFoundError(f'EPUB not found: {epub_path}')

        if output_epub_path is None:
            output_epub_path = str(input_path)

        toc_entries = []
        for np in nav_points:
            toc_entries.append(f'{np.label}:{np.href}')

        cmd = [
            self._get_ebook_convert_path(),
            str(input_path),
            output_epub_path,
            '--toc-filter', ','.join(toc_entries)
        ]

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=True
            )
            return output_epub_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Failed to add custom TOC: {e.stderr}') from e
