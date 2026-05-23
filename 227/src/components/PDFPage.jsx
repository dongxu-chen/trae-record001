import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { fabric } from 'fabric';

export function PDFPage({ 
  pdfDoc, 
  pageNum, 
  scale,
  baseScale, 
  tool, 
  color, 
  strokeWidth, 
  onSaveAnnotations,
  savedAnnotations = [],
  searchResults = [],
  currentSearchIndex = -1,
  transformAnnotationsForScale,
  onPageLoaded
}) {
  const pdfCanvasRef = useRef(null);
  const fabricCanvasRef = useRef(null);
  const fabricCanvasInstance = useRef(null);
  const renderTaskRef = useRef(null);
  const [pageSize, setPageSize] = useState({ width: 0, height: 0 });
  const [isRendering, setIsRendering] = useState(false);
  const isDrawing = useRef(false);
  const startPoint = useRef({ x: 0, y: 0 });
  const currentObject = useRef(null);
  const prevScaleRef = useRef(scale);
  const annotationsRef = useRef(savedAnnotations);

  useEffect(() => {
    annotationsRef.current = savedAnnotations;
  }, [savedAnnotations]);

  useEffect(() => {
    if (!pdfDoc || !pdfCanvasRef.current) return;

    const renderPage = async () => {
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
      }

      setIsRendering(true);
      
      try {
        const page = await pdfDoc.getPage(pageNum);
        const viewport = page.getViewport({ scale });
        
        pdfCanvasRef.current.height = viewport.height;
        pdfCanvasRef.current.width = viewport.width;
        setPageSize({ width: viewport.width, height: viewport.height });

        const context = pdfCanvasRef.current.getContext('2d');
        renderTaskRef.current = page.render({
          canvasContext: context,
          viewport: viewport
        });
        
        await renderTaskRef.current.promise;
        
        if (onPageLoaded) {
          onPageLoaded(pageNum);
        }
      } catch (error) {
        if (error.name !== 'RenderingCancelledException') {
          console.error('Error rendering page:', error);
        }
      } finally {
        setIsRendering(false);
      }
    };

    renderPage();

    return () => {
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
      }
    };
  }, [pdfDoc, pageNum, scale, onPageLoaded]);

  useEffect(() => {
    if (!fabricCanvasRef.current || pageSize.width === 0) return;

    if (fabricCanvasInstance.current) {
      const json = fabricCanvasInstance.current.toJSON();
      onSaveAnnotations(pageNum, json.objects);
      fabricCanvasInstance.current.dispose();
      fabricCanvasInstance.current = null;
    }

    const canvas = new fabric.Canvas(fabricCanvasRef.current, {
      width: pageSize.width,
      height: pageSize.height,
      backgroundColor: 'transparent',
      selection: tool === 'select',
      preserveObjectStacking: true
    });

    fabricCanvasInstance.current = canvas;

    if (savedAnnotations && savedAnnotations.length > 0) {
      canvas.loadFromJSON({ objects: savedAnnotations }, () => {
        canvas.renderAll();
      });
    }

    return () => {
      if (fabricCanvasInstance.current) {
        const json = fabricCanvasInstance.current.toJSON();
        onSaveAnnotations(pageNum, json.objects);
        fabricCanvasInstance.current.dispose();
        fabricCanvasInstance.current = null;
      }
    };
  }, [pageSize, pageNum]);

  useEffect(() => {
    if (!fabricCanvasInstance.current) return;
    if (prevScaleRef.current === scale) return;

    const canvas = fabricCanvasInstance.current;
    const oldScale = prevScaleRef.current;
    const newScale = scale;
    
    const scaleFactor = newScale / oldScale;
    
    const objects = canvas.getObjects();
    objects.forEach(obj => {
      if (obj.type === 'i-text') {
        obj.set({
          left: obj.left * scaleFactor,
          top: obj.top * scaleFactor,
          fontSize: obj.fontSize * scaleFactor
        });
      } else if (obj.type === 'rect') {
        obj.set({
          left: obj.left * scaleFactor,
          top: obj.top * scaleFactor,
          width: obj.width * scaleFactor,
          height: obj.height * scaleFactor,
          strokeWidth: Math.max(1, obj.strokeWidth * scaleFactor)
        });
      } else if (obj.type === 'ellipse') {
        obj.set({
          left: obj.left * scaleFactor,
          top: obj.top * scaleFactor,
          rx: obj.rx * scaleFactor,
          ry: obj.ry * scaleFactor,
          strokeWidth: Math.max(1, obj.strokeWidth * scaleFactor)
        });
      } else if (obj.type === 'line') {
        obj.set({
          x1: obj.x1 * scaleFactor,
          y1: obj.y1 * scaleFactor,
          x2: obj.x2 * scaleFactor,
          y2: obj.y2 * scaleFactor,
          strokeWidth: Math.max(1, obj.strokeWidth * scaleFactor)
        });
      } else {
        obj.set({
          left: obj.left * scaleFactor,
          top: obj.top * scaleFactor,
          scaleX: obj.scaleX,
          scaleY: obj.scaleY
        });
      }
      obj.setCoords();
    });
    
    canvas.renderAll();
    prevScaleRef.current = scale;
    
    const json = canvas.toJSON();
    onSaveAnnotations(pageNum, json.objects);
  }, [scale, pageNum, onSaveAnnotations]);

  useEffect(() => {
    if (!fabricCanvasInstance.current) return;
    
    const canvas = fabricCanvasInstance.current;
    canvas.selection = tool === 'select';
    
    canvas.forEachObject((obj) => {
      obj.selectable = tool === 'select';
      obj.evented = tool === 'select';
    });
  }, [tool]);

  useEffect(() => {
    if (!fabricCanvasInstance.current) return;
    
    const canvas = fabricCanvasInstance.current;
    const activeObject = canvas.getActiveObject();
    if (activeObject) {
      if (activeObject.type === 'i-text') {
        activeObject.set('fill', color);
      } else {
        activeObject.set('stroke', color);
        activeObject.set('strokeWidth', strokeWidth);
      }
      canvas.renderAll();
    }
  }, [color, strokeWidth]);

  const getCanvasPoint = useCallback((e) => {
    if (!fabricCanvasRef.current) return { x: 0, y: 0 };
    const rect = fabricCanvasRef.current.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
  }, []);

  const handleMouseDown = useCallback((e) => {
    if (!fabricCanvasInstance.current || tool === 'select' || tool === 'text') return;
    if (isRendering) return;
    
    const canvas = fabricCanvasInstance.current;
    isDrawing.current = true;
    startPoint.current = getCanvasPoint(e);

    switch (tool) {
      case 'rect':
        currentObject.current = new fabric.Rect({
          left: startPoint.current.x,
          top: startPoint.current.y,
          width: 0,
          height: 0,
          fill: 'transparent',
          stroke: color,
          strokeWidth: strokeWidth,
          selectable: true
        });
        break;
      case 'ellipse':
        currentObject.current = new fabric.Ellipse({
          left: startPoint.current.x,
          top: startPoint.current.y,
          rx: 0,
          ry: 0,
          fill: 'transparent',
          stroke: color,
          strokeWidth: strokeWidth,
          selectable: true
        });
        break;
      case 'arrow':
        currentObject.current = new fabric.Line(
          [startPoint.current.x, startPoint.current.y, startPoint.current.x, startPoint.current.y],
          {
            stroke: color,
            strokeWidth: strokeWidth,
            selectable: true
          }
        );
        break;
      case 'highlight':
        currentObject.current = new fabric.Rect({
          left: startPoint.current.x,
          top: startPoint.current.y,
          width: 0,
          height: 0,
          fill: color,
          opacity: 0.4,
          selectable: true
        });
        break;
      case 'line':
        currentObject.current = new fabric.Line(
          [startPoint.current.x, startPoint.current.y, startPoint.current.x, startPoint.current.y],
          {
            stroke: color,
            strokeWidth: strokeWidth,
            selectable: true
          }
        );
        break;
      default:
        return;
    }

    canvas.add(currentObject.current);
  }, [tool, color, strokeWidth, getCanvasPoint, isRendering]);

  const handleMouseMove = useCallback((e) => {
    if (!isDrawing.current || !currentObject.current || !fabricCanvasInstance.current) return;
    if (isRendering) return;

    const canvas = fabricCanvasInstance.current;
    const currentPoint = getCanvasPoint(e);

    switch (tool) {
      case 'rect':
      case 'highlight':
        currentObject.current.set({
          width: Math.abs(currentPoint.x - startPoint.current.x),
          height: Math.abs(currentPoint.y - startPoint.current.y),
          left: Math.min(startPoint.current.x, currentPoint.x),
          top: Math.min(startPoint.current.y, currentPoint.y)
        });
        break;
      case 'ellipse':
        currentObject.current.set({
          rx: Math.abs(currentPoint.x - startPoint.current.x) / 2,
          ry: Math.abs(currentPoint.y - startPoint.current.y) / 2,
          left: Math.min(startPoint.current.x, currentPoint.x) + Math.abs(currentPoint.x - startPoint.current.x) / 2,
          top: Math.min(startPoint.current.y, currentPoint.y) + Math.abs(currentPoint.y - startPoint.current.y) / 2
        });
        break;
      case 'arrow':
      case 'line':
        currentObject.current.set({
          x2: currentPoint.x,
          y2: currentPoint.y
        });
        break;
    }

    canvas.renderAll();
  }, [tool, getCanvasPoint, isRendering]);

  const handleMouseUp = useCallback(() => {
    if (!isDrawing.current) return;
    isDrawing.current = false;
    
    if (currentObject.current && fabricCanvasInstance.current) {
      const json = fabricCanvasInstance.current.toJSON();
      onSaveAnnotations(pageNum, json.objects);
    }
    currentObject.current = null;
  }, [pageNum, onSaveAnnotations]);

  const addText = useCallback((e) => {
    if (!fabricCanvasInstance.current || tool !== 'text') return;
    if (isRendering) return;
    
    const point = getCanvasPoint(e);
    const canvas = fabricCanvasInstance.current;
    
    const text = new fabric.IText('输入文字', {
      left: point.x,
      top: point.y,
      fontFamily: 'Arial',
      fontSize: 20 * (scale / baseScale),
      fill: color,
      selectable: true
    });
    
    canvas.add(text);
    canvas.setActiveObject(text);
    text.enterEditing();
    text.selectAll();
    
    const json = canvas.toJSON();
    onSaveAnnotations(pageNum, json.objects);
  }, [tool, color, getCanvasPoint, pageNum, onSaveAnnotations, scale, baseScale]);

  const handleDoubleClick = useCallback((e) => {
    if (tool === 'text') {
      addText(e);
    }
  }, [tool, addText]);

  const handleKeyDown = useCallback((e) => {
    if (!fabricCanvasInstance.current) return;
    if (isRendering) return;
    
    if (e.key === 'Delete' || e.key === 'Backspace') {
      const canvas = fabricCanvasInstance.current;
      const activeObjects = canvas.getActiveObjects();
      if (activeObjects.length > 0) {
        activeObjects.forEach(obj => canvas.remove(obj));
        canvas.discardActiveObject();
        canvas.renderAll();
        
        const json = canvas.toJSON();
        onSaveAnnotations(pageNum, json.objects);
      }
    }
  }, [pageNum, onSaveAnnotations, isRendering]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const scaledSearchResults = useMemo(() => {
    return searchResults.map(result => ({
      ...result,
      x: result.baseX * (scale / baseScale),
      y: result.baseY * (scale / baseScale),
      width: result.baseWidth * (scale / baseScale),
      height: result.baseHeight * (scale / baseScale)
    }));
  }, [searchResults, scale, baseScale]);

  const currentPageResults = scaledSearchResults.filter(r => r.pageNum === pageNum);

  return (
    <div 
      className="pdf-page-wrapper"
      style={{ width: pageSize.width, height: pageSize.height }}
    >
      <canvas
        ref={pdfCanvasRef}
        className="pdf-canvas"
      />
      {isRendering && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(255,255,255,0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10
        }}>
          <div style={{ fontSize: '14px', color: '#666' }}>渲染中...</div>
        </div>
      )}
      <canvas
        ref={fabricCanvasRef}
        className="fabric-canvas"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onDoubleClick={handleDoubleClick}
        style={{ 
          cursor: tool === 'select' ? 'default' : 'crosshair',
          opacity: isRendering ? 0.5 : 1
        }}
      />
      <div className="highlight-layer" style={{ width: pageSize.width, height: pageSize.height }}>
        {currentPageResults.map((result, index) => {
          const globalIndex = searchResults.findIndex(
            r => r.pageNum === result.pageNum && 
                 Math.abs(r.baseX - result.baseX) < 1 && 
                 Math.abs(r.baseY - result.baseY) < 1
          );
          return (
            <div
              key={index}
              className={`highlight-box ${globalIndex === currentSearchIndex ? 'current' : ''}`}
              style={{
                left: result.x,
                top: result.y,
                width: result.width,
                height: result.height
              }}
            />
          );
        })}
      </div>
    </div>
  );
}
