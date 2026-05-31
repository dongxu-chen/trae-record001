import React from 'react';
import { Modal, Descriptions, Table, Tag, Space, Typography } from 'antd';
import type { ServiceNodeDetail, ServiceCallDetail } from '../types';

const { Title, Text } = Typography;

interface ServiceDetailModalProps {
  visible: boolean;
  service: ServiceNodeDetail | null;
  onClose: () => void;
}

const ServiceDetailModal: React.FC<ServiceDetailModalProps> = ({ visible, service, onClose }) => {
  if (!service) return null;

  const callColumns = [
    {
      title: '服务名称',
      dataIndex: 'serviceName',
      key: 'serviceName',
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: '调用类型',
      dataIndex: 'callType',
      key: 'callType',
      render: (type: string) => {
        const colors: Record<string, string> = {
          'SYNC_HTTP': 'blue',
          'ASYNC_HTTP': 'orange',
          'MESSAGE_QUEUE': 'purple',
          'DATABASE': 'cyan',
          'GRPC': 'green'
        };
        return <Tag color={colors[type] || 'default'}>{type}</Tag>;
      }
    },
    {
      title: '协议',
      dataIndex: 'protocol',
      key: 'protocol'
    },
    {
      title: '异步',
      dataIndex: 'isAsync',
      key: 'isAsync',
      render: (isAsync: boolean) => isAsync ? <Tag color="orange">是</Tag> : <Tag color="default">否</Tag>
    },
    {
      title: '消息队列',
      dataIndex: 'messageQueue',
      key: 'messageQueue',
      render: (mq: string) => mq ? <Tag color="purple">{mq}</Tag> : '-'
    },
    {
      title: '方法/路径',
      dataIndex: 'path',
      key: 'path',
      render: (path: string, record: ServiceCallDetail) => (
        <Space>
          {record.httpMethod && <Tag color="blue">{record.httpMethod}</Tag>}
          {path && <Text code>{path}</Text>}
        </Space>
      )
    },
    {
      title: '调用次数',
      dataIndex: 'callCount',
      key: 'callCount',
      render: (count: number) => <Text strong>{count}</Text>
    },
    {
      title: '错误次数',
      dataIndex: 'errorCount',
      key: 'errorCount',
      render: (count: number) => count > 0 
        ? <Text type="danger" strong>{count}</Text> 
        : count
    },
    {
      title: '平均延迟',
      dataIndex: 'avgLatencyMs',
      key: 'avgLatencyMs',
      render: (latency: number) => `${latency.toFixed(2)}ms`
    }
  ];

  const statusColor = service.status === 'ACTIVE' ? 'success' : 'error';
  const langColors: Record<string, string> = {
    'Java': '#b07219',
    'Python': '#3572A5',
    'Go': '#00ADD8',
    'Node.js': '#339933',
    'Rust': '#dea584',
    'C#': '#178600'
  };

  return (
    <Modal
      title={`服务详情 - ${service.name}`}
      open={visible}
      onCancel={onClose}
      width={1000}
      footer={null}
    >
      <Descriptions bordered column={2} style={{ marginBottom: 20 }}>
        <Descriptions.Item label="服务ID">{service.id}</Descriptions.Item>
        <Descriptions.Item label="服务名称">{service.name}</Descriptions.Item>
        <Descriptions.Item label="命名空间">{service.namespace}</Descriptions.Item>
        <Descriptions.Item label="类型">{service.type}</Descriptions.Item>
        <Descriptions.Item label="编程语言">
          <Tag color={langColors[service.language] || 'default'}>
            {service.language || 'Unknown'}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="版本">{service.version || '-'}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={statusColor}>{service.status}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="服务类型">{service.serviceType || '-'}</Descriptions.Item>
        <Descriptions.Item label="Cluster IP">{service.clusterIp || '-'}</Descriptions.Item>
        <Descriptions.Item label="端口">{service.ports || '-'}</Descriptions.Item>
        <Descriptions.Item label="发现时间">{service.discoveredAt || '-'}</Descriptions.Item>
        <Descriptions.Item label="最后更新">{service.lastUpdated || '-'}</Descriptions.Item>
      </Descriptions>

      <Title level={5}>入站调用 ({service.incomingCalls?.length || 0})</Title>
      <Table
        columns={callColumns}
        dataSource={service.incomingCalls || []}
        rowKey="serviceId"
        size="small"
        pagination={false}
        style={{ marginBottom: 20 }}
      />

      <Title level={5}>出站调用 ({service.outgoingCalls?.length || 0})</Title>
      <Table
        columns={callColumns}
        dataSource={service.outgoingCalls || []}
        rowKey="serviceId"
        size="small"
        pagination={false}
      />
    </Modal>
  );
};

export default ServiceDetailModal;
