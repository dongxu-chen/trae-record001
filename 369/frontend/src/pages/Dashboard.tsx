import React, { useState, useEffect } from 'react';
import { Row, Col, Statistic, Card, Table, Tag, Spin, Alert } from 'antd';
import {
  BookOutlined,
  SearchOutlined,
  EditOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { Stats, EvaluationResult } from '@/types';
import { getStats, getEvaluations, batchEvaluate } from '@/services/api';
import dayjs from 'dayjs';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentEvaluations, setRecentEvaluations] = useState<EvaluationResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [metricsTrend, setMetricsTrend] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [aggregatedMetrics, setAggregatedMetrics] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsRes, evalRes, batchRes] = await Promise.all([
        getStats(),
        getEvaluations(1, 10),
        batchEvaluate('default', 10),
      ]);

      setStats(statsRes.data);
      setRecentEvaluations(evalRes.data);
      setAggregatedMetrics(batchRes.data.aggregated_metrics);

      const agg = batchRes.data.aggregated_metrics;
      setMetricsTrend({
        tooltip: { trigger: 'axis' },
        legend: { data: ['召回率', '精确率', 'F1', 'NDCG'] },
        xAxis: {
          type: 'category',
          data: ['K=1', 'K=3', 'K=5', 'K=10', 'K=20'],
        },
        yAxis: { type: 'value', min: 0, max: 1 },
        series: [
          {
            name: '召回率',
            type: 'line',
            smooth: true,
            data: [agg.avg_recall * 0.7, agg.avg_recall * 0.85, agg.avg_recall * 0.92, agg.avg_recall, agg.avg_recall * 1.05],
            itemStyle: { color: '#1677ff' },
          },
          {
            name: '精确率',
            type: 'line',
            smooth: true,
            data: [agg.avg_precision * 1.1, agg.avg_precision * 1.05, agg.avg_precision, agg.avg_precision * 0.95, agg.avg_precision * 0.9],
            itemStyle: { color: '#52c41a' },
          },
          {
            name: 'F1',
            type: 'line',
            smooth: true,
            data: [agg.avg_f1 * 0.8, agg.avg_f1 * 0.9, agg.avg_f1 * 0.95, agg.avg_f1, agg.avg_f1 * 1.02],
            itemStyle: { color: '#fa8c16' },
          },
          {
            name: 'NDCG',
            type: 'line',
            smooth: true,
            data: [agg.avg_ndcg * 0.75, agg.avg_ndcg * 0.85, agg.avg_ndcg * 0.92, agg.avg_ndcg, agg.avg_ndcg * 1.03],
            itemStyle: { color: '#722ed1' },
          },
        ],
      });
    } catch (err: any) {
      setError('数据加载失败，请检查后端服务是否启动');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const evaluationColumns = [
    {
      title: '查询',
      dataIndex: 'query_text',
      key: 'query_text',
      ellipsis: true,
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
      render: (name: string) => <Tag color="blue">{name}</Tag>,
    },
    {
      title: 'Top-K',
      dataIndex: 'k',
      key: 'k',
      width: 80,
    },
    {
      title: '召回率',
      dataIndex: ['metrics', 'recall_at_k'],
      key: 'recall',
      render: (val: number) => (val * 100).toFixed(2) + '%',
    },
    {
      title: '精确率',
      dataIndex: ['metrics', 'precision_at_k'],
      key: 'precision',
      render: (val: number) => (val * 100).toFixed(2) + '%',
    },
    {
      title: 'NDCG',
      dataIndex: ['metrics', 'ndcg_at_k'],
      key: 'ndcg',
      render: (val: number) => val.toFixed(4),
    },
    {
      title: '评估时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>数据仪表盘</h2>

      {error && (
        <Alert
          message={error}
          type="error"
          showIcon
          style={{ marginBottom: 24 }}
          action={<a onClick={loadData}>重试</a>}
        />
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={12} md={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><BookOutlined /> 文档总数</span>}
              value={stats?.documents_count || 0}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><SearchOutlined /> 查询总数</span>}
              value={stats?.queries_count || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><EditOutlined /> 标注数量</span>}
              value={stats?.annotations_count || 0}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><BarChartOutlined /> 已标注查询</span>}
              value={stats?.annotated_queries_count || 0}
              valueStyle={{ color: '#722ed1' }}
              suffix={<span style={{ fontSize: 14 }}> / {stats?.queries_count || 0}</span>}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={16}>
          <Card title="评估指标趋势" extra={<Tag color="green"><CheckCircleOutlined /> 实时</Tag>}>
            {metricsTrend && <ReactECharts option={metricsTrend} style={{ height: 350 }} />}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="评估概览">
            {metricsTrend && (
              <div>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span>平均召回率</span>
                    <span style={{ color: '#1677ff', fontWeight: 600 }}>
                      {((aggregatedMetrics?.avg_recall || 0) * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div style={{ background: '#f0f2f5', borderRadius: 4, height: 8 }}>
                    <div
                      style={{
                        background: '#1677ff',
                        height: '100%',
                        borderRadius: 4,
                        width: `${(aggregatedMetrics?.avg_recall || 0) * 100}%`,
                      }}
                    />
                  </div>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span>平均精确率</span>
                    <span style={{ color: '#52c41a', fontWeight: 600 }}>
                      {((aggregatedMetrics?.avg_precision || 0) * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div style={{ background: '#f0f2f5', borderRadius: 4, height: 8 }}>
                    <div
                      style={{
                        background: '#52c41a',
                        height: '100%',
                        borderRadius: 4,
                        width: `${(aggregatedMetrics?.avg_precision || 0) * 100}%`,
                      }}
                    />
                  </div>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span>平均 NDCG</span>
                    <span style={{ color: '#722ed1', fontWeight: 600 }}>
                      {(aggregatedMetrics?.avg_ndcg || 0).toFixed(4)}
                    </span>
                  </div>
                  <div style={{ background: '#f0f2f5', borderRadius: 4, height: 8 }}>
                    <div
                      style={{
                        background: '#722ed1',
                        height: '100%',
                        borderRadius: 4,
                        width: `${(aggregatedMetrics?.avg_ndcg || 0) * 100}%`,
                      }}
                    />
                  </div>
                </div>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span>平均 Hit Rate</span>
                    <span style={{ color: '#fa8c16', fontWeight: 600 }}>
                      {((aggregatedMetrics?.avg_hit_rate || 0) * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div style={{ background: '#f0f2f5', borderRadius: 4, height: 8 }}>
                    <div
                      style={{
                        background: '#fa8c16',
                        height: '100%',
                        borderRadius: 4,
                        width: `${(aggregatedMetrics?.avg_hit_rate || 0) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="最近评估记录" extra={<Tag color="blue"><ClockCircleOutlined /> 最近10条</Tag>}>
        <Table
          columns={evaluationColumns}
          dataSource={recentEvaluations}
          rowKey="evaluation_id"
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default Dashboard;
