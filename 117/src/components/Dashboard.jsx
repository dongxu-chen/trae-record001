import React, { useEffect, useRef, useState, useCallback } from 'react';
import { GridStack } from 'gridstack';
import 'gridstack/dist/gridstack.min.css';
import ChartComponent from './ChartComponent';
import ConfigPanel from './ConfigPanel';
import { Button, Space, message, Card, Upload, Modal } from 'antd';
import { PlusOutlined, SaveOutlined, FullscreenOutlined, FullscreenExitOutlined, UploadOutlined, DownloadOutlined, ClearOutlined } from '@ant-design/icons';

const Dashboard = () => {
  const gridRef = useRef(null);
  const gridInstance = useRef(null);
  const dashboardRef = useRef(null);
  const [widgets, setWidgets] = useState([]);
  const [configPanelVisible, setConfigPanelVisible] = useState(false);
  const [selectedWidget, setSelectedWidget] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [refreshTriggers, setRefreshTriggers] = useState({});
  const [globalTheme, setGlobalTheme] = useState('light');

  const handleChartClick = useCallback((sourceConfig, params) => {
    message.info(`图表 "${sourceConfig.title}" 被点击，正在联动刷新...`);
    
    const linkTargets = sourceConfig.linkTargets || [];
    const newTriggers = { ...refreshTriggers };
    
    widgets.forEach((widget) => {
      if (linkTargets.includes('all') || linkTargets.includes(widget.id)) {
        newTriggers[widget.id] = Date.now();
      }
    });
    
    setRefreshTriggers(newTriggers);
  }, [widgets, refreshTriggers]);

  const handleWidgetConfigChange = useCallback((widgetId, newConfig) => {
    setWidgets((prev) =>
      prev.map((w) => (w.id === widgetId ? { ...w, config: newConfig } : w))
    );
  }, []);

  const removeWidget = useCallback((widgetId) => {
    const container = document.getElementById(`content-${widgetId}`);
    if (container) {
      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
    }
    
    setWidgets((prev) => prev.filter((w) => w.id !== widgetId));
    gridInstance.current?.removeWidget(document.querySelector(`[gs-id="${widgetId}"]`));
    message.success('图表已删除');
  }, []);

  const renderWidget = useCallback((widget) => {
    const container = document.getElementById(`content-${widget.id}`);
    if (!container) return;

    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    const root = document.createElement('div');
    root.style.height = '100%';
    container.appendChild(root);

    import('react-dom/client').then(({ createRoot }) => {
      const reactRoot = createRoot(root);
      reactRoot.render(
        <ChartComponent
          config={{ ...widget.config, theme: widget.config.theme || globalTheme }}
          onConfigChange={(newConfig) => handleWidgetConfigChange(widget.id, newConfig)}
          onDelete={() => removeWidget(widget.id)}
          onOpenConfig={() => {
            setSelectedWidget(widget);
            setConfigPanelVisible(true);
          }}
          onChartClick={handleChartClick}
          triggerRefresh={refreshTriggers[widget.id]}
          isFullscreen={isFullscreen}
        />
      );
    });
  }, [handleWidgetConfigChange, removeWidget, handleChartClick, refreshTriggers, globalTheme]);

  const renderWidgets = useCallback((widgetList) => {
    if (!gridInstance.current) return;

    gridInstance.current.removeAll();

    widgetList.forEach((widget) => {
      const el = document.createElement('div');
      el.className = 'grid-stack-item';
      el.setAttribute('gs-id', widget.id);
      el.setAttribute('gs-x', widget.x);
      el.setAttribute('gs-y', widget.y);
      el.setAttribute('gs-w', widget.w);
      el.setAttribute('gs-h', widget.h);

      const content = document.createElement('div');
      content.className = 'grid-stack-item-content';
      content.id = `content-${widget.id}`;

      el.appendChild(content);
      gridInstance.current.addWidget(el);
      
      setTimeout(() => renderWidget(widget), 0);
    });
  }, [renderWidget]);

  useEffect(() => {
    if (!gridRef.current) return;

    gridInstance.current = GridStack.init({
      column: 12,
      row: 0,
      cellHeight: '80px',
      margin: 10,
      float: false,
      acceptWidgets: true,
      resizable: { handles: 'e, se, s, sw, w' },
      draggable: { handle: '.chart-header' },
      animate: true
    }, gridRef.current);

    const initialWidgets = [
      {
        id: 'widget-1',
        x: 0, y: 0, w: 6, h: 2,
        config: { title: '销售趋势', chartType: 'line', dataSource: 'static', autoRefresh: false, refreshInterval: 0, enableLink: true, linkTargets: ['widget-2', 'widget-3'] }
      },
      {
        id: 'widget-2',
        x: 6, y: 0, w: 6, h: 2,
        config: { title: '月度对比', chartType: 'bar', dataSource: 'static', autoRefresh: false, refreshInterval: 0, enableLink: false }
      },
      {
        id: 'widget-3',
        x: 0, y: 2, w: 4, h: 2,
        config: { title: '流量来源', chartType: 'pie', dataSource: 'static', autoRefresh: false, refreshInterval: 0, enableLink: false }
      },
      {
        id: 'widget-4',
        x: 4, y: 2, w: 8, h: 2,
        config: { title: '利润分析', chartType: 'line', dataSource: 'api', autoRefresh: true, refreshInterval: 30, enableLink: true, linkTargets: ['all'] }
      }
    ];

    setWidgets(initialWidgets);
    renderWidgets(initialWidgets);

    gridInstance.current.on('change', (event, items) => {
      const updatedWidgets = items.map((item) => ({
        id: item.id,
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
        config: widgets.find((w) => w.id === item.id)?.config || {}
      }));
      setWidgets(updatedWidgets);
    });

    gridInstance.current.on('dragstop', () => {
      gridInstance.current?.compact();
    });

    gridInstance.current.on('resizestop', () => {
      gridInstance.current?.compact();
    });

    return () => {
      widgets.forEach((widget) => {
        const container = document.getElementById(`content-${widget.id}`);
        if (container) {
          while (container.firstChild) {
            container.removeChild(container.firstChild);
          }
        }
      });
      gridInstance.current?.destroy();
      gridInstance.current = null;
    };
  }, []);

  useEffect(() => {
    widgets.forEach((widget) => {
      renderWidget(widget);
    });
  }, [globalTheme]);

  const addWidget = useCallback(() => {
    const newId = `widget-${Date.now()}`;
    const newWidget = {
      id: newId,
      x: 0, y: 0, w: 4, h: 2,
      config: { 
        title: '新图表', 
        chartType: 'line', 
        dataSource: 'static', 
        autoRefresh: false, 
        refreshInterval: 0,
        enableLink: false,
        theme: globalTheme
      }
    };

    setWidgets((prev) => [...prev, newWidget]);

    if (gridInstance.current) {
      const el = document.createElement('div');
      el.className = 'grid-stack-item';
      el.setAttribute('gs-id', newWidget.id);
      el.setAttribute('gs-x', newWidget.x);
      el.setAttribute('gs-y', newWidget.y);
      el.setAttribute('gs-w', newWidget.w);
      el.setAttribute('gs-h', newWidget.h);

      const content = document.createElement('div');
      content.className = 'grid-stack-item-content';
      content.id = `content-${newWidget.id}`;

      el.appendChild(content);
      gridInstance.current.addWidget(el);
      
      gridInstance.current.compact();
      
      setTimeout(() => renderWidget(newWidget), 0);
    }

    message.success('图表已添加');
  }, [renderWidget, globalTheme]);

  const saveLayout = useCallback(() => {
    const layout = widgets.map((w) => ({
      id: w.id,
      x: w.x,
      y: w.y,
      w: w.w,
      h: w.h,
      config: w.config
    }));
    localStorage.setItem('dashboardLayout', JSON.stringify(layout));
    message.success('布局已保存');
  }, [widgets]);

  const loadLayout = useCallback(() => {
    const saved = localStorage.getItem('dashboardLayout');
    if (saved) {
      const layout = JSON.parse(saved);
      
      widgets.forEach((widget) => {
        const container = document.getElementById(`content-${widget.id}`);
        if (container) {
          while (container.firstChild) {
            container.removeChild(container.firstChild);
          }
        }
      });
      
      setWidgets(layout);
      renderWidgets(layout);
      message.success('布局已加载');
    } else {
      message.info('没有保存的布局');
    }
  }, [widgets, renderWidgets]);

  const exportTheme = useCallback(() => {
    const themeConfig = {
      globalTheme,
      widgets: widgets.map((w) => ({
        id: w.id,
        title: w.config.title,
        theme: w.config.theme,
        chartType: w.config.chartType,
        enableFilter: w.config.enableFilter,
        filterScript: w.config.filterScript,
        enableLink: w.config.enableLink,
        linkTargets: w.config.linkTargets,
        position: { x: w.x, y: w.y, w: w.w, h: w.h }
      })),
      exportTime: new Date().toISOString()
    };

    const dataStr = JSON.stringify(themeConfig, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `dashboard-theme-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
    message.success('主题配置已导出');
  }, [widgets, globalTheme]);

  const importTheme = useCallback((file) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const themeConfig = JSON.parse(e.target.result);
        
        if (themeConfig.globalTheme) {
          setGlobalTheme(themeConfig.globalTheme);
        }

        if (themeConfig.widgets && themeConfig.widgets.length) {
          const updatedWidgets = themeConfig.widgets.map((w) => ({
            id: w.id,
            ...w.position,
            config: {
              title: w.title,
              theme: w.theme,
              chartType: w.chartType,
              enableFilter: w.enableFilter,
              filterScript: w.filterScript,
              enableLink: w.enableLink,
              linkTargets: w.linkTargets
            }
          }));
          
          widgets.forEach((widget) => {
            const container = document.getElementById(`content-${widget.id}`);
            if (container) {
              while (container.firstChild) {
                container.removeChild(container.firstChild);
              }
            }
          });
          
          setWidgets(updatedWidgets);
          renderWidgets(updatedWidgets);
        }

        message.success('主题配置已导入');
      } catch (error) {
        message.error('导入失败：文件格式错误');
      }
    };
    reader.readAsText(file);
    return false;
  }, [widgets, renderWidgets]);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      dashboardRef.current?.requestFullscreen().then(() => {
        setIsFullscreen(true);
        message.success('已进入全屏模式，按ESC退出');
      }).catch((err) => {
        message.error('全屏模式不可用');
      });
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
      });
    }
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  const setAllTheme = useCallback((theme) => {
    setGlobalTheme(theme);
    message.success(`已切换到${theme === 'dark' ? '深色' : '浅色'}主题`);
  }, []);

  const bgColor = globalTheme === 'dark' ? '#141414' : '#f0f2f5';
  const cardBgColor = globalTheme === 'dark' ? '#1f1f1f' : '#fff';
  const textColor = globalTheme === 'dark' ? '#fff' : '#000';

  return (
    <div 
      ref={dashboardRef} 
      style={{ 
        height: '100vh', 
        display: 'flex', 
        flexDirection: 'column',
        backgroundColor: bgColor,
        transition: 'all 0.3s'
      }}
    >
      <Card
        size="small"
        style={{ 
          borderRadius: 0, 
          borderLeft: 0, 
          borderRight: 0, 
          borderTop: 0,
          backgroundColor: cardBgColor,
          borderColor: globalTheme === 'dark' ? '#333' : '#f0f0f0'
        }}
        title={
          <h2 style={{ margin: 0, color: textColor }}>
            动态仪表盘低代码平台
            {isFullscreen && <span style={{ marginLeft: 16, fontSize: 14, color: '#1890ff' }}>全屏模式</span>}
          </h2>
        }
        extra={
          <Space wrap>
            <Button 
              type={globalTheme === 'dark' ? 'default' : 'primary'} 
              icon={<PlusOutlined />} 
              onClick={addWidget}
            >
              添加图表
            </Button>
            <Button icon={<SaveOutlined />} onClick={saveLayout}>
              保存布局
            </Button>
            <Button onClick={loadLayout}>加载布局</Button>
            <Button icon={<DownloadOutlined />} onClick={exportTheme}>
              导出主题
            </Button>
            <Upload 
              showUploadList={false}
              beforeUpload={importTheme}
              accept=".json"
            >
              <Button icon={<UploadOutlined />}>导入主题</Button>
            </Upload>
            <Button 
              onClick={() => setAllTheme(globalTheme === 'dark' ? 'light' : 'dark')}
            >
              {globalTheme === 'dark' ? '☀️ 浅色' : '🌙 深色'}
            </Button>
            <Button 
              icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />} 
              onClick={toggleFullscreen}
              type="primary"
              danger={isFullscreen}
            >
              {isFullscreen ? '退出全屏' : '大屏模式'}
            </Button>
          </Space>
        }
      />

      <div style={{ flex: 1, padding: 16, overflow: 'auto' }}>
        <div 
          ref={gridRef} 
          className="grid-stack" 
          style={{ 
            background: globalTheme === 'dark' ? '#141414' : '#fff',
            minHeight: isFullscreen ? 'calc(100vh - 120px)' : '600px'
          }} 
        />
      </div>

      <ConfigPanel
        visible={configPanelVisible}
        onClose={() => setConfigPanelVisible(false)}
        config={selectedWidget?.config || {}}
        onConfigChange={(newConfig) => {
          if (selectedWidget) {
            handleWidgetConfigChange(selectedWidget.id, newConfig);
          }
        }}
        onExportTheme={exportTheme}
        onImportTheme={() => {
          document.querySelector('.ant-upload input')?.click();
        }}
      />
    </div>
  );
};

export default Dashboard;
