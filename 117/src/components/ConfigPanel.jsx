import React, { useState } from 'react';
import { Drawer, Form, Input, Select, InputNumber, Switch, Button, Space, Divider, Collapse, message, Typography } from 'antd';
import { DatabaseOutlined, ClockCircleOutlined, FilterOutlined, LinkOutlined, SkinOutlined } from '@ant-design/icons';

const { TextArea } = Input;
const { Panel } = Collapse;
const { Text } = Typography;

const ConfigPanel = ({ visible, onClose, config, onConfigChange, onExportTheme, onImportTheme }) => {
  const [form] = Form.useForm();
  const [filterError, setFilterError] = useState('');

  const handleValuesChange = (changedValues) => {
    onConfigChange({ ...config, ...changedValues });
  };

  const validateFilter = () => {
    const filterScript = config.filterScript;
    if (!filterScript) {
      setFilterError('');
      return;
    }
    
    try {
      new Function('data', filterScript);
      setFilterError('');
      message.success('过滤器脚本验证通过');
    } catch (error) {
      setFilterError('脚本语法错误: ' + error.message);
    }
  };

  const defaultFilterScript = `// 数据过滤器示例
// data: 原始数据对象
// 返回处理后的数据

// 示例1: 数据筛选
// return data.filter(item => item.value > 100);

// 示例2: 数据聚合
// return data.reduce((acc, item) => acc + item.value, 0);

// 示例3: 数据转换
// return data.map(item => ({ ...item, value: item.value * 2 }));

return data;`;

  return (
    <Drawer
      title="图表配置"
      placement="right"
      onClose={onClose}
      open={visible}
      width={420}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={config}
        onValuesChange={handleValuesChange}
      >
        <Divider orientation="left">基本设置</Divider>
        <Form.Item label="图表标题" name="title">
          <Input placeholder="请输入图表标题" />
        </Form.Item>

        <Divider orientation="left">
          <DatabaseOutlined /> 数据源配置
        </Divider>
        <Form.Item label="数据源类型" name="dataSource">
          <Select
            options={[
              { value: 'static', label: '静态数据' },
              { value: 'api', label: 'Mock API' }
            ]}
          />
        </Form.Item>

        {config.dataSource === 'api' && (
          <Form.Item label="API地址" name="apiUrl">
            <Input placeholder="请输入API地址" />
          </Form.Item>
        )}

        <Divider orientation="left">
          <FilterOutlined /> 数据过滤器
        </Divider>
        <Form.Item label="启用数据过滤" name="enableFilter" valuePropName="checked">
          <Switch />
        </Form.Item>

        {config.enableFilter && (
          <>
            <Form.Item
              label="过滤脚本"
              name="filterScript"
              help={<Text type="danger">{filterError}</Text>}
            >
              <TextArea
                rows={8}
                placeholder={defaultFilterScript}
                defaultValue={defaultFilterScript}
                style={{ fontFamily: 'monospace' }}
              />
            </Form.Item>
            <Button type="dashed" onClick={validateFilter} style={{ marginBottom: 16 }}>
              验证脚本
            </Button>
          </>
        )}

        <Divider orientation="left">
          <LinkOutlined /> 联动配置
        </Divider>
        <Form.Item label="启用点击联动" name="enableLink" valuePropName="checked">
          <Switch />
        </Form.Item>

        {config.enableLink && (
          <Form.Item label="联动目标图表" name="linkTargets">
            <Select
              mode="multiple"
              placeholder="选择要联动刷新的图表"
              options={[
                { value: 'all', label: '全部图表' },
                { value: 'widget-1', label: '销售趋势' },
                { value: 'widget-2', label: '月度对比' },
                { value: 'widget-3', label: '流量来源' },
                { value: 'widget-4', label: '利润分析' }
              ]}
            />
          </Form.Item>
        )}

        <Divider orientation="left">
          <ClockCircleOutlined /> 刷新设置
        </Divider>
        <Form.Item label="开启自动刷新" name="autoRefresh" valuePropName="checked">
          <Switch />
        </Form.Item>

        {config.autoRefresh && (
          <Form.Item label="刷新间隔(秒)" name="refreshInterval">
            <InputNumber min={5} max={3600} style={{ width: '100%' }} placeholder="5-3600秒" />
          </Form.Item>
        )}

        <Divider orientation="left">
          <SkinOutlined /> 主题配置
        </Divider>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button block onClick={onExportTheme}>
            导出当前主题配置
          </Button>
          <Button block onClick={onImportTheme}>
            导入主题配置
          </Button>
          <Button block onClick={() => {
            onConfigChange({ ...config, theme: 'light' });
            message.success('已切换到浅色主题');
          }}>
            浅色主题
          </Button>
          <Button block onClick={() => {
            onConfigChange({ ...config, theme: 'dark' });
            message.success('已切换到深色主题');
          }}>
            深色主题
          </Button>
        </Space>

        <Divider />
        <Form.Item>
          <Space>
            <Button type="primary" onClick={onClose}>
              确定
            </Button>
            <Button onClick={onClose}>取消</Button>
          </Space>
        </Form.Item>
      </Form>
    </Drawer>
  );
};

export default ConfigPanel;
