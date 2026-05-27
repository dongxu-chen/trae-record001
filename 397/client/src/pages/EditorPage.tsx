import React, { useState, useEffect } from 'react';
import {
  Layout, Menu, Button, Input, Drawer, Form, InputNumber, ColorPicker, message
} from 'antd';
import {
  LineChartOutlined, BarChartOutlined, PieChartOutlined,
  AreaChartOutlined, DashboardOutlined, StockOutlined, TableOutlined,
  FontSizeOutlined, PictureOutlined, DeleteOutlined,
  SaveOutlined, UndoOutlined, RedoOutlined, DownloadOutlined
} from '@ant-design/icons';
import { useParams } from 'react-router-dom';
import { templateAPI } from '../services/api';
import { Template, TemplateComponent, LayoutConfig } from '../types';
import { generateId } from '../utils/helpers';
import ChartRenderer from '../components/ChartRenderer';

const { Sider, Content } = Layout;

const EditorPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [template, setTemplate] = useState<Template | null>(null);
  const [components, setComponents] = useState<TemplateComponent[]>([]);
  const [layout, setLayout] = useState<LayoutConfig>({
    gridCols: 12, gridRows: 8, gutter: 16, backgroundColor: '#0F172A'
  });
  const [selectedComponent, setSelectedComponent] = useState<TemplateComponent | null>(null);
  const [componentPanelVisible, setComponentPanelVisible] = useState(false);
  const [componentForm] = Form.useForm();

  useEffect(() => {
    if (id) {
      loadTemplate();
    }
  }, [id]);

  const loadTemplate = async () => {
    if (!id) return;
    try {
      const response = await templateAPI.getTemplateById(id);
      setTemplate(response.template);
      setComponents(response.template.components || []);
      if (response.template.layout) {
        setLayout(response.template.layout);
      }
    } catch (error) {
      console.error('加载模板失败:', error);
    }
  };

  const addComponent = (type: string, chartType?: string) => {
    const newComponent: TemplateComponent = {
      id: generateId(),
      type: type as any,
      chartType: chartType as any,
      title: '新组件',
      position: { x: 0, y: 0 },
      size: { w: 3, h: 2 },
      config: {},
      dataSource: {
        type: 'static',
        data: []
      }
    };

    if (type === 'metric') {
      newComponent.config = { value: '0', trend: '+0%', color: '#10B981' };
    }

    setComponents([...components, newComponent]);
    setSelectedComponent(newComponent);
    setComponentPanelVisible(true);
    componentForm.setFieldsValue(newComponent);
  };

  const updateComponent = (values: any) => {
    if (!selectedComponent) return;
    
    const updatedComponents = components.map(comp =>
      comp.id === selectedComponent.id
        ? { ...comp, ...values }
        : comp
    );
    setComponents(updatedComponents);
    setSelectedComponent({ ...selectedComponent, ...values });
  };

  const deleteComponent = () => {
    if (!selectedComponent) return;
    setComponents(components.filter(c => c.id !== selectedComponent.id));
    setSelectedComponent(null);
    setComponentPanelVisible(false);
  };

  const handleComponentClick = (comp: TemplateComponent) => {
    setSelectedComponent(comp);
    setComponentPanelVisible(true);
    componentForm.setFieldsValue(comp);
  };

  const saveTemplate = () => {
    message.success('模板已保存');
  };

  const exportTemplate = () => {
    const data = JSON.stringify({ components, layout }, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${template?.title || 'dashboard'}-template.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const componentMenuItems = [
    {
      key: 'charts',
      label: '图表组件',
      type: 'group' as const,
      children: [
        { key: 'line', label: '折线图', icon: <LineChartOutlined /> },
        { key: 'bar', label: '柱状图', icon: <BarChartOutlined /> },
        { key: 'pie', label: '饼图', icon: <PieChartOutlined /> },
        { key: 'area', label: '面积图', icon: <AreaChartOutlined /> },
        { key: 'gauge', label: '仪表盘', icon: <DashboardOutlined /> }
      ]
    },
    {
      key: 'basic',
      label: '基础组件',
      type: 'group' as const,
      children: [
        { key: 'metric', label: '指标卡片', icon: <StockOutlined /> },
        { key: 'table', label: '表格', icon: <TableOutlined /> },
        { key: 'text', label: '文本', icon: <FontSizeOutlined /> },
        { key: 'image', label: '图片', icon: <PictureOutlined /> }
      ]
    }
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    if (['line', 'bar', 'pie', 'area', 'gauge'].includes(key)) {
      addComponent('chart', key);
    } else {
      addComponent(key);
    }
  };

  return (
    <Layout className="h-screen">
      <Sider width={240} style={{ background: '#1E293B' }}>
        <div className="p-4 border-b border-slate-700">
          <h2 className="text-white font-bold text-lg">组件库</h2>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          items={componentMenuItems}
          onClick={handleMenuClick}
          style={{ background: '#1E293B' }}
        />
      </Sider>
      <Layout>
        <div className="h-14 px-6 flex items-center justify-between" style={{ background: '#1E293B', borderBottom: '1px solid #334155' }}>
          <div className="flex items-center gap-4">
            <h1 className="text-white font-semibold">
              {template?.title || '新建仪表板'}
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <Button icon={<UndoOutlined />}>撤销</Button>
            <Button icon={<RedoOutlined />}>重做</Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={saveTemplate}>
              保存
            </Button>
            <Button icon={<DownloadOutlined />} onClick={exportTemplate}>
              导出
            </Button>
          </div>
        </div>
        <Content className="p-6 overflow-auto" style={{ background: '#0F172A' }}>
          <div
            className="relative rounded-xl"
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${layout.gridCols}, 1fr)`,
              gridAutoRows: '100px',
              gap: `${layout.gutter}px`,
              background: layout.backgroundColor,
              padding: `${layout.gutter}px`,
              minHeight: '600px'
            }}
          >
            {components.map((comp) => (
              <div
                key={comp.id}
                className={`rounded-xl p-4 cursor-pointer transition-all ${selectedComponent?.id === comp.id ? 'ring-2 ring-blue-500' : ''}`}
                style={{
                  gridColumn: `${comp.position.x + 1} / span ${comp.size.w}`,
                  gridRow: `${comp.position.y + 1} / span ${comp.size.h}`,
                  background: '#1E293B',
                  border: '1px solid #334155'
                }}
                onClick={() => handleComponentClick(comp)}
              >
                <h4 className="text-white font-medium mb-2">{comp.title}</h4>
                {comp.type === 'chart' && (
                  <ChartRenderer component={comp} style={{ height: 'calc(100% - 30px)' }} />
                )}
                {comp.type === 'metric' && (
                  <div className="text-center py-4">
                    <p className="text-3xl font-bold text-white">{comp.config.value}</p>
                    <p className="text-sm" style={{ color: comp.config.color }}>{comp.config.trend}</p>
                  </div>
                )}
                {comp.type === 'text' && (
                  <div className="text-slate-300">文本组件</div>
                )}
                {comp.type === 'table' && (
                  <div className="text-slate-400">表格组件</div>
                )}
                {comp.type === 'image' && (
                  <div className="text-slate-400">图片组件</div>
                )}
              </div>
            ))}
          </div>
        </Content>
      </Layout>

      <Drawer
        title="组件属性"
        placement="right"
        onClose={() => setComponentPanelVisible(false)}
        open={componentPanelVisible}
        width={320}
      >
        {selectedComponent && (
          <Form
            form={componentForm}
            layout="vertical"
            onFinish={updateComponent}
            onValuesChange={updateComponent}
          >
            <Form.Item name="title" label="标题">
              <Input />
            </Form.Item>
            
            <div className="grid grid-cols-2 gap-4">
              <Form.Item name={['position', 'x']} label="X 位置">
                <InputNumber min={0} max={layout.gridCols - 1} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name={['position', 'y']} label="Y 位置">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Form.Item name={['size', 'w']} label="宽度">
                <InputNumber min={1} max={layout.gridCols} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name={['size', 'h']} label="高度">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </div>

            {selectedComponent.type === 'metric' && (
              <>
                <Form.Item name={['config', 'value']} label="数值">
                  <Input />
                </Form.Item>
                <Form.Item name={['config', 'trend']} label="趋势">
                  <Input />
                </Form.Item>
                <Form.Item name={['config', 'color']} label="颜色" trigger="onChange">
                  <ColorPicker showText />
                </Form.Item>
              </>
            )}

            <Form.Item>
              <div className="flex gap-2">
                <Button type="primary" htmlType="submit">应用</Button>
                <Button danger icon={<DeleteOutlined />} onClick={deleteComponent}>删除</Button>
              </div>
            </Form.Item>
          </Form>
        )}
      </Drawer>
    </Layout>
  );
};

export default EditorPage;
