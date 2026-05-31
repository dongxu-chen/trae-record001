import { useState, useEffect, useMemo } from 'react';
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
  Collapse,
  Progress,
  Descriptions,
  Badge,
  Spin,
  message,
} from 'antd';
import {
  SlidersHorizontal,
  ArrowUp,
  ArrowDown,
  CheckCircle,
  Clock,
  Bell,
  Search,
  Play,
  MagicWand,
  Barricade,
} from '@phosphor-icons/react';
import StatCard from '@/components/ui/StatCard';
import PieChart from '@/components/charts/PieChart';
import BarChart from '@/components/charts/BarChart';
import { useAnalysisStore } from '@/stores/analysisStore';
import { OptimizationSuggestion } from '@/types';
import {
  formatNumber,
  formatPercent,
  getScoreColor,
  generateChartColors,
  truncateText,
} from '@/utils/format';

const { Search: SearchInput } = Input;
const { Option } = Select;
const { Panel } = Collapse;

type OptimizationType = 'threshold' | 'period' | 'silence' | 'all';

const optimizationTypeOptions = [
  { label: '全部类型', value: 'all' },
  { label: '阈值调整', value: 'threshold', color: '#3B82F6' },
  { label: '周期调整', value: 'period', color: '#10B981' },
  { label: '静默期调整', value: 'silence', color: '#F59E0B' },
];

const getOptimizationType = (suggestion: OptimizationSuggestion): OptimizationType => {
  const { originalConfig, suggestedConfig } = suggestion;
  if (originalConfig.threshold !== suggestedConfig.threshold) return 'threshold';
  if (originalConfig.period !== suggestedConfig.period) return 'period';
  if (originalConfig.silencePeriod !== suggestedConfig.silencePeriod) return 'silence';
  return 'threshold';
};

const getOptimizationTypeInfo = (type: OptimizationType) => {
  switch (type) {
    case 'threshold':
      return { label: '阈值调整', color: '#3B82F6', icon: <SlidersHorizontal size={12} /> };
    case 'period':
      return { label: '周期调整', color: '#10B981', icon: <Clock size={12} /> };
    case 'silence':
      return { label: '静默期调整', color: '#F59E0B', icon: <Barricade size={12} /> };
    default:
      return { label: '其他', color: '#6B7280', icon: <SlidersHorizontal size={12} /> };
  }
};

const Optimizer: React.FC = () => {
  const {
    suggestions,
    optimizationSummary,
    loading,
    fetchSuggestions,
    setFilters,
  } = useAnalysisStore();

  const [minConfidence, setMinConfidence] = useState<number>(0.5);
  const [selectedType, setSelectedType] = useState<OptimizationType>('all');
  const [searchText, setSearchText] = useState<string>('');
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  const handleConfidenceChange = (value: number) => {
    setMinConfidence(value);
    setFilters({ minConfidence: value });
  };

  const handleTypeChange = (value: OptimizationType) => {
    setSelectedType(value);
  };

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const handleApplySuggestion = async (suggestion: OptimizationSuggestion) => {
    message.loading({ content: '正在应用优化建议...', key: suggestion.ruleName });
    await new Promise((resolve) => setTimeout(resolve, 1000));
    message.success({ content: `已应用规则 "${suggestion.ruleName}" 的优化建议`, key: suggestion.ruleName });
  };

  const handleSimulate = (suggestion: OptimizationSuggestion) => {
    message.info(`正在模拟评估规则 "${suggestion.ruleName}" 的优化效果...`);
  };

  const filteredSuggestions = useMemo(() => {
    return suggestions.filter((s) => {
      if (s.confidence < minConfidence) return false;
      if (selectedType !== 'all' && getOptimizationType(s) !== selectedType) return false;
      if (searchText && !s.ruleName.toLowerCase().includes(searchText.toLowerCase())) return false;
      return true;
    });
  }, [suggestions, minConfidence, selectedType, searchText]);

  const optimizationTypeData = useMemo(() => {
    const typeCount: Record<string, number> = {
      threshold: 0,
      period: 0,
      silence: 0,
    };

    filteredSuggestions.forEach((s) => {
      const type = getOptimizationType(s);
      typeCount[type]++;
    });

    return Object.entries(typeCount).map(([type, value]) => {
      const info = getOptimizationTypeInfo(type as OptimizationType);
      return {
        name: info.label,
        value,
        color: info.color,
      };
    });
  }, [filteredSuggestions]);

  const topReductionData = useMemo(() => {
    const colors = generateChartColors(10);
    return [...filteredSuggestions]
      .sort((a, b) => b.expectedImprovement.alertReduction - a.expectedImprovement.alertReduction)
      .slice(0, 10)
      .map((s, index) => ({
        name: truncateText(s.ruleName, 15),
        value: s.expectedImprovement.alertReduction,
        color: colors[index],
      }));
  }, [filteredSuggestions]);

  const confidenceDistributionData = useMemo(() => {
    const ranges = [
      { label: '0.0-0.2', min: 0, max: 0.2, color: '#6B7280' },
      { label: '0.2-0.4', min: 0.2, max: 0.4, color: '#06B6D4' },
      { label: '0.4-0.6', min: 0.4, max: 0.6, color: '#3B82F6' },
      { label: '0.6-0.8', min: 0.6, max: 0.8, color: '#F59E0B' },
      { label: '0.8-1.0', min: 0.8, max: 1.0, color: '#10B981' },
    ];

    return ranges.map((range) => {
      const count = filteredSuggestions.filter(
        (s) => s.confidence >= range.min && s.confidence < range.max
      ).length;
      return {
        name: range.label,
        value: count,
        color: range.color,
      };
    });
  }, [filteredSuggestions]);

  const configComparisonColumns = [
    {
      title: '配置项',
      dataIndex: 'key',
      key: 'key',
      width: 150,
      render: (text: string) => <span className="text-gray-300 font-medium">{text}</span>,
    },
    {
      title: '原始配置',
      dataIndex: 'original',
      key: 'original',
      width: 150,
      render: (value: any, record: any) => (
        <span className="text-gray-400">
          {record.changed && <ArrowUp size={12} className="inline mr-1 text-red-400" />}
          {String(value)}
        </span>
      ),
    },
    {
      title: '建议配置',
      dataIndex: 'suggested',
      key: 'suggested',
      width: 150,
      render: (value: any, record: any) => (
        <span className={record.changed ? 'text-green-400 font-medium' : 'text-gray-400'}>
          {record.changed && <ArrowDown size={12} className="inline mr-1 text-green-400" />}
          {String(value)}
        </span>
      ),
    },
  ];

  const getConfigComparisonData = (suggestion: OptimizationSuggestion) => {
    const { originalConfig, suggestedConfig } = suggestion;
    const configKeys = ['threshold', 'period', 'count', 'silencePeriod', 'op'];
    const configLabels: Record<string, string> = {
      threshold: '阈值',
      period: '检测周期',
      count: '触发次数',
      silencePeriod: '静默期',
      op: '比较操作',
    };

    return configKeys
      .filter((key) => originalConfig[key] !== undefined || suggestedConfig[key] !== undefined)
      .map((key) => ({
        key: configLabels[key] || key,
        original: originalConfig[key] ?? '-',
        suggested: suggestedConfig[key] ?? '-',
        changed: originalConfig[key] !== suggestedConfig[key],
      }));
  };

  const renderSuggestionCard = (suggestion: OptimizationSuggestion, index: number) => {
    const type = getOptimizationType(suggestion);
    const typeInfo = getOptimizationTypeInfo(type);
    const { expectedImprovement, confidence } = suggestion;

    const header = (
      <div className="flex items-center justify-between w-full py-2">
        <div className="flex items-center gap-4 flex-1">
          <Badge
            count={index + 1}
            style={{ backgroundColor: getScoreColor(confidence) }}
            size="small"
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <span className="font-medium text-gray-100 truncate max-w-xs">
                {suggestion.ruleName}
              </span>
              <Tag
                icon={typeInfo.icon}
                style={{
                  backgroundColor: `${typeInfo.color}20`,
                  borderColor: typeInfo.color,
                  color: typeInfo.color,
                }}
                className="text-xs"
              >
                {typeInfo.label}
              </Tag>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6 flex-shrink-0">
          <div className="text-center">
            <div className="text-xs text-gray-400 mb-1">置信度</div>
            <div className="flex items-center gap-2">
              <Progress
                type="circle"
                percent={Math.round(confidence * 100)}
                size={40}
                strokeColor={getScoreColor(confidence)}
                trailColor="#334155"
                format={(percent) => <span className="text-xs text-gray-300">{percent}%</span>}
              />
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-400 mb-1">预期减少</div>
            <div className="text-lg font-bold text-green-400">
              {formatNumber(expectedImprovement.alertReduction)}
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-400 mb-1">减少百分比</div>
            <div className="text-lg font-bold text-cyan-400">
              {formatPercent(expectedImprovement.reductionPercent)}
            </div>
          </div>
        </div>
      </div>
    );

    return (
      <Panel
        key={suggestion.ruleName}
        header={header}
        className="glass-card hover-lift"
        style={{
          background: 'rgba(30, 41, 59, 0.7)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '12px',
          marginBottom: '12px',
        }}
      >
        <div className="space-y-6 pt-2">
          <div className="grid grid-cols-2 gap-6">
            <Card
              title="配置对比"
              size="small"
              className="glass-card border-0"
              styles={{ header: { borderBottom: '1px solid #334155' } }}
            >
              <Table
                dataSource={getConfigComparisonData(suggestion)}
                columns={configComparisonColumns}
                rowKey="key"
                pagination={false}
                size="small"
                showHeader={false}
                locale={{ emptyText: '暂无配置对比数据' }}
              />
            </Card>

            <Card
              title="预期效果"
              size="small"
              className="glass-card border-0"
              styles={{ header: { borderBottom: '1px solid #334155' } }}
            >
              <Descriptions column={1} size="small" className="text-sm">
                <Descriptions.Item label="原始告警数">
                  <span className="text-gray-300">
                    {formatNumber(expectedImprovement.originalAlertCount)}
                  </span>
                </Descriptions.Item>
                <Descriptions.Item label="预期告警数">
                  <span className="text-gray-300">
                    {formatNumber(expectedImprovement.expectedAlertCount)}
                  </span>
                </Descriptions.Item>
                <Descriptions.Item label="告警减少量">
                  <span className="text-green-400 font-medium">
                    {formatNumber(expectedImprovement.alertReduction)}
                  </span>
                </Descriptions.Item>
                <Descriptions.Item label="噪声减少评分">
                  <div className="flex items-center gap-2">
                    <Progress
                      percent={Math.round(expectedImprovement.noiseReductionScore * 100)}
                      size="small"
                      strokeColor="#10B981"
                      trailColor="#334155"
                      className="w-32"
                    />
                    <span className="text-gray-300">
                      {formatPercent(expectedImprovement.noiseReductionScore * 100, 0)}
                    </span>
                  </div>
                </Descriptions.Item>
                <Descriptions.Item label="关键告警保留">
                  <Tag
                    icon={expectedImprovement.criticalityPreserved ? <CheckCircle size={12} /> : null}
                    color={expectedImprovement.criticalityPreserved ? 'success' : 'warning'}
                    style={{
                      backgroundColor: expectedImprovement.criticalityPreserved
                        ? 'rgba(16, 185, 129, 0.2)'
                        : 'rgba(245, 158, 11, 0.2)',
                      borderColor: expectedImprovement.criticalityPreserved ? '#10B981' : '#F59E0B',
                      color: expectedImprovement.criticalityPreserved ? '#10B981' : '#F59E0B',
                    }}
                  >
                    {expectedImprovement.criticalityPreserved ? '已保留' : '部分影响'}
                  </Tag>
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </div>

          <Card
            title="改进说明"
            size="small"
            className="glass-card border-0"
            styles={{ header: { borderBottom: '1px solid #334155' } }}
          >
            <p className="text-gray-300 leading-relaxed">{suggestion.reasoning}</p>
          </Card>

          <div className="flex justify-end gap-3">
            <Button
              icon={<Play size={16} />}
              onClick={() => handleSimulate(suggestion)}
              size="middle"
            >
              模拟评估
            </Button>
            <Button
              type="primary"
              icon={<MagicWand size={16} />}
              onClick={() => handleApplySuggestion(suggestion)}
              size="middle"
            >
              应用建议
            </Button>
          </div>
        </div>
      </Panel>
    );
  };

  const isLoading = loading.suggestions;

  return (
    <div className="space-y-6">
      <div className="glass-card p-5">
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={24} md={8} lg={8}>
            <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
              <SlidersHorizontal size={16} />
              <span>最低置信度: {formatPercent(minConfidence * 100, 0)}</span>
            </div>
            <Slider
              min={0}
              max={1}
              step={0.05}
              value={minConfidence}
              onChange={handleConfidenceChange}
              tooltip={{ formatter: (value) => value && formatPercent(value * 100, 0) }}
            />
          </Col>

          <Col xs={24} sm={24} md={8} lg={8}>
            <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
              <SlidersHorizontal size={16} />
              <span>优化类型</span>
            </div>
            <Select
              value={selectedType}
              onChange={handleTypeChange}
              className="w-full"
              size="middle"
            >
              {optimizationTypeOptions.map((option) => (
                <Option key={option.value} value={option.value}>
                  {option.color && (
                    <span style={{ color: option.color, marginRight: '8px' }}>●</span>
                  )}
                  {option.label}
                </Option>
              ))}
            </Select>
          </Col>

          <Col xs={24} sm={24} md={8} lg={8}>
            <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
              <Search size={16} />
              <span>搜索规则</span>
            </div>
            <SearchInput
              placeholder="输入规则名称搜索..."
              allowClear
              onChange={(e) => handleSearch(e.target.value)}
              onSearch={handleSearch}
              size="middle"
            />
          </Col>
        </Row>
      </div>

      <Spin spinning={isLoading}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="优化建议总数"
              value={optimizationSummary?.totalSuggestions || 0}
              icon={<SlidersHorizontal size={24} />}
              color="#3B82F6"
              tooltip="系统生成的优化建议总数"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="预期总减少告警数"
              value={optimizationSummary?.totalExpectedReduction || 0}
              icon={<Bell size={24} />}
              color="#10B981"
              tooltip="应用所有建议后预期减少的告警总数"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="平均减少百分比"
              value={optimizationSummary?.avgReductionPercent || 0}
              icon={<ArrowDown size={24} />}
              color="#06B6D4"
              suffix="%"
              tooltip="所有建议的平均告警减少百分比"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="高置信度建议数"
              value={optimizationSummary?.highConfidenceCount || 0}
              icon={<CheckCircle size={24} />}
              progress={
                optimizationSummary?.totalSuggestions
                  ? (optimizationSummary.highConfidenceCount / optimizationSummary.totalSuggestions) * 100
                  : 0
              }
              color="#10B981"
              tooltip="置信度 ≥ 0.8 的优化建议数量"
              loading={isLoading}
            />
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="mt-4">
          <Col xs={24} lg={8}>
            <Card className="glass-card hover-lift border-0" title="优化类型分布">
              <PieChart
                data={optimizationTypeData}
                type="donut"
                height={280}
                showLegend
              />
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card className="glass-card hover-lift border-0" title="预期减少量 TOP 10">
              <BarChart
                data={topReductionData}
                height={280}
                horizontal
                xAxisName="预期减少量"
                yAxisName="规则名称"
              />
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card className="glass-card hover-lift border-0" title="置信度分布">
              <BarChart
                data={confidenceDistributionData}
                height={280}
                xAxisName="置信度区间"
                yAxisName="建议数量"
              />
            </Card>
          </Col>
        </Row>

        <Card
          className="glass-card hover-lift border-0 mt-4"
          title={
            <div className="flex items-center justify-between">
              <span>优化建议列表</span>
              <span className="text-sm text-gray-400 font-normal">
                共 {formatNumber(filteredSuggestions.length)} 条建议
              </span>
            </div>
          }
          styles={{ body: { padding: '16px' } }}
        >
          {filteredSuggestions.length > 0 ? (
            <Collapse
              activeKey={expandedKeys}
              onChange={(keys) => setExpandedKeys(keys as string[])}
              ghost
              className="optimizer-collapse"
            >
              {filteredSuggestions.map((suggestion, index) =>
                renderSuggestionCard(suggestion, index)
              )}
            </Collapse>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <SlidersHorizontal size={48} className="mx-auto mb-3 opacity-30" />
              <p>暂无符合条件的优化建议</p>
              <p className="text-sm mt-1">请尝试调整筛选条件</p>
            </div>
          )}
        </Card>
      </Spin>
    </div>
  );
};

export default Optimizer;
