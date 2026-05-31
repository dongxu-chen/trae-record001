import { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Table,
  Tag,
  Select,
  Space,
  Button,
  Row,
  Col,
  Checkbox,
  Progress,
  Descriptions,
  Spin,
  Empty,
} from 'antd';
import ReactECharts from 'echarts-for-react';
import {
  LineChart as LineChartIcon,
  TrendingDown,
  CheckCircle,
  BarChart as BarChartIcon,
  Target,
  RefreshCw,
  ArrowsLeftRight,
  Play,
} from '@phosphor-icons/react';
import StatCard from '@/components/ui/StatCard';
import RadarChart from '@/components/charts/RadarChart';
import { useAnalysisStore } from '@/stores/analysisStore';
import {
  formatNumber,
  formatPercent,
  getTrendColor,
  getScoreColor,
  truncateText,
  generateChartColors,
} from '@/utils/format';
import type { RuleOptimizationResult, EvaluationResult } from '@/types';

const { Option } = Select;

const Evaluator: React.FC = () => {
  const {
    evaluationResults,
    overallEvaluation,
    loading,
    fetchEvaluation,
  } = useAnalysisStore();

  const [selectedRules, setSelectedRules] = useState<string[]>([]);
  const [showComparison, setShowComparison] = useState(false);

  useEffect(() => {
    fetchEvaluation();
  }, [fetchEvaluation]);

  const handleRefresh = () => {
    fetchEvaluation();
  };

  const stats = useMemo(
    () => ({
      totalEvaluations: overallEvaluation?.totalEvaluations || 0,
      totalReduction: overallEvaluation?.totalReduction || 0,
      overallReductionPercent: overallEvaluation?.overallReductionPercent || 0,
      highImpactOptimizations: overallEvaluation?.highImpactOptimizations || 0,
      avgImprovementPercent: overallEvaluation?.avgImprovementPercent || 0,
      avgNoiseReductionPercent: overallEvaluation?.avgNoiseReductionPercent || 0,
      avgCriticalCoverage: overallEvaluation?.avgCriticalCoverage || 0,
    }),
    [overallEvaluation]
  );

  const comparisonBarOption = useMemo(() => {
    const displayData = evaluationResults.slice(0, 10);
    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        borderColor: '#334155',
        borderWidth: 1,
        textStyle: { color: '#F1F5F9' },
        axisPointer: { type: 'shadow' },
      },
      legend: {
        data: ['原始告警数', '优化后告警数'],
        textStyle: { color: '#94A3B8', fontSize: 12 },
        top: 10,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: 60,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: displayData.map((d) => truncateText(d.ruleName, 10)),
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: {
          color: '#64748B',
          fontSize: 11,
          rotate: 30,
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisLabel: { color: '#64748B', fontSize: 11 },
        splitLine: { lineStyle: { color: '#1E293B', type: 'dashed' } },
      },
      series: [
        {
          name: '原始告警数',
          type: 'bar',
          data: displayData.map((d) => {
            const alertMetric = d.evaluation.find((e) => e.metricName === '告警数量');
            return alertMetric?.originalValue || 0;
          }),
          itemStyle: { color: '#EF4444', borderRadius: [4, 4, 0, 0] },
          barWidth: '35%',
        },
        {
          name: '优化后告警数',
          type: 'bar',
          data: displayData.map((d) => {
            const alertMetric = d.evaluation.find((e) => e.metricName === '告警数量');
            return alertMetric?.optimizedValue || 0;
          }),
          itemStyle: { color: '#10B981', borderRadius: [4, 4, 0, 0] },
          barWidth: '35%',
        },
      ],
    };
  }, [evaluationResults]);

  const radarData = useMemo(() => [
    {
      name: '告警减少',
      value: Math.round(stats.overallReductionPercent),
      max: 100,
    },
    {
      name: '噪声减少',
      value: Math.round(stats.avgNoiseReductionPercent),
      max: 100,
    },
    {
      name: '关键覆盖',
      value: Math.round(stats.avgCriticalCoverage),
      max: 100,
    },
    {
      name: '平均改进',
      value: Math.round(stats.avgImprovementPercent),
      max: 100,
    },
  ], [stats]);

  const histogramOption = useMemo(() => {
    const improvements = evaluationResults.map((d) => {
      const alertMetric = d.evaluation.find((e) => e.metricName === '告警数量');
      return alertMetric?.improvementPercent || 0;
    });

    const bins = [0, 20, 40, 60, 80, 100];
    const counts = new Array(bins.length - 1).fill(0);

    improvements.forEach((imp) => {
      for (let i = 0; i < bins.length - 1; i++) {
        if (imp >= bins[i] && imp < bins[i + 1]) {
          counts[i]++;
          break;
        }
      }
    });

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        borderColor: '#334155',
        borderWidth: 1,
        textStyle: { color: '#F1F5F9' },
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const data = params[0];
          return `
            <div style="padding: 4px;">
              <div style="color: #94A3B8; margin-bottom: 4px;">${data.name}</div>
              <div style="font-weight: 500;">${data.value} 条规则</div>
            </div>
          `;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: 20,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'],
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#64748B', fontSize: 11 },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisLabel: { color: '#64748B', fontSize: 11 },
        splitLine: { lineStyle: { color: '#1E293B', type: 'dashed' } },
      },
      series: [
        {
          type: 'bar',
          data: counts.map((count, i) => ({
            value: count,
            itemStyle: {
              color: generateChartColors(5)[i],
              borderRadius: [6, 6, 0, 0],
            },
          })),
          barWidth: '60%',
        },
      ],
    };
  }, [evaluationResults]);

  const comparisonData = useMemo(() => {
    return evaluationResults.filter((d) => selectedRules.includes(d.ruleName));
  }, [evaluationResults, selectedRules]);

  const comparisonColumns = [
    {
      title: '规则名',
      dataIndex: 'ruleName',
      key: 'ruleName',
      width: 200,
      render: (text: string) => (
        <span className="font-medium text-gray-200">{truncateText(text, 20)}</span>
      ),
    },
    {
      title: '原始告警数',
      dataIndex: 'originalAlerts',
      key: 'originalAlerts',
      width: 120,
      align: 'center' as const,
      render: (_: any, record: RuleOptimizationResult) => {
        const metric = record.evaluation.find((e) => e.metricName === '告警数量');
        return formatNumber(metric?.originalValue || 0);
      },
    },
    {
      title: '优化后',
      dataIndex: 'optimizedAlerts',
      key: 'optimizedAlerts',
      width: 120,
      align: 'center' as const,
      render: (_: any, record: RuleOptimizationResult) => {
        const metric = record.evaluation.find((e) => e.metricName === '告警数量');
        return formatNumber(metric?.optimizedValue || 0);
      },
    },
    {
      title: '减少量',
      dataIndex: 'reduction',
      key: 'reduction',
      width: 120,
      align: 'center' as const,
      render: (_: any, record: RuleOptimizationResult) => {
        const metric = record.evaluation.find((e) => e.metricName === '告警数量');
        const reduction = (metric?.originalValue || 0) - (metric?.optimizedValue || 0);
        return <span style={{ color: '#10B981' }}>{formatNumber(reduction)}</span>;
      },
    },
    {
      title: '减少%',
      dataIndex: 'reductionPercent',
      key: 'reductionPercent',
      width: 100,
      align: 'center' as const,
      render: (_: any, record: RuleOptimizationResult) => {
        const metric = record.evaluation.find((e) => e.metricName === '告警数量');
        const percent = metric?.improvementPercent || 0;
        return (
          <span style={{ color: getTrendColor(percent, true) }}>
            {formatPercent(percent)}
          </span>
        );
      },
    },
    {
      title: '噪声减少',
      dataIndex: 'noiseReduction',
      key: 'noiseReduction',
      width: 120,
      align: 'center' as const,
      render: (_: any, record: RuleOptimizationResult) => {
        const metric = record.evaluation.find((e) => e.metricName === '噪声减少');
        const percent = metric?.improvementPercent || 0;
        return (
          <span style={{ color: getTrendColor(percent, true) }}>
            {formatPercent(percent)}
          </span>
        );
      },
    },
    {
      title: '关键覆盖',
      dataIndex: 'criticalCoverage',
      key: 'criticalCoverage',
      width: 120,
      align: 'center' as const,
      render: (_: any, record: RuleOptimizationResult) => {
        const metric = record.evaluation.find((e) => e.metricName === '关键覆盖');
        const value = metric?.optimizedValue || 0;
        return <span style={{ color: '#3B82F6' }}>{formatPercent(value)}</span>;
      },
    },
  ];

  const getSimulationLineData = (record: RuleOptimizationResult) => {
    const sim = record.simulationResults;
    if (!sim || !sim.timeline) return [];

    const { timeline, originalAlerts, optimizedAlerts } = sim;
    return timeline.map((time: number, index: number) => ({
      time,
      original: originalAlerts?.[index] || 0,
      optimized: optimizedAlerts?.[index] || 0,
    }));
  };

  const simulationChartOption = (data: Array<{ time: number; original: number; optimized: number }>) => ({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: '#334155',
      borderWidth: 1,
      textStyle: { color: '#F1F5F9' },
    },
    legend: {
      data: ['原始告警', '优化后告警'],
      textStyle: { color: '#94A3B8', fontSize: 12 },
      top: 10,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 50,
      containLabel: true,
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: {
        color: '#64748B',
        fontSize: 11,
        formatter: (value: number) => {
          const date = new Date(value);
          return `${date.getMonth() + 1}-${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
        },
      },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: '#64748B', fontSize: 11 },
      splitLine: { lineStyle: { color: '#1E293B', type: 'dashed' } },
    },
    series: [
      {
        name: '原始告警',
        type: 'line',
        data: data.map((d) => [d.time, d.original]),
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: false,
        lineStyle: { color: '#EF4444', width: 2 },
        itemStyle: { color: '#EF4444' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(239, 68, 68, 0.2)' },
              { offset: 1, color: 'rgba(239, 68, 68, 0.02)' },
            ],
          },
        },
      },
      {
        name: '优化后告警',
        type: 'line',
        data: data.map((d) => [d.time, d.optimized]),
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: false,
        lineStyle: { color: '#10B981', width: 2 },
        itemStyle: { color: '#10B981' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(16, 185, 129, 0.2)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0.02)' },
            ],
          },
        },
      },
    ],
  });

  const expandedRowRender = (record: RuleOptimizationResult) => {
    const simData = getSimulationLineData(record);

    return (
      <div className="space-y-6">
        <Card className="glass-card border-0" size="small" title="评估指标详情">
          <Row gutter={[16, 16]}>
            {record.evaluation.map((metric: EvaluationResult, idx: number) => (
              <Col xs={24} sm={12} lg={6} key={idx}>
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <div className="text-sm text-gray-400 mb-2">{metric.metricName}</div>
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="text-xs text-gray-500">原始: </span>
                      <span className="text-red-400">{formatNumber(metric.originalValue)}</span>
                    </div>
                    <div>
                      <span className="text-xs text-gray-500">优化后: </span>
                      <span className="text-green-400">{formatNumber(metric.optimizedValue)}</span>
                    </div>
                  </div>
                  <Progress
                    percent={Math.round(metric.improvementPercent)}
                    strokeColor={getTrendColor(metric.improvementPercent, true)}
                    trailColor="#334155"
                    size="small"
                    format={(percent) => (
                      <span style={{ color: getTrendColor(metric.improvementPercent, true) }}>
                        {formatPercent(metric.improvementPercent)}
                      </span>
                    )}
                  />
                </div>
              </Col>
            ))}
          </Row>
        </Card>

        <Card className="glass-card border-0" size="small" title="配置对比">
          <Descriptions
            bordered
            size="small"
            column={1}
            labelStyle={{ width: 200, color: '#94A3B8' }}
            contentStyle={{ color: '#F1F5F9' }}
          >
            <Descriptions.Item label="原始配置">
              <pre className="text-xs bg-slate-800 p-3 rounded overflow-x-auto">
                {JSON.stringify(record.originalConfig, null, 2)}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="优化配置">
              <pre className="text-xs bg-slate-800 p-3 rounded overflow-x-auto">
                {JSON.stringify(record.optimizedConfig, null, 2)}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        </Card>

        {simData.length > 0 && (
          <Card className="glass-card border-0" size="small" title="模拟结果时间序列">
            <ReactECharts
              option={simulationChartOption(simData)}
              style={{ height: 300, width: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </Card>
        )}
      </div>
    );
  };

  const tableColumns = [
    {
      title: '规则名',
      dataIndex: 'ruleName',
      key: 'ruleName',
      width: 250,
      render: (text: string) => (
        <span className="font-medium text-gray-200">{truncateText(text, 25)}</span>
      ),
    },
    {
      title: '优化是否应用',
      dataIndex: 'optimizationApplied',
      key: 'optimizationApplied',
      width: 120,
      align: 'center' as const,
      render: (applied: boolean) =>
        applied ? (
          <Tag color="success" className="text-xs">
            <CheckCircle size={12} className="mr-1 inline" /> 已应用
          </Tag>
        ) : (
          <Tag color="default" className="text-xs">
            未应用
          </Tag>
        ),
    },
    {
      title: '原始告警数',
      dataIndex: 'originalAlerts',
      key: 'originalAlerts',
      width: 120,
      align: 'center' as const,
      render: (_: any, record: RuleOptimizationResult) => {
        const metric = record.evaluation.find((e) => e.metricName === '告警数量');
        return <span className="text-red-400">{formatNumber(metric?.originalValue || 0)}</span>;
      },
    },
    {
      title: '优化后告警数',
      dataIndex: 'optimizedAlerts',
      key: 'optimizedAlerts',
      width: 120,
      align: 'center' as const,      render: (_: any, record: RuleOptimizationResult) => {
        const metric = record.evaluation.find((e) => e.metricName === '告警数量');
        return <span className="text-green-400">{formatNumber(metric?.optimizedValue || 0)}</span>;
      },
    },
    {
      title: '减少量',
      dataIndex: 'reduction',
      key: 'reduction',
      width: 100,
      align: 'center' as const,
      render: (_: any, record: RuleOptimizationResult) => {
        const metric = record.evaluation.find((e) => e.metricName === '告警数量');
        const reduction = (metric?.originalValue || 0) - (metric?.optimizedValue || 0);
        return <span style={{ color: '#10B981' }}>{formatNumber(reduction)}</span>;
      },
    },
    {
      title: '减少%',
      dataIndex: 'reductionPercent',
      key: 'reductionPercent',
      width: 100,
      align: 'center' as const,
      render: (_: any, record: RuleOptimizationResult) => {
        const metric = record.evaluation.find((e) => e.metricName === '告警数量');
        const percent = metric?.improvementPercent || 0;
        return (
          <span style={{ color: getTrendColor(percent, true) }}>
            {formatPercent(percent)}
          </span>
        );
      },
    },
    {
      title: '评估指标',
      key: 'metrics',
      width: 250,
      render: (_: any, record: RuleOptimizationResult) => {
        const avgImprovement = record.evaluation.reduce(
          (sum, m) => sum + m.improvementPercent,
          0
        ) / record.evaluation.length;

        return (
          <Progress
            percent={Math.round(avgImprovement)}
            strokeColor={getScoreColor(avgImprovement / 100)}
            trailColor="#334155"
            size="small"
            format={(percent) => (
              <span style={{ color: getScoreColor(avgImprovement / 100) }}>
                {formatPercent(avgImprovement)}
              </span>
            )}
          />
        );
      },
    },
  ];

  const isLoading = loading.evaluation;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Evaluator 效果评估中心</h1>
        <Button
          type="primary"
          icon={<RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />}
          onClick={handleRefresh}
          loading={isLoading}
        >
          刷新数据
        </Button>
      </div>

      <Spin spinning={isLoading}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="总评估规则数"
              value={stats.totalEvaluations}
              icon={<BarChartIcon size={24} />}
              color="#3B82F6"
              tooltip="已完成评估的规则总数"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="总减少告警数"
              value={stats.totalReduction}
              icon={<TrendingDown size={24} />}
              color="#10B981"
              tooltip="通过优化总共减少的告警数量"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="总体减少百分比"
              value={formatPercent(stats.overallReductionPercent)}
              icon={<LineChartIcon size={24} />}
              progress={stats.overallReductionPercent}
              color="#8B5CF6"
              tooltip="告警总数减少的百分比"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="高影响优化数"
              value={stats.highImpactOptimizations}
              icon={<Target size={24} />}
              color="#EF4444"
              suffix="条"
              tooltip="减少百分比超过50%的高影响优化数量"
              loading={isLoading}
            />
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="mt-4">
          <Col xs={24} lg={14}>
            <Card className="glass-card hover-lift border-0" title="优化前后告警数对比">
              <ReactECharts
                option={comparisonBarOption}
                style={{ height: 350, width: '100%' }}
                opts={{ renderer: 'canvas' }}
              />
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card className="glass-card hover-lift border-0" title="各维度改进百分比">
              <RadarChart
                data={radarData}
                color="#8B5CF6"
                height={350}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="mt-4">
          <Col xs={24}>
            <Card className="glass-card hover-lift border-0" title="改进百分比分布">
              <ReactECharts
                option={histogramOption}
                style={{ height: 300, width: '100%' }}
                opts={{ renderer: 'canvas' }}
              />
            </Card>
          </Col>
        </Row>

        <Card
          className="glass-card hover-lift border-0 mt-4"
          title={
            <div className="flex items-center gap-2">
              <ArrowsLeftRight size={18} />
              <span>多配置对比</span>
            </div>
          }
          extra={
            <Space>
              <Checkbox
                checked={showComparison}
                onChange={(e) => setShowComparison(e.target.checked)}
              >
                显示对比表格
              </Checkbox>
              <Select
                mode="multiple"
                placeholder="选择要对比的规则"
                value={selectedRules}
                onChange={setSelectedRules}
                style={{ minWidth: 300 }}
                size="middle"
                maxTagCount={3}
                disabled={!showComparison}
              >
                {evaluationResults.map((result) => (
                  <Option key={result.ruleName} value={result.ruleName}>
                    {truncateText(result.ruleName, 25)}
                  </Option>
                ))}
              </Select>
              <Button
                type="primary"
                size="middle"
                icon={<Play size={14} />}
                onClick={() => setShowComparison(true)}
                disabled={selectedRules.length === 0}
              >
                开始对比
              </Button>
            </Space>
          }
        >
          {showComparison ? (
            comparisonData.length > 0 ? (
              <Table
                dataSource={comparisonData}
                columns={comparisonColumns}
                rowKey="ruleName"
                pagination={false}
                scroll={{ x: 900 }}
                locale={{ emptyText: '请选择规则进行对比' }}
              />
            ) : (
              <Empty
                description="请选择要对比的规则"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )
          ) : (
            <div className="text-center py-8 text-gray-400">
              勾选"显示对比表格"并选择规则以进行多配置对比
            </div>
          )}
        </Card>

        <Card
          className="glass-card hover-lift border-0 mt-4"
          title="评估结果列表"
          extra={
            <span className="text-sm text-gray-400">
              共 {formatNumber(evaluationResults.length)} 条评估结果
            </span>
          }
        >
          {evaluationResults.length > 0 ? (
            <Table
              dataSource={evaluationResults}
              columns={tableColumns}
              rowKey="ruleName"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${formatNumber(total)} 条`,
              }}
              scroll={{ x: 1100 }}
              expandable={{
                expandedRowRender,
                defaultExpandAllRows: false,
              }}
            />
          ) : (
            <Empty
              description="暂无评估结果"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </Card>
      </Spin>
    </div>
  );
};

export default Evaluator;
