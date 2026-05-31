import React, { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Button,
  Row,
  Col,
  Statistic,
  Progress,
  Descriptions,
  List,
  Tag,
  Space,
  Alert,
  Tabs,
  message,
  Spin,
} from 'antd';
import {
  ReloadOutlined,
  TrendingUpOutlined,
  TrendingDownOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  TrophyOutlined,
  TrophyTwoTone,
  ArrowUpOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { profileApi, tenantApi } from '../services/api';

const { Option } = Select;

const QuotaProfile = () => {
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState('');
  const [profile, setProfile] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadTenants();
  }, []);

  const loadTenants = async () => {
    try {
      const result = await tenantApi.list();
      const list = result.data || [];
      setTenants(list);
      if (list.length > 0) {
        setSelectedTenant(list[0].tenantId);
      }
    } catch (error) {
      message.error('加载租户失败');
    }
  };

  useEffect(() => {
    if (selectedTenant) {
      loadProfile();
    }
  }, [selectedTenant]);

  const loadProfile = async () => {
    if (!selectedTenant) return;
    setLoading(true);
    try {
      const [profileRes, historyRes] = await Promise.all([
        profileApi.get(selectedTenant),
        profileApi.getHistory(selectedTenant, 'hour', 50),
      ]);
      setProfile(profileRes.data);
      setHistory(historyRes.data || []);
    } catch (error) {
      message.error('加载画像失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    if (!selectedTenant) return;
    setRefreshing(true);
    try {
      const result = await profileApi.generate(selectedTenant);
      setProfile(result.data);
      message.success('画像已更新');
    } catch (error) {
      message.error('刷新失败');
    } finally {
      setRefreshing(false);
    }
  };

  const getUsageChartOption = () => {
    if (!history.length === 0) return {};
    return {
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: history.map(h => h.dateTime?.substring(11, 16) || ''),
      },
      yAxis: { type: 'value', name: '使用率', axisLabel: { formatter: '{value} %' } },
      series: [{
        name: '使用率',
        type: 'line',
        smooth: true,
        areaStyle: {},
        data: history.map(h => ((h.usageRate || 0) * 100).toFixed(1)),
        markLine: {
          data: [
          { type: 'average', name: '平均值' },
          { yAxis: 60, lineStyle: { color: '#faad14' } },
          { yAxis: 80, lineStyle: { color: '#f5222d' } },
        ],
        },
      }],
    };
  };

  const getPredictionChartOption = () => {
    if (!profile?.predictions?.hour) return {};
    const pred = profile.predictions.hour;
    const historical = pred.historicalData || [];
    const predicted = pred.predictedData || [];

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['历史', '预测'] },
      xAxis: {
        type: 'category',
        data: [...Array(historical.length).keys()).map(i => `T${i}`],
      },
      yAxis: { type: 'value', name: '用量' },
      series: [
        {
          name: '历史',
          type: 'line',
          data: historical,
          smooth: true,
        itemStyle: { color: '#1890ff' },
      },
      {
        name: '预测',
        type: 'line',
        data: [...Array(historical.length - 1).fill(null).concat(historical[historical.length - 1]),
        ...predicted),
        smooth: true,
        lineStyle: { type: 'dashed' },
        itemStyle: { color: '#52c41a' },
      },
    ],
    };
  };

  const getProfileLevelColor = (level) => {
    const colors = { ELITE: 'gold', GOLD: 'orange', SILVER: 'blue', BRONZE: 'default' };
    return colors[level] || 'default';
  };

  const renderProfileLevelText = (level) => {
    const texts = { ELITE: '精英', GOLD: '黄金', SILVER: '白银', BRONZE: '青铜' };
    return texts[level] || level;
  };

  const trendIcon = profile?.predictions?.hour?.trendDirection > 0 ?
    <TrendingUpOutlined style={{ color: '#f5222d' }} /> :
    <TrendingDownOutlined style={{ color: '#52c41a' }} />;

  const tabItems = [
    {
      key: 'overview',
      label: '综合画像',
      children: (
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Card>
              <Statistic
                title="画像等级"
                value={renderProfileLevelText(profile?.profileLevel)}
                prefix={<TrophyTwoTone twoToneColor={profile?.profileLevel === 'ELITE' ? '#faad14' : '#1890ff'} />}
                valueStyle={{ color: profile?.profileLevel === 'ELITE' ? '#faad14' : '#1890ff' }}
              />
              <Progress
                type="circle"
                percent={Math.round(((profile?.stabilityScore || 0) + (profile?.efficiencyScore || 0)) * 100)}
                status="active"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="稳定性评分" value={(profile?.stabilityScore * 100).toFixed(1)} suffix="%" />
              <Progress percent={Math.round((profile?.stabilityScore || 0) * 100} status="success" />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="效率评分" value={(profile?.efficiencyScore || 0) * 100).toFixed(1)} suffix="%" />
              <Progress percent={Math.round((profile?.efficiencyScore || 0) * 100} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="趋势预测"
                value={profile?.predictions?.hour?.trendDirection > 0 ? '上升' : '平稳/下降'}
                prefix={trendIcon}
              />
              <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}
                置信度: {((profile?.predictions?.hour?.confidence || 0) * 100).toFixed(0)}%
              </div>
            </Card>
          </Col>
          <Col span={12}>
            <Card title="使用趋势" size="small">
              <ReactECharts option={getUsageChartOption()} style={{ height: 200 }} />
            </Card>
          </Col>
          <Col span={12}>
            <Card title="用量预测" size="small">
              <ReactECharts option={getPredictionChartOption()} style={{ height: 200 }} />
            </Card>
          </Col>
        </Row>
        <Card title="智能建议" size="small">
          <Alert
            message="配额建议" description={profile?.recommendation || '暂无建议'} type="info" showIcon icon={<CheckCircleOutlined />} />
        </Card>
      </Space>
    ),
    },
    {
      key: 'statistics',
      label: '详细统计',
      children: (
        <Row gutter={[16, 16]}>
          {['minute', 'hour', 'day'].map(gran => (
            <Col span={8} key={gran}>
              <Card title={`${gran}统计` size="small">
                {profile?.statistics?.[gran] && (
                  <Descriptions column={1} size="small" bordered>
                    <Descriptions.Item label="总用量">{profile.statistics[gran].totalUsed}</Descriptions.Item>
                    <Descriptions.Item label="平均使用率">
                      {(profile.statistics[gran].average * 100).toFixed(1)}%
                    </Descriptions.Item>
                    <Descriptions.Item label="峰值使用率">
                      {(profile.statistics[gran].peak * 100).toFixed(1)}%
                    </Descriptions.Item>
                    <Descriptions.Item label="95分位">
                      {(profile.statistics[gran].percentile95 * 100).toFixed(1)}%
                    </Descriptions.Item>
                    <Descriptions.Item label="标准差">
                      {profile.statistics[gran].standardDeviation.toFixed(4)}
                    </Descriptions.Item>
                    <Descriptions.Item label="高峰时段">
                      {profile.statistics[gran].peakHour}点
                    </Descriptions.Item>
                  </Descriptions>
                </Card>
            </Col>
          ))}
        </Row>
      ),
    },
    {
      key: 'predictions',
      label: '趋势预测',
      children: (
        <Row gutter={[16, 16]}>
          {['hour', 'day'].map(gran => (
            <Col span={12} key={gran}>
              <Card title={`${gran}预测` size="small">
                {profile?.predictions?.[gran] && (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic
                          title="趋势方向"
                          value={profile.predictions[gran].trendDirection > 0 ? '上升' : '下降'}
                          prefix={profile.predictions[gran].trendDirection > 0 ?
                            <TrendingUpOutlined style={{ color: '#f5222d' }} /> :
                            <TrendingDownOutlined style={{ color: '#52c41a' }} />}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic title="置信度" value={(profile.predictions[gran].confidence * 100).toFixed(0)} suffix="%" />
                      </Col>
                      <Col span={8}>
                        <Statistic title="下周期预测" value={profile.predictions[gran].predictedNextDay?.toFixed(0)} />
                      </Col>
                    </Row>
                  </Space>
                }
              </Card>
            </Col>
          ))}
        </Row>
      ),
    },
    {
      key: 'anomalies',
      label: '异常检测',
      children: profile?.anomalies?.length > 0 ? (
        <List
          dataSource={profile.anomalies}
          renderItem={(item, index) => (
            <List.Item key={index}>
              <List.Item.Meta
                avatar={<WarningOutlined style={{ color: item.severity === 'CRITICAL' ? '#f5222d' : '#faad14' }} />}
                title={
                  <Space>
                    <Tag color={item.severity === 'CRITICAL' ? 'red' : 'orange'}>
                      {item.severity === 'CRITICAL' ? '严重' : '警告'}
                    </Tag>
                    <span>{item.type} - {item.granularity}</span>
                  </Space>
                }
                description={
                  <span>
                    期望: {(item.expected * 100).toFixed(1)}%,
                    实际: {(item.actual * 100).toFixed(1)}%,
                    偏差: {item.deviation.toFixed(2)}σ
                  </span>
                }
              />
            </List.Item>
          )}
        />
      ) : (
        <Alert message="暂无异常记录" type="info" showIcon icon={<CheckCircleOutlined />} />
      ),
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Select
            value={selectedTenant}
            onChange={setSelectedTenant}
            style={{ width: 250 }}
          >
            {tenants.map(t => (
              <Option key={t.tenantId} value={t.tenantId}>
                {t.tenantName}
              </Option>
            ))}
          </Select>
          <Button icon={<ReloadOutlined />} onClick={loadProfile}>加载</Button>
          <Button type="primary" icon={<ArrowUpOutlined />} loading={refreshing} onClick={handleRefresh}>
            重新生成画像
          </Button>
        </Space>

        <Spin spinning={loading}>
          {profile ? (
            <Tabs items={tabItems} />
          ) : (
            <Alert message="请选择租户查看配额画像" type="info" />
          )}
        </Spin>
      </Card>
    </Space>
  );
};

export default QuotaProfile;
