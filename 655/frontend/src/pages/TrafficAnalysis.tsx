import React, { useEffect, useState, useRef } from 'react';
import {
  Card, Row, Col, Select, DatePicker, Button, Space, Spin, message,
  Table, Statistic, Tag, Form,
} from 'antd';
import {
  ReloadOutlined, DownloadOutlined, BarChartOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { metricsAPI, reportsAPI } from '../services/api';
import type { TrafficMetrics, TrafficReport, ServiceReport } from '../types';

const { Option } = Select;
const { RangePicker } = DatePicker;

const TrafficAnalysis: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [namespace, setNamespace] = useState('default');
  const [metrics, setMetrics] = useState<TrafficMetrics[]>([]);
  const [reports, setReports] = useState<TrafficReport[]>([]);
  const [selectedService, setSelectedService] = useState<string>('');
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const demoMetrics: TrafficMetrics[] = [
    { serviceName: 'frontend', namespace: 'default', requestCount: 25680, errorCount: 128, p50Latency: 12, p95Latency: 45, p99Latency: 89, successRate: 0.995, throughput: 428, timestamp: new Date().toISOString() },
    { serviceName: 'user-service', namespace: 'default', requestCount: 12800, errorCount: 64, p50Latency: 8, p95Latency: 32, p99Latency: 67, successRate: 0.995, throughput: 213, timestamp: new Date().toISOString() },
    { serviceName: 'order-service', namespace: 'default', requestCount: 18200, errorCount: 218, p50Latency: 22, p95Latency: 78, p99Latency: 156, successRate: 0.988, throughput: 303, timestamp: new Date().toISOString() },
    { serviceName: 'payment-service', namespace: 'default', requestCount: 7400, errorCount: 22, p50Latency: 45, p95Latency: 120, p99Latency: 230, successRate: 0.997, throughput: 123, timestamp: new Date().toISOString() },
    { serviceName: 'product-service', namespace: 'default', requestCount: 9500, errorCount: 10, p50Latency: 15, p95Latency: 48, p99Latency: 92, successRate: 0.999, throughput: 158, timestamp: new Date().toISOString() },
    { serviceName: 'inventory-service', namespace: 'default', requestCount: 6200, errorCount: 31, p50Latency: 20, p95Latency: 55, p99Latency: 110, successRate: 0.995, throughput: 103, timestamp: new Date().toISOString() },
  ];

  useEffect(() => {
    fetchMetrics();
  }, [namespace, selectedService]);

  useEffect(() => {
    drawCharts();
  }, [metrics]);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const res = await metricsAPI.getMetrics(namespace, selectedService || undefined);
      setMetrics(res.data?.metrics?.length ? res.data.metrics : demoMetrics);
    } catch {
      setMetrics(demoMetrics);
      message.info('已加载演示数据');
    } finally {
      setLoading(false);
    }
  };

  const drawCharts = () => {
    const canvas = canvasRef.current;
    if (!canvas || metrics.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement?.getBoundingClientRect();
    if (!rect) return;

    canvas.width = rect.width * dpr;
    canvas.height = 400 * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = '400px';
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = 400;
    const padding = { top: 40, right: 30, bottom: 60, left: 80 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    ctx.clearRect(0, 0, w, h);

    ctx.fillStyle = '#fafafa';
    ctx.fillRect(0, 0, w, h);

    const barWidth = Math.min(60, (chartW / metrics.length) * 0.6);
    const gap = (chartW - barWidth * metrics.length) / (metrics.length + 1);

    const maxRequests = Math.max(...metrics.map((m) => m.requestCount), 1);

    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (chartH / 5) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.strokeStyle = '#e8e8e8';
      ctx.lineWidth = 1;
      ctx.stroke();

      const value = Math.round(maxRequests * (1 - i / 5));
      ctx.fillStyle = '#8c8c8c';
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(value.toLocaleString(), padding.left - 10, y + 4);
    }

    metrics.forEach((m, i) => {
      const x = padding.left + gap + i * (barWidth + gap);
      const barH = (m.requestCount / maxRequests) * chartH;
      const y = padding.top + chartH - barH;

      const gradient = ctx.createLinearGradient(x, y, x, padding.top + chartH);
      gradient.addColorStop(0, '#1890ff');
      gradient.addColorStop(1, '#69c0ff');
      ctx.fillStyle = gradient;
      ctx.fillRect(x, y, barWidth, barH);

      const errorH = (m.errorCount / maxRequests) * chartH;
      const errorY = padding.top + chartH - errorH;
      ctx.fillStyle = '#ff4d4f';
      ctx.fillRect(x, errorY, barWidth, errorH);

      ctx.fillStyle = '#333';
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.save();
      ctx.translate(x + barWidth / 2, padding.top + chartH + 12);
      ctx.rotate(-Math.PI / 6);
      ctx.fillText(m.serviceName, 0, 0);
      ctx.restore();
    });

    ctx.fillStyle = '#333';
    ctx.font = 'bold 14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('服务请求量与错误量分布', w / 2, 24);

    ctx.font = '11px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillStyle = '#1890ff';
    ctx.fillRect(w - padding.right - 150, 10, 12, 12);
    ctx.fillStyle = '#333';
    ctx.fillText('请求量', w - padding.right - 134, 20);

    ctx.fillStyle = '#ff4d4f';
    ctx.fillRect(w - padding.right - 70, 10, 12, 12);
    ctx.fillStyle = '#333';
    ctx.fillText('错误量', w - padding.right - 54, 20);
  };

  const handleGenerateReport = async (values: any) => {
    try {
      const res = await reportsAPI.generateReport({
        name: values.name,
        type: values.type,
        startDate: values.dateRange[0].toISOString(),
        endDate: values.dateRange[1].toISOString(),
        namespace,
        services: metrics.map((m) => m.serviceName),
      });
      message.success('报表生成成功');
      setReports([res.data, ...reports]);
    } catch {
      message.error('报表生成失败');
    }
  };

  const totalRequests = metrics.reduce((sum, m) => sum + m.requestCount, 0);
  const totalErrors = metrics.reduce((sum, m) => sum + m.errorCount, 0);
  const avgLatency = metrics.length > 0
    ? metrics.reduce((sum, m) => sum + m.p50Latency, 0) / metrics.length
    : 0;
  const avgSuccessRate = metrics.length > 0
    ? metrics.reduce((sum, m) => sum + m.successRate, 0) / metrics.length
    : 0;

  const reportColumns = [
    { title: '服务名称', dataIndex: 'serviceName', key: 'serviceName' },
    { title: '总请求量', dataIndex: 'totalRequests', key: 'totalRequests', render: (v: number) => v.toLocaleString() },
    {
      title: '错误率', dataIndex: 'errorRate', key: 'errorRate',
      render: (v: number) => (
        <Tag color={v > 2 ? 'red' : v > 1 ? 'orange' : 'green'}>{v.toFixed(2)}%</Tag>
      ),
    },
    { title: '平均延迟(ms)', dataIndex: 'avgLatency', key: 'avgLatency', render: (v: number) => v.toFixed(1) },
    { title: '入流量', dataIndex: 'trafficIn', key: 'trafficIn', render: (v: number) => v ? v.toFixed(1) + ' MB/s' : '-' },
    { title: '出流量', dataIndex: 'trafficOut', key: 'trafficOut', render: (v: number) => v ? v.toFixed(1) + ' MB/s' : '-' },
  ];

  return (
    <Spin spinning={loading}>
      <Card
        title="流量分析报表"
        extra={
          <Space>
            <Select value={namespace} onChange={setNamespace} style={{ width: 140 }}>
              <Option value="default">default</Option>
              <Option value="production">production</Option>
              <Option value="staging">staging</Option>
            </Select>
            <Select value={selectedService} onChange={setSelectedService} style={{ width: 180 }} allowClear placeholder="选择服务">
              {demoMetrics.map((m) => (
                <Option key={m.serviceName} value={m.serviceName}>{m.serviceName}</Option>
              ))}
            </Select>
            <Button icon={<ReloadOutlined />} onClick={fetchMetrics}>刷新</Button>
          </Space>
        }
      >
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="总请求量" value={totalRequests} valueStyle={{ color: '#1890ff' }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="总错误数" value={totalErrors} valueStyle={{ color: '#ff4d4f' }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="平均P50延迟" value={avgLatency.toFixed(1)} suffix="ms" valueStyle={{ color: '#fa8c16' }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="平均成功率" value={(avgSuccessRate * 100).toFixed(2)} suffix="%" valueStyle={{ color: '#52c41a' }} />
            </Card>
          </Col>
        </Row>

        <Card title="请求量分布图" size="small" style={{ marginBottom: 24 }}>
          <div style={{ width: '100%' }}>
            <canvas ref={canvasRef} />
          </div>
        </Card>

        <Card title="服务流量明细" size="small">
          <Table
            columns={reportColumns}
            dataSource={metrics.map((m) => ({
              serviceName: m.serviceName,
              totalRequests: m.requestCount,
              errorRate: m.requestCount > 0 ? (m.errorCount / m.requestCount) * 100 : 0,
              avgLatency: m.p50Latency,
              trafficIn: m.throughput * 0.001,
              trafficOut: m.throughput * 0.0008,
            }))}
            rowKey="serviceName"
            pagination={false}
            size="small"
          />
        </Card>
      </Card>

      <Card title="生成报表" style={{ marginTop: 16 }}>
        <Form layout="inline" onFinish={handleGenerateReport}>
          <Form.Item name="name" rules={[{ required: true, message: '请输入报表名称' }]}>
            <Input placeholder="报表名称" style={{ width: 200 }} />
          </Form.Item>
          <Form.Item name="type" initialValue="daily" rules={[{ required: true }]}>
            <Select style={{ width: 120 }}>
              <Option value="daily">日报</Option>
              <Option value="weekly">周报</Option>
              <Option value="monthly">月报</Option>
            </Select>
          </Form.Item>
          <Form.Item name="dateRange" rules={[{ required: true, message: '请选择时间范围' }]}>
            <RangePicker
              defaultValue={[dayjs().subtract(7, 'day'), dayjs()]}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<BarChartOutlined />}>
              生成报表
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </Spin>
  );
};

export default TrafficAnalysis;
