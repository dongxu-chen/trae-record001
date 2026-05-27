import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Select, Button, Spin, Alert, Space, Tag } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  BarChartOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { ConfusionMatrixData, ModelInfo } from '@/types';
import { getConfusionMatrix, getModels } from '@/services/api';

const { Option } = Select;

const ConfusionMatrixPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ConfusionMatrixData | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState('default');
  const [k, setK] = useState(10);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    loadData();
  }, [selectedModel, k]);

  const loadModels = async () => {
    try {
      const res = await getModels();
      setModels(res.data);
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getConfusionMatrix(selectedModel, k);
      setData(res.data);
    } catch (err: any) {
      setError('加载混淆矩阵数据失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const getChartOption = () => {
    if (!data) return {};

    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
      },
      series: [
        {
          name: '分类统计',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['35%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            show: true,
            formatter: '{b}: {c}',
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 16,
              fontWeight: 'bold',
            },
          },
          data: [
            { value: data.tp, name: '真阳性 (TP)', itemStyle: { color: '#52c41a' } },
            { value: data.fp, name: '假阳性 (FP)', itemStyle: { color: '#faad14' } },
            { value: data.fn, name: '假阴性 (FN)', itemStyle: { color: '#ff4d4f' } },
            { value: data.tn, name: '真阴性 (TN)', itemStyle: { color: '#1677ff' } },
          ],
        },
      ],
    };
  };

  const getMetricsChartOption = () => {
    if (!data) return {};

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: ['准确率', '精确率', '召回率', 'F1 Score', '特异性'],
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 1,
        axisLabel: {
          formatter: '{value}',
        },
      },
      series: [
        {
          name: '指标值',
          type: 'bar',
          data: [
            { value: data.accuracy, itemStyle: { color: '#1677ff' } },
            { value: data.precision, itemStyle: { color: '#52c41a' } },
            { value: data.recall, itemStyle: { color: '#fa8c16' } },
            { value: data.f1_score, itemStyle: { color: '#722ed1' } },
            { value: data.specificity, itemStyle: { color: '#13c2c2' } },
          ],
          label: {
            show: true,
            position: 'top',
            formatter: '{c}',
          },
          barWidth: '50%',
        },
      ],
    };
  };

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>混淆矩阵分析</h2>

      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <span style={{ color: '#666' }}>检索模型：</span>
          <Select
            value={selectedModel}
            onChange={setSelectedModel}
            style={{ width: 200 }}
          >
            {models.map(model => (
              <Option key={model.model_name} value={model.model_name}>
                {model.model_name}
              </Option>
            ))}
          </Select>

          <span style={{ color: '#666' }}>Top-K：</span>
          <Select value={k} onChange={setK} style={{ width: 120 }}>
            {[1, 3, 5, 10, 20, 30, 50].map(val => (
              <Option key={val} value={val}>Top {val}</Option>
            ))}
          </Select>

          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
        </Space>
      </Card>

      {error && (
        <Alert message={error} type="error" showIcon style={{ marginBottom: 24 }} />
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '100px' }}>
          <Spin size="large" />
        </div>
      ) : data ? (
        <div>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={12} sm={8}>
              <Card className="metric-card">
                <Statistic
                  title={
                    <span>
                      <CheckCircleOutlined style={{ color: '#52c41a' }} /> 真阳性 (TP)
                    </span>
                  }
                  value={data.tp}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8}>
              <Card className="metric-card">
                <Statistic
                  title={
                    <span>
                      <CloseCircleOutlined style={{ color: '#faad14' }} /> 假阳性 (FP)
                    </span>
                  }
                  value={data.fp}
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8}>
              <Card className="metric-card">
                <Statistic
                  title={
                    <span>
                      <CloseCircleOutlined style={{ color: '#ff4d4f' }} /> 假阴性 (FN)
                    </span>
                  }
                  value={data.fn}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8}>
              <Card className="metric-card">
                <Statistic
                  title={
                    <span>
                      <CheckCircleOutlined style={{ color: '#1677ff' }} /> 真阴性 (TN)
                    </span>
                  }
                  value={data.tn}
                  valueStyle={{ color: '#1677ff' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8}>
              <Card className="metric-card">
                <Statistic
                  title="准确率"
                  value={data.accuracy * 100}
                  suffix="%"
                  precision={2}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8}>
              <Card className="metric-card">
                <Statistic
                  title="F1 Score"
                  value={data.f1_score * 100}
                  suffix="%"
                  precision={2}
                  valueStyle={{ color: '#13c2c2' }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="混淆矩阵分布">
                <ReactECharts option={getChartOption()} style={{ height: 400 }} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="评估指标对比">
                <ReactECharts option={getMetricsChartOption()} style={{ height: 400 }} />
              </Card>
            </Col>
          </Row>

          <Card
            title={
              <Space>
                <BarChartOutlined />
                <span>混淆矩阵表格</span>
              </Space>
            }
            style={{ marginTop: 24 }}
          >
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'center' }}>
                <thead>
                  <tr>
                    <th style={{ padding: 16, border: '1px solid #e8e8e8', background: '#fafafa' }}></th>
                    <th style={{ padding: 16, border: '1px solid #e8e8e8', background: '#fafafa' }} colSpan={2}>
                      <Tag color="blue">预测值</Tag>
                    </th>
                  </tr>
                  <tr>
                    <th style={{ padding: 16, border: '1px solid #e8e8e8', background: '#fafafa' }}></th>
                    <th style={{ padding: 16, border: '1px solid #e8e8e8', background: '#fafafa' }}>相关 (1)</th>
                    <th style={{ padding: 16, border: '1px solid #e8e8e8', background: '#fafafa' }}>不相关 (0)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td rowSpan={2} style={{ padding: 16, border: '1px solid #e8e8e8', background: '#fafafa', width: 120 }}>
                      <div style={{ writingMode: 'vertical-rl', textOrientation: 'mixed' }}>
                        <Tag color="green">真实值</Tag>
                      </div>
                    </td>
                    <td className="confusion-matrix-cell tp-cell" style={{ border: '1px solid #e8e8e8' }}>
                      <div style={{ fontSize: 24, fontWeight: 'bold', color: '#389e0d' }}>{data.tp}</div>
                      <div style={{ fontSize: 12, color: '#666' }}>真阳性 (TP)</div>
                      <div style={{ fontSize: 12, color: '#999' }}>正确预测为相关</div>
                    </td>
                    <td className="confusion-matrix-cell fn-cell" style={{ border: '1px solid #e8e8e8' }}>
                      <div style={{ fontSize: 24, fontWeight: 'bold', color: '#cf1322' }}>{data.fn}</div>
                      <div style={{ fontSize: 12, color: '#666' }}>假阴性 (FN)</div>
                      <div style={{ fontSize: 12, color: '#999' }}>错误预测为不相关</div>
                    </td>
                  </tr>
                  <tr>
                    <td className="confusion-matrix-cell fp-cell" style={{ border: '1px solid #e8e8e8' }}>
                      <div style={{ fontSize: 24, fontWeight: 'bold', color: '#d46b08' }}>{data.fp}</div>
                      <div style={{ fontSize: 12, color: '#666' }}>假阳性 (FP)</div>
                      <div style={{ fontSize: 12, color: '#999' }}>错误预测为相关</div>
                    </td>
                    <td className="confusion-matrix-cell tn-cell" style={{ border: '1px solid #e8e8e8' }}>
                      <div style={{ fontSize: 24, fontWeight: 'bold', color: '#096dd9' }}>{data.tn}</div>
                      <div style={{ fontSize: 12, color: '#666' }}>真阴性 (TN)</div>
                      <div style={{ fontSize: 12, color: '#999' }}>正确预测为不相关</div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
};

export default ConfusionMatrixPage;
