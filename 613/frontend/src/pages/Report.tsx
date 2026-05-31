import { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Table,
  Tag,
  DatePicker,
  Space,
  Button,
  Row,
  Col,
  Divider,
  Typography,
  Steps,
  List,
  Progress,
  Select,
  Spin,
  Dropdown,
  MenuProps,
} from 'antd';
import {
  FileText,
  Download,
  Play,
  AlertTriangle,
  CheckCircle,
  Target,
  Lightbulb,
  Bell,
  TrendingDown,
  Gauge,
  Clock,
  Users,
  BarChart3,
  Settings,
  ArrowRight,
  FilePdf,
  FileHtml,
} from '@phosphor-icons/react';
import dayjs, { Dayjs } from 'dayjs';
import StatCard from '@/components/ui/StatCard';
import LineChart from '@/components/charts/LineChart';
import PieChart from '@/components/charts/PieChart';
import BarChart from '@/components/charts/BarChart';
import RadarChart from '@/components/charts/RadarChart';
import { useAnalysisStore } from '@/stores/analysisStore';
import {
  formatTime,
  formatNumber,
  formatPercent,
  getPriorityColor,
  getSeverityColor,
  truncateText,
  generateChartColors,
  getScoreColor,
} from '@/utils/format';
import type {
  AlertCluster,
  InefficientRule,
  OptimizationSuggestion,
  RuleOptimizationResult,
} from '@/types';

const { Title, Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;
const { Step } = Steps;

const timeRangeOptions = [
  { label: '24小时', value: 24 },
  { label: '7天', value: 168 },
  { label: '30天', value: 720 },
  { label: '90天', value: 2160 },
  { label: '自定义', value: -1 },
];

const priorityOptions = [
  { label: '严重', value: 'CRITICAL', color: '#EF4444' },
  { label: '警告', value: 'WARNING', color: '#F59E0B' },
  { label: '信息', value: 'INFO', color: '#3B82F6' },
];

const Report: React.FC = () => {
  const {
    overallStatistics,
    clusters,
    clusterSummary,
    inefficientRules,
    suggestions,
    optimizationSummary,
    evaluationResults,
    overallEvaluation,
    loading,
    filters,
    setFilters,
    fetchFullReport,
  } = useAnalysisStore();

  const [selectedTimeRange, setSelectedTimeRange] = useState<number>(168);
  const [customDateRange, setCustomDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [reportGenerated, setReportGenerated] = useState<boolean>(false);
  const [activeSection, setActiveSection] = useState<number>(0);

  useEffect(() => {
    if (reportGenerated) {
      fetchFullReport();
    }
  }, [fetchFullReport, reportGenerated, filters.lookbackHours]);

  const handleTimeRangeChange = (value: number) => {
    setSelectedTimeRange(value);
    if (value !== -1) {
      setCustomDateRange(null);
      setFilters({ lookbackHours: value });
    }
  };

  const handleCustomDateChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      setCustomDateRange(dates as [Dayjs, Dayjs]);
      const hours = dates[1].diff(dates[0], 'hour');
      setFilters({ lookbackHours: hours });
    }
  };

  const handleGenerateReport = () => {
    setReportGenerated(true);
    fetchFullReport();
  };

  const exportMenuItems: MenuProps['items'] = [
    {
      key: 'pdf',
      label: (
        <Space>
          <FilePdf size={16} />
          <span>导出 PDF</span>
        </Space>
      ),
    },
    {
      key: 'html',
      label: (
        <Space>
          <FileHtml size={16} />
          <span>导出 HTML</span>
        </Space>
      ),
    },
  ];

  const handleExport = (key: string) => {
    console.log(`Exporting report as ${key}`);
  };

  const isLoading = loading.fullReport;
  const hasData = reportGenerated && overallStatistics;

  const alertTrendData = useMemo(() => {
    if (!overallStatistics) return [];

    const now = Date.now();
    const hours = filters.lookbackHours;
    const interval = Math.max(1, Math.floor(hours / 24));
    const data: Array<{ time: number; value: number }> = [];

    for (let i = hours; i >= 0; i -= interval) {
      const time = now - i * 60 * 60 * 1000;
      const baseValue = overallStatistics.totalAlerts / hours;
      const variance = Math.random() * 0.4 - 0.2;
      data.push({
        time,
        value: Math.max(0, Math.round(baseValue * interval * (1 + variance))),
      });
    }

    return data;
  }, [overallStatistics, filters.lookbackHours]);

  const priorityDistributionData = useMemo(() => {
    if (!overallStatistics) return [];

    return priorityOptions.map((p) => ({
      name: p.label,
      value: overallStatistics.priorityDistribution[p.value] || 0,
      color: p.color,
    }));
  }, [overallStatistics]);

  const clusterDistributionData = useMemo(() => {
    if (!clusters || clusters.length === 0) return [];

    const colors = generateChartColors(Math.min(clusters.length, 10));
    return clusters
      .slice(0, 10)
      .map((cluster, index) => ({
        name: truncateText(cluster.ruleName, 15),
        value: cluster.alertCount,
        color: colors[index],
      }))
      .sort((a, b) => b.value - a.value);
  }, [clusters]);

  const inefficiencyScoreDistribution = useMemo(() => {
    if (!inefficientRules || inefficientRules.length === 0) return [];

    const scoreRanges = [
      { name: '0-20', min: 0, max: 0.2, count: 0, color: '#10B981' },
      { name: '20-40', min: 0.2, max: 0.4, count: 0, color: '#06B6D4' },
      { name: '40-60', min: 0.4, max: 0.6, count: 0, color: '#3B82F6' },
      { name: '60-80', min: 0.6, max: 0.8, count: 0, color: '#F59E0B' },
      { name: '80-100', min: 0.8, max: 1.0, count: 0, color: '#EF4444' },
    ];

    inefficientRules.forEach((rule) => {
      const range = scoreRanges.find(
        (r) => rule.inefficiencyScore >= r.min && rule.inefficiencyScore < r.max
      );
      if (range) range.count++;
    });

    return scoreRanges.map((r) => ({
      name: r.name,
      value: r.count,
      color: r.color,
    }));
  }, [inefficientRules]);

  const radarData = useMemo(() => {
    if (!overallEvaluation) return [];

    return [
      { name: '告警减少率', value: overallEvaluation.overallReductionPercent, max: 100 },
      { name: '降噪效果', value: overallEvaluation.avgNoiseReductionPercent, max: 100 },
      { name: '关键告警覆盖率', value: overallEvaluation.avgCriticalCoverage, max: 100 },
      { name: '规则效率提升', value: overallEvaluation.avgImprovementPercent, max: 100 },
      { name: '高影响优化', value: (overallEvaluation.highImpactOptimizations / Math.max(overallEvaluation.totalEvaluations, 1)) * 100, max: 100 },
    ];
  }, [overallEvaluation]);

  const optimizationTypeData = useMemo(() => {
    if (!optimizationSummary) return [];

    return [
      { name: '阈值调整', value: optimizationSummary.thresholdIncreases, color: '#3B82F6' },
      { name: '周期调整', value: optimizationSummary.periodIncreases, color: '#10B981' },
      { name: '其他优化', value: Math.max(0, optimizationSummary.totalSuggestions - optimizationSummary.thresholdIncreases - optimizationSummary.periodIncreases), color: '#8B5CF6' },
    ];
  }, [optimizationSummary]);

  const sortedInefficientRules = useMemo(() => {
    return [...inefficientRules].sort((a, b) => b.inefficiencyScore - a.inefficiencyScore);
  }, [inefficientRules]);

  const sortedSuggestions = useMemo(() => {
    return [...suggestions].sort((a, b) => b.expectedImprovement.reductionPercent - a.expectedImprovement.reductionPercent);
  }, [suggestions]);

  const actionItems = useMemo(() => {
    if (!sortedSuggestions.length) return [];

    return sortedSuggestions.slice(0, 10).map((suggestion, index) => ({
      id: index + 1,
      title: `优化规则: ${suggestion.ruleName}`,
      description: suggestion.reasoning,
      priority: suggestion.expectedImprovement.reductionPercent > 50 ? 'HIGH' : suggestion.expectedImprovement.reductionPercent > 20 ? 'MEDIUM' : 'LOW',
      expectedReduction: suggestion.expectedImprovement.reductionPercent,
      confidence: suggestion.confidence,
    }));
  }, [sortedSuggestions]);

  const alertClusterColumns = [
    {
      title: '聚类ID',
      dataIndex: 'clusterId',
      key: 'clusterId',
      width: 120,
      render: (text: string) => <Text className="font-mono text-gray-300 text-xs">{text.slice(0, 8)}...</Text>,
    },
    {
      title: '规则名称',
      dataIndex: 'ruleName',
      key: 'ruleName',
      width: 200,
      render: (text: string) => <Text className="text-gray-200">{truncateText(text, 20)}</Text>,
    },
    {
      title: '告警数量',
      dataIndex: 'alertCount',
      key: 'alertCount',
      width: 100,
      render: (value: number) => <Text className="text-blue-400 font-medium">{formatNumber(value)}</Text>,
    },
    {
      title: '影响服务数',
      dataIndex: 'services',
      key: 'services',
      width: 100,
      render: (services: string[]) => <Text className="text-gray-300">{services.length}</Text>,
    },
    {
      title: '优先级分布',
      dataIndex: 'priorityDistribution',
      key: 'priorityDistribution',
      width: 150,
      render: (dist: Record<string, number>) => (
        <Space size={4}>
          {Object.entries(dist).map(([p, count]) => (
            <Tag key={p} color={getPriorityColor(p)} className="text-xs">
              {count}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '时间跨度',
      dataIndex: 'timeSpan',
      key: 'timeSpan',
      width: 200,
      render: (span: { start: number; end: number }) => (
        <Text className="text-gray-400 text-xs">
          {formatTime(span.start, 'MM-DD HH:mm')} ~ {formatTime(span.end, 'MM-DD HH:mm')}
        </Text>
      ),
    },
  ];

  const inefficientRulesColumns = [
    {
      title: '规则名称',
      dataIndex: 'ruleName',
      key: 'ruleName',
      width: 200,
      render: (text: string) => <Text className="text-gray-200 font-medium">{truncateText(text, 20)}</Text>,
    },
    {
      title: '告警总数',
      dataIndex: 'totalAlerts',
      key: 'totalAlerts',
      width: 100,
      render: (value: number) => <Text className="text-blue-400">{formatNumber(value)}</Text>,
    },
    {
      title: '频率评分',
      dataIndex: 'frequencyScore',
      key: 'frequencyScore',
      width: 100,
      render: (value: number) => (
        <Progress percent={Math.round(value * 100)} size="small" strokeColor={getScoreColor(value)} showInfo={false} />
      ),
    },
    {
      title: '临界度评分',
      dataIndex: 'criticalityScore',
      key: 'criticalityScore',
      width: 100,
      render: (value: number) => (
        <Progress percent={Math.round(value * 100)} size="small" strokeColor={getScoreColor(value)} showInfo={false} />
      ),
    },
    {
      title: '噪声评分',
      dataIndex: 'noiseScore',
      key: 'noiseScore',
      width: 100,
      render: (value: number) => (
        <Progress percent={Math.round(value * 100)} size="small" strokeColor={getScoreColor(value)} showInfo={false} />
      ),
    },
    {
      title: '低效度评分',
      dataIndex: 'inefficiencyScore',
      key: 'inefficiencyScore',
      width: 120,
      render: (value: number) => (
        <Space>
          <Progress
            percent={Math.round(value * 100)}
            size="small"
            strokeColor={getScoreColor(value)}
            format={() => <Text style={{ color: getScoreColor(value) }} className="font-mono">{formatPercent(value * 100, 0)}</Text>}
          />
        </Space>
      ),
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => (
        <Tag
          color={getSeverityColor(severity)}
          style={{
            backgroundColor: `${getSeverityColor(severity)}20`,
            borderColor: getSeverityColor(severity),
            color: getSeverityColor(severity),
          }}
        >
          {severity === 'HIGH' ? '高' : severity === 'MEDIUM' ? '中' : '低'}
        </Tag>
      ),
    },
  ];

  const suggestionsColumns = [
    {
      title: '规则名称',
      dataIndex: 'ruleName',
      key: 'ruleName',
      width: 200,
      render: (text: string) => <Text className="text-gray-200 font-medium">{truncateText(text, 20)}</Text>,
    },
    {
      title: '原始配置',
      dataIndex: 'originalConfig',
      key: 'originalConfig',
      width: 150,
      render: (config: Record<string, any>) => (
        <Text className="text-gray-400 text-xs font-mono">
          阈值: {config.threshold} / 周期: {config.period}
        </Text>
      ),
    },
    {
      title: '建议配置',
      dataIndex: 'suggestedConfig',
      key: 'suggestedConfig',
      width: 150,
      render: (config: Record<string, any>) => (
        <Text className="text-green-400 text-xs font-mono">
          阈值: {config.threshold} / 周期: {config.period}
        </Text>
      ),
    },
    {
      title: '预期告警减少',
      dataIndex: 'expectedImprovement',
      key: 'expectedImprovement',
      width: 150,
      render: (improvement: { alertReduction: number; reductionPercent: number }) => (
        <Space direction="vertical" size={0}>
          <Text className="text-green-400 font-medium">-{formatNumber(improvement.alertReduction)}</Text>
          <Text className="text-gray-500 text-xs">{formatPercent(improvement.reductionPercent)}</Text>
        </Space>
      ),
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 120,
      render: (value: number) => (
        <Progress
          percent={Math.round(value * 100)}
          size="small"
          strokeColor={value >= 0.8 ? '#10B981' : value >= 0.5 ? '#F59E0B' : '#EF4444'}
          format={() => <Text className="font-mono text-xs">{formatPercent(value * 100, 0)}</Text>}
        />
      ),
    },
    {
      title: '关键告警保留',
      dataIndex: 'expectedImprovement',
      key: 'criticalPreserved',
      width: 120,
      render: (improvement: { criticalityPreserved: boolean }) => (
        improvement.criticalityPreserved ? (
          <Tag color="green">已保留</Tag>
        ) : (
          <Tag color="orange">需验证</Tag>
        )
      ),
    },
  ];

  const evaluationColumns = [
    {
      title: '规则名称',
      dataIndex: 'ruleName',
      key: 'ruleName',
      width: 200,
      render: (text: string) => <Text className="text-gray-200 font-medium">{truncateText(text, 20)}</Text>,
    },
    {
      title: '优化状态',
      dataIndex: 'optimizationApplied',
      key: 'optimizationApplied',
      width: 100,
      render: (applied: boolean) => (
        applied ? (
          <Tag color="green" icon={<CheckCircle size={12} />}>已应用</Tag>
        ) : (
          <Tag color="orange" icon={<Settings size={12} />}>待应用</Tag>
        )
      ),
    },
    {
      title: '原始告警数',
      dataIndex: 'evaluation',
      key: 'originalAlerts',
      width: 120,
      render: (evaluation: any[]) => {
        const alertMetric = evaluation?.find((e: any) => e.metricName === 'alertCount');
        return <Text className="text-gray-300">{formatNumber(alertMetric?.originalValue || 0)}</Text>;
      },
    },
    {
      title: '优化后告警数',
      dataIndex: 'evaluation',
      key: 'optimizedAlerts',
      width: 120,
      render: (evaluation: any[]) => {
        const alertMetric = evaluation?.find((e: any) => e.metricName === 'alertCount');
        return <Text className="text-green-400">{formatNumber(alertMetric?.optimizedValue || 0)}</Text>;
      },
    },
    {
      title: '提升百分比',
      dataIndex: 'evaluation',
      key: 'improvement',
      width: 150,
      render: (evaluation: any[]) => {
        const alertMetric = evaluation?.find((e: any) => e.metricName === 'alertCount');
        const improvement = alertMetric?.improvementPercent || 0;
        return (
          <Tag color={improvement >= 50 ? 'green' : improvement >= 20 ? 'blue' : 'orange'}>
            {improvement > 0 ? '+' : ''}{formatPercent(improvement)}
          </Tag>
        );
      },
    },
  ];

  const sectionSteps = [
    { title: '告警概览', icon: <Bell size={16} /> },
    { title: '聚类分析', icon: <Users size={16} /> },
    { title: '低效规则', icon: <AlertTriangle size={16} /> },
    { title: '优化建议', icon: <Lightbulb size={16} /> },
    { title: '效果评估', icon: <BarChart3 size={16} /> },
    { title: '行动建议', icon: <Target size={16} /> },
  ];

  const ChapterSection: React.FC<{
    icon: React.ReactNode;
    title: string;
    description: string;
    children: React.ReactNode;
  }> = ({ icon, title, description, children }) => (
    <Card className="glass-card hover-lift border-0 mb-6">
      <div className="flex items-start gap-4 mb-6">
        <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center flex-shrink-0">
          <div className="text-blue-400">{icon}</div>
        </div>
        <div className="flex-1">
          <Title level={3} className="!mb-1 !text-white">{title}</Title>
          <Text className="text-gray-400">{description}</Text>
        </div>
      </div>
      {children}
    </Card>
  );

  return (
    <div className="space-y-6">
      <Card className="glass-card border-0">
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={24} md={8} lg={5}>
            <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
              <Clock size={16} />
              <span>分析时间范围</span>
            </div>
            <Space.Compact className="w-full">
              <Select
                value={selectedTimeRange}
                onChange={handleTimeRangeChange}
                className="flex-1"
                size="middle"
              >
                {timeRangeOptions.map((option) => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
              {selectedTimeRange === -1 && (
                <RangePicker
                  value={customDateRange}
                  onChange={handleCustomDateChange}
                  size="middle"
                  style={{ width: 'auto' }}
                />
              )}
            </Space.Compact>
          </Col>

          <Col xs={24} sm={12} md={8} lg={4}>
            <Button
              type="primary"
              icon={<Play size={16} />}
              onClick={handleGenerateReport}
              loading={isLoading}
              size="middle"
              className="w-full h-10"
            >
              生成完整报告
            </Button>
          </Col>

          <Col xs={24} sm={12} md={8} lg={4}>
            <Dropdown menu={{ items: exportMenuItems, onClick: ({ key }) => handleExport(key) }} disabled={!hasData}>
              <Button icon={<Download size={16} />} size="middle" className="w-full h-10">
                导出报告
              </Button>
            </Dropdown>
          </Col>

          <Col xs={0} lg={11}>
            <div className="flex items-center justify-end gap-3">
              <Space size={[8, 0]} wrap>
                {hasData && (
                  <>
                    <Tag color="blue">
                      <FileText size={12} className="mr-1" />
                      报告已生成
                    </Tag>
                    <Tag color="green">
                      <CheckCircle size={12} className="mr-1" />
                      数据完整
                    </Tag>
                  </>
                )}
              </Space>
            </div>
          </Col>
        </Row>
      </Card>

      {hasData && (
        <Card className="glass-card border-0">
          <Title level={4} className="!mb-4 !text-white flex items-center gap-2">
            <FileText size={20} />
            报告概览
          </Title>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <div className="text-sm text-gray-400 mb-2">分析时间范围</div>
                <div className="text-white font-medium">
                  {formatTime(overallStatistics.timeRange.start)}
                </div>
                <div className="text-gray-500 text-sm">至</div>
                <div className="text-white font-medium">
                  {formatTime(overallStatistics.timeRange.end)}
                </div>
              </div>
            </Col>
            <Col xs={24} md={8}>
              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                <div className="text-sm text-gray-400 mb-2">数据覆盖情况</div>
                <div className="flex items-center gap-2">
                  <CheckCircle size={16} className="text-green-400" />
                  <span className="text-white">告警数据: {formatNumber(overallStatistics.totalAlerts)} 条</span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <CheckCircle size={16} className="text-green-400" />
                  <span className="text-white">规则数据: {formatNumber(overallStatistics.uniqueRules)} 条</span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <CheckCircle size={16} className="text-green-400" />
                  <span className="text-white">服务数据: {formatNumber(overallStatistics.uniqueServices)} 个</span>
                </div>
              </div>
            </Col>
            <Col xs={24} md={8}>
              <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
                <div className="text-sm text-gray-400 mb-2">关键结论摘要</div>
                <Paragraph className="text-white text-sm mb-0">
                  分析发现 <span className="text-orange-400 font-bold">{formatNumber(overallStatistics.inefficientRulesCount)}</span> 条低效规则，
                  占比 <span className="text-orange-400 font-bold">{formatPercent(overallStatistics.inefficientRulesPercentage)}</span>。
                  通过优化可减少约 <span className="text-green-400 font-bold">{formatNumber(overallStatistics.potentialAlertReduction)}</span> 条告警，
                  降噪率达 <span className="text-green-400 font-bold">{formatPercent(overallStatistics.potentialReductionPercentage)}</span>。
                </Paragraph>
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {hasData && (
        <Card className="glass-card border-0">
          <Steps
            current={activeSection}
            onChange={setActiveSection}
            items={sectionSteps.map((step, index) => ({
              key: index,
              title: step.title,
              icon: step.icon,
            }))}
            className="report-steps"
          />
        </Card>
      )}

      <Spin spinning={isLoading}>
        {hasData && (
          <>
            {activeSection === 0 && (
              <ChapterSection
                icon={<Bell size={24} />}
                title="章节1：告警概览"
                description="展示告警总量、趋势和优先级分布，提供全面的告警数据概览。"
              >
                <Row gutter={[16, 16]} className="mb-6">
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="总告警数"
                      value={overallStatistics.totalAlerts}
                      icon={<Bell size={24} />}
                      color="#3B82F6"
                      tooltip="选定时间范围内的告警总数"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="唯一规则数"
                      value={overallStatistics.uniqueRules}
                      icon={<Settings size={24} />}
                      color="#8B5CF6"
                      tooltip="触发告警的唯一规则数量"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="涉及服务数"
                      value={overallStatistics.uniqueServices}
                      icon={<Users size={24} />}
                      color="#06B6D4"
                      tooltip="受告警影响的服务数量"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="严重告警数"
                      value={overallStatistics.highSeverityCount}
                      icon={<AlertTriangle size={24} />}
                      color="#EF4444"
                      tooltip="严重级别告警数量"
                    />
                  </Col>
                </Row>

                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={14}>
                    <Card className="glass-card border-0" title="告警趋势图">
                      <LineChart
                        data={alertTrendData}
                        color="#3B82F6"
                        height={300}
                        showArea
                        smooth
                      />
                    </Card>
                  </Col>
                  <Col xs={24} lg={10}>
                    <Card className="glass-card border-0" title="优先级分布">
                      <PieChart
                        data={priorityDistributionData}
                        type="donut"
                        height={300}
                        showLegend
                      />
                    </Card>
                  </Col>
                </Row>
              </ChapterSection>
            )}

            {activeSection === 1 && (
              <ChapterSection
                icon={<Users size={24} />}
                title="章节2：聚类分析结果"
                description="通过聚类算法识别相似告警模式，发现重复和周期性告警问题。"
              >
                <Row gutter={[16, 16]} className="mb-6">
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="聚类总数"
                      value={clusterSummary?.totalClusters || 0}
                      icon={<Users size={24} />}
                      color="#8B5CF6"
                      tooltip="识别出的告警聚类数量"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="聚类告警总数"
                      value={clusterSummary?.totalAlertsInClusters || 0}
                      icon={<Bell size={24} />}
                      color="#3B82F6"
                      tooltip="所有聚类包含的告警总数"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="平均聚类大小"
                      value={clusterSummary?.avgClusterSize || 0}
                      icon={<Gauge size={24} />}
                      color="#06B6D4"
                      tooltip="每个聚类的平均告警数量"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="周期性聚类占比"
                      value={clusterSummary ? (clusterSummary.periodicPercentage * 100).toFixed(1) : 0}
                      icon={<Clock size={24} />}
                      color="#F59E0B"
                      suffix="%"
                      progress={clusterSummary?.periodicPercentage ? clusterSummary.periodicPercentage * 100 : 0}
                      tooltip="呈现周期性模式的聚类占比"
                    />
                  </Col>
                </Row>

                <Row gutter={[16, 16]} className="mb-6">
                  <Col xs={24} lg={10}>
                    <Card className="glass-card border-0" title="聚类大小分布 TOP 10">
                      <BarChart
                        data={clusterDistributionData}
                        height={300}
                        horizontal
                        xAxisName="告警数"
                        yAxisName="聚类"
                      />
                    </Card>
                  </Col>
                  <Col xs={24} lg={14}>
                    <Card className="glass-card border-0" title="聚类详情">
                      <Table<AlertCluster>
                        dataSource={clusters.slice(0, 10)}
                        columns={alertClusterColumns}
                        rowKey="clusterId"
                        pagination={false}
                        scroll={{ x: 800 }}
                        size="small"
                      />
                    </Card>
                  </Col>
                </Row>
              </ChapterSection>
            )}

            {activeSection === 2 && (
              <ChapterSection
                icon={<AlertTriangle size={24} />}
                title="章节3：低效规则识别"
                description="通过多维度评分识别低效告警规则，包括频率、临界度和噪声评分。"
              >
                <Row gutter={[16, 16]} className="mb-6">
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="低效规则数"
                      value={overallStatistics.inefficientRulesCount}
                      icon={<AlertTriangle size={24} />}
                      color="#F59E0B"
                      suffix={`/ ${formatPercent(overallStatistics.inefficientRulesPercentage)}`}
                      progress={overallStatistics.inefficientRulesPercentage}
                      tooltip="低效规则占总规则数的比例"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="低效规则告警数"
                      value={overallStatistics.alertsFromInefficient}
                      icon={<Bell size={24} />}
                      color="#EF4444"
                      suffix={`/ ${formatPercent(overallStatistics.alertsFromInefficientPercentage)}`}
                      progress={overallStatistics.alertsFromInefficientPercentage}
                      tooltip="低效规则产生的告警占比"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="平均低效度评分"
                      value={(overallStatistics.avgInefficiencyScore * 100).toFixed(1)}
                      icon={<Gauge size={24} />}
                      color="#EF4444"
                      suffix="分"
                      tooltip="所有低效规则的平均低效度评分"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="高严重度规则"
                      value={overallStatistics.highSeverityCount}
                      icon={<AlertTriangle size={24} />}
                      color="#EF4444"
                      tooltip="高严重级别的低效规则数量"
                    />
                  </Col>
                </Row>

                <Row gutter={[16, 16]} className="mb-6">
                  <Col xs={24} lg={8}>
                    <Card className="glass-card border-0" title="低效度评分分布">
                      <BarChart
                        data={inefficiencyScoreDistribution}
                        height={300}
                        xAxisName="评分区间"
                        yAxisName="规则数"
                      />
                    </Card>
                  </Col>
                  <Col xs={24} lg={16}>
                    <Card className="glass-card border-0" title="低效规则列表">
                      <Table<InefficientRule>
                        dataSource={sortedInefficientRules}
                        columns={inefficientRulesColumns}
                        rowKey="ruleName"
                        pagination={{
                          pageSize: 5,
                          size: 'small',
                        }}
                        scroll={{ x: 900 }}
                        size="small"
                      />
                    </Card>
                  </Col>
                </Row>
              </ChapterSection>
            )}

            {activeSection === 3 && (
              <ChapterSection
                icon={<Lightbulb size={24} />}
                title="章节4：优化建议"
                description="针对低效规则提供具体的配置优化建议，包括阈值调整和周期调整。"
              >
                <Row gutter={[16, 16]} className="mb-6">
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="优化建议总数"
                      value={optimizationSummary?.totalSuggestions || 0}
                      icon={<Lightbulb size={24} />}
                      color="#10B981"
                      tooltip="系统生成的优化建议总数"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="预期总减少告警"
                      value={optimizationSummary?.totalExpectedReduction || 0}
                      icon={<TrendingDown size={24} />}
                      color="#10B981"
                      tooltip="通过优化可预期减少的告警总数"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="平均减少率"
                      value={optimizationSummary?.avgReductionPercent || 0}
                      icon={<TrendingDown size={24} />}
                      color="#10B981"
                      suffix="%"
                      progress={optimizationSummary?.avgReductionPercent || 0}
                      tooltip="所有建议的平均告警减少率"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="平均置信度"
                      value={(optimizationSummary?.avgConfidence || 0) * 100}
                      icon={<Target size={24} />}
                      color="#3B82F6"
                      suffix="%"
                      progress={(optimizationSummary?.avgConfidence || 0) * 100}
                      tooltip="优化建议的平均置信度"
                    />
                  </Col>
                </Row>

                <Row gutter={[16, 16]} className="mb-6">
                  <Col xs={24} lg={8}>
                    <Card className="glass-card border-0" title="优化类型分布">
                      <PieChart
                        data={optimizationTypeData}
                        type="donut"
                        height={300}
                        showLegend
                      />
                    </Card>
                  </Col>
                  <Col xs={24} lg={16}>
                    <Card className="glass-card border-0" title="优化建议详情">
                      <Table<OptimizationSuggestion>
                        dataSource={sortedSuggestions}
                        columns={suggestionsColumns}
                        rowKey="ruleName"
                        pagination={{
                          pageSize: 5,
                          size: 'small',
                        }}
                        scroll={{ x: 900 }}
                        size="small"
                      />
                    </Card>
                  </Col>
                </Row>
              </ChapterSection>
            )}

            {activeSection === 4 && (
              <ChapterSection
                icon={<BarChart3 size={24} />}
                title="章节5：效果评估"
                description="通过模拟分析评估优化效果，展示优化前后的对比数据。"
              >
                <Row gutter={[16, 16]} className="mb-6">
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="评估规则总数"
                      value={overallEvaluation?.totalEvaluations || 0}
                      icon={<BarChart3 size={24} />}
                      color="#3B82F6"
                      tooltip="参与效果评估的规则数量"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="总体减少率"
                      value={overallEvaluation?.overallReductionPercent || 0}
                      icon={<TrendingDown size={24} />}
                      color="#10B981"
                      suffix="%"
                      progress={overallEvaluation?.overallReductionPercent || 0}
                      tooltip="优化后的总体告警减少率"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="平均降噪率"
                      value={overallEvaluation?.avgNoiseReductionPercent || 0}
                      icon={<TrendingDown size={24} />}
                      color="#06B6D4"
                      suffix="%"
                      progress={overallEvaluation?.avgNoiseReductionPercent || 0}
                      tooltip="平均噪声告警减少率"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="高影响优化"
                      value={overallEvaluation?.highImpactOptimizations || 0}
                      icon={<Target size={24} />}
                      color="#EF4444"
                      tooltip="产生显著效果的优化数量"
                    />
                  </Col>
                </Row>

                <Row gutter={[16, 16]} className="mb-6">
                  <Col xs={24} lg={8}>
                    <Card className="glass-card border-0" title="优化效果雷达图">
                      <RadarChart
                        data={radarData}
                        color="#3B82F6"
                        height={300}
                      />
                    </Card>
                  </Col>
                  <Col xs={24} lg={16}>
                    <Card className="glass-card border-0" title="评估结果详情">
                      <Table<RuleOptimizationResult>
                        dataSource={evaluationResults}
                        columns={evaluationColumns}
                        rowKey="ruleName"
                        pagination={{
                          pageSize: 5,
                          size: 'small',
                        }}
                        scroll={{ x: 800 }}
                        size="small"
                      />
                    </Card>
                  </Col>
                </Row>

                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={12}>
                    <Card className="glass-card border-0" title="优化前后对比">
                      <BarChart
                        data={[
                          { name: '原始告警数', value: overallEvaluation?.totalOriginalAlerts || 0, color: '#EF4444' },
                          { name: '优化后告警数', value: overallEvaluation?.totalOptimizedAlerts || 0, color: '#10B981' },
                        ]}
                        height={250}
                        xAxisName="指标"
                        yAxisName="告警数"
                      />
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card className="glass-card border-0" title="关键指标覆盖率">
                      <div className="space-y-4 p-4">
                        <div>
                          <div className="flex justify-between mb-1">
                            <Text className="text-gray-400">关键告警覆盖率</Text>
                            <Text className="text-green-400 font-mono">{formatPercent(overallEvaluation?.avgCriticalCoverage || 0)}</Text>
                          </div>
                          <Progress
                            percent={overallEvaluation?.avgCriticalCoverage || 0}
                            strokeColor="#10B981"
                            trailColor="#334155"
                            showInfo={false}
                          />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <Text className="text-gray-400">平均提升率</Text>
                            <Text className="text-blue-400 font-mono">{formatPercent(overallEvaluation?.avgImprovementPercent || 0)}</Text>
                          </div>
                          <Progress
                            percent={overallEvaluation?.avgImprovementPercent || 0}
                            strokeColor="#3B82F6"
                            trailColor="#334155"
                            showInfo={false}
                          />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <Text className="text-gray-400">降噪效果</Text>
                            <Text className="text-cyan-400 font-mono">{formatPercent(overallEvaluation?.avgNoiseReductionPercent || 0)}</Text>
                          </div>
                          <Progress
                            percent={overallEvaluation?.avgNoiseReductionPercent || 0}
                            strokeColor="#06B6D4"
                            trailColor="#334155"
                            showInfo={false}
                          />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <Text className="text-gray-400">总减少率</Text>
                            <Text className="text-emerald-400 font-mono">{formatPercent(overallEvaluation?.overallReductionPercent || 0)}</Text>
                          </div>
                          <Progress
                            percent={overallEvaluation?.overallReductionPercent || 0}
                            strokeColor="#10B981"
                            trailColor="#334155"
                            showInfo={false}
                          />
                        </div>
                      </div>
                    </Card>
                  </Col>
                </Row>
              </ChapterSection>
            )}

            {activeSection === 5 && (
              <ChapterSection
                icon={<Target size={24} />}
                title="章节6：行动建议"
                description="根据优化效果和优先级，提供可执行的优化任务清单，按优先级排序。"
              >
                <Row gutter={[16, 16]} className="mb-6">
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="待执行任务"
                      value={actionItems.length}
                      icon={<Target size={24} />}
                      color="#F59E0B"
                      tooltip="待执行的优化任务总数"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="高优先级任务"
                      value={actionItems.filter(i => i.priority === 'HIGH').length}
                      icon={<AlertTriangle size={24} />}
                      color="#EF4444"
                      tooltip="需要立即处理的高优先级任务"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="中优先级任务"
                      value={actionItems.filter(i => i.priority === 'MEDIUM').length}
                      icon={<AlertTriangle size={24} />}
                      color="#F59E0B"
                      tooltip="需要尽快处理的中优先级任务"
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="低优先级任务"
                      value={actionItems.filter(i => i.priority === 'LOW').length}
                      icon={<CheckCircle size={24} />}
                      color="#10B981"
                      tooltip="可延后处理的低优先级任务"
                    />
                  </Col>
                </Row>

                <Card className="glass-card border-0" title="优化任务清单（按优先级排序）">
                  <List
                    itemLayout="vertical"
                    size="large"
                    dataSource={actionItems}
                    renderItem={(item) => (
                      <List.Item
                        key={item.id}
                        className="!border-b !border-gray-700 !py-4"
                      >
                        <List.Item.Meta
                          title={
                            <div className="flex items-center justify-between">
                              <Space>
                                <span className="text-lg font-bold text-white">
                                  #{item.id} {item.title}
                                </span>
                                <Tag
                                  color={getSeverityColor(item.priority)}
                                  style={{
                                    backgroundColor: `${getSeverityColor(item.priority)}20`,
                                    borderColor: getSeverityColor(item.priority),
                                    color: getSeverityColor(item.priority),
                                  }}
                                >
                                  {item.priority === 'HIGH' ? '高优先级' : item.priority === 'MEDIUM' ? '中优先级' : '低优先级'}
                                </Tag>
                              </Space>
                              <Space>
                                <Tag color="green">
                                  <TrendingDown size={12} className="mr-1" />
                                  预期减少 {formatPercent(item.expectedReduction)}
                                </Tag>
                                <Tag color="blue">
                                  <Target size={12} className="mr-1" />
                                  置信度 {formatPercent(item.confidence * 100)}
                                </Tag>
                              </Space>
                            </div>
                          }
                          description={
                            <div className="mt-2">
                              <Text className="text-gray-400">{item.description}</Text>
                              <div className="flex items-center justify-between mt-4">
                                <div className="flex items-center gap-4">
                                  <div>
                                    <Text className="text-gray-500 text-xs">预期减少告警</Text>
                                    <div className="text-green-400 font-bold">
                                      {formatPercent(item.expectedReduction)}
                                    </div>
                                  </div>
                                  <div>
                                    <Text className="text-gray-500 text-xs">建议执行顺序</Text>
                                    <div className="text-blue-400 font-bold">
                                      第 {item.id} 位
                                    </div>
                                  </div>
                                </div>
                                <Button type="primary" icon={<ArrowRight size={14} />} size="small">
                                  查看详情
                                </Button>
                              </div>
                            </div>
                          }
                        />
                      </List.Item>
                    )}
                  />
                </Card>

                <Divider className="!border-gray-700" />

                <Card className="glass-card border-0 bg-gradient-to-r from-blue-500/10 to-purple-500/10">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                      <Lightbulb size={24} className="text-blue-400" />
                    </div>
                    <div className="flex-1">
                      <Title level={4} className="!mb-2 !text-white">后续建议</Title>
                      <Paragraph className="text-gray-300 mb-4">
                        建议按照优先级顺序执行优化任务。高优先级任务预计可带来 {formatPercent(actionItems.filter(i => i.priority === 'HIGH').reduce((sum, i) => sum + i.expectedReduction, 0))} 的告警减少。
                        建议在执行优化后重新运行分析，以验证效果并发现新的优化机会。
                      </Paragraph>
                      <Space>
                        <Button type="primary" size="middle">
                          批量应用高优先级优化
                        </Button>
                        <Button size="middle">
                          导出执行计划
                        </Button>
                      </Space>
                    </div>
                  </div>
                </Card>
              </ChapterSection>
            )}
          </>
        )}

        {!reportGenerated && !isLoading && (
          <Card className="glass-card border-0 text-center py-16">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-blue-500/10 flex items-center justify-center">
              <FileText size={40} className="text-blue-400" />
            </div>
            <Title level={3} className="!mb-2 !text-white">
              生成分析报告
            </Title>
            <Paragraph className="text-gray-400 max-w-md mx-auto mb-6">
              选择分析时间范围后点击"生成完整报告"按钮，系统将自动分析告警数据、识别低效规则、生成优化建议并评估效果。
            </Paragraph>
            <Button
              type="primary"
              size="large"
              icon={<Play size={18} />}
              onClick={handleGenerateReport}
              className="h-12 px-8"
            >
              开始生成报告
            </Button>
          </Card>
        )}
      </Spin>

      <style>{`
        .report-steps .ant-steps-item-title {
          color: #94A3B8 !important;
        }
        .report-steps .ant-steps-item-active .ant-steps-item-title {
          color: #60A5FA !important;
        }
        .report-steps .ant-steps-item-finish .ant-steps-item-title {
          color: #10B981 !important;
        }
        .report-steps .ant-steps-item-container {
          cursor: pointer;
        }
      `}</style>
    </div>
  );
};

export default Report;
