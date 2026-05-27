import React, { useMemo, useRef, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsInstance } from 'echarts-for-react';
import { useTheme, useChartType } from '@/store/useThemeStore';
import { useDebounce } from '@/hooks/useDebounce';
import { generateChartOption } from '@/utils/chartOptions';
import './index.less';

const ChartPreview: React.FC = () => {
  const theme = useTheme();
  const chartType = useChartType();
  const chartRef = useRef<ReactECharts>(null);
  const debouncedTheme = useDebounce(theme, 100);

  const option = useMemo(() => {
    return generateChartOption(debouncedTheme, chartType);
  }, [debouncedTheme, chartType]);

  useEffect(() => {
    if (chartRef.current) {
      const chart: EChartsInstance = chartRef.current.getEchartsInstance();
      chart.resize();
    }
  }, [chartType]);

  return (
    <section className="chart-preview">
      <div className="chart-preview-header">
        <div className="chart-info">
          <h2 className="chart-title">实时预览</h2>
          <span className="chart-type-badge">{chartType}</span>
        </div>
        <p className="chart-hint">
          切换图表类型时主题配置保持不变，修改配置实时生效
        </p>
      </div>
      <div className="chart-container">
        <ReactECharts
          ref={chartRef}
          option={option}
          notMerge={false}
          lazyUpdate={true}
          style={{ height: '100%', width: '100%' }}
        />
      </div>
      <div className="chart-footer">
        <div className="color-legend">
          <span className="legend-label">当前色板:</span>
          {theme.color.slice(0, 6).map((color, index) => (
            <div
              key={index}
              className="legend-color"
              style={{ backgroundColor: color }}
              title={color}
            />
          ))}
          {theme.color.length > 6 && (
            <span className="legend-more">+{theme.color.length - 6}</span>
          )}
        </div>
      </div>
    </section>
  );
};

export default React.memo(ChartPreview);
