import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Row, Col, Statistic, Alert, Empty, Spin, Button } from 'antd';
import { LineChartOutlined, WarningOutlined, ReloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { checkApi } from '../services/api';
import dayjs from 'dayjs';

const PredictiveCheck = () => {
  const [predictions, setPredictions] = useState([]);
  const [trendDataMap, setTrendDataMap] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadPredictions();
  }, []);

  const loadPredictions = async () => {
    setLoading(true);
    try {
      const data = await checkApi.getAllPredictions();
      setPredictions(data || []);

      const trendMap = {};
      for (const pred of (data || [])) {
        try {
          const trendData = await checkApi.getTrendData(pred.tableName);
          trendMap[pred.tableName] = trendData || [];
        } catch (e) { /* ignore */ }
      }
      setTrendDataMap(trendMap);
    } catch (error) {
      console.error('Failed to load predictions:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (level) => {
    const map = { CRITICAL: '#ff4d4f', HIGH: '#fa541c', MEDIUM: '#faad14', LOW: '#52c41a' };
    return map[level] || '#8c8c8c';
  };

  const getRiskTag = (level) => {
    const colorMap = { CRITICAL: 'red', HIGH: 'orange', MEDIUM: 'warning', LOW: 'success' };
    const textMap = { CRITICAL: '严重', HIGH: '高', MEDIUM: '中等', LOW: '低' };
    return <Tag color={colorMap[level] || 'default'}>{textMap[level] || level}</Tag>;
  };

  const buildTrendChart = (tableName) => {
    const dataPoints = trendDataMap[tableName] || [];
    if (dataPoints.length < 2) return null;

    const prediction = predictions.find(p => p.tableName === tableName);

    const diffChart = {
      title: { text: `${tableName} - 差异趋势`, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { data: ['差异数', '差异率', '预测'], bottom: 0 },
      xAxis: {
        type: 'category',
        data: dataPoints.map(d => dayjs(d.timestamp).format('MM-DD HH:mm'))
      },
      yAxis: [
        { type: 'value', name: '数量' },
        { type: 'value', name: '差异率', axisLabel: { formatter: '{value}%' } }
      ],
      series: [
        {
          name: '差异数', type: 'bar', data: dataPoints.map(d => d.diffCount),
          itemStyle: { color: '#1890ff' }
        },
        {
          name: '差异率', type: 'line', yAxisIndex: 1, smooth: true,
          data: dataPoints.map(d => (d.diffRate * 100).toFixed(2)),
          itemStyle: { color: '#faad14' }
        },
        ...(prediction?.predictedDiffCount ? [{
          name: '预测', type: 'line', smooth: true,
          data: [...new Array(dataPoints.length - 1).fill(null), dataPoints[dataPoints.length - 1].diffCount, prediction.predictedDiffCount.toFixed(0)],
          itemStyle: { color: '#ff4d4f', type: 'dashed' },
          lineStyle: { type: 'dashed' }
        }] : [])
      ],
      grid: { left: 50, right: 50, top: 40, bottom: 40 }
    };

    const latencyChart = {
      title: { text: `${tableName} - 延迟趋势`, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { data: ['平均延迟', '最大延迟', '预测'], bottom: 0 },
      xAxis: {
        type: 'category',
        data: dataPoints.map(d => dayjs(d.timestamp).format('MM-DD HH:mm'))
      },
      yAxis: { type: 'value', name: '毫秒' },
      series: [
        {
          name: '平均延迟', type: 'line', smooth: true,
          data: dataPoints.map(d => d.avgLatencyMs.toFixed(0)),
          itemStyle: { color: '#1890ff' },
          areaStyle: { color: 'rgba(24, 144, 255, 0.1)' }
        },
        {
          name: '最大延迟', type: 'line', smooth: true,
          data: dataPoints.map(d => d.maxLatencyMs.toFixed(0)),
          itemStyle: { color: '#722ed1' }
        },
        ...(prediction?.predictedAvgLatency ? [{
          name: '预测', type: 'line', smooth: true,
          data: [...new Array(dataPoints.length - 1).fill(null), dataPoints[dataPoints.length - 1].avgLatencyMs.toFixed(0), prediction.predictedAvgLatency.toFixed(0)],
          itemStyle: { color: '#ff4d4f' },
          lineStyle: { type: 'dashed' }
        }] : [])
      ],
      grid: { left: 50, right: 20, top: 40, bottom: 40 }
    };

    return { diffChart, latencyChart };
  };

  const columns = [
    { title: '表名', dataIndex: 'tableName', key: 'tableName', width: 150 },
    { title: '风险等级', dataIndex: 'riskLevel', key: 'riskLevel', width: 100, render: getRiskTag },
    { title: '差异趋势', dataIndex: 'diffTrendRate', key: 'diffTrendRate', width: 120,
      render: (v) => <span style={{ color: v > 0 ? '#ff4d4f' : '#52c41a' }}>{(v * 100).toFixed(1)}%</span>
    },
    { title: '延迟趋势', dataIndex: 'latencyTrendRate', key: 'latencyTrendRate', width: 120,
      render: (v) => <span style={{ color: v > 0 ? '#ff4d4f' : '#52c41a' }}>{(v * 100).toFixed(1)}%</span>
    },
    { title: '预测差异', dataIndex: 'predictedDiffCount', key: 'predictedDiffCount', width: 100,
      render: (v) => v != null ? <span style={{ fontWeight: 'bold' }}>{Math.round(v)}</span> : '-'
    },
    { title: '预测延迟', dataIndex: 'predictedAvgLatency', key: 'predictedAvgLatency', width: 100,
      render: (v) => v != null ? `${Math.round(v)}ms` : '-'
    },
    { title: '建议下次校验', dataIndex: 'nextCheckSuggestion', key: 'nextCheckSuggestion', width: 170,
      render: (v) => v ? dayjs(v).format('MM-DD HH:mm') : '-'
    }
  ];

  const alertPredictions = predictions.filter(p => p.alertTriggered);

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>
          <LineChartOutlined style={{ marginRight: 8 }} />
          预测性校验
        </h3>
        <Button icon={<ReloadOutlined />} onClick={loadPredictions}>刷新分析</Button>
      </div>

      {alertPredictions.length > 0 && (
        <Alert
          message={`检测到 ${alertPredictions.length} 个高风险预警`}
          description={alertPredictions.map(p => `${p.tableName}: ${p.recommendation}`).join('；')}
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      {predictions.length > 0 ? (
        <>
          <Table columns={columns} dataSource={predictions} rowKey="tableName" size="small" style={{ marginBottom: 16 }}
            expandable={{
              expandedRowRender: (record) => {
                const charts = buildTrendChart(record.tableName);
                if (!charts) return <Empty description="数据点不足，无法生成趋势图" />;
                return (
                  <Row gutter={[16, 16]}>
                    <Col xs={24} md={12}>
                      <ReactECharts option={charts.diffChart} style={{ height: 300 }} />
                    </Col>
                    <Col xs={24} md={12}>
                      <ReactECharts option={charts.latencyChart} style={{ height: 300 }} />
                    </Col>
                  </Row>
                );
              }
            }}
          />

          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <Card size="small" title="风险分布">
                <Row gutter={[8, 8]}>
                  {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(level => (
                    <Col span={12} key={level}>
                      <Card size="small" style={{ borderLeft: `3px solid ${getRiskColor(level)}` }}>
                        <Statistic
                          title={level}
                          value={predictions.filter(p => p.riskLevel === level).length}
                          valueStyle={{ color: getRiskColor(level) }}
                        />
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Card>
            </Col>
            <Col xs={24} md={16}>
              <Card size="small" title="建议操作">
                {predictions.filter(p => p.recommendation).map(p => (
                  <div key={p.tableName} style={{ marginBottom: 8, padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                    <Tag color={getRiskColor(p.riskLevel)}>{p.tableName}</Tag>
                    <span style={{ fontSize: 13 }}>{p.recommendation}</span>
                  </div>
                ))}
              </Card>
            </Col>
          </Row>
        </>
      ) : (
        <Empty description="暂无预测数据，需要先执行多次校验任务积累历史数据" />
      )}
    </Spin>
  );
};

export default PredictiveCheck;
