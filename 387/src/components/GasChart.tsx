import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface GasChartProps {
  data: Array<{
    timestamp: number;
    baseFee: string;
    average: string;
    low: string;
    high: string;
    peakBaseFee?: string;
    peakTimestamp?: number;
  }>;
  height?: number;
  showPeak?: boolean;
}

export default function GasChart({ data, height = 300, showPeak = true }: GasChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current || !data.length) return;

    if (chartInstance.current) {
      chartInstance.current.dispose();
    }

    const chart = echarts.init(chartRef.current);
    chartInstance.current = chart;

    const timestamps = data.map((d) => {
      const date = new Date(d.timestamp * 1000);
      return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:00`;
    });

    const baseFeeData = data.map((d) => Number(d.baseFee) / 1e9);
    const avgData = data.map((d) => Number(d.average) / 1e9);
    const lowData = data.map((d) => Number(d.low) / 1e9);
    const highData = data.map((d) => Number(d.high) / 1e9);
    const peakData = data.map((d) => d.peakBaseFee ? Number(d.peakBaseFee) / 1e9 : null);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        borderColor: 'rgba(6, 182, 212, 0.3)',
        textStyle: { color: '#e2e8f0' },
        formatter: (params: any) => {
          const idx = params[0].dataIndex;
          const peakInfo = peakData[idx] ? `<div style="color: #f472b6">Peak: ${peakData[idx]?.toFixed(2)} Gwei</div>` : '';
          return `
            <div style="font-family: monospace">
              <div style="margin-bottom: 8px; color: #94a3b8">${timestamps[idx]}</div>
              <div style="color: #f59e0b">Base Fee: ${baseFeeData[idx].toFixed(2)} Gwei</div>
              <div style="color: #06b6d4">Average: ${avgData[idx].toFixed(2)} Gwei</div>
              ${peakInfo}
              <div style="color: #10b981">Low: ${lowData[idx].toFixed(2)} Gwei</div>
              <div style="color: #ef4444">High: ${highData[idx].toFixed(2)} Gwei</div>
            </div>
          `;
        },
      },
      legend: {
        data: showPeak 
          ? ['Base Fee', 'Average', 'Peak', 'Low', 'High']
          : ['Base Fee', 'Average', 'Low', 'High'],
        textStyle: { color: '#94a3b8', fontSize: 11 },
        top: 0,
        right: 0,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: timestamps,
        axisLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.5)' } },
        axisLabel: { 
          color: '#64748b', 
          fontSize: 10, 
          interval: Math.floor(data.length / 12),
          rotate: data.length > 48 ? 45 : 0,
        },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        name: 'Gwei',
        nameTextStyle: { color: '#64748b', fontSize: 10 },
        axisLine: { show: false },
        axisLabel: { color: '#64748b', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.2)' } },
      },
      series: [
        {
          name: 'High',
          type: 'line',
          smooth: true,
          symbol: 'none',
          data: highData,
          lineStyle: { color: '#ef4444', width: 1, type: 'dashed' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(239, 68, 68, 0.05)' },
              { offset: 1, color: 'rgba(239, 68, 68, 0)' },
            ]),
          },
        },
        {
          name: 'Average',
          type: 'line',
          smooth: true,
          symbol: 'none',
          data: avgData,
          lineStyle: { color: '#06b6d4', width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(6, 182, 212, 0.2)' },
              { offset: 1, color: 'rgba(6, 182, 212, 0.02)' },
            ]),
          },
        },
        {
          name: 'Base Fee',
          type: 'line',
          smooth: true,
          symbol: 'none',
          data: baseFeeData,
          lineStyle: { color: '#f59e0b', width: 2 },
        },
        ...(showPeak ? [{
          name: 'Peak',
          type: 'scatter',
          data: peakData.map((val, idx) => val !== null ? [idx, val] : null),
          symbol: 'diamond',
          symbolSize: 8,
          itemStyle: { color: '#f472b6' },
        }] : []),
        {
          name: 'Low',
          type: 'line',
          smooth: true,
          symbol: 'none',
          data: lowData,
          lineStyle: { color: '#10b981', width: 1, type: 'dashed' },
        },
      ],
    };

    chart.setOption(option);

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.dispose();
    };
  }, [data, showPeak]);

  return <div ref={chartRef} style={{ height }} />;
}
