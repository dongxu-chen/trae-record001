import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Row, Col, Statistic, Progress, Empty, Spin, Button, Descriptions } from 'antd';
import { FileTextOutlined, ReloadOutlined, DownloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import { checkApi } from '../services/api';

const ReportPage = () => {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    setLoading(true);
    try {
      const data = await checkApi.getAllReports();
      setReports(data || []);
      if (data && data.length > 0 && !selectedReport) {
        setSelectedReport(data[0]);
      }
    } catch (error) {
      console.error('Failed to load reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (rate) => {
    if (rate > 0.05) return '#ff4d4f';
    if (rate > 0.01) return '#faad14';
    return '#52c41a';
  };

  const diffTypePieOption = selectedReport?.diffStatistics ? {
    title: { text: '差异类型分布', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: selectedReport.diffStatistics.missingInTargetCount, name: '目标缺失', itemStyle: { color: '#ff4d4f' } },
        { value: selectedReport.diffStatistics.missingInSourceCount, name: '源端缺失', itemStyle: { color: '#faad14' } },
        { value: selectedReport.diffStatistics.valueMismatchCount, name: '值不匹配', itemStyle: { color: '#1890ff' } },
        { value: selectedReport.diffStatistics.latencyExceededCount, name: '延迟超标', itemStyle: { color: '#722ed1' } }
      ].filter(d => d.value > 0)
    }]
  } : null;

  const repairStatusOption = selectedReport?.repairStatistics ? {
    title: { text: '修复状态统计', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: selectedReport.repairStatistics.successCount, name: '修复成功', itemStyle: { color: '#52c41a' } },
        { value: selectedReport.repairStatistics.failedCount, name: '修复失败', itemStyle: { color: '#ff4d4f' } },
      ].filter(d => d.value > 0)
    }]
  } : null;

  const topDiffFieldsOption = selectedReport?.diffStatistics?.topDiffFields?.length > 0 ? {
    title: { text: '差异字段TOP10', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: selectedReport.diffStatistics.topDiffFields.map(f => f.fieldName).reverse()
    },
    series: [{
      type: 'bar',
      data: selectedReport.diffStatistics.topDiffFields.map(f => f.count).reverse(),
      itemStyle: { color: '#1890ff' }
    }],
    grid: { left: 100, right: 20, top: 40, bottom: 20 }
  } : null;

  const repairColumns = [
    { title: 'Key', dataIndex: 'key', key: 'key', width: 200 },
    { title: '差异类型', dataIndex: 'diffType', key: 'diffType', width: 120,
      render: (t) => {
        const map = { MISSING_IN_TARGET: '目标缺失', MISSING_IN_SOURCE: '源端缺失', VALUE_MISMATCH: '值不匹配', LATENCY_EXCEEDED: '延迟超标' };
        return <Tag>{map[t] || t}</Tag>;
      }
    },
    { title: '修复状态', dataIndex: 'repairStatus', key: 'repairStatus', width: 100,
      render: (s) => {
        const map = { SUCCESS: { c: 'success', t: '成功' }, FAILED: { c: 'error', t: '失败' }, IN_PROGRESS: { c: 'processing', t: '进行中' } };
        const cfg = map[s] || { c: 'default', t: s };
        return <Tag color={cfg.c}>{cfg.t}</Tag>;
      }
    },
    { title: '尝试次数', dataIndex: 'repairAttempts', key: 'repairAttempts', width: 80 },
    { title: '错误信息', dataIndex: 'repairErrorMessage', key: 'repairErrorMessage', ellipsis: true }
  ];

  const handleExportReport = () => {
    if (!selectedReport) return;
    const json = JSON.stringify(selectedReport, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `check-report-${selectedReport.taskId}-${dayjs().format('YYYYMMDDHHmmss')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>
          <FileTextOutlined style={{ marginRight: 8 }} />
          校验报告
        </h3>
        <div>
          <Button icon={<ReloadOutlined />} onClick={loadReports} style={{ marginRight: 8 }}>刷新</Button>
          <Button icon={<DownloadOutlined />} onClick={handleExportReport} disabled={!selectedReport}>导出报告</Button>
        </div>
      </div>

      {selectedReport?.summary ? (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={8} md={4}>
              <Card size="small"><Statistic title="源端记录" value={selectedReport.summary.totalSourceRecords} /></Card>
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Card size="small"><Statistic title="目标记录" value={selectedReport.summary.totalTargetRecords} /></Card>
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Card size="small">
                <Statistic title="差异率" value={(selectedReport.summary.diffRate * 100).toFixed(2)} suffix="%"
                  valueStyle={{ color: getRiskColor(selectedReport.summary.diffRate) }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Card size="small">
                <Statistic title="修复率" value={(selectedReport.summary.repairRate * 100).toFixed(1)} suffix="%"
                  valueStyle={{ color: selectedReport.summary.repairRate > 0.8 ? '#52c41a' : '#faad14' }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Card size="small"><Statistic title="平均延迟" value={selectedReport.summary.avgLatencyMs.toFixed(0)} suffix="ms" /></Card>
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Card size="small"><Statistic title="耗时" value={selectedReport.summary.durationMs} suffix="ms" /></Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {diffTypePieOption && (
              <Col xs={24} md={8}>
                <Card size="small"><ReactECharts option={diffTypePieOption} style={{ height: 250 }} /></Card>
              </Col>
            )}
            {repairStatusOption && (
              <Col xs={24} md={8}>
                <Card size="small"><ReactECharts option={repairStatusOption} style={{ height: 250 }} /></Card>
              </Col>
            )}
            {topDiffFieldsOption && (
              <Col xs={24} md={8}>
                <Card size="small"><ReactECharts option={topDiffFieldsOption} style={{ height: 250 }} /></Card>
              </Col>
            )}
          </Row>

          <Card title="修复记录" size="small" style={{ marginBottom: 16 }}>
            <Table
              columns={repairColumns}
              dataSource={selectedReport.repairRecords || []}
              rowKey="diffId"
              size="small"
              pagination={{ pageSize: 10 }}
            />
          </Card>

          <Card size="small">
            <Descriptions title="报告元信息" column={3} size="small">
              <Descriptions.Item label="报告ID">{selectedReport.id}</Descriptions.Item>
              <Descriptions.Item label="任务ID">{selectedReport.taskId}</Descriptions.Item>
              <Descriptions.Item label="数据源">{selectedReport.sourceType}</Descriptions.Item>
              <Descriptions.Item label="表名">{selectedReport.tableName}</Descriptions.Item>
              <Descriptions.Item label="校验模式">{selectedReport.checkMode === 'STRATIFIED_HASH' ? '分层哈希' : '全量比对'}</Descriptions.Item>
              <Descriptions.Item label="生成时间">{dayjs(selectedReport.generatedAt).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
            </Descriptions>
          </Card>
        </>
      ) : (
        <Empty description="暂无报告数据，请先执行校验任务" />
      )}
    </Spin>
  );
};

export default ReportPage;
