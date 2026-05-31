import React, { useState, useEffect } from 'react';
import {
  Card, Button, Table, Tag, Space, message, Statistic, Row, Col,
  Progress, Descriptions, List, Tooltip, Badge, Alert, Divider
} from 'antd';
import {
  ThunderboltOutlined, CheckCircleOutlined, CloseCircleOutlined,
  BarChartOutlined, RocketOutlined, SwapOutlined
} from '@ant-design/icons';
import { recommendationApi } from '../services/api';

const Recommendation = () => {
  const [loading, setLoading] = useState(false);
  const [recommendation, setRecommendation] = useState(null);

  useEffect(() => {
    loadRecommendation();
  }, []);

  const loadRecommendation = async () => {
    setLoading(true);
    try {
      const res = await recommendationApi.getStrategyRecommendation('default', true);
      setRecommendation(res.data?.data);
    } catch (e) {
      message.error('加载推荐失败');
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return '#52c41a';
    if (confidence >= 0.6) return '#1677ff';
    if (confidence >= 0.4) return '#faad14';
    return '#ff4d4f';
  };

  const renderRecommendedStrategy = () => {
    if (!recommendation?.recommendedStrategy) return null;
    const s = recommendation.recommendedStrategy;
    return (
      <Card
        title={
          <Space>
            <ThunderboltOutlined style={{ color: '#faad14' }} />
            推荐策略
            <Tag color="gold" icon={<CheckCircleOutlined />}>
              置信度 {(recommendation.confidenceScore * 100).toFixed(0)}%
            </Tag>
          </Space>
        }
        size="small"
        extra={
          <Space>
            <Button type="primary" size="small">
              <RocketOutlined /> 应用策略
            </Button>
            <Button size="small">
              <SwapOutlined /> 验证效果
            </Button>
          </Space>
        }
      >
        <Descriptions bordered size="small" column={3}>
          <Descriptions.Item label="策略名称">{s.name}</Descriptions.Item>
          <Descriptions.Item label="策略类型">{s.type}</Descriptions.Item>
          <Descriptions.Item label="限流阈值">{s.threshold} QPS</Descriptions.Item>
          <Descriptions.Item label="超时时间">{s.timeoutMs} ms</Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>{s.description}</Descriptions.Item>
        </Descriptions>
        
        {recommendation.recommendationReason && (
          <Alert
            style={{ marginTop: 12 }}
            message="推荐理由"
            description={recommendation.recommendationReason}
            type="info"
            showIcon
          />
        )}
      </Card>
    );
  };

  const renderHistoricalPerformance = () => {
    if (!recommendation?.historicalPerformance?.length) return null;
    
    const columns = [
      { title: '策略名称', dataIndex: 'strategyName', key: 'name', width: 150 },
      { title: '演练次数', dataIndex: 'drillCount', key: 'count', width: 100 },
      { 
        title: '平均得分', 
        dataIndex: 'avgScore', 
        key: 'avg',
        width: 150,
        render: (v) => <Progress percent={v?.toFixed(0)} size="small" />
      },
      { title: '最佳得分', dataIndex: 'bestScore', key: 'best', width: 100, render: v => v?.toFixed(1) },
      { title: '最差得分', dataIndex: 'worstScore', key: 'worst', width: 100, render: v => v?.toFixed(1) },
      { title: '平均恢复时间', dataIndex: 'avgRecoveryTimeMs', key: 'recovery', width: 120, render: v => `${v?.toFixed(0)}ms` },
      { title: '平均错误率', dataIndex: 'avgErrorRate', key: 'error', width: 100, render: v => `${v?.toFixed(1)}%` },
      { title: '峰值QPS', dataIndex: 'peakQpsHandled', key: 'qps', width: 100, render: v => v?.toFixed(0) },
    ];

    return (
      <Card title={
        <Space>
          <BarChartOutlined />
          历史表现对比
        </Space>
      } size="small" style={{ marginTop: 16 }}>
        <Table
          columns={columns}
          dataSource={recommendation.historicalPerformance}
          rowKey="strategyId"
          size="small"
          pagination={false}
        />
      </Card>
    );
  };

  const renderAlternatives = () => {
    if (!recommendation?.alternativeStrategies?.length) return null;
    
    return (
      <Card title={
        <Space>
          <SwapOutlined />
          备选策略 ({recommendation.alternativeStrategies.length})
        </Space>
      } size="small" style={{ marginTop: 16 }}>
        <List
          grid={{ gutter: 16, column: 2 }}
          dataSource={recommendation.alternativeStrategies}
          renderItem={(item) => (
            <List.Item>
              <Card size="small" title={item.name}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="类型">{item.type}</Descriptions.Item>
                  <Descriptions.Item label="阈值">{item.threshold} QPS</Descriptions.Item>
                  <Descriptions.Item label="超时">{item.timeoutMs} ms</Descriptions.Item>
                </Descriptions>
              </Card>
            </List.Item>
          )}
        />
      </Card>
    );
  };

  return (
    <div>
      <Card
        title="智能策略推荐"
        extra={
          <Space>
            <Button icon={<SwapOutlined />} onClick={loadRecommendation} loading={loading}>
              刷新推荐
            </Button>
          </Space>
        }
      >
        {recommendation && (
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="分析策略数"
                  value={recommendation.historicalPerformance?.length || 0}
                  suffix="个"
                  prefix={<BarChartOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="推荐置信度"
                  value={(recommendation.confidenceScore * 100).toFixed(0)}
                  suffix="%"
                  valueStyle={{ color: getConfidenceColor(recommendation.confidenceScore) }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="备选策略"
                  value={recommendation.alternativeStrategies?.length || 0}
                  suffix="个"
                  prefix={<SwapOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="场景类型"
                  value={recommendation.scenarioType === 'SPIKE_PRONE' ? '突发流量型' : 
                         recommendation.scenarioType === 'GRADUAL_GROWTH' ? '平稳增长型' : '混合型'}
                  valueStyle={{ fontSize: 14 }}
                />
              </Card>
            </Col>
          </Row>
        )}

        {renderRecommendedStrategy()}
        {renderHistoricalPerformance()}
        {renderAlternatives()}

        {!recommendation && !loading && (
          <div style={{ textAlign: 'center', padding: 48 }}>
            暂无推荐数据，请先执行演练任务
          </div>
        )}
      </Card>
    </div>
  );
};

export default Recommendation;
