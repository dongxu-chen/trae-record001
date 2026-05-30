import type { Shape, Shape3D, DXFExportOptions, Point } from '../../shared/types';
import { SHAPE_NAMES, SHAPE3D_NAMES } from '../../shared/types';

function hexToDxfColor(hex: string): number {
  const h = hex.replace('#', '');
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);

  const colorMap: [number, number, number, number][] = [
    [0, 0, 0, 0],
    [255, 0, 0, 1],
    [255, 255, 0, 2],
    [0, 255, 0, 3],
    [0, 255, 255, 4],
    [0, 0, 255, 5],
    [255, 0, 255, 6],
    [255, 255, 255, 7],
    [128, 128, 128, 8],
    [192, 192, 192, 9],
  ];

  let minDist = Infinity;
  let nearestColor = 7;

  for (const [cr, cg, cb, index] of colorMap) {
    const dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2;
    if (dist < minDist) {
      minDist = dist;
      nearestColor = index;
    }
  }

  return nearestColor;
}

function dxfSection(sectionName: string, content: string): string {
  return `0
SECTION
2
${sectionName}
${content}0
ENDSEC
`;
}

function dxfHeader(unit: string = 'mm'): string {
  const units: Record<string, number> = {
    'unitless': 0,
    'in': 1,
    'ft': 2,
    'mm': 4,
    'cm': 5,
    'm': 6,
    'km': 7,
  };

  const insUnits = units[unit] || 4;

  return dxfSection('HEADER', `9
$ACADVER
1
AC1009
9
$INSBASE
10
0.0
20
0.0
30
0.0
9
$INSUNITS
70
${insUnits}
9
$EXTMIN
10
0.0
20
0.0
30
0.0
9
$EXTMAX
10
1000.0
20
1000.0
30
0.0
`);
}

function dxfTables(): string {
  return dxfSection('TABLES', `0
TABLE
2
LAYER
70
0
0
LAYER
2
0
70
0
62
7
6
CONTINUOUS
0
LAYER
2
RECTANGLES
70
0
62
1
6
CONTINUOUS
0
LAYER
2
CIRCLES
70
0
62
3
6
CONTINUOUS
0
LAYER
2
TRIANGLES
70
0
62
2
6
CONTINUOUS
0
LAYER
2
POLYGONS
70
0
62
6
6
CONTINUOUS
0
LAYER
2
DIMENSIONS
70
0
62
5
6
CONTINUOUS
0
LAYER
2
3D_SHAPES
70
0
62
4
6
CONTINUOUS
0
LAYER
2
RELATIONS
70
0
62
8
6
CONTINUOUS
0
ENDTAB
0
TABLE
2
LTYPE
70
0
0
LTYPE
2
CONTINUOUS
70
0
3
Solid line
72
65
73
0
40
0.0
0
ENDTAB
0
TABLE
2
STYLE
70
0
0
STYLE
2
STANDARD
70
0
40
0.0
41
1.0
50
0.0
71
0
42
2.5
3
txt
4

0
ENDTAB
`);
}

function dxfEntities(
  shapes: Shape[],
  shapes3D: Shape3D[],
  options: DXFExportOptions
): string {
  const { scale = 1, separateLayers = true } = options;

  let entities = '';

  for (const shape of shapes) {
    const layerName = separateLayers ? `${shape.type.toUpperCase()}S` : '0';
    const color = hexToDxfColor(shape.color || '#ffffff');

    if (shape.type === 'circle' && shape.radius) {
      const cx = shape.center.x * scale;
      const cy = -shape.center.y * scale;
      const r = shape.radius * scale;

      entities += `0
CIRCLE
8
${layerName}
62
${color}
10
${cx.toFixed(4)}
20
${cy.toFixed(4)}
30
0.0
40
${r.toFixed(4)}
`;
    } else {
      const points = shape.points;
      if (points.length >= 3) {
        let polyline = `0
LWPOLYLINE
8
${layerName}
62
${color}
70
1
`;

        for (const p of points) {
          polyline += `10
${(p.x * scale).toFixed(4)}
20
${(-p.y * scale).toFixed(4)}
`;
        }

        polyline += `40
0.0
`;
        entities += polyline;
      }
    }

    if (options.includeConstructionLines) {
      const cx = shape.center.x * scale;
      const cy = -shape.center.y * scale;

      entities += `0
TEXT
8
DIMENSIONS
62
5
10
${cx.toFixed(4)}
20
${(cy - 10 * scale).toFixed(4)}
30
0.0
40
${(2.5 * scale).toFixed(4)}
1
${SHAPE_NAMES[shape.type]}_${shape.id.substring(0, 4)}
`;
    }
  }

  for (const shape3d of shapes3D) {
    const layerName = '3D_SHAPES';
    const color = hexToDxfColor(shape3d.color || '#888888');

    for (const face of shape3d.faces) {
      if (face.points.length >= 3) {
        let polyline = `0
LWPOLYLINE
8
${layerName}
62
${color}
70
1
`;

        for (const p of face.points) {
          polyline += `10
${(p.x * scale).toFixed(4)}
20
${(-p.y * scale).toFixed(4)}
`;
        }

        polyline += `40
0.0
`;
        entities += polyline;
      }
    }

    if (options.includeConstructionLines) {
      const cx = shape3d.center.x * scale;
      const cy = -shape3d.center.y * scale;

      entities += `0
TEXT
8
DIMENSIONS
62
5
10
${cx.toFixed(4)}
20
${(cy - 20 * scale).toFixed(4)}
30
0.0
40
${(3 * scale).toFixed(4)}
1
${SHAPE3D_NAMES[shape3d.type]}
`;
    }
  }

  return dxfSection('ENTITIES', entities);
}

function dxfBlocks(): string {
  return dxfSection('BLOCKS', `0
BLOCK
2
*Model_Space
70
0
10
0.0
20
0.0
30
0.0
0
ENDBLK
0
BLOCK
2
*Paper_Space
70
0
10
0.0
20
0.0
30
0.0
0
ENDBLK
`);
}

function dxfObjects(): string {
  return dxfSection('OBJECTS', `0
DICTIONARY
3
ACAD_GROUP
0
ENDTAB
`);
}

export function exportToDXF(
  shapes: Shape[],
  shapes3D: Shape3D[] = [],
  options: DXFExportOptions = {}
): string {
  const { unit = 'mm', scale = 1 } = options;

  let dxf = `0
SECTION
2
HEADER
9
$ACADVER
1
AC1009
9
$INSBASE
10
0.0
20
0.0
30
0.0
0
ENDSEC
0
SECTION
2
CLASSES
0
ENDSEC
`;

  dxf += dxfTables();
  dxf += dxfBlocks();
  dxf += dxfEntities(shapes, shapes3D, options);

  dxf += `0
SECTION
2
OBJECTS
0
DICTIONARY
100
AcDbDictionary
3
ACAD_GROUP
0
ENDTAB
0
ENDSEC
0
EOF
`;

  return dxf;
}

export function downloadDXF(
  shapes: Shape[],
  shapes3D: Shape3D[] = [],
  options: DXFExportOptions = {},
  filename: string = 'shapes.dxf'
): void {
  const dxfContent = exportToDXF(shapes, shapes3D, options);
  const blob = new Blob([dxfContent], { type: 'application/dxf' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function exportShapesWithAnnotations(
  shapes: Shape[],
  shapes3D: Shape3D[] = [],
  options: DXFExportOptions = {}
): string {
  return exportToDXF(shapes, shapes3D, {
    ...options,
    includeConstructionLines: true,
  });
}

export function createDXFWithLayers(
  shapesByLayer: Record<string, Shape[]>,
  options: DXFExportOptions = {}
): string {
  const allShapes = Object.values(shapesByLayer).flat();
  return exportToDXF(allShapes, [], options);
}
