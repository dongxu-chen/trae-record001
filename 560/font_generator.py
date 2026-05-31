from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.ttLib.tables import _h_e_a_d, _h_h_e_a, _m_a_x_p, _h_m_t_x
from fontTools.ttLib.tables._v_h_e_a import table__v_h_e_a
from fontTools.pens.transformPen import TransformPen
import numpy as np
from typing import Dict, List, Tuple
import os
from config import Config


class FontGenerator:
    def __init__(self, font_name: str = "MyHandwriting", units_per_em: int = Config.FONT_UNITS_PER_EM):
        self.font_name = font_name
        self.units_per_em = units_per_em
        self.glyphs = {}
        self.adv_widths = {}
    
    def add_glyph(self, char: str, points: np.ndarray, advance_width: int = None):
        if points is None or len(points) < 2:
            return False
        
        if advance_width is None:
            x_coords = points[:, 0]
            width = np.max(x_coords) - np.min(x_coords)
            advance_width = int(width * 1.2)
        
        self.glyphs[char] = points
        self.adv_widths[char] = max(advance_width, 200)
        
        return True
    
    def _points_to_contour(self, points: np.ndarray) -> List[Tuple[int, int]]:
        contour = []
        for point in points:
            x = int(round(point[0]))
            y = int(round(point[1]))
            contour.append((x, y))
        return contour
    
    def _create_glyph_outline(self, pen: TTGlyphPen, points: np.ndarray):
        if points is None or len(points) < 3:
            return
        
        contour = self._points_to_contour(points)
        
        if len(contour) < 3:
            return
        
        pen.moveTo(contour[0])
        
        for point in contour[1:]:
            pen.lineTo(point)
        
        pen.closePath()
    
    def generate_ttf(self, output_path: str):
        font = TTFont()
        
        font.setGlyphOrder(['.notdef'])
        
        glyf_table = font.newTable('glyf')
        glyf_table.glyphs = {}
        
        pen = TTGlyphPen(None)
        pen.moveTo((0, 0))
        pen.lineTo((50, 0))
        pen.lineTo((50, 50))
        pen.lineTo((0, 50))
        pen.closePath()
        glyf_table.glyphs['.notdef'] = pen.glyph()
        
        cmap_data = {}
        
        for char, points in self.glyphs.items():
            glyph_name = f'uni{ord(char):04X}'
            font.glyphOrder.append(glyph_name)
            
            pen = TTGlyphPen(None)
            self._create_glyph_outline(pen, points)
            glyf_table.glyphs[glyph_name] = pen.glyph()
            
            cmap_data[ord(char)] = glyph_name
        
        head = font.newTable('head')
        head.unitsPerEm = self.units_per_em
        head.created = head.modified = 0
        head.magicNumber = 0x5F0F3CF5
        head.flags = 0
        head.macStyle = 0
        head.lowestRecPPEM = 8
        head.fontDirectionHint = 2
        head.indexToLocFormat = 0
        head.glyphDataFormat = 0
        head.xMin = Config.DESCENDER
        head.yMin = Config.DESCENDER
        head.xMax = Config.ASCENDER
        head.yMax = Config.ASCENDER
        
        hhea = font.newTable('hhea')
        hhea.ascent = Config.ASCENDER
        hhea.descent = Config.DESCENDER
        hhea.lineGap = 0
        hhea.advanceWidthMax = max(self.adv_widths.values()) if self.adv_widths else 500
        hhea.minLeftSideBearing = 0
        hhea.minRightSideBearing = 0
        hhea.xMaxExtent = hhea.advanceWidthMax
        hhea.caretSlopeRise = 1
        hhea.caretSlopeRun = 0
        hhea.caretOffset = 0
        hhea.reserved0 = 0
        hhea.reserved1 = 0
        hhea.reserved2 = 0
        hhea.reserved3 = 0
        hhea.metricDataFormat = 0
        hhea.numberOfHMetrics = len(self.glyphs) + 1
        
        maxp = font.newTable('maxp')
        maxp.tableVersion = 0x00010000
        maxp.numGlyphs = len(font.glyphOrder)
        maxp.maxPoints = 256
        maxp.maxContours = 1
        maxp.maxCompositePoints = 0
        maxp.maxCompositeContours = 0
        maxp.maxZones = 2
        maxp.maxTwilightPoints = 0
        maxp.maxStorage = 0
        maxp.maxFunctionDefs = 0
        maxp.maxInstructionDefs = 0
        maxp.maxStackElements = 0
        maxp.maxSizeOfInstructions = 0
        maxp.maxComponentElements = 0
        maxp.maxComponentDepth = 0
        
        hmtx = font.newTable('hmtx')
        hmtx.metrics = {}
        hmtx.metrics['.notdef'] = (500, 0)
        
        for char, points in self.glyphs.items():
            glyph_name = f'uni{ord(char):04X}'
            adv_width = self.adv_widths.get(char, 500)
            x_min = int(np.min(points[:, 0])) if len(points) > 0 else 0
            hmtx.metrics[glyph_name] = (adv_width, x_min)
        
        cmap = font.newTable('cmap')
        cmap.tableVersion = 0
        
        cmap_subtable = CmapSubtable.newSubtable(4)
        cmap_subtable.platformID = 3
        cmap_subtable.platEncID = 1
        cmap_subtable.language = 0
        cmap_subtable.cmap = cmap_data
        
        cmap.tables = [cmap_subtable]
        
        name = font.newTable('name')
        name.names = []
        
        name_string = self.font_name
        from fontTools.ttLib.tables._n_a_m_e import NameRecord
        
        def add_name(nameID, string):
            nr = NameRecord()
            nr.nameID = nameID
            nr.platformID = 3
            nr.platEncID = 1
            nr.langID = 0x409
            nr.string = string.encode('utf-16-be')
            name.names.append(nr)
        
        add_name(1, name_string)
        add_name(2, 'Regular')
        add_name(4, f'{name_string} Regular')
        add_name(6, name_string)
        
        os2 = font.newTable('OS/2')
        os2.version = 4
        os2.xAvgCharWidth = sum(self.adv_widths.values()) // len(self.adv_widths) if self.adv_widths else 500
        os2.usWeightClass = 400
        os2.usWidthClass = 5
        os2.fsType = 0
        os2.ySubscriptXSize = 650
        os2.ySubscriptYSize = 600
        os2.ySubscriptXOffset = 0
        os2.ySubscriptYOffset = 75
        os2.ySuperscriptXSize = 650
        os2.ySuperscriptYSize = 600
        os2.ySuperscriptXOffset = 0
        os2.ySuperscriptYOffset = 350
        os2.yStrikeoutSize = 50
        os2.yStrikeoutPosition = 300
        os2.sFamilyClass = 0
        os2.panose = b'\x00' * 10
        os2.ulUnicodeRange1 = 0xFFFFFFFF
        os2.ulUnicodeRange2 = 0xFFFFFFFF
        os2.ulUnicodeRange3 = 0xFFFFFFFF
        os2.ulUnicodeRange4 = 0xFFFFFFFF
        os2.achVendID = 'PUBL'
        os2.fsSelection = 64
        os2.usFirstCharIndex = min(cmap_data.keys()) if cmap_data else 0
        os2.usLastCharIndex = max(cmap_data.keys()) if cmap_data else 0
        os2.sTypoAscender = Config.ASCENDER
        os2.sTypoDescender = Config.DESCENDER
        os2.sTypoLineGap = 0
        os2.usWinAscent = Config.ASCENDER
        os2.usWinDescent = abs(Config.DESCENDER)
        os2.ulCodePageRange1 = 0xFFFFFFFF
        os2.ulCodePageRange2 = 0xFFFFFFFF
        
        post = font.newTable('post')
        post.formatType = 2.0
        post.italicAngle = 0
        post.underlinePosition = -100
        post.underlineThickness = 50
        post.isFixedPitch = 0
        post.minMemType42 = 0
        post.maxMemType42 = 0
        post.minMemType1 = 0
        post.maxMemType1 = 0
        
        font.save(output_path)
        return output_path
    
    def generate_otf(self, output_path: str):
        return self.generate_ttf(output_path)


class FontCreator:
    def __init__(self, font_name: str = "MyHandwritingFont"):
        self.font_name = font_name
        self.generator = FontGenerator(font_name)
        self.char_metrics = {}
    
    def process_points(self, points: np.ndarray, scale: float = 1.0) -> np.ndarray:
        if points is None or len(points) == 0:
            return None
        
        processed = points.copy()
        
        processed[:, 1] = -processed[:, 1]
        
        processed = processed * scale
        
        centroid = np.mean(processed, axis=0)
        processed = processed - centroid + np.array([250, 300])
        
        return processed
    
    def add_character(self, char: str, points: np.ndarray):
        if points is None or len(points) < 3:
            return False
        
        processed = self.process_points(points, scale=300)
        
        if processed is None:
            return False
        
        self.char_metrics[char] = {
            'original_points': points,
            'processed_points': processed
        }
        
        return self.generator.add_glyph(char, processed)
    
    def add_characters_from_dict(self, char_points_dict: Dict[str, np.ndarray]):
        success_count = 0
        for char, points in char_points_dict.items():
            if self.add_character(char, points):
                success_count += 1
        return success_count
    
    def create_font(self, output_dir: str, file_format: str = 'ttf') -> str:
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f'{self.font_name}.{file_format}')
        
        if file_format.lower() == 'otf':
            return self.generator.generate_otf(output_path)
        else:
            return self.generator.generate_ttf(output_path)
    
    def get_character_count(self) -> int:
        return len(self.char_metrics)
    
    def get_supported_chars(self) -> List[str]:
        return list(self.char_metrics.keys())


class BaseFontGenerator:
    def __init__(self):
        self.base_glyphs = {}
    
    def generate_base_char(self, char: str) -> np.ndarray:
        if char in self.base_glyphs:
            return self.base_glyphs[char]
        
        shape = self._get_char_shape(char)
        points = self._shape_to_points(shape)
        
        self.base_glyphs[char] = points
        return points
    
    def _get_char_shape(self, char: str) -> str:
        if char.isalpha():
            if char.islower():
                return 'oval'
            else:
                return 'rectangle'
        elif char.isdigit():
            return 'digit'
        else:
            return 'simple'
    
    def _shape_to_points(self, shape: str, num_points: int = 128) -> np.ndarray:
        if shape == 'oval':
            t = np.linspace(0, 2 * np.pi, num_points)
            x = 0.4 * np.cos(t)
            y = 0.6 * np.sin(t)
        elif shape == 'rectangle':
            points = []
            for i in range(num_points):
                t = i / num_points
                if t < 0.25:
                    x = t * 4
                    y = 1
                elif t < 0.5:
                    x = 1
                    y = 1 - (t - 0.25) * 4
                elif t < 0.75:
                    x = 1 - (t - 0.5) * 4
                    y = -1
                else:
                    x = -1
                    y = -1 + (t - 0.75) * 4
                x -= 0.5
                points.append((x, y * 0.6))
            return np.array(points)
        elif shape == 'digit':
            t = np.linspace(0, 2 * np.pi, num_points)
            x = 0.35 * np.cos(t)
            y = 0.5 * np.sin(t)
        else:
            t = np.linspace(0, 2 * np.pi, num_points)
            x = 0.4 * np.cos(t)
            y = 0.4 * np.sin(t)
        
        return np.column_stack([x, y])
