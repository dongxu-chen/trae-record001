import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as echarts from 'echarts';
import { Button, Select, Space, message, Popconfirm, Tag } from 'antd';
import { ReloadOutlined, SettingOutlined, BarChartOutlined, LineChartOutlined, PieChartOutlined, DeleteOutlined, FullscreenOutlined, FullscreenExitOutlined } from '@ant-design/icons';
import { fetchMockAPI, staticData } from '../utils/mockData';

const ChartComponent = ({ 
  config, 
  onConfigChange, 
  onRefresh, 
  onDelete, 
  onOpenConfig,
  onChartClick,
  triggerRefresh,
  isFullscreen
}) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);
  const [loading, setLoading] = useState(false);
  const [clickData, setClickData] = useState(null);

  const chartType = config.chartType || 'line';
  const dataSource = config.dataSource || 'static';
  const refreshInterval = config.refreshInterval || 0;
  const theme = config.theme || 'light';

  const applyFilter = useCallback((data, filterScript) => {
    if (!filterScript) return data;
    try {
      const filterFunc = new Function('data', filterScript);
      return filterFunc(data) || data;
    } catch (error) {
      console.error('过滤器执行失败:', error);
      return data;
    }
  }, []);

  const handleResize = useCallback(() => {
    chartInstance.current?.resize();
  }, []);

  const renderChart = useCallback(async () => {
    if (!chartInstance.current) return;
    
    setLoading(true);
    try {
      let data;
      if (dataSource === 'api') {
        data = await fetchMockAPI(chartType);
      } else {
        data = staticData[chartType];
      }

      if (config.enableFilter && config.filterScript) {
        data = applyFilter(data, config.filterScript);
      }

      const option = getChartOption(chartType, data, config.title, theme);
      chartInstance.current.setOption(option, { notMerge: false, lazyUpdate: true });
    } catch (error) {
      message.error('数据加载失败');
    } finally {
      setLoading(false);
    }
  }, [chartType, dataSource, config.title, config.enableFilter, config.filterScript, theme, applyFilter]);

  useEffect(() => {
    if (!chartRef.current) return;

    const themeConfig = theme === 'dark' ? 'dark' : undefined;
    chartInstance.current = echarts.init(chartRef.current, themeConfig);

    renderChart();

    chartInstance.current.on('click', (params) => {
      if (config.enableLink) {
        setClickData(params);
        onChartClick && onChartClick(config, params);
      }
    });

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [handleResize]);

  useEffect(() => {
    renderChart();
  }, [renderChart]);

  useEffect(() => {
    if (triggerRefresh) {
      renderChart();
    }
  }, [triggerRefresh, renderChart]);

  useEffect(() => {
    const observer = new ResizeObserver(() => {
      handleResize();
    });

    if (chartRef.current) {
      observer.observe(chartRef.current);
    }

    return () => {
      observer.disconnect();
    };
  }, [handleResize]);

  useEffect(() => {
    if (refreshInterval <= 0 || !config.autoRefresh) return;

    const interval = setInterval(async () => {
      if (dataSource === 'api' && chartInstance.current) {
        let data = await fetchMockAPI(chartType);
        if (config.enableFilter && config.filterScript) {
          data = applyFilter(data, config.filterScript);
        }
        const option = getChartOption(chartType, data, config.title, theme);
        chartInstance.current.setOption(option, { notMerge: false, lazyUpdate: true });
      }
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [refreshInterval, chartType, dataSource, config.title, config.autoRefresh, config.enableFilter, config.filterScript, theme, applyFilter]);

  useEffect(() => {
    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, []);

  const getChartOption = (type, data, title, theme) => {
    const isDark = theme === 'dark';
    const textColor = isDark ? '#fff' : '#333';
    const bgColor = isDark ? '#141414' : '#fff';

    const baseOption = {
      backgroundColor: bgColor,
      title: { 
        text: title || '图表', 
        left: 'center', 
        top: 10, 
        textStyle: { fontSize: 14, color: textColor } 
      },
      tooltip: { 
        trigger: type === 'pie' ? 'item' : 'axis',
        backgroundColor: isDark ? 'rgba(0,0,0,0.8)' : 'rgba(255,255,255,0.9)',
        textStyle: { color: isDark ? '#fff' : '#333' }
      },
      legend: { 
        bottom: 10, 
        left: 'center',
        textStyle: { color: textColor }
      },
      grid: { left: '3%', right: '4%', bottom: '15%', top: '15%', containLabel: true },
      animationDuration: 1000,
      animationEasing: 'cubicOut'
    };

    if (type === 'pie') {
      return {
        ...baseOption,
        series: [
          {
            name: '访问来源',
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: { borderRadius: 10, borderColor: bgColor, borderWidth: 2 },
            label: { show: false, position: 'center', color: textColor },
            emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
            labelLine: { show: false },
            data: data.data
          }
        ]
      };
    }

    return {
      ...baseOption,
      xAxis: { 
        type: 'category', 
        data: data.xAxis,
        axisLine: { lineStyle: { color: isDark ? '#444' : '#ccc' } },
        axisLabel: { color: textColor }
      },
      yAxis: { 
        type: 'value',
        axisLine: { lineStyle: { color: isDark ? '#444' : '#ccc' } },
        axisLabel: { color: textColor },
        splitLine: { lineStyle: { color: isDark ? '#333' : '#eee' } }
      },
      series: data.series.map((item) => ({
        ...item,
        type: type,
        smooth: type === 'line',
        itemStyle: type === 'bar' ? { borderRadius: [4, 4, 0, 0] } : {}
      }))
    };
  };

  const handleChartTypeChange = (value) => {
    onConfigChange({ ...config, chartType: value });
  };

  const handleRefresh = async () => {
    await renderChart();
    onRefresh && onRefresh();
    message.success('数据已刷新');
  };

  const containerStyle = {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: theme === 'dark' ? '#141414' : '#fff',
    transition: 'all 0.3s'
  };

  const headerStyle = {
    ...chartHeaderStyle,
    backgroundColor: theme === 'dark' ? '#1f1f1f' : '#fafafa',
    borderBottom: `1px solid ${theme === 'dark' ? '#333' : '#f0f0f0'}`
  };

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <span style={{ ...titleStyle, color: theme === 'dark' ? '#fff' : '#262626' }}>
          {config.title || '图表'}
          {config.enableLink && <Tag color="blue" style={{ marginLeft: 8 }}>联动中</Tag>}
        </span>
        <Space size="small">
          <Select
            value={chartType}
            onChange={handleChartTypeChange}
            size="small"
            style={{ width: 100 }}
            options={[
              { value: 'line', label: <span><LineChartOutlined /> 折线图</span> },
              { value: 'bar', label: <span><BarChartOutlined /> 柱状图</span> },
              { value: 'pie', label: <span><PieChartOutlined /> 饼图</span> }
            ]}
          />
          <Button
            icon={<ReloadOutlined />}
            size="small"
            loading={loading}
            onClick={handleRefresh}
          />
          <Button 
            icon={<SettingOutlined />} 
            size="small" 
            onClick={onOpenConfig}
          />
          <Popconfirm
            title="确定要删除这个图表吗？"
            onConfirm={onDelete}
            okText="确定"
            cancelText="取消"
          >
            <Button icon={<DeleteOutlined />} size="small" danger />
          </Popconfirm>
        </Space>
      </div>
      <div ref={chartRef} className="chart-container" style={{ cursor: config.enableLink ? 'pointer' : 'default' }} />
      {clickData && config.enableLink && (
        <div style={{ 
          padding: '8px 16px', 
          fontSize: 12, 
          backgroundColor: theme === 'dark' ? '#1f1f1f' : '#e6f7ff',
          borderTop: `1px solid ${theme === 'dark' ? '#333' : '#91d5ff'}`
        }}>
          已选中: {clickData.name} - {clickData.value}
        </div>
      )}
    </div>
  );
};

const chartHeaderStyle = {
  padding: '12px 16px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
};

const titleStyle = {
  fontWeight: 500,
  fontSize: 14,
  display: 'flex',
  alignItems: 'center'
};

export default ChartComponent;
