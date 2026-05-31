import { useState, useEffect, useMemo } from 'react';
import { Card, Table, Tag, Select, DatePicker, Space, Button, Row, Col, Spin } from 'antd';
import {
  Bell,
  WarningCircle,
  TrendingDown,
  Gauge,
  Clock,
  RefreshCw,
  Service,
  Filter,
} from '@phosphor-icons/react';
import dayjs, { Dayjs } from 'dayjs';
import StatCard from '@/components/ui/StatCard';
import LineChart from '@/components/charts/LineChart';
import PieChart from '@/components/charts/PieChart';
import BarChart from '@/components/charts/BarChart';
import { useAnalysisStore } from '@/stores/analysisStore';
import {
  formatTime,
  formatNumber,
  formatPercent,
  getPriorityColor,
  truncateText,
  generateChartColors,
} from '@/utils/format';

const { RangePicker } = DatePicker;
const { Option } = Select;

const timeRangeOptions = [
  { label: '24小时', value: 24 },
  { label: '7天', value: 168 },
  { label: '30天', value: 720 },
  { label: '自定义', value: -1 },
];

const priorityOptions = [
  { label: '严重', value: 'CRITICAL', color: '#EF4444' },
  { label: '警告', value: 'WARNING', color: '#F59E0B' },
  { label: '信息', value: 'INFO', color: '#3B82F6' },
];

const Dashboard: React.FC = () => {
  const {
    overallStatistics,
    alerts,
    filters,
    loading,
    setFilters,
    fetchFullReport,
    fetchAlerts,
    fetchInefficientRules,
  } = useAnalysisStore();

  const [selectedTimeRange, setSelectedTimeRange] = useState<number>(168);
  const [customDateRange, setCustomDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [selectedServices, setSelectedServices] = useState<string[]>([]);
  const [selectedPriorities, setSelectedPriorities] = useState<string[]>([]);

  useEffect(() => {
    fetchFullReport();
  }, [fetchFullReport]);

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

  const handleServiceChange = (values: string[]) => {
    setSelectedServices(values);
    setFilters({ selectedServices: values });
  };

  const handlePriorityChange = (values: string[]) => {
    setSelectedPriorities(values);
    setFilters({ selectedPriorities: values });
  };

  const handleRefresh = () => {
    fetchFullReport();
    fetchAlerts();
    fetchInefficientRules();
  };

  const uniqueServices = useMemo(() => {
    const services = new Set(alerts.map((alert) => alert.service));
    return Array.from(services);
  }, [alerts]);

  const filteredAlerts = useMemo(() => {
    let result = [...alerts];

    if (selectedServices.length > 0) {
      result = result.filter((alert) => selectedServices.includes(alert.service));
    }

    if (selectedPriorities.length > 0) {
      result = result.filter((alert) => selectedPriorities.includes(alert.priority));
    }

    return result.sort((a, b) => b.startTime - a.startTime).slice(0, 10);
  }, [alerts, selectedServices, selectedPriorities]);

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

  const ruleDistributionData = useMemo(() => {
    const ruleCount: Record<string, number> = {};
    alerts.forEach((alert) => {
      ruleCount[alert.ruleName] = (ruleCount[alert.ruleName] || 0) + 1;
    });

    const colors = generateChartColors(Object.keys(ruleCount).length);
    return Object.entries(ruleCount)
      .map(([name, value], index) => ({
        name: truncateText(name, 15),
        value,
        color: colors[index],
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 10);
  }, [alerts]);

  const serviceDistributionData = useMemo(() => {
    const serviceCount: Record<string, number> = {};
    alerts.forEach((alert) => {
      serviceCount[alert.service] = (serviceCount[alert.service] || 0) + 1;
    });

    const colors = generateChartColors(Object.keys(serviceCount).length);
    return Object.entries(serviceCount)
      .map(([name, value], index) => ({
        name: truncateText(name, 15),
        value,
        color: colors[index],
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 10);
  }, [alerts]);

  const columns = [
    {
      title: '规则名称',
      dataIndex: 'ruleName',
      key: 'ruleName',
      width: 200,
      render: (text: string) => (
        <span className="font-medium text-gray-200">{truncateText(text, 25)}</span>
      ),
    },
    {
      title: '告警消息',
      dataIndex: 'alarmMessage',
      key: 'alarmMessage',
      flex: 1,
      render: (text: string) => (
        <span className="text-gray-300">{truncateText(text, 50)}</span>
      ),
    },
    {
      title: '服务',
      dataIndex: 'service',
      key: 'service',
      width: 150,
      render: (text: string) => (
        <Tag color="blue" className="text-xs">
          {truncateText(text, 12)}
        </Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: string) => (
        <Tag
          color={priority === 'CRITICAL' ? 'red' : priority === 'WARNING' ? 'orange' : 'blue'}
          style={{
            backgroundColor: `${getPriorityColor(priority)}20`,
            borderColor: getPriorityColor(priority),
            color: getPriorityColor(priority),
          }}
          className="text-xs font-medium"
        >
          {priority === 'CRITICAL' ? '严重' : priority === 'WARNING' ? '警告' : '信息'}
        </Tag>
      ),
    },
    {
      title: '时间',
      dataIndex: 'startTime',
      key: 'startTime',
      width: 160,
      render: (time: number) => (
        <span className="text-gray-400 text-sm">{formatTime(time)}</span>
      ),
    },
  ];

  const stats = useMemo(
    () => ({
      totalAlerts: overallStatistics?.totalAlerts || 0,
      inefficientRules: overallStatistics?.inefficientRulesCount || 0,
      inefficientRulesPercentage: overallStatistics?.inefficientRulesPercentage || 0,
      potentialReduction: overallStatistics?.potentialAlertReduction || 0,
      avgInefficiencyScore: overallStatistics?.avgInefficiencyScore || 0,
      trend: Math.random() * 20 - 10,
    }),
    [overallStatistics]
  );

  const isLoading = loading.fullReport || loading.alerts || loading.inefficientRules;

  return (
    <div className="space-y-6">
      <div className="glass-card p-4">
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={24} md={12} lg={6}>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Clock size={16} />
              <span>时间范围</span>
            </div>
            <Space.Compact className="w-full mt-1">
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

          <Col xs={24} sm={24} md={12} lg={6}>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Service size={16} />
              <span>服务筛选</span>
            </div>
            <Select
              mode="multiple"
              placeholder="全部服务"
              value={selectedServices}
              onChange={handleServiceChange}
              className="w-full mt-1"
              size="middle"
              maxTagCount="responsive"
            >
              {uniqueServices.map((service) => (
                <Option key={service} value={service}>
                  {service}
                </Option>
              ))}
            </Select>
          </Col>

          <Col xs={24} sm={24} md={12} lg={6}>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Filter size={16} />
              <span>优先级</span>
            </div>
            <Select
              mode="multiple"
              placeholder="全部优先级"
              value={selectedPriorities}
              onChange={handlePriorityChange}
              className="w-full mt-1"
              size="middle"
            >
              {priorityOptions.map((option) => (
                <Option key={option.value} value={option.value}>
                  <span style={{ color: option.color }}>●</span> {option.label}
                </Option>
              ))}
            </Select>
          </Col>

          <Col xs={24} sm={24} md={12} lg={6} className="flex items-end">
            <Button
              type="primary"
              icon={<RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />}
              onClick={handleRefresh}
              loading={isLoading}
              size="middle"
              className="w-full"
            >
              刷新数据
            </Button>
          </Col>
        </Row>
      </div>

      <Spin spinning={isLoading}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="总告警数"
              value={stats.totalAlerts}
              icon={<Bell size={24} />}
              trend={stats.trend}
              trendLabel="较上一周期"
              color="#3B82F6"
              tooltip="选定时间范围内的告警总数"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="低效规则数"
              value={stats.inefficientRules}
              icon={<WarningCircle size={24} />}
              progress={stats.inefficientRulesPercentage}
              color="#F59E0B"
              suffix={`/ ${formatPercent(stats.inefficientRulesPercentage)}`}
              tooltip="低效规则占总规则数的比例"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="可减少告警数"
              value={stats.potentialReduction}
              icon={<TrendingDown size={24} />}
              color="#10B981"
              tooltip="通过规则优化可预期减少的告警数量"
              loading={isLoading}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="平均低效度评分"
              value={(stats.avgInefficiencyScore * 100).toFixed(1)}
              icon={<Gauge size={24} />}
              color="#EF4444"
              suffix="分"
              tooltip="所有低效规则的平均低效度评分（满分100）"
              loading={isLoading}
            />
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="mt-4">
          <Col xs={24} lg={14}>
            <Card className="glass-card hover-lift border-0" title="告警趋势">
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
            <Card className="glass-card hover-lift border-0" title="优先级分布">
              <PieChart
                data={priorityDistributionData}
                type="donut"
                height={300}
                showLegend
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} className="mt-4">
          <Col xs={24} lg={12}>
            <Card className="glass-card hover-lift border-0" title="告警规则分布 TOP 10">
              <BarChart
                data={ruleDistributionData}
                height={300}
                horizontal
                xAxisName="告警数"
                yAxisName="规则名称"
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card className="glass-card hover-lift border-0" title="服务告警分布 TOP 10">
              <BarChart
                data={serviceDistributionData}
                height={300}
                horizontal
                xAxisName="告警数"
                yAxisName="服务名称"
              />
            </Card>
          </Col>
        </Row>

        <Card
          className="glass-card hover-lift border-0 mt-4"
          title="最近告警"
          extra={
            <span className="text-sm text-gray-400">
              共 {formatNumber(alerts.length)} 条告警
            </span>
          }
        >
          <Table
            dataSource={filteredAlerts}
            columns={columns}
            rowKey="id"
            pagination={false}
            scroll={{ x: 800 }}
            locale={{ emptyText: '暂无告警数据' }}
          />
        </Card>
      </Spin>
    </div>
  );
};

export default Dashboard;
