import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Tag,
  Button,
  Space,
  message,
  Collapse,
  Alert,
  Typography,
  Modal,
  Input,
} from 'antd';
import {
  CodeOutlined,
  CopyOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { slowLogAPI, auditAPI } from '../api/api';

const { Panel } = Collapse;
const { TextArea } = Input;
const { Paragraph, Text } = Typography;

function getPriorityColor(priority) {
  const colors = {
    critical: '#cf1322',
    high: '#ff4d4f',
    medium: '#faad14',
    low: '#1890ff',
  };
  return colors[priority] || '#999';
}

function getPriorityLabel(priority) {
  const labels = {
    critical: '紧急',
    high: '高',
    medium: '中',
    low: '低',
  };
  return labels[priority] || priority;
}

function getRiskColor(risk) {
  const colors = {
    critical: '#cf1322',
    high: '#ff4d4f',
    medium: '#faad14',
    low: '#1890ff',
    normal: '#52c41a',
  };
  return colors[risk] || '#999';
}

function getRiskLabel(risk) {
  const labels = {
    critical: '严重',
    high: '高',
    medium: '中',
    low: '低',
    normal: '正常',
  };
  return labels[risk] || risk;
}

function AutoOptimization() {
  const [loading, setLoading] = useState(false);
  const [commands, setCommands] = useState([]);
  const [scripts, setScripts] = useState({});
  const [selectedScript, setSelectedScript] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [cmdRes, scriptRes] = await Promise.all([
        slowLogAPI.getAutoOptimizationCommands(),
        slowLogAPI.getOptimizationScripts('all'),
      ]);

      if (cmdRes.data.success) {
        setCommands(cmdRes.data.data || []);
      }
      if (scriptRes.data.success) {
        setScripts(scriptRes.data.data || {});
      }
    } catch (error) {
      message.error('加载优化命令失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      message.success('已复制到剪贴板');
    });
  };

  const markAsExecuted = async (item, result) => {
    try {
      setExecuting(true);
      await auditAPI.createLog({
        action_type: `${item.key_type}_optimization`,
        target_key: item.key,
        description: `执行优化: ${item.key}`,
        status: 'completed',
        metadata: {
          ...item,
          execution_result: result,
        },
      });
      message.success('已记录执行日志');
    } catch (error) {
      message.error('记录日志失败');
      console.error(error);
    } finally {
      setExecuting(false);
    }
  };

  const expandedRowRender = (record) => (
    <Card size="small" style={{ margin: '8px 0' }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        {record.optimization_commands?.map((cmd, idx) => (
          <div key={idx} style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 8 }}>
              <Text strong>{cmd.description}</Text>
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined />}
                onClick={() => copyToClipboard(cmd.command)}
              >
                复制
              </Button>
              <Button
                type="text"
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => markAsExecuted(record, `执行了: ${cmd.description}`)}
              >
                标记已执行
              </Button>
            </div>
            <Paragraph
              style={{
                background: '#f5f5f5',
                padding: 12,
                borderRadius: 4,
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap',
                marginBottom: 4,
              }}
            >
              {cmd.command}
            </Paragraph>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {cmd.explanation}
            </Text>
          </div>
        ))}
      </Space>
    </Card>
  );

  const columns = [
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (val) => (
        <Tag color={getPriorityColor(val)} style={{ fontWeight: 'bold' }}>
          {getPriorityLabel(val)}
        </Tag>
      ),
      sorter: (a, b) => {
        const order = { critical: 0, high: 1, medium: 2, low: 3 };
        return (order[a.priority] || 99) - (order[b.priority] || 99);
      },
    },
    {
      title: 'Key',
      dataIndex: 'key',
      key: 'key',
      render: (text) => <Tag color="magenta">{text}</Tag>,
    },
    {
      title: '类型',
      dataIndex: 'key_type',
      key: 'key_type',
      width: 100,
      render: (val) => <Tag>{val}</Tag>,
    },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 100,
      render: (val) => (
        <Tag color={getRiskColor(val)}>{getRiskLabel(val)}</Tag>
      ),
    },
    {
      title: '元素数',
      dataIndex: 'elements',
      key: 'elements',
      width: 100,
      render: (val) => (val !== undefined ? val.toLocaleString() : '-'),
      sorter: (a, b) => (a.elements || 0) - (b.elements || 0),
    },
    {
      title: '访问次数',
      dataIndex: 'access_count',
      key: 'access_count',
      width: 120,
      render: (val) => (val !== undefined ? val.toLocaleString() : '-'),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, textAlign: 'right' }}>
        <Button onClick={loadData} loading={loading} type="primary">
          刷新优化建议
        </Button>
      </div>

      {commands.length > 0 && (
        <Alert
          message={`发现 ${commands.length} 个可优化项`}
          description={
            <div>
              <Tag color="red">
                紧急: {commands.filter((c) => c.priority === 'critical').length}
              </Tag>
              <Tag color="orange">
                高: {commands.filter((c) => c.priority === 'high').length}
              </Tag>
              <Tag color="gold">
                中: {commands.filter((c) => c.priority === 'medium').length}
              </Tag>
            </div>
          }
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      <Card title="自动优化建议" className="table-container" style={{ marginBottom: 16 }}>
        <Table
          columns={columns}
          dataSource={commands}
          rowKey="key"
          loading={loading}
          expandable={{
            expandedRowRender,
            expandRowByClick: true,
          }}
          pagination={{
            pageSize: 10,
            showTotal: (total) => `共 ${total} 项优化建议`,
          }}
        />
      </Card>

      <Card title="优化脚本库" extra={<CodeOutlined />}>
        <Collapse defaultActiveKey={[]}>
          {Object.entries(scripts).map(([key, script]) => (
            <Panel
              header={
                <Space>
                  <Tag color="purple">{key}</Tag>
                  <Text>{key}</Text>
                </Space>
              }
              key={key}
            >
              <div style={{ marginBottom: 8 }}>
                <Button
                  type="primary"
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={() => copyToClipboard(script)}
                >
                  复制脚本
                </Button>
              </div>
              <pre
                style={{
                  background: '#f5f5f5',
                  padding: 16,
                  borderRadius: 4,
                  overflowX: 'auto',
                  fontSize: 12,
                }}
              >
                {script}
              </pre>
            </Panel>
          ))}
        </Collapse>
      </Card>
    </div>
  );
}

export default AutoOptimization;
