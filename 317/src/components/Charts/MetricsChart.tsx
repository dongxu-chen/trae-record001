import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface DataPoint {
  timestamp: number;
  value: number;
}

interface MetricsChartProps {
  data: DataPoint[];
  label: string;
  color: string;
  width?: number;
  height?: number;
}

export const MetricsChart: React.FC<MetricsChartProps> = ({
  data,
  label,
  color,
  width = 280,
  height = 120,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || data.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 10, right: 10, bottom: 25, left: 35 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    const xScale = d3
      .scaleTime()
      .domain(d3.extent(data, (d) => new Date(d.timestamp)) as [Date, Date])
      .range([0, innerWidth]);

    const maxValue = Math.max(...data.map((d) => d.value), 10);
    const yScale = d3
      .scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([innerHeight, 0])
      .nice();

    const area = d3
      .area<DataPoint>()
      .x((d) => xScale(new Date(d.timestamp)))
      .y0(innerHeight)
      .y1((d) => yScale(d.value))
      .curve(d3.curveMonotoneX);

    const line = d3
      .line<DataPoint>()
      .x((d) => xScale(new Date(d.timestamp)))
      .y((d) => yScale(d.value))
      .curve(d3.curveMonotoneX);

    const gradient = svg
      .append('defs')
      .append('linearGradient')
      .attr('id', `gradient-${label.replace(/\s/g, '-')}`)
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '0%')
      .attr('y2', '100%');

    gradient
      .append('stop')
      .attr('offset', '0%')
      .attr('stop-color', color)
      .attr('stop-opacity', 0.3);

    gradient
      .append('stop')
      .attr('offset', '100%')
      .attr('stop-color', color)
      .attr('stop-opacity', 0.02);

    g.append('path')
      .datum(data)
      .attr('fill', `url(#gradient-${label.replace(/\s/g, '-')})`)
      .attr('d', area);

    g.append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', 2)
      .attr('d', line);

    const xAxis = d3
      .axisBottom(xScale)
      .ticks(4)
      .tickFormat((d) => {
        const date = d as Date;
        return d3.timeFormat('%H:%M:%S')(date);
      });

    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxis)
      .selectAll('text')
      .attr('fill', '#94a3b8')
      .attr('font-size', '10px')
      .attr('transform', 'rotate(-30)')
      .style('text-anchor', 'end');

    g.selectAll('.domain, .tick line')
      .attr('stroke', '#334155')
      .attr('stroke-width', 0.5);

    const yAxis = d3.axisLeft(yScale).ticks(4);

    g.append('g')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', '#94a3b8')
      .attr('font-size', '10px');

    g.selectAll('.domain')
      .attr('stroke', '#334155')
      .attr('stroke-width', 0.5);

    g.selectAll('.tick line')
      .attr('stroke', '#334155')
      .attr('stroke-width', 0.5)
      .attr('stroke-dasharray', '2,2');

    const latestData = data[data.length - 1];
    g.append('circle')
      .attr('cx', xScale(new Date(latestData.timestamp)))
      .attr('cy', yScale(latestData.value))
      .attr('r', 4)
      .attr('fill', color)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5);

    g.append('text')
      .attr('x', innerWidth - 5)
      .attr('y', 12)
      .attr('text-anchor', 'end')
      .attr('fill', '#94a3b8')
      .attr('font-size', '11px')
      .text(label);
  }, [data, label, color, width, height]);

  if (data.length === 0) {
    return (
      <div className="chart-placeholder">
        <span>暂无数据</span>
      </div>
    );
  }

  return (
    <div className="metrics-chart">
      <svg ref={svgRef} width={width} height={height} />
    </div>
  );
};
