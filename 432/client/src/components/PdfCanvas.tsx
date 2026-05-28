import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { Canvas, Rect, Circle, Line, Textbox } from 'fabric';
import { usePdfContext } from '../contexts/PdfContext';
import { toRelativePosition, toAbsolutePosition } from '../utils/coordinateUtils';
import { AnnotationType } from '../types';

pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js`;

const PdfCanvas: React.FC = () => {
  const { state, addAnnotation, dispatch } = usePdfContext();
  const containerRef = useRef<HTMLDivElement>(null);
  const pdfCanvasRef = useRef<HTMLCanvasElement>(null);
  const fabricCanvasRef = useRef<Canvas | null>(null);
  const [pdfDoc, setPdfDoc] = useState<any>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState<{ x: number; y: number } | null>(null);
  const [currentObject, setCurrentObject] = useState<any>(null);

  const { document, tool, viewer } = state;
  const { currentPage, zoom } = viewer;
  const { currentTool, currentColor } = tool;

  const renderPage = useCallback(async (pageNum: number, scale: number) => {
    if (!pdfDoc || !pdfCanvasRef.current || !containerRef.current) return;

    const page = await pdfDoc.getPage(pageNum + 1);
    const viewport = page.getViewport({ scale });

    const canvas = pdfCanvasRef.current;
    const context = canvas.getContext('2d')!;
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    await page.render({
      canvasContext: context,
      viewport: viewport,
    }).promise;

    if (fabricCanvasRef.current) {
      fabricCanvasRef.current.setDimensions({
        width: viewport.width,
        height: viewport.height,
      });
      renderAnnotations(pageNum, viewport.width, viewport.height);
    }
  }, [pdfDoc]);

  const renderAnnotations = useCallback((pageIndex: number, pageWidth: number, pageHeight: number) => {
    if (!fabricCanvasRef.current || !document) return;

    const canvas = fabricCanvasRef.current;
    canvas.clear();

    const pageAnnotations = document.annotations.filter(
      (a) => a.pageIndex === pageIndex
    );

    pageAnnotations.forEach((annotation) => {
      const absPos = toAbsolutePosition(annotation.position, pageWidth, pageHeight);
      let fabricObj: any = null;

      switch (annotation.type) {
        case 'highlight':
        case 'underline':
        case 'strikeout':
          fabricObj = new Rect({
            left: absPos.x,
            top: absPos.y,
            width: absPos.width || 100,
            height: absPos.height || 20,
            fill: annotation.type === 'highlight' ? annotation.color + '80' : 'transparent',
            stroke: annotation.type !== 'highlight' ? annotation.color : 'transparent',
            strokeWidth: annotation.type === 'underline' ? 2 : annotation.type === 'strikeout' ? 2 : 0,
            selectable: true,
            hasControls: true,
          });
          break;

        case 'rectangle':
          fabricObj = new Rect({
            left: absPos.x,
            top: absPos.y,
            width: absPos.width || 50,
            height: absPos.height || 50,
            fill: 'transparent',
            stroke: annotation.color,
            strokeWidth: 2,
            selectable: true,
            hasControls: true,
          });
          break;

        case 'circle':
          fabricObj = new Circle({
            left: absPos.x,
            top: absPos.y,
            radius: Math.min(absPos.width || 25, absPos.height || 25) / 2,
            fill: 'transparent',
            stroke: annotation.color,
            strokeWidth: 2,
            selectable: true,
            hasControls: true,
          });
          break;

        case 'arrow':
          fabricObj = new Line([absPos.x, absPos.y, absPos.x + (absPos.width || 50), absPos.y + (absPos.height || 0)], {
            stroke: annotation.color,
            strokeWidth: 2,
            selectable: true,
            hasControls: true,
          });
          break;

        case 'comment':
          fabricObj = new Textbox(annotation.content || '批注', {
            left: absPos.x,
            top: absPos.y,
            width: 150,
            fill: '#1d2129',
            backgroundColor: annotation.color + '30',
            fontSize: 12,
            padding: 8,
            selectable: true,
            hasControls: true,
          });
          break;
      }

      if (fabricObj) {
        fabricObj.set('data', { annotationId: annotation.id });
        canvas.add(fabricObj);
      }
    });

    canvas.renderAll();
  }, [document]);

  useEffect(() => {
    if (!document) return;

    const loadPdf = async () => {
      const arrayBuffer = await document.file.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      setPdfDoc(pdf);
    };

    loadPdf();
  }, [document]);

  useEffect(() => {
    if (pdfDoc && pdfCanvasRef.current && containerRef.current) {
      if (!fabricCanvasRef.current) {
        const fabricCanvas = new Canvas('fabric-canvas', {
          selection: currentTool === 'select',
          preserveObjectStacking: true,
        });
        fabricCanvasRef.current = fabricCanvas;

        fabricCanvas.on('mouse:down', handleMouseDown);
        fabricCanvas.on('mouse:move', handleMouseMove);
        fabricCanvas.on('mouse:up', handleMouseUp);
      }

      renderPage(currentPage, zoom);
    }

    return () => {
      if (fabricCanvasRef.current) {
        fabricCanvasRef.current.dispose();
        fabricCanvasRef.current = null;
      }
    };
  }, [pdfDoc, currentPage, zoom, currentTool]);

  const handleMouseDown = (options: any) => {
    if (currentTool === 'select' || !fabricCanvasRef.current) return;

    const pointer = fabricCanvasRef.current.getPointer(options.e);
    setIsDrawing(true);
    setStartPoint(pointer);

    const pageSize = document?.pageSizes[currentPage];
    if (!pageSize) return;

    const scaledWidth = pageSize.width * zoom;
    const scaledHeight = pageSize.height * zoom;

    let newObj: any = null;

    switch (currentTool) {
      case 'highlight':
        newObj = new Rect({
          left: pointer.x,
          top: pointer.y,
          width: 0,
          height: 20,
          fill: currentColor + '80',
          stroke: 'transparent',
          selectable: false,
          evented: false,
        });
        break;

      case 'underline':
      case 'strikeout':
        newObj = new Line([pointer.x, pointer.y, pointer.x, pointer.y], {
          stroke: currentColor,
          strokeWidth: currentTool === 'underline' ? 2 : 2,
          selectable: false,
          evented: false,
        });
        break;

      case 'rectangle':
        newObj = new Rect({
          left: pointer.x,
          top: pointer.y,
          width: 0,
          height: 0,
          fill: 'transparent',
          stroke: currentColor,
          strokeWidth: 2,
          selectable: false,
          evented: false,
        });
        break;

      case 'circle':
        newObj = new Circle({
          left: pointer.x,
          top: pointer.y,
          radius: 0,
          fill: 'transparent',
          stroke: currentColor,
          strokeWidth: 2,
          selectable: false,
          evented: false,
        });
        break;

      case 'arrow':
        newObj = new Line([pointer.x, pointer.y, pointer.x, pointer.y], {
          stroke: currentColor,
          strokeWidth: 2,
          selectable: false,
          evented: false,
        });
        break;

      case 'comment':
        const commentText = prompt('请输入批注内容：');
        if (commentText) {
          const relPos = toRelativePosition(pointer.x, pointer.y, scaledWidth, scaledHeight);
          addAnnotation({
            type: 'comment',
            pageIndex: currentPage,
            position: relPos,
            color: currentColor,
            content: commentText,
          });
        }
        setIsDrawing(false);
        return;
    }

    if (newObj) {
      fabricCanvasRef.current.add(newObj);
      setCurrentObject(newObj);
    }
  };

  const handleMouseMove = (options: any) => {
    if (!isDrawing || !currentObject || !fabricCanvasRef.current || !startPoint) return;

    const pointer = fabricCanvasRef.current.getPointer(options.e);

    if (currentObject instanceof Rect) {
      const width = pointer.x - startPoint.x;
      const height = currentTool === 'highlight' ? 20 : pointer.y - startPoint.y;
      currentObject.set({
        width: Math.abs(width),
        height: Math.abs(height),
        left: width < 0 ? pointer.x : startPoint.x,
        top: height < 0 ? pointer.y : startPoint.y,
      });
    } else if (currentObject instanceof Circle) {
      const dx = pointer.x - startPoint.x;
      const dy = pointer.y - startPoint.y;
      const radius = Math.sqrt(dx * dx + dy * dy);
      currentObject.set({
        radius: radius,
        left: startPoint.x - radius,
        top: startPoint.y - radius,
      });
    } else if (currentObject instanceof Line) {
      currentObject.set({ x2: pointer.x, y2: pointer.y });
    }

    fabricCanvasRef.current.renderAll();
  };

  const handleMouseUp = () => {
    if (!isDrawing || !currentObject || !document) {
      setIsDrawing(false);
      setCurrentObject(null);
      setStartPoint(null);
      return;
    }

    const pageSize = document.pageSizes[currentPage];
    if (!pageSize) return;

    const scaledWidth = pageSize.width * zoom;
    const scaledHeight = pageSize.height * zoom;

    let relPos;

    if (currentObject instanceof Rect || currentObject instanceof Circle) {
      const obj = currentObject as any;
      relPos = toRelativePosition(
        obj.left,
        obj.top,
        scaledWidth,
        scaledHeight,
        obj.width || obj.radius * 2,
        obj.height || obj.radius * 2
      );
    } else if (currentObject instanceof Line) {
      const line = currentObject as Line;
      const x1 = line.x1 || 0;
      const y1 = line.y1 || 0;
      const x2 = line.x2 || 0;
      const y2 = line.y2 || 0;
      relPos = toRelativePosition(
        Math.min(x1, x2),
        Math.min(y1, y2),
        scaledWidth,
        scaledHeight,
        Math.abs(x2 - x1),
        Math.abs(y2 - y1)
      );
    }

    if (relPos && currentTool !== 'select') {
      let annotationType: AnnotationType = currentTool as AnnotationType;
      if (annotationType === 'underline') annotationType = 'underline';
      if (annotationType === 'strikeout') annotationType = 'strikeout';

      addAnnotation({
        type: annotationType,
        pageIndex: currentPage,
        position: relPos,
        color: currentColor,
      });
    }

    setIsDrawing(false);
    setCurrentObject(null);
    setStartPoint(null);
  };

  const handlePrevPage = () => {
    if (currentPage > 0) {
      dispatch({ type: 'SET_CURRENT_PAGE', payload: currentPage - 1 });
    }
  };

  const handleNextPage = () => {
    if (document && currentPage < document.numPages - 1) {
      dispatch({ type: 'SET_CURRENT_PAGE', payload: currentPage + 1 });
    }
  };

  if (!document) {
    return null;
  }

  return (
    <div className="flex-1 flex flex-col pdf-canvas-container overflow-hidden">
      <div className="flex-1 overflow-auto p-8 flex justify-center">
        <div
          ref={containerRef}
          className="relative bg-white shadow-2xl"
          style={{ lineHeight: 0 }}
        >
          <canvas
            ref={pdfCanvasRef}
            className="block"
          />
          <canvas
            id="fabric-canvas"
            className="absolute top-0 left-0"
          />
        </div>
      </div>

      <div className="h-12 bg-white border-t border-gray-200 flex items-center justify-center gap-4">
        <button
          className="px-4 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handlePrevPage}
          disabled={currentPage === 0}
        >
          上一页
        </button>
        <span className="text-sm text-gray-600">
          第 <span className="font-semibold text-gray-900">{currentPage + 1}</span> / {document.numPages} 页
        </span>
        <button
          className="px-4 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleNextPage}
          disabled={currentPage === document.numPages - 1}
        >
          下一页
        </button>
      </div>
    </div>
  );
};

export default PdfCanvas;
