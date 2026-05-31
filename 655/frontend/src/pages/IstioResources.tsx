import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Spin, message, Tabs, Modal } from 'antd';
import { ReloadOutlined, EyeOutlined } from '@ant-design/icons';
import { istioAPI } from '../services/api';
import type { VirtualService, DestinationRule } from '../types';

const { TabPane } = Tabs;

const IstioResources: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [namespace, setNamespace] = useState('default');
  const [virtualServices, setVirtualServices] = useState<VirtualService[]>([]);
  const [destinationRules, setDestinationRules] = useState<DestinationRule[]>([]);
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailContent, setDetailContent] = useState<any>(null);
  const [detailTitle, setDetailTitle] = useState('');

  useEffect(() => {
    fetchResources();
  }, [namespace]);

  const fetchResources = async () => {
    setLoading(true);
    try {
      const [vsRes, drRes] = await Promise.allSettled([
        istioAPI.getVirtualServices(namespace),
        istioAPI.getDestinationRules(namespace),
      ]);

      if (vsRes.status === 'fulfilled') {
        setVirtualServices(vsRes.value.data?.virtualServices || []);
      }
      if (drRes.status === 'fulfilled') {
        setDestinationRules(drRes.value.data?.destinationRules || []);
      }
    } catch {
      message.error('获取Istio资源失败');
    } finally {
      setLoading(false);
    }
  };

  const showDetail = (title: string, content: any) => {
    setDetailTitle(title);
    setDetailContent(content);
    setDetailVisible(true);
  };

  const vsColumns = [
    { title: '名称', dataIndex: ['metadata', 'name'], key: 'name', width: 200 },
    { title: '命名空间', dataIndex: ['metadata', 'namespace'], key: 'namespace', width: 140 },
    {
      title: 'Hosts', key: 'hosts', width: 240,
      render: (_: any, record: VirtualService) => (
        <Space wrap>
          {(record.spec?.hosts || []).map((h: string, i: number) => (
            <Tag key={i} color="blue">{h}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '路由数', key: 'routes', width: 100,
      render: (_: any, record: VirtualService) => record.spec?.http?.length || 0,
    },
    {
      title: '操作', key: 'action', width: 100,
      render: (_: any, record: VirtualService) => (
        <Button type="link" icon={<EyeOutlined />} size="small"
          onClick={() => showDetail(`VirtualService: ${record.metadata.name}`, record.spec)}>
          详情
        </Button>
      ),
    },
  ];

  const drColumns = [
    { title: '名称', dataIndex: ['metadata', 'name'], key: 'name', width: 200 },
    { title: '命名空间', dataIndex: ['metadata', 'namespace'], key: 'namespace', width: 140 },
    {
      title: 'Host', key: 'host', width: 200,
      render: (_: any, record: DestinationRule) => (
        <Tag color="purple">{record.spec?.host || '-'}</Tag>
      ),
    },
    {
      title: 'Subsets', key: 'subsets', width: 300,
      render: (_: any, record: DestinationRule) => (
        <Space wrap>
          {(record.spec?.subsets || []).map((s: any, i: number) => (
            <Tag key={i} color="green">{s.name}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '操作', key: 'action', width: 100,
      render: (_: any, record: DestinationRule) => (
        <Button type="link" icon={<EyeOutlined />} size="small"
          onClick={() => showDetail(`DestinationRule: ${record.metadata.name}`, record.spec)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <Spin spinning={loading}>
      <Card
        title="Istio资源管理"
        extra={
          <Space>
            <Select value={namespace} onChange={(v) => { setNamespace(v); }} style={{ width: 140 }}>
              <option value="default">default</option>
              <option value="istio-system">istio-system</option>
              <option value="production">production</option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={fetchResources}>刷新</Button>
          </Space>
        }
      >
        <Tabs defaultActiveKey="vs">
          <TabPane tab={`VirtualServices (${virtualServices.length})`} key="vs">
            <Table
              columns={vsColumns}
              dataSource={virtualServices}
              rowKey={(r) => r.metadata?.name || Math.random().toString()}
              pagination={{ pageSize: 10 }}
              size="middle"
            />
          </TabPane>
          <TabPane tab={`DestinationRules (${destinationRules.length})`} key="dr">
            <Table
              columns={drColumns}
              dataSource={destinationRules}
              rowKey={(r) => r.metadata?.name || Math.random().toString()}
              pagination={{ pageSize: 10 }}
              size="middle"
            />
          </TabPane>
        </Tabs>
      </Card>

      <Modal
        title={detailTitle}
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={700}
      >
        <pre style={{
          background: '#f5f5f5',
          padding: 16,
          borderRadius: 8,
          overflow: 'auto',
          maxHeight: 500,
          fontSize: 13,
        }}>
          {JSON.stringify(detailContent, null, 2)}
        </pre>
      </Modal>
    </Spin>
  );
};

export default IstioResources;
