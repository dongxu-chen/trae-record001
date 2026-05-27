import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  message,
  Input,
  Select,
  Tooltip,
  Divider,
  Progress,
  Badge,
} from 'antd';
import {
  ThunderboltOutlined,
  SearchOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { ClickEvent, AutoAnnotationResult, Query } from '@/types';
import {
  getClickEvents,
  getQueries,
  generateAutoAnnotations,
} from '@/services/api';
import dayjs from 'dayjs';

const { Option } = Select;

const AutoAnnotation: React.FC = () => {
  const [queries, setQueries] = useState<Query[]>([]);
  const [clickEvents, setClickEvents] = useState<ClickEvent[]>([]);
  const [selectedQuery, setSelectedQuery] = useState<string>('');
  const [requestId, setRequestId] = useState<string>('');
  const [sessionId, setSessionId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [autoResult, setAutoResult] = useState<AutoAnnotationResult | null>(null);
  const [minDwellTime, setMinDwellTime] = useState(3);
  const [maxAnnotations, setMaxAnnotations] = useState(10);
  
  const chartRef = useRef<any>(null);

  useEffect(() => {
    loadQueries();
  }, []);

  const loadQueries = async () => {
    try {
      const res = await getQueries(1, 100);
      setQueries(res.data);
    } catch (err: any) {
      message.error('加载查询失败：' + (err.response?.data?.detail || err.message));
    }
  };

  const loadClickEvents = async () => {
    try {
      setLoading(true);
      const res = await getClickEvents(
        requestId || undefined,
        selectedQuery || undefined,
        sessionId || undefined
      );
      setClickEvents(res.data);
    } catch (err: any) {
      message.error('加载点击事件失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateAutoAnnotations = async () => {
    if (!requestId || !selectedQuery) {
      message.warning('请先选择查询并输入Request ID');
      return;
    }

    try {
      setLoading(true);
      const res = await generateAutoAnnotations(
        requestId,
        selectedQuery,
        minDwellTime,
        maxAnnotations
      );
      setAutoResult(res.data);
      
      if (res.data.auto_generated) {
        message.success(res.data.message);
      } else {
        message.warning(res.data.message);
      }
    } catch (err: any) {
      message.error('生成自动标注失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const getClickTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      normal: 'blue',
      quick_view: 'cyan',
      deep_view: 'geekblue',
      copy: 'purple',
    };
    return colors[type] || 'default';
  };

  const getClickTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      normal: '普通点击',
      quick_view: '快速浏览',
      deep_view: '深度浏览',
      copy: '复制内容',
    };
    return labels[type] || type;
  };

  const getDwellTimeLevel = (time: number) => {
    if (time >= 30) return { label: '深度阅读', color: 'success' };
    if (time >= 10) return { label: '认真阅读', color: 'processing' };
    if (time >= 3) return { label: '简单浏览', color: 'warning' };
    return { label: '快速跳过', color: 'error' };
  };

  const getClickHeatmapOption = () => {
    const docClickMap: Record<string, { clicks: number; totalDwellTime: number }> = {};
    
    clickEvents.forEach(event => {
      if (!docClickMap[event.doc_id]) {
        docClickMap[event.doc_id] = { clicks: 0, totalDwellTime: 0 };
      }
      docClickMap[event.doc_id].clicks += 1;
      docClickMap[event.doc_id].totalDwellTime += event.dwell_time;
    });

    const docIds = Object.keys(docClickMap);
    const clickCounts = docIds.map(id => docClickMap[id].clicks);
    const avgDwellTimes = docIds.map(id => 
      (docClickMap[id].totalDwellTime / docClickMap[id].clicks).toFixed(1)
    );

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      legend: {
        data: ['点击次数', '平均停留时间(秒)'],
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: docIds.map(id => id.slice(0, 12) + '...'),
        axisLabel: {
          rotate: 45,
          fontSize: 10,
        },
      },
      yAxis: [
        {
          type: 'value',
          name: '点击次数',
          position: 'left',
        },
        {
          type: 'value',
          name: '停留时间(秒)',
          position: 'right',
        },
      ],
      series: [
        {
          name: '点击次数',
          type: 'bar',
          data: clickCounts,
          itemStyle: {
            color: '#1677ff',
          },
        },
        {
          name: '平均停留时间(秒)',
          type: 'line',
          yAxisIndex: 1,
          data: avgDwellTimes,
          itemStyle: {
            color: '#52c41a',
          },
          smooth: true,
        },
      ],
    };
  };

  const getRelevancePredictionOption = () => {
    if (!clickEvents.length) return {};

    const relevanceLevels = [0, 1, 2, 3];
    const predictions = [0, 0, 0, 0];

    clickEvents.forEach(event => {
      const avgDwell = event.dwell_time;
      if (avgDwell >= 30 || event.click_type === 'deep_view') {
        predictions[3]++;
      } else if (avgDwell >= 10) {
        predictions[2]++;
      } else if (avgDwell >= minDwellTime || event.click_type === 'quick_view') {
        predictions[1]++;
      } else {
        predictions[0]++;
      }
    });

    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        data: ['不相关', '一般相关', '相关', '高度相关'],
      },
      series: [
        {
          name: '相关性预测',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            show: false,
            position: 'center',
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 16,
              fontWeight: 'bold',
            },
          },
          labelLine: {
            show: false,
          },
          data: [
            { value: predictions[0], name: '不相关' },
            { value: predictions[1], name: '一般相关' },
            { value: predictions[2], name: '相关' },
            { value: predictions[3], name: '高度相关' },
          ],
          color: ['#ff4d4f', '#faad14', '#1677ff', '#52c41a'],
        },
      ],
    };
  };

  const columns = [
    {
      title: '文档ID',
      dataIndex: 'doc_id',
      key: 'doc_id',
      width: 150,
      render: (id: string) => <Tag color="blue">{id}</Tag>,
    },
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 80,
      render: (rank: number) => (
        <Badge
          count={rank}
          showZero
          style={{ backgroundColor: rank <= 3 ? '#52c41a' : '#1677ff' }}
        />
      ),
    },
    {
      title: '点击位置',
      dataIndex: 'click_position',
      key: 'click_position',
      width: 100,
    },
    {
      title: '停留时间',
      dataIndex: 'dwell_time',
      key: 'dwell_time',
      width: 150,
      render: (time: number) => {
        const level = getDwellTimeLevel(time);
        return (
          <Tooltip title={`${time} 秒`}>
            <Tag color={level.color}>
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              {time.toFixed(1)}s - {level.label}
            </Tag>
          </Tooltip>
        );
      },
    },
    {
      title: '点击类型',
      dataIndex: 'click_type',
      key: 'click_type',
      width: 120,
      render: (type: string) => (
        <Tag color={getClickTypeColor(type)}>
          {getClickTypeLabel(type)}
        </Tag>
      ),
    },
    {
      title: '预测相关性',
      key: 'predicted_relevance',
      width: 120,
      render: (_: any, record: ClickEvent) => {
        const avgDwell = record.dwell_time;
        let predicted = 0;
        if (avgDwell >= 30 || record.click_type === 'deep_view') {
          predicted = 3;
        } else if (avgDwell >= 10) {
          predicted = 2;
        } else if (avgDwell >= minDwellTime || record.click_type === 'quick_view') {
          predicted = 1;
        }
        
        const colors = ['error', 'warning', 'processing', 'success'];
        const labels = ['不相关', '一般相关', '相关', '高度相关'];
        return <Tag color={colors[predicted]}>{labels[predicted]}</Tag>;
      },
    },
    {
      title: 'Request ID',
      dataIndex: 'request_id',
      key: 'request_id',
      width: 200,
      render: (rid: string) => (
        <Tooltip title="点击复制">
          <Tag
            color="geekblue"
            style={{ cursor: 'pointer', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}
            onClick={() => {
              navigator.clipboard.writeText(rid);
              message.success('已复制');
            }}
          >
            <CopyOutlined style={{ marginRight: 4 }} />
            {rid}
          </Tag>
        </Tooltip>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => dayjs(time).format('MM-DD HH:mm:ss'),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>
        <ThunderboltOutlined style={{ marginRight: 8, color: '#1677ff' }} />
        自动化标注辅助
      </h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><EyeOutlined /> 点击事件总数</span>}
              value={clickEvents.length}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><SearchOutlined /> 涉及文档数</span>}
              value={new Set(clickEvents.map(e => e.doc_id)).size}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><CheckCircleOutlined /> 可生成标注</span>}
              value={clickEvents.filter(e => e.dwell_time >= minDwellTime).length}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><ClockCircleOutlined /> 平均停留时间</span>}
              value={clickEvents.length > 0 
                ? (clickEvents.reduce((sum, e) => sum + e.dwell_time, 0) / clickEvents.length).toFixed(1)
                : 0}
              suffix="秒"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="点击行为筛选"
        style={{ marginBottom: 24 }}
      >
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <div style={{ marginBottom: 8 }}>选择查询</div>
            <Select
              style={{ width: '100%' }}
              placeholder="请选择查询"
              value={selectedQuery || undefined}
              onChange={(value) => setSelectedQuery(value)}
              showSearch
              optionFilterProp="children"
            >
              {queries.map(q => (
                <Option key={q.query_id} value={q.query_id}>
                  {q.query_text}
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 8 }}>Request ID</div>
            <Input
              placeholder="输入Request ID"
              value={requestId}
              onChange={(e) => setRequestId(e.target.value)}
              allowClear
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 8 }}>Session ID</div>
            <Input
              placeholder="输入Session ID（可选）"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              allowClear
            />
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 8 }}>&nbsp;</div>
            <Space>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={loadClickEvents}
                loading={loading}
              >
                查询点击事件
              </Button>
              <Button icon={<ReloadOutlined />} onClick={loadQueries}>
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="文档点击热力图">
            <ReactECharts
              ref={chartRef}
              option={getClickHeatmapOption()}
              style={{ height: 300 }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="相关性预测分布">
            <ReactECharts
              option={getRelevancePredictionOption()}
              style={{ height: 300 }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="自动标注生成"
        style={{ marginBottom: 24 }}
        extra={
          <Space>
            <span>最小停留时间:</span>
            <Input
              type="number"
              value={minDwellTime}
              onChange={(e) => setMinDwellTime(Number(e.target.value))}
              style={{ width: 80 }}
              min={1}
              max={60}
            />
            <span>秒</span>
            <Divider type="vertical" />
            <span>最大标注数:</span>
            <Input
              type="number"
              value={maxAnnotations}
              onChange={(e) => setMaxAnnotations(Number(e.target.value))}
              style={{ width: 80 }}
              min={1}
              max={50}
            />
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleGenerateAutoAnnotations}
              loading={loading}
              disabled={!requestId || !selectedQuery}
            >
              生成自动标注
            </Button>
          </Space>
        }
      >
        {autoResult ? (
          <div>
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="自动生成标注数"
                    value={autoResult.annotations_count}
                    valueStyle={{ color: autoResult.auto_generated ? '#52c41a' : '#ff4d4f' }}
                  />
                </Card>
              </Col>
              <Col span={16}>
                <Alert
                  message={autoResult.message}
                  type={autoResult.auto_generated ? 'success' : 'warning'}
                  showIcon
                />
              </Col>
            </Row>
            
            {autoResult.annotations.length > 0 && (
              <Table
                size="small"
                dataSource={autoResult.annotations}
                rowKey={(record: any) => record._id}
                columns={[
                  {
                    title: '文档ID',
                    dataIndex: 'doc_id',
                    key: 'doc_id',
                    render: (id: string) => <Tag>{id}</Tag>,
                  },
                  {
                    title: '相关性',
                    dataIndex: 'relevance',
                    key: 'relevance',
                    render: (rel: number) => {
                      const colors = ['error', 'warning', 'processing', 'success'];
                      const labels = ['不相关', '一般相关', '相关', '高度相关'];
                      return <Tag color={colors[rel]}>{labels[rel]}</Tag>;
                    },
                  },
                  {
                    title: '标注者',
                    dataIndex: 'annotator',
                    key: 'annotator',
                    render: (annotator: string) => (
                      <Tag color={annotator === 'auto' ? 'purple' : 'blue'}>{annotator}</Tag>
                    ),
                  },
                ]}
                pagination={false}
              />
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: '#999', padding: 24 }}>
            请先筛选点击事件，然后点击"生成自动标注"按钮
          </div>
        )}
      </Card>

      <Card title="点击事件详情">
        <Table
          columns={columns}
          dataSource={clickEvents}
          rowKey={(record, index) => `${record.request_id}_${record.doc_id}_${index}`}
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
};

export default AutoAnnotation;
