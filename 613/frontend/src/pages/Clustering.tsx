import React, { useMemo, useEffect } from 'react';
import { Card, Collapse, Badge, List, Row, Col, Space, Tag, Empty, Spin } from 'antd';
import {
  GitBranch,
  Bell,
  Users,
  Clock,
  AlertTriangle,
  Calendar,
  Server,
  BarChart3,
  PieChart as PieChartIcon,
  Activity,
  Info,
  Refresh,
} from '@phosphor-icons/react';
import StatCard from '@/components/ui/StatCard';
import BarChart from '@/components/charts/BarChart';
import PieChart from '@/components/charts/PieChart';
import LineChart from '@/components/charts/LineChart';
import { useAnalysisStore } from '@/stores/analysisStore';
import { AlertCluster } from '@/types';
import {
  formatTime,
  formatNumber,
  formatPercent,
  getPriorityColor,
  formatDuration,
  generateChartColors,
} from '@/utils/format';

const { Panel } = Collapse;

const Clustering: React.FC = () => {
  const { clusters, clusterSummary, loading, fetchClusters } = useAnalysisStore();

  useEffect(() => {
    fetchClusters();
  }, [fetchClusters]);

  const isLoading = loading.clusters || loading.fullReport;

  const clusterSizeDistribution = useMemo(() => {
    if (!clusters.length) return [];
    const sizeRanges = [
      { name: '1-10', min: 1, max: 10, count: 0 },
      { name: '11-50', min: 11, max: 50, count: 0 },
      { name: '51-100', min: 51, max: 100, count: 0 },
      { name: '101-500', min: 101, max: 500, count: 0 },
      { name: '500+', min: 501, max: Infinity, count: 0 },
    ];
    clusters.forEach((cluster) => {
      const range = sizeRanges.find(
        (r) => cluster.alertCount >= r.min && cluster.alertCount <= r.max
      );
      if (range) range.count++;
    });
    const colors = generateChartColors(sizeRanges.length);
    return sizeRanges.map((r, i) => ({
      name: r.name,
      value: r.count,
      color: colors[i],
    }));
  }, [clusters]);

  const ruleDistributionData = useMemo(() => {
    if (!clusterSummary?.ruleDistribution) return [];
    const entries = Object.entries(clusterSummary.ruleDistribution);
    const colors = generateChartColors(entries.length);
    return entries.map(([name, value], i) => ({
      name,
      value,
      color: colors[i],
    }));
  }, [clusterSummary]);

  const timelineData = useMemo(() => {
    if (!clusters.length) return [];
    return clusters.map((cluster) => ({
      time: cluster.timeSpan.start,
      value: cluster.alertCount,
    }));
  }, [clusters]);

  const getTimeSpanDuration = (cluster: AlertCluster) => {
    const durationMs = cluster.timeSpan.end - cluster.timeSpan.start;
    const durationSeconds = Math.floor(durationMs / 1000);
    return formatDuration(durationSeconds);
  };

  const renderPriorityTags = (distribution: Record<string, number>) => {
    return Object.entries(distribution).map(([priority, count]) => (
      <Tag
        key={priority}
        style={{
          backgroundColor: `${getPriorityColor(priority)}20`,
          color: getPriorityColor(priority),
          borderColor: `${getPriorityColor(priority)}40`,
        }}
      >
        {priority}: {count}
      </Tag>
    ));
  };

  const renderPatternFeatures = (features: Record<string, any>) => {
    const items = [];
    if (features.isPeriodic) {
      items.push({
        label: '周期性',
        value: features.period ? `每${formatDuration(features.period)}` : '是',
        color: '#10B981',
      });
    }
    if (features.timeDistribution) {
      const peakHour = Object.entries(features.timeDistribution).sort(
        (a, b) => (b[1] as number) - (a[1] as number)
      )[0];
      items.push({
        label: '高峰时段',
        value: `${peakHour[0]}:00`,
        color: '#F59E0B',
      });
    }
    if (features.severityScore !== undefined) {
      items.push({
        label: '严重度评分',
        value: (features.severityScore * 100).toFixed(0) + '%',
        color: '#EF4444',
      });
    }
    if (features.noiseScore !== undefined) {
      items.push({
        label: '噪声评分',
        value: (features.noiseScore * 100).toFixed(0) + '%',
        color: '#8B5CF6',
      });
    }
    return items;
  };

  const customExpandIcon = ({ isActive }: { isActive: boolean }) => (
    <Activity
      size={16}
      style={{
        transform: isActive ? 'rotate(180deg)' : 'rotate(0deg)',
        transition: 'transform 0.3s',
        color: '#64748B',
      }}
    />
  );

  return (
    <div className="min-h-screen p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100 mb-2 flex items-center gap-3">
            <GitBranch size={28} className="text-blue-500" />
            告警聚类分析
          </h1>
          <p className="text-gray-400 text-sm">
            通过智能聚类算法识别相似告警模式，帮助您发现隐藏的系统问题
          </p>
        </div>
        <button
          onClick={fetchClusters}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Refresh size={16} className={isLoading ? 'animate-spin' : ''} />
          刷新数据
        </button>
      </div>

      <Spin spinning={isLoading} tip="加载中...">
        <Row gutter={[16, 16]} className="mb-6">
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="聚类总数"
              value={clusterSummary?.totalClusters || 0}
              icon={<GitBranch size={24} />}
              color="#3B82F6"
              suffix="个"
              tooltip="识别到的告警聚类总数量"
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="聚类覆盖告警数"
              value={clusterSummary?.totalAlertsInClusters || 0}
              icon={<Bell size={24} />}
              color="#10B981"
              suffix="条"
              tooltip="被聚类覆盖的告警总数"
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="平均聚类大小"
              value={clusterSummary?.avgClusterSize || 0}
              icon={<Users size={24} />}
              color="#F59E0B"
              suffix="条/簇"
              tooltip="每个聚类平均包含的告警数量"
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="周期性聚类占比"
              value={clusterSummary?.periodicPercentage || 0}
              icon={<Clock size={24} />}
              color="#8B5CF6"
              suffix="%"
              progress={clusterSummary?.periodicPercentage || 0}
              tooltip="具有周期性特征的聚类占比"
            />
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="mb-6">
          <Col xs={24} lg={12}>
            <Card
              className="glass-card border-0"
              title={
                <div className="flex items-center gap-2">
                  <BarChart3 size={18} className="text-blue-500" />
                  <span className="text-gray-200 font-medium">聚类大小分布</span>
                </div>
              }
            >
              {clusterSizeDistribution.length > 0 ? (
                <BarChart
                  data={clusterSizeDistribution}
                  xAxisName="告警数量区间"
                  yAxisName="聚类数"
                  height={300}
                />
              ) : (
                <Empty description="暂无数据" className="py-8" />
              )}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card
              className="glass-card border-0"
              title={
                <div className="flex items-center gap-2">
                  <PieChartIcon size={18} className="text-purple-500" />
                  <span className="text-gray-200 font-medium">规则聚类分布</span>
                </div>
              }
            >
              {ruleDistributionData.length > 0 ? (
                <PieChart data={ruleDistributionData} type="donut" height={300} />
              ) : (
                <Empty description="暂无数据" className="py-8" />
              )}
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="mb-6">
          <Col span={24}>
            <Card
              className="glass-card border-0"
              title={
                <div className="flex items-center gap-2">
                  <Activity size={18} className="text-cyan-500" />
                  <span className="text-gray-200 font-medium">聚类时间线</span>
                </div>
              }
              extra={
                <Tag color="cyan" className="m-0">
                  按起始时间分布
                </Tag>
              }
            >
              {timelineData.length > 0 ? (
                <LineChart
                  data={timelineData}
                  color="#06B6D4"
                  height={250}
                  showArea={true}
                  smooth={false}
                />
              ) : (
                <Empty description="暂无数据" className="py-8" />
              )}
            </Card>
          </Col>
        </Row>

        <Card
          className="glass-card border-0"
          title={
            <div className="flex items-center gap-2">
              <GitBranch size={18} className="text-blue-500" />
              <span className="text-gray-200 font-medium">聚类详情列表</span>
              <Tag color="blue" className="ml-2">
                共 {clusters.length} 个聚类
              </Tag>
            </div>
          }
          extra={
            <Space>
              <Info size={16} className="text-gray-400" />
              <span className="text-gray-400 text-sm">点击展开查看详情</span>
            </Space>
          }
        >
          {clusters.length > 0 ? (
            <Collapse
              ghost
              expandIcon={customExpandIcon}
              className="cluster-collapse"
            >
              {clusters.map((cluster) => (
                <Panel
                  key={cluster.clusterId}
                  header={
                    <div className="flex items-center justify-between w-full py-2">
                      <div className="flex items-center gap-4 flex-wrap">
                        <Badge
                          count={cluster.alertCount}
                          showZero
                          color="#3B82F6"
                          offset={[0, 2]}
                        >
                          <span className="text-gray-200 font-medium ml-2">
                            {cluster.ruleName}
                          </span>
                        </Badge>
                        <Tag
                          color="default"
                          className="bg-gray-800 border-gray-700 text-gray-300"
                        >
                          <GitBranch size={12} className="mr-1 inline" />
                          {cluster.clusterId}
                        </Tag>
                        <div className="flex items-center gap-1 text-gray-400 text-sm">
                          <Server size={14} />
                          <span>{cluster.services.length} 个服务</span>
                        </div>
                        <div className="flex items-center gap-1 text-gray-400 text-sm">
                          <Calendar size={14} />
                          <span>{getTimeSpanDuration(cluster)}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {renderPriorityTags(cluster.priorityDistribution)}
                      </div>
                    </div>
                  }
                >
                  <div className="pl-6 pr-2">
                    <Row gutter={[16, 16]}>
                      <Col xs={24} lg={12}>
                        <Card
                          size="small"
                          className="bg-gray-900/50 border-gray-800"
                          title={
                            <div className="flex items-center gap-2 text-gray-300">
                              <AlertTriangle size={14} className="text-orange-500" />
                              样本告警 ({cluster.sampleAlerts.length})
                            </div>
                          }
                        >
                          <List
                            size="small"
                            dataSource={cluster.sampleAlerts.slice(0, 5)}
                            renderItem={(alert) => (
                              <List.Item className="border-b border-gray-800 py-2">
                                <div className="w-full">
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="text-gray-200 text-sm truncate flex-1">
                                      {alert.alarmMessage}
                                    </span>
                                    <Tag
                                      color={getPriorityColor(alert.priority)}
                                      className="ml-2 flex-shrink-0"
                                    >
                                      {alert.priority}
                                    </Tag>
                                  </div>
                                  <div className="flex items-center justify-between text-xs text-gray-500">
                                    <span>{alert.service}</span>
                                    <span>{formatTime(alert.startTime)}</span>
                                  </div>
                                </div>
                              </List.Item>
                            )}
                          />
                          {cluster.sampleAlerts.length > 5 && (
                            <div className="text-center text-gray-500 text-xs pt-2">
                              还有 {cluster.sampleAlerts.length - 5} 条更多告警...
                            </div>
                          )}
                        </Card>
                      </Col>
                      <Col xs={24} lg={12}>
                        <Card
                          size="small"
                          className="bg-gray-900/50 border-gray-800"
                          title={
                            <div className="flex items-center gap-2 text-gray-300">
                              <Activity size={14} className="text-green-500" />
                              模式特征
                            </div>
                          }
                        >
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-gray-400 text-sm">时间范围</span>
                              <span className="text-gray-200 text-sm">
                                {formatTime(cluster.timeSpan.start)} ~{' '}
                                {formatTime(cluster.timeSpan.end)}
                              </span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-gray-400 text-sm">涉及服务</span>
                              <div className="flex flex-wrap gap-1 justify-end">
                                {cluster.services.slice(0, 3).map((svc) => (
                                  <Tag
                                    key={svc}
                                    color="blue"
                                    className="bg-blue-900/30 text-blue-400 border-blue-800"
                                  >
                                    {svc}
                                  </Tag>
                                ))}
                                {cluster.services.length > 3 && (
                                  <Tag color="default">+{cluster.services.length - 3}</Tag>
                                )}
                              </div>
                            </div>
                            {renderPatternFeatures(cluster.patternFeatures).map(
                              (item, i) => (
                                <div
                                  key={i}
                                  className="flex items-center justify-between"
                                >
                                  <span className="text-gray-400 text-sm">
                                    {item.label}
                                  </span>
                                  <span
                                    className="text-sm font-medium"
                                    style={{ color: item.color }}
                                  >
                                    {item.value}
                                  </span>
                                </div>
                              )
                            )}
                            {cluster.patternFeatures.isPeriodic &&
                              cluster.patternFeatures.period && (
                                <div className="mt-3 p-3 bg-green-900/20 rounded-lg border border-green-800/30">
                                  <div className="text-green-400 text-sm font-medium mb-1">
                                    🔄 周期性告警检测
                                  </div>
                                  <p className="text-gray-400 text-xs">
                                    该聚类表现出明显的周期性特征，建议优化告警静默策略或检查定时任务配置。
                                  </p>
                                </div>
                              )}
                          </div>
                        </Card>
                      </Col>
                    </Row>
                  </div>
                </Panel>
              ))}
            </Collapse>
          ) : (
            <Empty
              description={
                <div className="text-gray-400">
                  <AlertTriangle size={48} className="mb-4 mx-auto text-gray-600" />
                  <p>暂无聚类数据</p>
                  <p className="text-sm text-gray-500 mt-2">
                    请确保系统已收集足够的告警数据
                  </p>
                </div>
              }
              className="py-16"
            />
          )}
        </Card>
      </Spin>
    </div>
  );
};

export default Clustering;
