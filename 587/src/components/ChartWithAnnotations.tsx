import React, { useRef, useEffect, useState, useCallback } from 'react';
import * as echarts from 'echarts';
import AnnotationCanvas from './AnnotationCanvas';
import { Annotation } from '../../shared/types';
import { useWebSocket } from '../hooks/useWebSocket';
import { useStore } from '../store/useStore';

interface ChartWithAnnotationsProps {
  chartData: any;
  chartType?: string;
}

const ChartWithAnnotations: React.FC<ChartWithAnnotationsProps> = ({
  chartData,
  chartType = 'line',
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });

  const { sendAnnotationAdd, sendAnnotationUpdate, sendAnnotationDelete } = useWebSocket();
  const { selectedAnnotationId, setSelectedAnnotationId, deleteAnnotation } = useStore();

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstanceRef.current = echarts.init(chartRef.current);

    const option = {
      ...chartData,
      tooltip: {
        trigger: 'axis',
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
    };

    chartInstanceRef.current.setOption(option);

    const handleResize = () => {
      chartInstanceRef.current?.resize();
      updateDimensions();
    };

    window.addEventListener('resize', handleResize);
    updateDimensions();

    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstanceRef.current?.dispose();
    };
  }, [chartData]);

  const updateDimensions = useCallback(() => {
    if (containerRef.current) {
      const { width, height } = containerRef.current.getBoundingClientRect();
      setDimensions({ width, height });
    }
  }, []);

  useEffect(() => {
    updateDimensions();
  }, [updateDimensions]);

  const handleAddAnnotation = useCallback(
    (annotation: Omit<Annotation, 'id' | 'createdAt' | 'updatedAt'>) => {
      sendAnnotationAdd(annotation);
    },
    [sendAnnotationAdd]
  );

  const handleUpdateAnnotation = useCallback(
    (annotationId: string, updates: Partial<Annotation>) => {
      sendAnnotationUpdate(annotationId, updates);
    },
    [sendAnnotationUpdate]
  );

  const handleDeleteAnnotation = useCallback(
    (annotationId: string) => {
      sendAnnotationDelete(annotationId);
      deleteAnnotation(annotationId);
    },
    [sendAnnotationDelete, deleteAnnotation]
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedAnnotationId) {
        const isInputFocused = document.activeElement?.tagName === 'INPUT' || 
                               document.activeElement?.tagName === 'TEXTAREA';
        if (!isInputFocused) {
          e.preventDefault();
          handleDeleteAnnotation(selectedAnnotationId);
        }
      }
      if (e.key === 'Escape') {
        setSelectedAnnotationId(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedAnnotationId, handleDeleteAnnotation, setSelectedAnnotationId]);

  return (
    <div
      ref={containerRef}
      className="relative w-full bg-white rounded-xl shadow-lg overflow-hidden"
      style={{ height: '500px' }}
    >
      <div ref={chartRef} className="w-full h-full" />
      <AnnotationCanvas
        width={dimensions.width}
        height={dimensions.height}
        onAddAnnotation={handleAddAnnotation}
        onUpdateAnnotation={handleUpdateAnnotation}
      />
    </div>
  );
};

export default ChartWithAnnotations;
