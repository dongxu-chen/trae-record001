import { useState, useEffect, useRef } from 'react';
import {
  Card,
  Space,
  Select,
  Button,
  Input,
  Tabs,
  Table,
  Tag,
  Tooltip,
  Descriptions,
  Row,
  Col,
  Progress
} from 'antd';
import {
  ReloadOutlined,
  ApiOutlined,
  TableOutlined,
  FieldNumberOutlined,
  LineChartOutlined,
  AimOutlined
} from '@ant-design/icons';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';

const { TabPane } = Tabs;
const { TextArea } = Input;

// 自定义节点
const TableNode = ({ data }) => {
  return (
    <div style={{
      background: '#fff',
      border: '2px solid #1890ff',
      borderRadius: '8px',
      padding: '12px',
      minWidth: '180px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <TableOutlined style={{ color: '#1890ff' }} />
        <strong>{data.label}</strong>
        {data.isSource && <Tag color="green">源</Tag>}
        {data.isTarget && <Tag color="orange">目标</Tag>}
      </div>
      {data.columns && data.columns.length > 0 && (
        <div style={{ fontSize: '12px', color: '#666' }}>
          {data.columns.slice(0, 3).join(', ')}
          {data.columns.length > 3 && `... (+${data.columns.length - 3})`}
        </div>
      )}
    </div>
  );
};

const FieldNode = ({ data }) => {
  return (
    <div style={{
      background: '#f9f9f9',
      border: '1px solid #d9d9d9',
      borderRadius: '4px',
      padding: '4px 8px',
      fontSize: '12px'
    }}>
      <FieldNumberOutlined style={{ marginRight: '4px' }} />
      {data.label}
    </div>
  );
};

const nodeTypes = {
  table: TableNode,
  field: FieldNode
};

export default function LineageViewer() {
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [sqlInput, setSqlInput] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('graph');

  // 示例SQL
  const sampleSQL = `
SELECT
    o.order_id,
    o.customer_id,
    c.customer_name,
    SUM(o.amount) as total_amount,
    COUNT(o.order_id) as order_count
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
LEFT JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_date >= '2024-01-01'
GROUP BY o.order_id, o.customer_id, c.customer_name
  `.trim();

  const analyzeSQL = async () => {
    if (!sqlInput.trim()) return;
    setLoading(true);
    try {
      // 模拟API调用
      const result = mockAnalyzeSQL(sqlInput);
      setAnalysisResult(result);
      buildGraphFromResult(result);
    } catch (error) {
      console.error('Analysis error:', error);
    } finally {
      setLoading(false);
    }
  };

  const mockAnalyzeSQL = (sql) => {
    return {
      tables: {
        source: ['orders', 'customers', 'order_items'],
        target: ['result_table'],
        all: ['orders', 'customers', 'order_items', 'result_table']
      },
      field_lineages: [
        {
          source_table: 'orders',
          source_column: 'order_id',
          target_table: 'result_table',
          target_column: 'order_id',
          transformation: 'direct'
        },
        {
          source_table: 'orders',
          source_column: 'customer_id',
          target_table: 'result_table',
          target_column: 'customer_id',
          transformation: 'direct'
        },
        {
          source_table: 'customers',
          source_column: 'customer_name',
          target_table: 'result_table',
          target_column: 'customer_name',
          transformation: 'direct'
        },
        {
          source_table: 'orders',
          source_column: 'amount',
          target_table: 'result_table',
          target_column: 'total_amount',
          transformation: 'aggregate',
          expression: 'SUM(amount)'
        },
        {
          source_table: 'orders',
          source_column: 'order_id',
          target_table: 'result_table',
          target_column: 'order_count',
          transformation: 'aggregate',
          expression: 'COUNT(order_id)'
        }
      ],
      transformation_types: ['direct', 'aggregate', 'join']
    };
  };

  const buildGraphFromResult = (result) => {
    const newNodes = [];
    const newEdges = [];

    // 布局表节点
    const tables = result.tables.all;
    const tablePositions = {};
    tables.forEach((table, index) => {
      const isSource = result.tables.source.includes(table);
      const isTarget = result.tables.target.includes(table);
      const x = isTarget ? 500 : isSource ? 50 : 250;
      const y = index * 150 + 50;
      tablePositions[table] = { x, y };

      const columns = result.field_lineages
        .filter(fl => fl.source_table === table || fl.target_table === table)
        .map(fl => fl.source_column || fl.target_column);

      newNodes.push({
        id: `table_${table}`,
        type: 'table',
        position: { x, y },
        data: {
          label: table,
          isSource,
          isTarget,
          columns: [...new Set(columns)]
        }
      });
    });

    // 添加字段边
    result.field_lineages.forEach((fl, index) => {
      const sourceTablePos = tablePositions[fl.source_table];
      const targetTablePos = tablePositions[fl.target_table];

      if (sourceTablePos && targetTablePos) {
        newEdges.push({
          id: `edge_${index}`,
          source: `table_${fl.source_table}`,
          target: `table_${fl.target_table}`,
          animated: fl.transformation !== 'direct',
          label: fl.expression || fl.transformation,
          style: {
            stroke: fl.transformation === 'aggregate' ? '#ff4d4f' :
                   fl.transformation === 'join' ? '#722ed1' : '#1890ff',
            strokeWidth: 2
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#1890ff'
          }
        });
      }
    });

    setNodes(newNodes);
    setEdges(newEdges);
  };

  const onConnect = (params) => {
    setEdges((eds) => addEdge(params, eds));
  };

  const lineageColumns = [
    { title: '源表', dataIndex: 'source_table', key: 'source_table', render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '源字段', dataIndex: 'source_column', key: 'source_column' },
    { title: '→', key: 'arrow', render: () => '→' },
    { title: '目标表', dataIndex: 'target_table', key: 'target_table', render: (v) => <Tag color="orange">{v}</Tag> },
    { title: '目标字段', dataIndex: 'target_column', key: 'target_column' },
    { title: '转换类型', dataIndex: 'transformation', key: 'transformation', render: (v) => <Tag>{v}</Tag> },
    { title: '表达式', dataIndex: 'expression', key: 'expression' }
  ];

  const performanceColumns = [
    { title: '指标', dataIndex: 'metric', key: 'metric' },
    { title: '值', dataIndex: 'value', key: 'value' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (status) => (
      <Tag color={status === 'good' ? 'green' : status === 'warning' ? 'orange' : 'red'}>
        {status}
      </Tag>
    )}
  ];

  return (
    <div style={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Card title="数据血缘分析" extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => setSqlInput(sampleSQL)}>
              加载示例
            </Button>
          </Space>
        }>
          <Row gutter={16}>
            <Col span={12}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <label>输入SQL语句：</label>
                <TextArea
                  value={sqlInput}
                  onChange={(e) => setSqlInput(e.target.value)}
                  rows={8}
                  placeholder="输入SQL语句进行血缘分析..."
                />
                <Button
                  type="primary"
                  icon={<ApiOutlined />}
                  onClick={analyzeSQL}
                  loading={loading}
                  block
                >
                  分析血缘
                </Button>
              </Space>
            </Col>
            <Col span={12}>
              {analysisResult && (
                <Descriptions title="分析结果" bordered size="small" column={1}>
                  <Descriptions.Item label="源表数量">
                    {analysisResult.tables.source.map(t => <Tag key={t} color="blue">{t}</Tag>)}
                  </Descriptions.Item>
                  <Descriptions.Item label="目标表数量">
                    {analysisResult.tables.target.map(t => <Tag key={t} color="orange">{t}</Tag>)}
                  </Descriptions.Item>
                  <Descriptions.Item label="字段映射数量">
                    {analysisResult.field_lineages.length}
                  </Descriptions.Item>
                  <Descriptions.Item label="转换类型">
                    {analysisResult.transformation_types.map(t => <Tag key={t}>{t}</Tag>)}
                  </Descriptions.Item>
                </Descriptions>
              )}
            </Col>
          </Row>
        </Card>

        <Card style={{ flex: 1, overflow: 'hidden' }} bodyStyle={{ height: '100%', padding: 0 }}>
          <Tabs activeKey={activeTab} onChange={setActiveTab} style={{ height: '100%' }}>
            <TabPane tab={<span><LineChartOutlined />血缘图谱</span>} key="graph">
              <div ref={reactFlowWrapper} style={{ height: '500px' }}>
                <ReactFlowProvider>
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    nodeTypes={nodeTypes}
                    fitView
                  >
                    <Controls />
                    <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
                  </ReactFlow>
                </ReactFlowProvider>
              </div>
            </TabPane>
            <TabPane tab={<span><FieldNumberOutlined />字段级血缘</span>} key="fields">
              <Table
                dataSource={analysisResult?.field_lineages || []}
                columns={lineageColumns}
                rowKey={(record, index) => index}
                pagination={false}
                scroll={{ y: 400 }}
              />
            </TabPane>
            <TabPane tab={<span><AimOutlined />性能分析</span>} key="performance">
              <Row gutter={16} style={{ padding: '16px' }}>
                <Col span={12}>
                  <Card title="性能概览" size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>
                        <div style={{ marginBottom: '8px' }}>总体性能评分</div>
                        <Progress percent={85} status="active" strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }} />
                      </div>
                      <Descriptions column={1} size="small">
                        <Descriptions.Item label="执行时间">12.5 秒</Descriptions.Item>
                        <Descriptions.Item label="数据吞吐量">1,234 行/秒</Descriptions.Item>
                        <Descriptions.Item label="内存使用峰值">256 MB</Descriptions.Item>
                      </Descriptions>
                    </Space>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="优化建议" size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Alert message="建议增加join字段的索引" type="info" showIcon />
                      <Alert message="可以考虑对orders表进行分区" type="warning" showIcon />
                      <Alert message="聚合操作可以优化" type="success" showIcon />
                    </Space>
                  </Card>
                </Col>
              </Row>
            </TabPane>
          </Tabs>
        </Card>
      </Space>
    </div>
  );
}
