import React, { useRef, useEffect, useCallback } from 'react';
import { useCanvasStore } from '../store/canvasStore';
import { pointInPolygon, findNearestVertex, transformShape } from '../utils/shapeRecognition';
import { render3DShape } from '../utils/shape3DInference';
import { renderRelations } from '../utils/shapeRelations';
import type { Point } from '../../shared/types';
import { SHAPE_COLORS, SHAPE3D_NAMES, RELATION_NAMES } from '../../shared/types';

export const Canvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef<Point | null>(null);
  const panStartRef = useRef<Point | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    shapes,
    shapes3D,
    relations,
    selectedShapeId,
    selectedShape3DId,
    selectedRelationIds,
    drawPaths,
    currentPath,
    backgroundImage,
    toolMode,
    viewMode,
    showRelations,
    isRecognizing,
    zoom,
    panOffset,
    mousePosition,
    selectedVertexIndex,
    calibration,
    setToolMode,
    setViewMode,
    setShowRelations,
    setBackgroundImage,
    startDrawing,
    continueDrawing,
    finishDrawing,
    selectShape,
    selectShape3D,
    selectVertex,
    updateShapePoints,
    setZoom,
    setPanOffset,
    setMousePosition,
    clearCanvas,
    undo,
    redo,
    recognizeFromCanvas,
    exportCanvas,
    exportToDXF,
    correctSelectedShape,
    correctAllShapes,
    infer3DShapes,
    detectRelations,
    getRealValue,
    getUnitLabel,
  } = useCanvasStore();

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const resizeCanvas = () => {
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    return () => window.removeEventListener('resize', resizeCanvas);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    const gridSize = 20;
    for (let x = 0; x < canvas.width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }

    ctx.save();
    ctx.translate(panOffset.x, panOffset.y);
    ctx.scale(zoom, zoom);

    if (backgroundImage) {
      const img = new Image();
      img.src = backgroundImage;
      if (img.complete) {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      }
    }

    drawPaths.forEach((path) => {
      if (path.points.length < 2) return;
      ctx.strokeStyle = path.color;
      ctx.lineWidth = path.lineWidth;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();
      ctx.moveTo(path.points[0].x, path.points[0].y);
      for (let i = 1; i < path.points.length; i++) {
        ctx.lineTo(path.points[i].x, path.points[i].y);
      }
      ctx.stroke();
    });

    if (currentPath.length > 1) {
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();
      ctx.moveTo(currentPath[0].x, currentPath[0].y);
      for (let i = 1; i < currentPath.length; i++) {
        ctx.lineTo(currentPath[i].x, currentPath[i].y);
      }
      ctx.stroke();
    }

    if (showRelations && relations.length > 0) {
      renderRelations(ctx, relations, shapes, selectedRelationIds);
    }

    if (viewMode === '2d' || viewMode === 'both') {
      shapes.forEach((shape) => {
        if (viewMode === 'both' && shape.shape3DId) return;

        const isSelected = shape.id === selectedShapeId;
        const color = shape.color || SHAPE_COLORS[shape.type];

        ctx.fillStyle = isSelected ? `${color}40` : `${color}20`;
        ctx.strokeStyle = color;
        ctx.lineWidth = isSelected ? 3 : 2;

        if (shape.type === 'circle' && shape.radius) {
          ctx.beginPath();
          ctx.arc(shape.center.x, shape.center.y, shape.radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        } else {
          ctx.beginPath();
          if (shape.points.length > 0) {
            ctx.moveTo(shape.points[0].x, shape.points[0].y);
            for (let i = 1; i < shape.points.length; i++) {
              ctx.lineTo(shape.points[i].x, shape.points[i].y);
            }
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
          }
        }

        if (shape.corrected) {
          ctx.strokeStyle = '#22D3EE';
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 3]);
          if (shape.type === 'circle' && shape.radius) {
            ctx.beginPath();
            ctx.arc(shape.center.x, shape.center.y, shape.radius, 0, Math.PI * 2);
            ctx.stroke();
          } else if (shape.points.length > 0) {
            ctx.beginPath();
            ctx.moveTo(shape.points[0].x, shape.points[0].y);
            for (let i = 1; i < shape.points.length; i++) {
              ctx.lineTo(shape.points[i].x, shape.points[i].y);
            }
            ctx.closePath();
            ctx.stroke();
          }
          ctx.setLineDash([]);
        }

        if (isSelected) {
          ctx.strokeStyle = '#00D4FF';
          ctx.lineWidth = 2;
          ctx.setLineDash([5, 5]);
          const bbox = shape.boundingBox;
          ctx.strokeRect(bbox.x - 5, bbox.y - 5, bbox.width + 10, bbox.height + 10);
          ctx.setLineDash([]);

          const vertexRadius = 6;
          shape.points.forEach((point, index) => {
            if (shape.type === 'circle' && shape.points.length > 12) {
              if (index !== 0) return;
            }
            const isVertexSelected = index === selectedVertexIndex;
            ctx.fillStyle = isVertexSelected ? '#00D4FF' : '#ffffff';
            ctx.strokeStyle = '#00D4FF';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(point.x, point.y, isVertexSelected ? vertexRadius + 2 : vertexRadius, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
          });

          const unitLabel = getUnitLabel();
          ctx.fillStyle = '#ffffff';
          ctx.font = '12px Inter, sans-serif';

          let areaVal: number, perimVal: number;
          if (calibration.enabled) {
            const ratio = calibration.realLength / calibration.pixelLength;
            areaVal = shape.area * ratio * ratio;
            perimVal = shape.perimeter * ratio;
            ctx.fillText(`面积: ${areaVal.toFixed(2)} ${unitLabel}²`, shape.center.x, shape.center.y - 15);
            ctx.fillText(`周长: ${perimVal.toFixed(2)} ${unitLabel}`, shape.center.x, shape.center.y + 5);
          } else {
            ctx.fillText(`面积: ${shape.area.toFixed(1)} px²`, shape.center.x, shape.center.y - 15);
            ctx.fillText(`周长: ${shape.perimeter.toFixed(1)} px`, shape.center.x, shape.center.y + 5);
          }

          if (shape.corrected) {
            ctx.fillStyle = '#22D3EE';
            ctx.font = '11px Inter, sans-serif';
            ctx.fillText('✓ 已校正', shape.center.x, shape.center.y + 22);
          }

          if (shape.shape3DId) {
            const s3d = shapes3D.find(s => s.id === shape.shape3DId);
            if (s3d) {
              ctx.fillStyle = '#A78BFA';
              ctx.font = '11px Inter, sans-serif';
              ctx.fillText(`3D: ${SHAPE3D_NAMES[s3d.type]}`, shape.center.x, shape.center.y + 37);
            }
          }
        }
      });
    }

    if (viewMode === '3d' || viewMode === 'both') {
      shapes3D.forEach((shape3d) => {
        const isSelected = shape3d.id === selectedShape3DId;
        render3DShape(ctx, shape3d, isSelected, zoom);

        if (isSelected) {
          const unitLabel = getUnitLabel();
          ctx.fillStyle = '#ffffff';
          ctx.font = '12px Inter, sans-serif';
          ctx.textAlign = 'center';

          if (shape3d.volume) {
            let volVal: number;
            if (calibration.enabled) {
              const ratio = calibration.realLength / calibration.pixelLength;
              volVal = shape3d.volume * ratio * ratio * ratio;
              ctx.fillText(`体积: ${volVal.toFixed(2)} ${unitLabel}³`, shape3d.center.x, shape3d.center.y - 30);
            } else {
              ctx.fillText(`体积: ${shape3d.volume.toFixed(1)} px³`, shape3d.center.x, shape3d.center.y - 30);
            }
          }
          if (shape3d.surfaceArea) {
            let saVal: number;
            if (calibration.enabled) {
              const ratio = calibration.realLength / calibration.pixelLength;
              saVal = shape3d.surfaceArea * ratio * ratio;
              ctx.fillText(`表面积: ${saVal.toFixed(2)} ${unitLabel}²`, shape3d.center.x, shape3d.center.y - 15);
            } else {
              ctx.fillText(`表面积: ${shape3d.surfaceArea.toFixed(1)} px²`, shape3d.center.x, shape3d.center.y - 15);
            }
          }
          ctx.fillText(`${SHAPE3D_NAMES[shape3d.type]} (置信度: ${(shape3d.confidence * 100).toFixed(0)}%)`, shape3d.center.x, shape3d.center.y + 5);
          ctx.textAlign = 'left';
        }
      });
    }

    if (calibration.startPoint && calibration.endPoint && toolMode === 'calibrate') {
      ctx.strokeStyle = '#F59E0B';
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 4]);
      ctx.beginPath();
      ctx.moveTo(calibration.startPoint.x, calibration.startPoint.y);
      ctx.lineTo(calibration.endPoint.x, calibration.endPoint.y);
      ctx.stroke();
      ctx.setLineDash([]);

      const pixelLen = Math.sqrt(
        (calibration.endPoint.x - calibration.startPoint.x) ** 2 +
        (calibration.endPoint.y - calibration.startPoint.y) ** 2
      );
      const midX = (calibration.startPoint.x + calibration.endPoint.x) / 2;
      const midY = (calibration.startPoint.y + calibration.endPoint.y) / 2;

      ctx.fillStyle = '#F59E0B';
      ctx.beginPath();
      ctx.arc(calibration.startPoint.x, calibration.startPoint.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(calibration.endPoint.x, calibration.endPoint.y, 5, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#FEF3C7';
      ctx.font = '13px Space Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${pixelLen.toFixed(1)} px`, midX, midY - 10);
      ctx.textAlign = 'left';
    } else if (calibration.startPoint && toolMode === 'calibrate') {
      ctx.strokeStyle = '#F59E0B';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(calibration.startPoint.x, calibration.startPoint.y);
      ctx.lineTo(mousePosition.x, mousePosition.y);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = '#F59E0B';
      ctx.beginPath();
      ctx.arc(calibration.startPoint.x, calibration.startPoint.y, 5, 0, Math.PI * 2);
      ctx.fill();
    }

    if (calibration.enabled) {
      const refP = calibration.startPoint;
      const refE = calibration.endPoint;
      if (refP && refE) {
        ctx.strokeStyle = '#F59E0B80';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 6]);
        ctx.beginPath();
        ctx.moveTo(refP.x, refP.y);
        ctx.lineTo(refE.x, refE.y);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = '#F59E0B60';
        ctx.beginPath();
        ctx.arc(refP.x, refP.y, 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(refE.x, refE.y, 3, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    ctx.restore();

    if (isRecognizing) {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;

      ctx.strokeStyle = '#00D4FF';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(centerX, centerY, 40, 0, Math.PI * 1.5);
      ctx.stroke();

      ctx.fillStyle = '#ffffff';
      ctx.font = '16px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('正在识别形状...', centerX, centerY + 80);
      ctx.textAlign = 'left';
    }
  }, [
    shapes, shapes3D, relations,
    selectedShapeId, selectedShape3DId, selectedRelationIds,
    drawPaths, currentPath, backgroundImage,
    viewMode, showRelations,
    zoom, panOffset, isRecognizing, selectedVertexIndex,
    calibration, mousePosition,
    getUnitLabel,
  ]);

  const getCanvasPoint = useCallback((e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - panOffset.x) / zoom;
    const y = (e.clientY - rect.top - panOffset.y) / zoom;
    return { x, y };
  }, [zoom, panOffset]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const point = getCanvasPoint(e);
    const canvas = canvasRef.current;
    if (!canvas) return;

    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      isDraggingRef.current = true;
      panStartRef.current = { x: e.clientX - panOffset.x, y: e.clientY - panOffset.y };
      return;
    }

    if (toolMode === 'draw') {
      startDrawing(point);
      isDraggingRef.current = true;
      dragStartRef.current = point;
    } else if (toolMode === 'calibrate') {
      startDrawing(point);
    } else if (toolMode === 'select') {
      if (viewMode === '3d' || viewMode === 'both') {
        let found3D = false;
        for (let i = shapes3D.length - 1; i >= 0; i--) {
          const s3d = shapes3D[i];
          const centerPt = { x: s3d.center.x, y: s3d.center.y };
          const dist = Math.sqrt(
            (point.x - centerPt.x) ** 2 + (point.y - centerPt.y) ** 2
          );
          const avgSize = (s3d.size.width + s3d.size.height) / 2;
          if (dist < avgSize) {
            selectShape3D(s3d.id);
            found3D = true;
            break;
          }
        }
        if (found3D) return;
      }

      let foundShape = false;
      for (let i = shapes.length - 1; i >= 0; i--) {
        const shape = shapes[i];
        if (shape.type === 'circle' && shape.radius) {
          const dist = Math.sqrt(
            (point.x - shape.center.x) ** 2 + (point.y - shape.center.y) ** 2
          );
          if (dist <= shape.radius) {
            selectShape(shape.id);
            foundShape = true;
            break;
          }
        } else if (pointInPolygon(point, shape.points)) {
          selectShape(shape.id);
          foundShape = true;
          break;
        }
      }
      if (!foundShape) {
        selectShape(null);
        selectShape3D(null);
      }
    } else if (toolMode === 'edit' && selectedShapeId) {
      const shape = shapes.find(s => s.id === selectedShapeId);
      if (shape) {
        const vertexIndex = findNearestVertex(point, shape.points, 15 / zoom);
        if (vertexIndex !== null) {
          selectVertex(vertexIndex);
          isDraggingRef.current = true;
          dragStartRef.current = point;
        } else {
          if (shape.type === 'circle' && shape.radius) {
            const dist = Math.sqrt(
              (point.x - shape.center.x) ** 2 + (point.y - shape.center.y) ** 2
            );
            if (dist <= shape.radius) {
              isDraggingRef.current = true;
              dragStartRef.current = point;
            }
          } else if (pointInPolygon(point, shape.points)) {
            isDraggingRef.current = true;
            dragStartRef.current = point;
          }
        }
      }
    } else if (toolMode === 'pan') {
      isDraggingRef.current = true;
      panStartRef.current = { x: e.clientX - panOffset.x, y: e.clientY - panOffset.y };
    }
  }, [
    toolMode, viewMode,
    getCanvasPoint, startDrawing,
    shapes, shapes3D,
    selectedShapeId,
    selectShape, selectShape3D, selectVertex,
    panOffset, zoom,
  ]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const point = getCanvasPoint(e);
    setMousePosition(point);

    if (!isDraggingRef.current) return;

    if (panStartRef.current && (toolMode === 'pan' || e.altKey)) {
      const newOffset = {
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y,
      };
      setPanOffset(newOffset);
      return;
    }

    if (toolMode === 'draw') {
      continueDrawing(point);
    } else if (toolMode === 'edit' && selectedShapeId && selectedVertexIndex !== null) {
      const shape = shapes.find(s => s.id === selectedShapeId);
      if (shape) {
        const newPoints = [...shape.points];
        newPoints[selectedVertexIndex] = point;
        updateShapePoints(selectedShapeId, newPoints);
      }
    } else if (toolMode === 'edit' && selectedShapeId && dragStartRef.current) {
      const shape = shapes.find(s => s.id === selectedShapeId);
      if (shape) {
        const dx = point.x - dragStartRef.current.x;
        const dy = point.y - dragStartRef.current.y;
        const newPoints = transformShape(shape.points, 1, 0, { x: dx, y: dy });
        updateShapePoints(selectedShapeId, newPoints);
        dragStartRef.current = point;
      }
    }
  }, [
    toolMode, getCanvasPoint, continueDrawing,
    selectedShapeId, selectedVertexIndex, shapes,
    updateShapePoints, setMousePosition, setPanOffset,
  ]);

  const handleMouseUp = useCallback(() => {
    isDraggingRef.current = false;
    dragStartRef.current = null;
    panStartRef.current = null;

    if (toolMode === 'draw') {
      finishDrawing();
    }
  }, [toolMode, finishDrawing]);

  const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(zoom + delta);
  }, [zoom, setZoom]);

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      setBackgroundImage(dataUrl);

      const img = new Image();
      img.onload = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      };
      img.src = dataUrl;
    };
    reader.readAsDataURL(file);
  }, [setBackgroundImage]);

  const handleRecognize = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    recognizeFromCanvas(canvas);
  }, [recognizeFromCanvas]);

  const handleExport = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    exportCanvas(canvas);
  }, [exportCanvas]);

  const handleExportDXF = useCallback(() => {
    exportToDXF();
  }, [exportToDXF]);

  const handleInfer3D = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    infer3DShapes(canvas.width, canvas.height);
  }, [infer3DShapes]);

  const handleDetectRelations = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    detectRelations(canvas.width, canvas.height);
  }, [detectRelations]);

  const tools = [
    { id: 'draw', icon: '✏️', label: '手绘' },
    { id: 'select', icon: '👆', label: '选择' },
    { id: 'edit', icon: '✂️', label: '编辑' },
    { id: 'calibrate', icon: '📏', label: '标定' },
    { id: 'pan', icon: '✋', label: '平移' },
  ];

  const viewModes = [
    { id: '2d', label: '2D' },
    { id: '3d', label: '3D' },
    { id: 'both', label: '2D+3D' },
  ];

  const cursorStyle =
    toolMode === 'pan' ? 'grab' :
    toolMode === 'draw' ? 'crosshair' :
    toolMode === 'select' ? 'pointer' :
    toolMode === 'calibrate' ? 'crosshair' :
    toolMode === 'edit' ? 'move' : 'default';

  return (
    <div className="flex flex-col h-full bg-slate-900">
      <div className="flex items-center justify-between px-4 py-3 bg-slate-800 border-b border-slate-700 flex-wrap gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex bg-slate-700 rounded-lg p-1">
            {tools.map((tool) => (
              <button
                key={tool.id}
                onClick={() => setToolMode(tool.id as any)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-all ${
                  toolMode === tool.id
                    ? 'bg-cyan-500 text-white shadow-lg'
                    : 'text-slate-300 hover:bg-slate-600'
                }`}
                title={tool.label}
              >
                <span className="mr-1">{tool.icon}</span>
                {tool.label}
              </button>
            ))}
          </div>

          <div className="flex bg-slate-700 rounded-lg p-1">
            {viewModes.map((vm) => (
              <button
                key={vm.id}
                onClick={() => setViewMode(vm.id as any)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-all ${
                  viewMode === vm.id
                    ? 'bg-violet-500 text-white shadow-lg'
                    : 'text-slate-300 hover:bg-slate-600'
                }`}
              >
                {vm.label}
              </button>
            ))}
          </div>

          <div className="w-px h-8 bg-slate-600 mx-2" />

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-4 py-2 bg-slate-700 text-slate-200 rounded-lg hover:bg-slate-600 transition-all flex items-center gap-2"
          >
            <span>📁</span>
            上传图像
          </button>

          <button
            onClick={handleRecognize}
            disabled={isRecognizing}
            className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-cyan-500/30"
          >
            <span>{isRecognizing ? '⏳' : '🔍'}</span>
            {isRecognizing ? '识别中...' : '识别形状'}
          </button>

          <div className="w-px h-8 bg-slate-600 mx-1" />

          <button
            onClick={correctSelectedShape}
            disabled={!selectedShapeId}
            className="px-3 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
            title="校正选中形状"
          >
            <span>📐</span>
            校正
          </button>

          <button
            onClick={correctAllShapes}
            disabled={shapes.length === 0}
            className="px-3 py-2 bg-violet-700 text-white rounded-lg hover:bg-violet-600 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
            title="校正全部形状"
          >
            <span>📐✨</span>
            全部校正
          </button>

          <div className="w-px h-8 bg-slate-600 mx-1" />

          <button
            onClick={handleInfer3D}
            disabled={shapes.length === 0}
            className="px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 shadow-lg shadow-indigo-500/30"
            title="从2D形状推断3D几何体"
          >
            <span>🎲</span>
            推断3D
          </button>

          <button
            onClick={handleDetectRelations}
            disabled={shapes.length < 2}
            className={`px-3 py-2 rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 ${
              showRelations
                ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                : 'bg-slate-700 text-slate-200 hover:bg-slate-600'
            }`}
            title="检测形状间的逻辑关系"
          >
            <span>🔗</span>
            关系检测
          </button>

          <button
            onClick={() => setShowRelations(!showRelations)}
            className={`px-3 py-2 rounded-lg transition-all flex items-center gap-1 ${
              showRelations
                ? 'bg-emerald-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
            title="显示/隐藏关系线"
          >
            {showRelations ? '👁️' : '👁️‍🗨️'}
            {showRelations ? '显示关系' : '隐藏关系'}
          </button>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {calibration.enabled && (
            <div className="px-3 py-1.5 bg-amber-500/20 border border-amber-500/40 rounded-lg text-amber-300 text-sm font-medium">
              📏 1 {calibration.unit} = {calibration.pixelLength.toFixed(1)} px
            </div>
          )}
          {shapes3D.length > 0 && (
            <div className="px-3 py-1.5 bg-violet-500/20 border border-violet-500/40 rounded-lg text-violet-300 text-sm font-medium">
              🎲 3D: {shapes3D.length} 个
            </div>
          )}
          {relations.length > 0 && (
            <div className="px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/40 rounded-lg text-emerald-300 text-sm font-medium">
              🔗 关系: {relations.length} 个
            </div>
          )}
          <button
            onClick={undo}
            className="p-2 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 transition-all"
            title="撤销"
          >
            ↩️
          </button>
          <button
            onClick={redo}
            className="p-2 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 transition-all"
            title="重做"
          >
            ↪️
          </button>
          <div className="w-px h-8 bg-slate-600 mx-1" />
          <button
            onClick={clearCanvas}
            className="px-4 py-2 bg-red-600/80 text-white rounded-lg hover:bg-red-500 transition-all flex items-center gap-2"
          >
            <span>🗑️</span>
            清除
          </button>
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 transition-all flex items-center gap-2 shadow-lg shadow-emerald-500/30"
          >
            <span>💾</span>
            导出PNG
          </button>
          <button
            onClick={handleExportDXF}
            disabled={shapes.length === 0 && shapes3D.length === 0}
            className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-orange-500/30"
          >
            <span>📐</span>
            导出DXF
          </button>
        </div>
      </div>

      <div ref={containerRef} className="flex-1 relative overflow-hidden">
        <canvas
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
          className="absolute inset-0"
          style={{ cursor: cursorStyle }}
        />

        {toolMode === 'calibrate' && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-amber-500/90 text-black px-4 py-2 rounded-lg text-sm font-medium shadow-lg">
            📏 标定模式：点击画布设置参考线的起点和终点
          </div>
        )}

        {viewMode === '3d' && shapes3D.length === 0 && shapes.length > 0 && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-violet-500/90 text-white px-4 py-2 rounded-lg text-sm font-medium shadow-lg">
            🎲 点击「推断3D」按钮从2D形状生成3D模型
          </div>
        )}
      </div>

      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-t border-slate-700 text-sm text-slate-400 flex-wrap gap-2">
        <div className="flex items-center gap-4 flex-wrap">
          <span>坐标: ({mousePosition.x.toFixed(0)}, {mousePosition.y.toFixed(0)})</span>
          <span>|</span>
          <span>缩放: {(zoom * 100).toFixed(0)}%</span>
          <span>|</span>
          <span>2D形状: {shapes.length} 个</span>
          {shapes3D.length > 0 && (
            <>
              <span>|</span>
              <span className="text-violet-400">3D模型: {shapes3D.length} 个</span>
            </>
          )}
          {relations.length > 0 && (
            <>
              <span>|</span>
              <span className="text-emerald-400">关系: {relations.length} 个</span>
            </>
          )}
          {calibration.enabled && (
            <>
              <span>|</span>
              <span className="text-amber-400">📏 单位: {calibration.unit}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-cyan-400">Alt+拖拽=平移</span>
          <span>|</span>
          <span className="text-cyan-400">滚轮=缩放</span>
        </div>
      </div>
    </div>
  );
};
