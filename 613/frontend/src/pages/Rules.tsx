import { useState, useMemo } from 'react';
import {
  Card,
  Table,
  Tag,
  Slider,
  Select,
  Input,
  Space,
  Button,
  Row,
  Col,
  Progress,
  Tooltip,
  Typography,
  Divider,
  Empty,
} from 'antd';
import {
  AlertTriangle,
  TrendingUp,
  BarChart3,
  Target,
  Search,
  Filter,
  RefreshCw,
  Eye,
  Settings,
  ChevronDown,
  ChevronRight,
  Activity,
  Zap,
  SignalHigh,
  Volume2,
  Lightbulb,
} from '@phosphor-icons/react';
import StatCard from '@/components/ui/StatCard';
import BarChart from '@/components/charts/BarChart';
import RadarChart from '@/components/charts/RadarChart';
import PieChart from '@/components/charts/PieChart';
import { useAnalysisStore } from '@/stores/analysisStore';
import { InefficientRule } from '@/types';
import {
  formatNumber,
  formatPercent,
  getSeverityColor,
  getScoreColor,
  truncateText,
} from '@/utils/format';

const { Title, Text } = Typography;
const { Option } = Select;

const Rules: React.FC = () => {
  const { inefficientRules, overallStatistics, loading, fetchInefficientRules } =
    useAnalysisStore();

  const [minScore, setMinScore] = useState<number>(0);
  const [severityFilter, setSeverityFilter] = useState<string[]>([]);
  const [searchText, setSearchText] = useState<string>('');
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([]);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });

  const filteredRules = useMemo(() => {
    return inefficientRules.filter((rule) => {
      const matchScore = rule.inefficiencyScore >= minScore;
      const matchSeverity =
        severityFilter.length === 0 || severityFilter.includes(rule.severity);
      const matchSearch =
        searchText === '' ||
        rule.ruleName.toLowerCase().includes(searchText.toLowerCase());
      return matchScore && matchSeverity && matchSearch;
    });
  }, [inefficientRules, minScore, severityFilter, searchText]);

  const barChartData = useMemo(() => {
    const distribution: Record<string, number> = {
      '0.0-0.2': 0,
      '0.2-0.4': 0,
      '0.4-0.6': 0,
      '0.6-0.8': 0,
      '0.8-1.0': 0,
    };

    filteredRules.forEach((rule) => {
      const score = rule.inefficiencyScore;
      if (score < 0.2) distribution['0.0-0.2']++;
      else if (score < 0.4) distribution['0.2-0.4']++;
      else if (score < 0.6) distribution['0.4-0.6']++;
      else if (score < 0.8) distribution['0.6-0.8']++;
      else distribution['0.8-1.0']++;
    });

    return Object.entries(distribution).map(([name, value]) => ({
      name,
      value,
      color: name === '0.8-1.0'
        ? '#EF4444'
        : name === '0.6-0.8'
        ? '#F59E0B'
        : name === '0.4-0.6'
        ? '#06B6D4'
        : '#10B981',
    }));
  }, [filteredRules]);

  const radarChartData = useMemo(() => {
    if (filteredRules.length === 0) {
      return [
        { name: '频率', value: 0, max: 1 },
        { name: '关键度', value: 0, max: 1 },
        { name: '噪声', value: 0, max: 1 },
        { name: '低效度', value: 0, max: 1 },
      ];
    }

    const avgFrequency =
      filteredRules.reduce((sum, r) => sum + r.frequencyScore, 0) /
      filteredRules.length;
    const avgCriticality =
      filteredRules.reduce((sum, r) => sum + r.criticalityScore, 0) /
      filteredRules.length;
    const avgNoise =
      filteredRules.reduce((sum, r) => sum + r.noiseScore, 0) /
      filteredRules.length;
    const avgInefficiency =
      filteredRules.reduce((sum, r) => sum + r.inefficiencyScore, 0) /
      filteredRules.length;

    return [
      { name: '频率', value: Number(avgFrequency.toFixed(2)), max: 1 },
      { name: '关键度', value: Number(avgCriticality.toFixed(2)), max: 1 },
      { name: '噪声', value: Number(avgNoise.toFixed(2)), max: 1 },
      { name: '低效度', value: Number(avgInefficiency.toFixed(2)), max: 1 },
    ];
  }, [filteredRules]);

  const pieChartData = useMemo(() => {
    const distribution: Record<string, number> = {
      HIGH: 0,
      MEDIUM: 0,
      LOW: 0,
    };

    filteredRules.forEach((rule) => {
      distribution[rule.severity]++;
    });

    return [
      {
        name: '高严重',
        value: distribution.HIGH,
        color: getSeverityColor('HIGH'),
      },
      {
        name: '中严重',
        value: distribution.MEDIUM,
        color: getSeverityColor('MEDIUM'),
      },
      {
        name: '低严重',
        value: distribution.LOW,
        color: getSeverityColor('LOW'),
      },
    ];
  }, [filteredRules]);

  const handleRefresh = () => {
    fetchInefficientRules();
  };

  const handleExpand = (expanded: boolean, record: InefficientRule) => {
    if (expanded) {
      setExpandedRowKeys([...expandedRowKeys, record.ruleName]);
    } else {
      setExpandedRowKeys(
        expandedRowKeys.filter((key) => key !== record.ruleName)
      );
    }
  };

  const handleViewDetail = (rule: InefficientRule) => {
    console.log('View detail:', rule.ruleName);
  };

  const handleOptimize = (rule: InefficientRule) => {
    console.log('Optimize rule:', rule.ruleName);
  };

  const expandedRowRender = (record: InefficientRule) => {
    return (
      <div className="p-4 bg-slate-900/50 rounded-lg">
        <Row gutter={[24, 16]}>
          <Col xs={24} md={12}>
            <Title level={5} className="text-gray-300 mb-3">
              <Activity size={16} className="mr-2 inline" />
              详细指标数据
            </Title>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <Text className="text-gray-400 text-sm">频率评分</Text>
                  <Text
                    className="text-sm font-medium"
                    style={{ color: getScoreColor(record.frequencyScore) }}
                  >
                    {(record.frequencyScore * 100).toFixed(1)}%
                  </Text>
                </div>
                <Progress
                  percent={record.frequencyScore * 100}
                  showInfo={false}
                  strokeColor={getScoreColor(record.frequencyScore)}
                  trailColor="#334155"
                  size="small"
                />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <Text className="text-gray-400 text-sm">关键度评分</Text>
                  <Text
                    className="text-sm font-medium"
                    style={{ color: getScoreColor(record.criticalityScore) }}
                  >
                    {(record.criticalityScore * 100).toFixed(1)}%
                  </Text>
                </div>
                <Progress
                  percent={record.criticalityScore * 100}
                  showInfo={false}
                  strokeColor={getScoreColor(record.criticalityScore)}
                  trailColor="#334155"
                  size="small"
                />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <Text className="text-gray-400 text-sm">噪声评分</Text>
                  <Text
                    className="text-sm font-medium"
                    style={{ color: getScoreColor(record.noiseScore) }}
                  >
                    {(record.noiseScore * 100).toFixed(1)}%
                  </Text>
                </div>
                <Progress
                  percent={record.noiseScore * 100}
                  showInfo={false}
                  strokeColor={getScoreColor(record.noiseScore)}
                  trailColor="#334155"
                  size="small"
                />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <Text className="text-gray-400 text-sm">低效度评分</Text>
                  <Text
                    className="text-sm font-medium"
                    style={{ color: getScoreColor(record.inefficiencyScore) }}
                  >
                    {(record.inefficiencyScore * 100).toFixed(1)}%
                  </Text>
                </div>
                <Progress
                  percent={record.inefficiencyScore * 100}
                  showInfo={false}
                  strokeColor={getScoreColor(record.inefficiencyScore)}
                  trailColor="#334155"
                  size="small"
                />
              </div>
            </div>
          </Col>
          <Col xs={24} md={12}>
            <Title level={5} className="text-gray-300 mb-3">
              <Lightbulb size={16} className="mr-2 inline" />
              优化建议预览
            </Title>
            <Card
              className="bg-slate-800/50 border-slate-700"
              styles={{ body: { padding: '16px' } }}
            >
              <Text className="text-gray-300 leading-relaxed">
                {record.recommendation}
              </Text>
              {record.metricsData && Object.keys(record.metricsData).length > 0 && (
                <>
                  <Divider className="my-3 border-slate-700" />
                  <div className="text-xs text-gray-500 space-y-1">
                    {Object.entries(record.metricsData).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span>{key}:</span>
                        <span className="text-gray-400">
                          {typeof value === 'number'
                            ? formatNumber(value)
                            : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </Card>
          </Col>
        </Row>
      </div>
    );
  };

  const columns = [
    {
      title: '规则名',
      dataIndex: 'ruleName',
      key: 'ruleName',
      sorter: (a: InefficientRule, b: InefficientRule) =>
        a.ruleName.localeCompare(b.ruleName),
      render: (text: string) => (
        <Tooltip title={text}>
          <span className="text-gray-200 font-medium">
            {truncateText(text, 30)}
          </span>
        </Tooltip>
      ),
    },
    {
      title: '总告警数',
      dataIndex: 'totalAlerts',
      key: 'totalAlerts',
      sorter: (a: InefficientRule, b: InefficientRule) =>
        a.totalAlerts - b.totalAlerts,
      render: (value: number) => (
        <span className="text-gray-300 font-mono">
          {formatNumber(value)}
        </span>
      ),
    },
    {
      title: '低效度评分',
      dataIndex: 'inefficiencyScore',
      key: 'inefficiencyScore',
      sorter: (a: InefficientRule, b: InefficientRule) =>
        a.inefficiencyScore - b.inefficiencyScore,
      render: (value: number) => (
        <div className="flex items-center gap-2">
          <Progress
            type="circle"
            percent={Math.round(value * 100)}
            size={40}
            strokeColor={getScoreColor(value)}
            trailColor="#334155"
            format={(percent) => (
              <span
                className="text-xs font-bold"
                style={{ color: getScoreColor(value) }}
              >
                {percent}%
              </span>
            )}
          />
        </div>
      ),
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      filters: [
        { text: '高严重', value: 'HIGH' },
        { text: '中严重', value: 'MEDIUM' },
        { text: '低严重', value: 'LOW' },
      ],
      onFilter: (value: string | number | boolean, record: InefficientRule) =>
        record.severity === value,
      render: (severity: string) => (
        <Tag
          color={getSeverityColor(severity)}
          className="border-0 font-medium"
        >
          {severity === 'HIGH'
            ? '高严重'
            : severity === 'MEDIUM'
            ? '中严重'
            : '低严重'}
        </Tag>
      ),
    },
    {
      title: '频率评分',
      dataIndex: 'frequencyScore',
      key: 'frequencyScore',
      sorter: (a: InefficientRule, b: InefficientRule) =>
        a.frequencyScore - b.frequencyScore,
      render: (value: number) => (
        <Tooltip title={`${(value * 100).toFixed(1)}%`}>
          <div className="flex items-center gap-1">
            <Zap size={14} style={{ color: getScoreColor(value) }} />
            <Progress
              percent={Math.round(value * 100)}
              showInfo={false}
              strokeColor={getScoreColor(value)}
              trailColor="#334155"
              size="small"
              style={{ width: 60 }}
            />
          </div>
        </Tooltip>
      ),
    },
    {
      title: '关键度评分',
      dataIndex: 'criticalityScore',
      key: 'criticalityScore',
      sorter: (a: InefficientRule, b: InefficientRule) =>
        a.criticalityScore - b.criticalityScore,
      render: (value: number) => (
        <Tooltip title={`${(value * 100).toFixed(1)}%`}>
          <div className="flex items-center gap-1">
            <SignalHigh size={14} style={{ color: getScoreColor(value) }} />
            <Progress
              percent={Math.round(value * 100)}
              showInfo={false}
              strokeColor={getScoreColor(value)}
              trailColor="#334155"
              size="small"
              style={{ width: 60 }}
            />
          </div>
        </Tooltip>
      ),
    },
    {
      title: '噪声评分',
      dataIndex: 'noiseScore',
      key: 'noiseScore',
      sorter: (a: InefficientRule, b: InefficientRule) =>
        a.noiseScore - b.noiseScore,
      render: (value: number) => (
        <Tooltip title={`${(value * 100).toFixed(1)}%`}>
          <div className="flex items-center gap-1">
            <Volume2 size={14} style={{ color: getScoreColor(value) }} />
            <Progress
              percent={Math.round(value * 100)}
              showInfo={false}
              strokeColor={getScoreColor(value)}
              trailColor="#334155"
              size="small"
              style={{ width: 60 }}
            />
          </div>
        </Tooltip>
      ),
    },
    {
      title: '建议',
      dataIndex: 'recommendation',
      key: 'recommendation',
      render: (text: string) => (
        <Tooltip title={text}>
          <span className="text-gray-400 text-sm">
            {truncateText(text, 25)}
          </span>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: InefficientRule) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              size="small"
              icon={<Eye size={16} />}
              onClick={() => handleViewDetail(record)}
              className="text-blue-400 hover:text-blue-300"
            />
          </Tooltip>
          <Tooltip title="优化规则">
            <Button
              type="text"
              size="small"
              icon={<Settings size={16} />}
              onClick={() => handleOptimize(record)}
              className="text-emerald-400 hover:text-emerald-300"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <Title level={2} className="text-white mb-1">
            低效规则识别
          </Title>
          <Text className="text-gray-400">
            识别和分析告警系统中的低效规则，提供优化建议
          </Text>
        </div>
        <Button
          type="primary"
          icon={<RefreshCw size={16} />}
          onClick={handleRefresh}
          loading={loading.inefficientRules}
          className="bg-blue-600 hover:bg-blue-500"
        >
          刷新数据
        </Button>
      </div>

      <Card className="glass-card border-0">
        <div className="flex items-center gap-2 mb-4">
          <Filter size={18} className="text-gray-400" />
          <Text className="text-gray-300 font-medium">筛选条件</Text>
        </div>
        <Row gutter={[24, 16]} align="middle">
          <Col xs={24} md={8}>
            <div className="flex items-center gap-4">
              <Text className="text-gray-400 whitespace-nowrap text-sm min-w-[100px]">
                最低低效度:
              </Text>
              <div className="flex-1 flex items-center gap-3">
                <Slider
                  min={0}
                  max={1}
                  step={0.05}
                  value={minScore}
                  onChange={setMinScore}
                  tooltip={{
                    formatter: (value) => `${(value! * 100).toFixed(0)}%`,
                  }}
                  styles={{
                    track: { backgroundColor: '#3B82F6' },
                    rail: { backgroundColor: '#334155' },
                    handle: {
                      borderColor: '#3B82F6',
                      backgroundColor: '#1E293B',
                    },
                  }}
                />
                <Text
                  className="text-sm font-mono font-bold min-w-[50px]"
                  style={{ color: getScoreColor(minScore) }}
                >
                  {(minScore * 100).toFixed(0)}%
                </Text>
              </div>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <div className="flex items-center gap-4">
              <Text className="text-gray-400 whitespace-nowrap text-sm min-w-[100px]">
                严重程度:
              </Text>
              <Select
                mode="multiple"
                placeholder="选择严重程度"
                value={severityFilter}
                onChange={setSeverityFilter}
                className="flex-1"
                style={{ minWidth: 200 }}
                options={[
                  { label: '高严重', value: 'HIGH' },
                  { label: '中严重', value: 'MEDIUM' },
                  { label: '低严重', value: 'LOW' },
                ]}
              />
            </div>
          </Col>
          <Col xs={24} md={8}>
            <div className="flex items-center gap-4">
              <Text className="text-gray-400 whitespace-nowrap text-sm min-w-[100px]">
                搜索规则:
              </Text>
              <Input
                placeholder="按规则名搜索"
                prefix={<Search size={16} className="text-gray-500" />}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                allowClear
                className="flex-1"
              />
            </div>
          </Col>
        </Row>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="低效规则总数"
            value={overallStatistics?.inefficientRulesCount || 0}
            icon={<AlertTriangle size={24} />}
            color="#EF4444"
            progress={
              overallStatistics?.inefficientRulesPercentage
                ? overallStatistics.inefficientRulesPercentage
                : 0
            }
            tooltip="识别出的低效告警规则总数"
            loading={loading.inefficientRules}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="高严重程度规则数"
            value={overallStatistics?.highSeverityCount || 0}
            icon={<Target size={24} />}
            color="#F59E0B"
            progress={
              overallStatistics?.highSeverityCount &&
              overallStatistics?.inefficientRulesCount
                ? (overallStatistics.highSeverityCount /
                    overallStatistics.inefficientRulesCount) *
                  100
                : 0
            }
            tooltip="高严重程度的低效规则数量"
            loading={loading.inefficientRules}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="低效规则告警占比"
            value={formatPercent(
              overallStatistics?.alertsFromInefficientPercentage || 0
            )}
            icon={<TrendingUp size={24} />}
            color="#8B5CF6"
            progress={overallStatistics?.alertsFromInefficientPercentage || 0}
            tooltip="来自低效规则的告警占总告警数的比例"
            loading={loading.inefficientRules}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="平均低效度评分"
            value={(overallStatistics?.avgInefficiencyScore || 0).toFixed(2)}
            icon={<BarChart3 size={24} />}
            color="#06B6D4"
            progress={(overallStatistics?.avgInefficiencyScore || 0) * 100}
            tooltip="所有低效规则的平均低效度评分"
            loading={loading.inefficientRules}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            className="glass-card border-0 h-full"
            title={
              <div className="flex items-center gap-2">
                <BarChart3 size={18} className="text-blue-400" />
                <span className="text-gray-200">低效度评分分布</span>
              </div>
            }
          >
            {filteredRules.length > 0 ? (
              <BarChart
                data={barChartData}
                xAxisName="评分区间"
                yAxisName="规则数量"
                color="#3B82F6"
              />
            ) : (
              <Empty
                description="暂无数据"
                className="py-12"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={6}>
          <Card
            className="glass-card border-0 h-full"
            title={
              <div className="flex items-center gap-2">
                <Target size={18} className="text-purple-400" />
                <span className="text-gray-200">多维度评分雷达</span>
              </div>
            }
          >
            {filteredRules.length > 0 ? (
              <RadarChart
                data={radarChartData}
                color="#8B5CF6"
                height={280}
              />
            ) : (
              <Empty
                description="暂无数据"
                className="py-12"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={6}>
          <Card
            className="glass-card border-0 h-full"
            title={
              <div className="flex items-center gap-2">
                <AlertTriangle size={18} className="text-orange-400" />
                <span className="text-gray-200">严重程度分布</span>
              </div>
            }
          >
            {filteredRules.length > 0 ? (
              <PieChart
                data={pieChartData}
                type="donut"
                height={280}
                showLegend={true}
              />
            ) : (
              <Empty
                description="暂无数据"
                className="py-12"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>
      </Row>

      <Card
        className="glass-card border-0"
        title={
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={18} className="text-emerald-400" />
              <span className="text-gray-200">低效规则列表</span>
              <Tag color="blue" className="ml-2">
                共 {filteredRules.length} 条
              </Tag>
            </div>
          </div>
        }
      >
        <Table
          dataSource={filteredRules}
          columns={columns}
          rowKey="ruleName"
          loading={loading.inefficientRules}
          expandable={{
            expandedRowRender,
            expandedRowKeys,
            onExpand: handleExpand,
            expandIcon: ({ expanded, onExpand, record }) =>
              expanded ? (
                <ChevronDown
                  size={16}
                  className="text-gray-400 cursor-pointer hover:text-gray-200"
                  onClick={(e) => onExpand(record, e)}
                />
              ) : (
                <ChevronRight
                  size={16}
                  className="text-gray-400 cursor-pointer hover:text-gray-200"
                  onClick={(e) => onExpand(record, e)}
                />
              ),
          }}
          pagination={{
            ...pagination,
            total: filteredRules.length,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
            onChange: (page, pageSize) =>
              setPagination({ current: page, pageSize }),
          }}
          scroll={{ x: 1200 }}
          rowClassName={() => 'hover:bg-slate-800/30'}
        />
      </Card>
    </div>
  );
};

export default Rules;
