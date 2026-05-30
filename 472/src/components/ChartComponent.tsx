import { useEffect, useRef, useState, useCallback } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import type { ChartType, DataPoint, Annotation } from '../types';
import { getAnnotationColor } from '../utils/export';
import { findNearestDataPoint, SNAP_THRESHOLD, type SnapResult } from '../utils/snapToData';

interface ChartComponentProps {
  chartType: ChartType;
  dataPoints: DataPoint[];
  annotations: Annotation[];
  onDataPointClick: (index: number, dataPoint: DataPoint) => void;
  highlightedIndex?: number | null;
  onSnapChange?: (snapResult: SnapResult | null) => void;
}

export const ChartComponent = ({
  chartType,
  dataPoints,
  annotations,
  onDataPointClick,
  highlightedIndex,
  onSnapChange,
}: ChartComponentProps) => {
  const chartRef = useRef<ReactECharts>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
  const [snappedPoint, setSnappedPoint] = useState<SnapResult | null>(null);

  useEffect(() => {
    const updateDimensions = () => {
      const container = chartRef.current?.getEchartsInstance().getDom().parentElement;
      if (container) {
        setDimensions({
          width: container.clientWidth,
          height: Math.max(400, container.clientHeight - 20),
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!containerRef.current || dataPoints.length === 0) return;

      const nearest = findNearestDataPoint(e.clientX, e.clientY, dataPoints, containerRef.current, chartType);

      if (nearest && nearest.distance < SNAP_THRESHOLD) {
        setSnappedPoint(nearest);
        onSnapChange?.(nearest);
      } else {
        setSnappedPoint(null);
        onSnapChange?.(null);
      }
    },
    [dataPoints, chartType, onSnapChange]
  );

  const handleMouseLeave = useCallback(() => {
    setSnappedPoint(null);
    onSnapChange?.(null);
  }, [onSnapChange]);

  const handleClick = useCallback(
    (e: MouseEvent) => {
      if (snappedPoint && snappedPoint.distance < SNAP_THRESHOLD) {
        onDataPointClick(snappedPoint.index, snappedPoint.point);
      }
    },
    [snappedPoint, onDataPointClick]
  );

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('mousemove', handleMouseMove);
      container.addEventListener('mouseleave', handleMouseLeave);
      container.addEventListener('click', handleClick);
      return () => {
        container.removeEventListener('mousemove', handleMouseMove);
        container.removeEventListener('mouseleave', handleMouseLeave);
        container.removeEventListener('click', handleClick);
      };
    }
  }, [handleMouseMove, handleMouseLeave, handleClick]);

  const getChartOption = (): EChartsOption => {
    const baseOption: EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: chartType === 'scatter' ? 'item' : 'axis',
        backgroundColor: 'rgba(30, 41, 59, 0.95)',
        borderColor: '#475569',
        borderWidth: 1,
        textStyle: { color: '#e2e8f0' },
        formatter: (params: any) => {
          const data = Array.isArray(params) ? params[0] : params;
          const index = data.dataIndex;
          const pointAnnotations = annotations.filter((a) => a.dataPointIndex === index);
          let html = `<div class="font-semibold">${data.name || String(data.value[0])}</div>`;
          html += `<div class="text-slate-400">值: ${data.value[1] || data.value}</div>`;
          if (pointAnnotations.length > 0) {
            html += '<div class="mt-2 pt-2 border-t border-slate-600">';
            pointAnnotations.forEach((a) => {
              html += `<div style="color: ${a.color || getAnnotationColor(a.type)}">● ${a.label}</div>`;
            });
            html += '</div>';
          }
          return html;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10%',
        containLabel: true,
      },
      xAxis: {
        type: chartType === 'scatter' ? 'value' : 'category',
        axisLine: { lineStyle: { color: '#475569' } },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
        splitLine: { lineStyle: { color: '#334155' } },
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: '#475569' } },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
        splitLine: { lineStyle: { color: '#334155' } },
      },
    };

    const chartData = dataPoints.map((dp, index) => {
      const pointAnnotations = annotations.filter((a) => a.dataPointIndex === index);
      const itemStyle: any = {};

      if (highlightedIndex === index) {
        itemStyle.borderColor = '#fbbf24';
        itemStyle.borderWidth = 3;
      }

      if (snappedPoint?.index === index) {
        itemStyle.borderColor = '#06b6d4';
        itemStyle.borderWidth = 4;
        itemStyle.shadowColor = '#06b6d4';
        itemStyle.shadowBlur = 15;
      }

      if (pointAnnotations.length > 0) {
        const firstAnnotation = pointAnnotations[0];
        itemStyle.color = firstAnnotation.color || getAnnotationColor(firstAnnotation.type);
      }

      return {
        value: chartType === 'bar' ? dp.y : [dp.x, dp.y],
        name: String(dp.x),
        itemStyle: Object.keys(itemStyle).length > 0 ? itemStyle : undefined,
        symbolSize: snappedPoint?.index === index ? (chartType === 'scatter' ? 18 : 14) : undefined,
      };
    });

    if (chartType === 'timeSeries') {
      return {
        ...baseOption,
        xAxis: { ...baseOption.xAxis, type: 'category', boundaryGap: false },
        series: [
          {
            name: '数据',
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 8,
            lineStyle: { color: '#3b82f6', width: 2 },
            itemStyle: { color: '#3b82f6' },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                  { offset: 1, color: 'rgba(59, 130, 246, 0.05)' },
                ],
              },
            },
            data: chartData,
          },
        ],
      };
    } else if (chartType === 'scatter') {
      return {
        ...baseOption,
        series: [
          {
            name: '数据点',
            type: 'scatter',
            symbolSize: 12,
            itemStyle: { color: '#06b6d4', opacity: 0.8 },
            data: chartData,
          },
        ],
      };
    } else {
      return {
        ...baseOption,
        series: [
          {
            name: '数据',
            type: 'bar',
            barWidth: '60%',
            itemStyle: {
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: '#8b5cf6' },
                  { offset: 1, color: '#6366f1' },
                ],
              },
              borderRadius: [4, 4, 0, 0],
            },
            data: chartData,
          },
        ],
      };
    }
  };

  return (
    <div ref={containerRef} className="w-full h-full bg-slate-800/50 rounded-xl p-4 relative cursor-crosshair">
      <ReactECharts
        ref={chartRef}
        option={getChartOption()}
        style={{ width: '100%', height: '100%', minHeight: '400px', pointerEvents: 'none' }}
        opts={{ renderer: 'canvas' }}
      />
      {snappedPoint && snappedPoint.distance < SNAP_THRESHOLD && (
        <div
          className="absolute z-10 px-3 py-2 bg-slate-900 text-white text-sm rounded-lg shadow-lg pointer-events-none border border-slate-600"
          style={{
            left: '50%',
            top: 20,
            transform: 'translateX(-50%)',
          }}
        >
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
            <span>吸附到数据点 #{snappedPoint.index}</span>
            <span className="text-slate-400">
              ({String(snappedPoint.point.x)}, {snappedPoint.point.y})
            </span>
            <span className="text-xs text-cyan-400">点击添加标注</span>
          </div>
        </div>
      )}
    </div>
  );
};
