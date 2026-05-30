import { create } from 'zustand';
import type { Shape, Shape3D, ShapeRelation, Point, DrawPath, CalibrationData, DXFExportOptions } from '../../shared/types';
import { recognizeShapes, correctShape, convertPixelToReal } from '../utils/shapeRecognition';
import { infer3DShapes } from '../utils/shape3DInference';
import { detectShapeRelations } from '../utils/shapeRelations';
import { downloadDXF } from '../utils/dxfExporter';

type ToolMode = 'draw' | 'select' | 'edit' | 'pan' | 'calibrate';
type ViewMode = '2d' | '3d' | 'both';

interface CanvasState {
  shapes: Shape[];
  shapes3D: Shape3D[];
  relations: ShapeRelation[];
  selectedShapeId: string | null;
  selectedShape3DId: string | null;
  selectedRelationIds: Set<string>;
  drawPaths: DrawPath[];
  currentPath: Point[];
  backgroundImage: string | null;
  toolMode: ToolMode;
  viewMode: ViewMode;
  showRelations: boolean;
  isDrawing: boolean;
  isRecognizing: boolean;
  zoom: number;
  panOffset: Point;
  mousePosition: Point;
  selectedVertexIndex: number | null;
  history: { shapes: Shape[]; shapes3D: Shape3D[]; relations: ShapeRelation[]; drawPaths: DrawPath[] }[];
  historyIndex: number;
  calibration: CalibrationData;

  setToolMode: (mode: ToolMode) => void;
  setViewMode: (mode: ViewMode) => void;
  setShowRelations: (show: boolean) => void;
  setBackgroundImage: (image: string | null) => void;
  startDrawing: (point: Point) => void;
  continueDrawing: (point: Point) => void;
  finishDrawing: () => void;
  selectShape: (id: string | null) => void;
  selectShape3D: (id: string | null) => void;
  toggleRelationSelection: (id: string) => void;
  selectVertex: (index: number | null) => void;
  updateShapePoints: (shapeId: string, points: Point[]) => void;
  setShapes: (shapes: Shape[]) => void;
  infer3DShapes: (canvasWidth: number, canvasHeight: number) => void;
  detectRelations: (canvasWidth: number, canvasHeight: number) => void;
  recognizeFromCanvas: (canvas: HTMLCanvasElement) => Promise<void>;
  correctSelectedShape: () => void;
  correctAllShapes: () => void;
  clearCanvas: () => void;
  undo: () => void;
  redo: () => void;
  setZoom: (zoom: number) => void;
  setPanOffset: (offset: Point) => void;
  setMousePosition: (pos: Point) => void;
  exportCanvas: (canvas: HTMLCanvasElement) => void;
  exportToDXF: (options?: DXFExportOptions) => void;
  saveHistory: () => void;
  setCalibration: (data: Partial<CalibrationData>) => void;
  resetCalibration: () => void;
  getRealValue: (pixelValue: number) => number;
  getUnitLabel: () => string;
}

const defaultCalibration: CalibrationData = {
  enabled: false,
  pixelLength: 1,
  realLength: 1,
  unit: 'px',
  startPoint: null,
  endPoint: null,
};

const initialState = {
  shapes: [],
  shapes3D: [],
  relations: [],
  selectedShapeId: null,
  selectedShape3DId: null,
  selectedRelationIds: new Set<string>(),
  drawPaths: [],
  currentPath: [],
  backgroundImage: null,
  toolMode: 'draw' as ToolMode,
  viewMode: '2d' as ViewMode,
  showRelations: true,
  isDrawing: false,
  isRecognizing: false,
  zoom: 1,
  panOffset: { x: 0, y: 0 },
  mousePosition: { x: 0, y: 0 },
  selectedVertexIndex: null,
  history: [],
  historyIndex: -1,
  calibration: { ...defaultCalibration },
};

export const useCanvasStore = create<CanvasState>((set, get) => ({
  ...initialState,

  setToolMode: (mode) => set({ toolMode: mode, selectedVertexIndex: null }),

  setViewMode: (mode) => set({ viewMode: mode }),

  setShowRelations: (show) => set({ showRelations: show }),

  setBackgroundImage: (image) => set({ backgroundImage: image }),

  startDrawing: (point) => {
    const { toolMode, calibration } = get();
    if (toolMode === 'draw') {
      set({ isDrawing: true, currentPath: [point] });
    } else if (toolMode === 'calibrate') {
      if (!calibration.startPoint) {
        set({ calibration: { ...calibration, startPoint: point, endPoint: null } });
      } else if (!calibration.endPoint) {
        set({ calibration: { ...calibration, endPoint: point } });
      } else {
        set({ calibration: { ...calibration, startPoint: point, endPoint: null } });
      }
    }
  },

  continueDrawing: (point) => {
    const { isDrawing, currentPath } = get();
    if (isDrawing) {
      set({ currentPath: [...currentPath, point] });
    }
  },

  finishDrawing: () => {
    const { isDrawing, currentPath, drawPaths, saveHistory } = get();
    if (isDrawing && currentPath.length > 1) {
      saveHistory();
      set({
        isDrawing: false,
        drawPaths: [...drawPaths, { points: currentPath, color: '#ffffff', lineWidth: 3 }],
        currentPath: [],
      });
    } else {
      set({ isDrawing: false, currentPath: [] });
    }
  },

  selectShape: (id) => set({ selectedShapeId: id, selectedShape3DId: null, selectedVertexIndex: null }),

  selectShape3D: (id) => set({ selectedShape3DId: id, selectedShapeId: null, selectedVertexIndex: null }),

  toggleRelationSelection: (id) => {
    const { selectedRelationIds } = get();
    const newSet = new Set(selectedRelationIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    set({ selectedRelationIds: newSet });
  },

  selectVertex: (index) => set({ selectedVertexIndex: index }),

  updateShapePoints: (shapeId, points) => {
    const { shapes, saveHistory } = get();
    saveHistory();
    set({
      shapes: shapes.map((s) =>
        s.id === shapeId
          ? {
              ...s,
              points,
              area: calculateArea(points),
              perimeter: calculatePerimeter(points),
              center: calculateCenter(points),
              boundingBox: calculateBoundingBox(points),
            }
          : s
      ),
    });
  },

  setShapes: (shapes) => {
    const { saveHistory } = get();
    saveHistory();
    set({ shapes, selectedShapeId: null, shapes3D: [], relations: [] });
  },

  infer3DShapes: (canvasWidth, canvasHeight) => {
    const { shapes, saveHistory } = get();
    if (shapes.length === 0) return;

    const inferred = infer3DShapes(shapes);
    const updatedShapes = shapes.map(s => {
      const s3d = inferred.find(i => i.sourceShapeId === s.id);
      return s3d ? { ...s, shape3DId: s3d.id } : s;
    });

    saveHistory();
    set({ shapes3D: inferred, shapes: updatedShapes, viewMode: '3d' });
  },

  detectRelations: (canvasWidth, canvasHeight) => {
    const { shapes, saveHistory } = get();
    if (shapes.length < 2) return;

    const relations = detectShapeRelations(shapes, canvasWidth, canvasHeight);
    saveHistory();
    set({ relations, showRelations: true });
  },

  recognizeFromCanvas: async (canvas) => {
    set({ isRecognizing: true });

    try {
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error('无法获取Canvas上下文');

      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

      let recognizedShapes: Shape[] = [];
      let recognizedShapes3D: Shape3D[] = [];
      let recognizedRelations: ShapeRelation[] = [];

      try {
        const response = await fetch('/api/shapes/recognize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            imageData: canvas.toDataURL('image/png'),
            options: {
              minContourArea: 100,
              epsilonFactor: 0.02,
              enableCorrection: true,
              enable3DInference: true,
              enableRelationDetection: true,
            },
          }),
        });

        const result = await response.json();

        if (result.success && result.shapes && result.shapes.length > 0) {
          recognizedShapes = result.shapes;
          recognizedShapes3D = result.shapes3D || [];
          recognizedRelations = result.relations || [];
        }
      } catch {
        // fallback to local
      }

      if (recognizedShapes.length === 0) {
        recognizedShapes = recognizeShapes(imageData, canvas.width, canvas.height, {
          minContourArea: 100,
          epsilonFactor: 0.02,
          enableCorrection: true,
        });

        recognizedShapes3D = infer3DShapes(recognizedShapes);
        recognizedShapes = recognizedShapes.map(s => {
          const s3d = recognizedShapes3D.find(i => i.sourceShapeId === s.id);
          return s3d ? { ...s, shape3DId: s3d.id } : s;
        });
        recognizedRelations = detectShapeRelations(recognizedShapes, canvas.width, canvas.height);
      }

      if (recognizedShapes.length > 0) {
        const { saveHistory } = get();
        saveHistory();
        set({
          shapes: recognizedShapes,
          shapes3D: recognizedShapes3D,
          relations: recognizedRelations,
          drawPaths: [],
          showRelations: true,
        });
      }
    } catch (error) {
      console.error('识别失败:', error);
    } finally {
      set({ isRecognizing: false });
    }
  },

  correctSelectedShape: () => {
    const { shapes, selectedShapeId, saveHistory } = get();
    if (!selectedShapeId) return;
    const shape = shapes.find(s => s.id === selectedShapeId);
    if (!shape || shape.corrected) return;

    saveHistory();
    const corrected = correctShape(shape);
    set({
      shapes: shapes.map(s => s.id === selectedShapeId ? corrected : s),
    });
  },

  correctAllShapes: () => {
    const { shapes, saveHistory } = get();
    const uncorrected = shapes.filter(s => !s.corrected);
    if (uncorrected.length === 0) return;

    saveHistory();
    set({
      shapes: shapes.map(s => s.corrected ? s : correctShape(s)),
    });
  },

  clearCanvas: () => {
    const { saveHistory } = get();
    saveHistory();
    set({
      shapes: [],
      shapes3D: [],
      relations: [],
      drawPaths: [],
      currentPath: [],
      selectedShapeId: null,
      selectedShape3DId: null,
      selectedVertexIndex: null,
      selectedRelationIds: new Set(),
    });
  },

  undo: () => {
    const { history, historyIndex } = get();
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      const state = history[newIndex];
      set({
        ...state,
        historyIndex: newIndex,
        selectedShapeId: null,
        selectedShape3DId: null,
        selectedVertexIndex: null,
        selectedRelationIds: new Set(),
      });
    }
  },

  redo: () => {
    const { history, historyIndex } = get();
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      const state = history[newIndex];
      set({
        ...state,
        historyIndex: newIndex,
        selectedShapeId: null,
        selectedShape3DId: null,
        selectedVertexIndex: null,
        selectedRelationIds: new Set(),
      });
    }
  },

  setZoom: (zoom) => set({ zoom: Math.max(0.1, Math.min(5, zoom)) }),

  setPanOffset: (offset) => set({ panOffset: offset }),

  setMousePosition: (pos) => set({ mousePosition: pos }),

  exportCanvas: (canvas) => {
    const link = document.createElement('a');
    link.download = `shapes-${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  },

  exportToDXF: (options = {}) => {
    const { shapes, shapes3D, calibration } = get();
    const defaultOptions: DXFExportOptions = {
      unit: calibration.enabled ? calibration.unit : 'mm',
      scale: calibration.enabled ? calibration.realLength / calibration.pixelLength : 1,
      separateLayers: true,
      includeConstructionLines: true,
    };

    const finalOptions = { ...defaultOptions, ...options };
    downloadDXF(shapes, shapes3D, finalOptions, `shapes-${Date.now()}.dxf`);
  },

  saveHistory: () => {
    const { shapes, shapes3D, relations, drawPaths, history, historyIndex } = get();
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push({
      shapes: [...shapes],
      shapes3D: [...shapes3D],
      relations: [...relations],
      drawPaths: [...drawPaths],
    });
    if (newHistory.length > 50) newHistory.shift();
    set({ history: newHistory, historyIndex: newHistory.length - 1 });
  },

  setCalibration: (data) => {
    const { calibration } = get();
    const newCal = { ...calibration, ...data };
    if (newCal.startPoint && newCal.endPoint) {
      const dx = newCal.endPoint.x - newCal.startPoint.x;
      const dy = newCal.endPoint.y - newCal.startPoint.y;
      newCal.pixelLength = Math.sqrt(dx * dx + dy * dy);
      if (newCal.pixelLength > 0 && newCal.realLength > 0) {
        newCal.enabled = true;
      }
    }
    set({ calibration: newCal });
  },

  resetCalibration: () => set({ calibration: { ...defaultCalibration } }),

  getRealValue: (pixelValue: number): number => {
    const { calibration } = get();
    if (!calibration.enabled || calibration.pixelLength <= 0) return pixelValue;
    return convertPixelToReal(pixelValue, calibration);
  },

  getUnitLabel: (): string => {
    const { calibration } = get();
    return calibration.enabled ? calibration.unit : 'px';
  },
}));

function calculateArea(points: Point[]): number {
  let area = 0;
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    area += points[i].x * points[j].y;
    area -= points[j].x * points[i].y;
  }
  return Math.abs(area) / 2;
}

function calculatePerimeter(points: Point[]): number {
  let perimeter = 0;
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    const dx = points[j].x - points[i].x;
    const dy = points[j].y - points[i].y;
    perimeter += Math.sqrt(dx * dx + dy * dy);
  }
  return perimeter;
}

function calculateCenter(points: Point[]): Point {
  let cx = 0, cy = 0;
  const n = points.length;
  for (const p of points) {
    cx += p.x;
    cy += p.y;
  }
  return { x: cx / n, y: cy / n };
}

function calculateBoundingBox(points: Point[]): { x: number; y: number; width: number; height: number } {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of points) {
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x);
    maxY = Math.max(maxY, p.y);
  }
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}
