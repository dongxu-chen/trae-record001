import React, { useState, useEffect } from 'react';
import {
  Card, Button, Row, Col, Statistic, Select, Tag, message,
  Progress, Descriptions, List, Alert, Spin, Divider,
} from 'antd';
import {
  SafetyCertificateOutlined, ArrowDownOutlined, ArrowUpOutlined,
  ThunderboltOutlined, ExperimentOutlined,
} from '@ant-design/icons';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar,
} from 'recharts';
import { evaluationAPI, topologyAPI } from '../services/api';

function EffectivenessEval() {
  const [loading, setLoading] = useState(false);
  const [services, setServices] = useState([]);
  const [selectedService, setSelectedService] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [servicesRes, historyRes] = await Promise.all([
        topologyAPI.getServices(),
        evaluationAPI.getHistory(),
      ]);
      setServices(servicesRes.data);
      setHistory(historyRes.data);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const runEvaluation = async (serviceId) => {
    try {
      setLoading(true);
      const res = await evaluationAPI.evaluate(serviceId, 30);
      setEvaluation(res.data);
      message.success('效果评估完成');
    } catch (error) {
      message.error('评估失败');
    } finally {
      setLoading(false);
    }
  };

  const evaluateAll = async () => {
    try {
      setLoading(true);
      const res = await evaluationAPI.evaluateAll(30);
      setHistory(res.data);
      message.success('全部服务评估完成');
    } catch (error) {
      message.error('评估失败');
    } finally {
      setLoading(false);
    }
  };

  const formatComparisonData = () => {
    if (!evaluation?.beforeMetrics || !evaluation?.afterMetrics) return [];

    const before = evaluation.beforeMetrics;
    const after = evaluation.afterMetrics;

    return [
      { metric: '平均延迟(ms)', 限流前: Math.round(before.avgLatencyMs), 限流后: Math.round(after.avgLatencyMs) },
      { metric: 'P95延迟(ms)', 限流前: Math.round(before.p95LatencyMs), 限流后: Math.round(after.p95LatencyMs) },
      { metric: 'P99延迟(ms)', 限流前: Math.round(before.p99LatencyMs), 限流后: Math.round(after.p99LatencyMs) },
      { metric: '错误率(%)', 限流前: +(before.errorRate * 100).toFixed(2), 限流后: +(after.errorRate * 100).toFixed(2) },
      { metric: 'CPU(%)', 限流前: +(before.cpuUtilization * 100).toFixed(1), 限流后: +(after.cpuUtilization * 100).toFixed(1) },
      { metric: '稳定性评分', 限流前: +(before.stabilityScore * 100).toFixed(1), 限流后: +(after.stabilityScore * 100).toFixed(1) },
    ];
  };

  const getVerdictColor = (score) => {
    if (score >= 70) return '#52c41a';
    if (score >= 50) return '#faad14';
    if (score >= 30) return '#fa8c16';
    return '#ff4d4f';
  };

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>限流效果评估</h2>

      <Alert
        message="限流前后系统稳定性对比"
        description="评估限流配置生效前后的系统稳定性指标变化，量化限流保护效果。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col span={8}>
            <Select
              style={{ width: '100%' }}
              placeholder="选择服务"
              onChange={setSelectedService}
              value={selectedService}
            >
              {services.map(s => (
                <Select.Option key={s.serviceId} value={s.serviceId}>
                  {s.serviceName}
                </Select.Option>
              ))}
            </Select>
          </Col>
          <Col span={4}>
            <Button type="primary" icon={<ExperimentOutlined />}
              loading={loading} onClick={() => runEvaluation(selectedService)}
              disabled={!selectedService}>
              评估此服务
            </Button>
          </Col>
          <Col span={4}>
            <Button icon={<ThunderboltOutlined />} loading={loading} onClick={evaluateAll}>
              评估全部
            </Button>
          </Col>
        </Row>
      </Card>

      {evaluation && (
        <>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="效果评分"
                  value={evaluation.effectivenessScore.toFixed(1)}
                  suffix="/100"
                  valueStyle={{ color: getVerdictColor(evaluation.effectivenessScore) }}
                  prefix={<SafetyCertificateOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="延迟降低"
                  value={evaluation.latencyReductionPercent.toFixed(1)}
                  suffix="%"
                  valueStyle={{ color: evaluation.latencyReductionPercent > 0 ? '#52c41a' : '#ff4d4f' }}
                  prefix={evaluation.latencyReductionPercent > 0 ? <ArrowDownOutlined /> : <ArrowUpOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="错误率降低"
                  value={evaluation.errorRateReductionPercent.toFixed(1)}
                  suffix="%"
                  valueStyle={{ color: evaluation.errorRateReductionPercent > 0 ? '#52c41a' : '#ff4d4f' }}
                  prefix={evaluation.errorRateReductionPercent > 0 ? <ArrowDownOutlined /> : <ArrowUpOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="稳定性提升"
                  value={evaluation.stabilityImprovement.toFixed(1)}
                  suffix="%"
                  valueStyle={{ color: evaluation.stabilityImprovement > 0 ? '#52c41a' : '#ff4d4f' }}
                  prefix={evaluation.stabilityImprovement > 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                />
              </Card>
            </Col>
          </Row>

          <Card title="评估结论" style={{ marginBottom: 24 }}>
            <Alert
              message={evaluation.overallVerdict}
              type={evaluation.effectivenessScore >= 50 ? 'success' : 'warning'}
              showIcon
              description={
                <div>
                  <Progress
                    percent={evaluation.effectivenessScore}
                    strokeColor={getVerdictColor(evaluation.effectivenessScore)}
                    style={{ maxWidth: 400, marginTop: 8 }}
                  />
                </div>
              }
            />
          </Card>

          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={14}>
              <Card title="限流前后指标对比">
                <div style={{ height: 350 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={formatComparisonData()}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="metric" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="限流前" fill="#ff4d4f" />
                      <Bar dataKey="限流后" fill="#52c41a" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </Col>
            <Col span={10}>
              <Card title="详细发现">
                <List
                  size="small"
                  dataSource={evaluation.findings}
                  renderItem={item => <List.Item style={{ fontSize: 12 }}>{item}</List.Item>}
                />
              </Card>
              {evaluation.recommendations && Object.keys(evaluation.recommendations).length > 0 && (
                <Card title="优化建议" style={{ marginTop: 16 }}>
                  <List
                    size="small"
                    dataSource={Object.entries(evaluation.recommendations)}
                    renderItem={([key, value]) => (
                      <List.Item>
                        <Tag color="blue">{key}</Tag> {String(value)}
                      </List.Item>
                    )}
                  />
                </Card>
              )}
            </Col>
          </Row>
        </>
      )}

      <Card title="评估历史">
        <Spin spinning={loading}>
          {history.length > 0 ? (
            <List
              dataSource={history}
              renderItem={item => (
                <List.Item
                  actions={[
                    <Tag color={getVerdictColor(item.effectivenessScore)}>
                      {item.effectivenessScore.toFixed(0)}分
                    </Tag>,
                  ]}
                >
                  <List.Item.Meta
                    title={`${item.serviceId} - ${item.overallVerdict}`}
                    description={`延迟降低${item.latencyReductionPercent?.toFixed(1) || 0}% | 错误率降低${item.errorRateReductionPercent?.toFixed(1) || 0}%`}
                  />
                </List.Item>
              )}
            />
          ) : (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无评估记录，请先运行评估</div>
          )}
        </Spin>
      </Card>
    </div>
  );
}

export default EffectivenessEval;
