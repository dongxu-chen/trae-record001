import { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Typography,
  Table,
  Tag,
  Progress,
  Space,
  Tooltip,
  Badge,
  Timeline,
  Alert,
  Button,
  Modal,
  Form,
  Input,
  DatePicker,
  message,
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  ApiOutlined,
  TagOutlined,
  StopOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import type { ColumnsType } from 'antd/es/table';
import {
  TrendingUp,
  Users,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';
import dayjs from 'dayjs';
import type { VersionCallStat, DeprecatedVersionSchedule, VersionStatsData } from '../types';
import statsApi from '../api/statsApi';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { TextArea } = Input;

export default function Dashboard() {
  const [versionStats, setVersionStats] = useState<VersionStatsData | null>(null);
  const [deprecatedVersions, setDeprecatedVersions] = useState<DeprecatedVersionSchedule[]>([]);
  const [loading, setLoading] = useState(false);
  const [scheduleModalVisible, setScheduleModalVisible] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<DeprecatedVersionSchedule | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [stats, deprecated] = await Promise.all([
        statsApi.getVersionStats(),
        statsApi.getDeprecatedVersions(),
      ]);
      setVersionStats(stats);
      setDeprecatedVersions(deprecated);
    } catch (error) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEditSchedule = (record: DeprecatedVersionSchedule) => {
    setEditingSchedule(record);
    form.setFieldsValue({
      plannedRetireTime: record.plannedRetireTime ? dayjs(record.plannedRetireTime) : null,
      deprecationMessage: record.deprecationMessage,
    });
    setScheduleModalVisible(true);
  };

  const handleSaveSchedule = async () => {
    if (!editingSchedule) return;

    try {
      const values = await form.validateFields();
      await statsApi.updateDeprecationSchedule(editingSchedule.id, {
        plannedRetireTime: values.plannedRetireTime.toISOString(),
        deprecationMessage: values.deprecationMessage,
      });
      message.success('废弃时间表已更新');
      setScheduleModalVisible(false);
      loadData();
    } catch (error) {
      message.error('保存失败');
    }
  };

  const handleSyncConfig = async (id: string) => {
    try {
      await statsApi.syncDeprecationConfig(id);
      message.success('配置已同步到网关');
    } catch (error) {
      message.error('同步失败');
    }
  };

  const getVersionTrafficPieOption = (): EChartsOption => {
    if (!versionStats) {
      return {
        title: {
          text: '版本调用量占比',
          left: 'center',
        },
        series: [],
      };
    }

    const data = versionStats.versions.map((v) => ({
      value: v.callCount,
      name: `${v.serviceName} ${v.version}`,
      percentage: v.percentage,
    }));

    return {
      title: {
        text: '版本流量占比',
        left: 'center',
        textStyle: { fontSize: 16, fontWeight: 500 },
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          const stat = versionStats.versions[params.dataIndex];
          return `${params.name}<br/>调用量: ${params.value.toLocaleString()}次<br/>占比: ${params.percent}%<br/>成功率: ${((stat.successCount / stat.callCount) * 100).toFixed(2)}%<br/>平均响应: ${stat.avgResponseTime}ms`;
        },
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
      },
      series: [
        {
          name: '流量占比',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['40%', '55%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            show: false,
            position: 'center',
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 20,
              fontWeight: 'bold',
              formatter: '{b}\n{d}%',
            },
          },
          labelLine: {
            show: false,
          },
          data,
        },
      ],
    };
  };

  const getVersionTrendOption = (): EChartsOption => {
    if (!versionStats) {
      return {
        title: {
          text: '近7日版本调用趋势',
          left: 'center',
        },
        xAxis: { type: 'category', data: [] },
        yAxis: { type: 'value' },
        series: [],
      };
    }

    const { trendData } = versionStats;
    const versions = Object.keys(trendData.versions);
    const colors = ['#1890ff', '#52c41a', '#fa8c16', '#722ed1', '#eb2f96'];

    return {
      title: {
        text: '近7日版本调用趋势',
        left: 'center',
        textStyle: { fontSize: 16, fontWeight: 500 },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      legend: {
        data: versions,
        bottom: 10,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: trendData.dates,
      },
      yAxis: {
        type: 'value',
        name: '请求数',
      },
      series: versions.map((version, index) => ({
        name: version,
        type: 'line',
        smooth: true,
        data: trendData.versions[version],
        itemStyle: { color: colors[index % colors.length] },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: `${colors[index % colors.length]}4d` },
              { offset: 1, color: `${colors[index % colors.length]}0d` },
            ],
          },
        },
      })),
    };
  };

  const deprecationColumns: ColumnsType<DeprecatedVersionSchedule> = [
    {
      title: '服务名称',
      dataIndex: 'serviceName',
      key: 'serviceName',
      width: 120,
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '版本号',
      dataIndex: 'version',
      key: 'version',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const color = status === 'OFFLINE' ? 'default' : 'warning';
        const text = status === 'OFFLINE' ? '已下线' : '已废弃';
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '废弃时间',
      dataIndex: 'deprecateTime',
      key: 'deprecateTime',
      width: 160,
      render: (text) => text ? dayjs(text).format('YYYY-MM-DD') : '-',
    },
    {
      title: '计划下线时间',
      dataIndex: 'plannedRetireTime',
      key: 'plannedRetireTime',
      width: 160,
      render: (text, record) => {
        if (!text) return '-';
        const days = record.daysRemaining || 0;
        let color = '#52c41a';
        if (days <= 0) color = '#ff4d4f';
        else if (days <= 30) color = '#faad14';

        return (
          <Space>
            <span>{dayjs(text).format('YYYY-MM-DD')}</span>
            {days !== undefined && (
              <Tag color={days <= 0 ? 'error' : days <= 30 ? 'warning' : 'success'}>
                {days <= 0 ? `已超期${Math.abs(days)}天` : `剩余${days}天`}
              </Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: '提示信息',
      dataIndex: 'deprecationMessage',
      key: 'deprecationMessage',
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <span>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<SettingOutlined />}
            onClick={() => handleEditSchedule(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={<SyncOutlined />}
            onClick={() => handleSyncConfig(record.id)}
          >
            同步
          </Button>
        </Space>
      ),
    },
  ];

  const overviewData = {
    activeVersions: versionStats?.versions?.filter(v => !v.version.includes('deprecated')).length || 5,
    deprecatedVersions: deprecatedVersions.length,
    totalCalls: versionStats?.totalCalls?.toLocaleString() || '355,500',
    callGrowth: 15,
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <Title level={3} style={{ marginBottom: 24 }}>版本管理仪表盘</Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="活跃版本数"
              value={overviewData.activeVersions}
              prefix={<TagOutlined />}
              valueStyle={{ color: '#3f8600' }}
              suffix={
                <span style={{ fontSize: 14, color: '#3f8600' }}>
                  <ArrowUpOutlined /> {overviewData.callGrowth}%
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="废弃版本数"
              value={overviewData.deprecatedVersions}
              prefix={<StopOutlined />}
              valueStyle={{ color: '#cf1322' }}
              suffix={
                <span style={{ fontSize: 14, color: '#cf1322' }}>
                  <ClockCircleOutlined /> 待处理
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总调用量"
              value={overviewData.totalCalls}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#1890ff' }}
              suffix={
                <span style={{ fontSize: 14, color: '#3f8600' }}>
                  <TrendingUp size={14} />
                </span>
              }
            />
          </Card>
        </Col>
      </Row>

      {deprecatedVersions.some(v => v.daysRemaining !== undefined && v.daysRemaining <= 7 && v.daysRemaining > 0) && (
        <Alert
          message={
            <Space>
              <WarningOutlined />
              <span>警告：有版本将在7天内下线，请及时处理升级！</span>
            </Space>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" type="primary" onClick={() => document.getElementById('deprecation-table')?.scrollIntoView({ behavior: 'smooth' })}>
              查看详情
            </Button>
          }
        />
      )}

      {deprecatedVersions.some(v => v.daysRemaining !== undefined && v.daysRemaining <= 0) && (
        <Alert
          message={
            <Space>
              <AlertTriangle size={16} style={{ color: '#ff4d4f' }} />
              <span>紧急：有版本已超期下线，所有请求将被拦截！</span>
            </Space>
          }
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" danger onClick={() => document.getElementById('deprecation-table')?.scrollIntoView({ behavior: 'smooth' })}>
              立即处理
            </Button>
          }
        />
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={14}>
          <Card loading={loading}>
            <ReactECharts
              option={getVersionTrendOption()}
              style={{ height: 400 }}
              opts={{ renderer: 'canvas' }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card loading={loading}>
            <ReactECharts
              option={getVersionTrafficPieOption()}
              style={{ height: 400 }}
              opts={{ renderer: 'canvas' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <Users size={16} />
                各版本调用统计
              </Space>
            }
            loading={loading}
          >
            {versionStats && (
              <Table
                dataSource={versionStats.versions}
                pagination={false}
                size="small"
                rowKey="version"
              >
                <Table.Column
                  title="版本"
                  key="version"
                  render={(_, record: VersionCallStat) => (
                    <Space>
                      <Tag color="blue">{record.serviceName}</Tag>
                      <span>{record.version}</span>
                    </Space>
                  )}
                />
                <Table.Column
                  title="调用量"
                  dataIndex="callCount"
                  key="callCount"
                  render={(text) => text?.toLocaleString()}
                />
                <Table.Column
                  title="成功率"
                  key="successRate"
                  render={(_, record: VersionCallStat) => {
                    const rate = record.callCount > 0 ? (record.successCount / record.callCount) * 100 : 0;
                    return (
                      <Progress
                        percent={Number(rate.toFixed(1))}
                        size="small"
                        strokeColor={rate >= 99 ? '#52c41a' : rate >= 95 ? '#faad14' : '#ff4d4f'}
                      />
                    );
                  }}
                />
                <Table.Column
                  title="平均响应"
                  dataIndex="avgResponseTime"
                  key="avgResponseTime"
                  render={(text) => `${text}ms`}
                />
                <Table.Column
                  title="占比"
                  dataIndex="percentage"
                  key="percentage"
                  render={(text) => `${text?.toFixed(1)}%`}
                />
              </Table>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <Badge status="processing" color="green" />
                版本生命周期
              </Space>
            }
          >
            <Timeline
              mode="left"
              items={[
                {
                  color: 'blue',
                  children: (
                    <div>
                      <Text strong>DRAFT - 草稿</Text>
                      <div style={{ color: '#888', fontSize: 12 }}>版本开发中，可编辑修改</div>
                    </div>
                  ),
                },
                {
                  color: 'green',
                  children: (
                    <div>
                      <Text strong>PUBLISHED - 已发布</Text>
                      <div style={{ color: '#888', fontSize: 12 }}>正式对外提供服务</div>
                    </div>
                  ),
                },
                {
                  color: 'gold',
                  children: (
                    <div>
                      <Text strong>DEPRECATED - 已废弃</Text>
                      <div style={{ color: '#888', fontSize: 12 }}>设置下线时间表，通知客户端升级</div>
                    </div>
                  ),
                },
                {
                  color: 'red',
                  children: (
                    <div>
                      <Text strong>OFFLINE - 已下线</Text>
                      <div style={{ color: '#888', fontSize: 12 }}>超期后网关自动拦截所有请求</div>
                    </div>
                  ),
                },
              ]}
            />

            <div style={{ marginTop: 16, padding: 12, background: '#fafafa', borderRadius: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                <CheckCircle size={12} style={{ marginRight: 4, color: '#52c41a' }} />
                废弃版本会在响应头中添加 X-API-Deprecation-Warning 提示客户端升级
              </Text>
              <div style={{ marginTop: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  <StopOutlined style={{ marginRight: 4, color: '#ff4d4f' }} />
                  超期版本网关返回 410 Gone 状态码，拒绝服务
                </Text>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Card
        id="deprecation-table"
        title={
          <Space>
            <WarningOutlined style={{ color: '#faad14' }} />
            API废弃时间表
            <Badge count={deprecatedVersions.length} color="#faad14" />
          </Space>
        }
        extra={
          <Button icon={<SyncOutlined />} onClick={loadData} loading={loading}>
            刷新
          </Button>
        }
        loading={loading}
      >
        <Table
          dataSource={deprecatedVersions}
          columns={deprecationColumns}
          pagination={false}
          rowKey="id"
          rowClassName={(record) =>
            record.daysRemaining !== undefined && record.daysRemaining <= 0 ? 'bg-red-50' :
            record.daysRemaining !== undefined && record.daysRemaining <= 7 ? 'bg-yellow-50' : ''
          }
        />
      </Card>

      <Modal
        title="编辑废弃时间表"
        open={scheduleModalVisible}
        onOk={handleSaveSchedule}
        onCancel={() => setScheduleModalVisible(false)}
        okText="保存"
        cancelText="取消"
      >
        {editingSchedule && (
          <div style={{ marginBottom: 16 }}>
            <Tag color="blue">{editingSchedule.serviceName}</Tag>
            <Text strong>{editingSchedule.version}</Text>
          </div>
        )}
        <Form form={form} layout="vertical">
          <Form.Item
            name="plannedRetireTime"
            label="计划下线时间"
            rules={[{ required: true, message: '请选择计划下线时间' }]}
          >
            <DatePicker
              style={{ width: '100%' }}
              showTime
              format="YYYY-MM-DD HH:mm:ss"
              placeholder="选择计划下线时间"
            />
          </Form.Item>
          <Form.Item
            name="deprecationMessage"
            label="废弃提示信息"
            rules={[{ required: true, message: '请输入废弃提示信息' }]}
          >
            <TextArea
              rows={4}
              placeholder="请输入客户端升级提示信息，例如：该版本将于30天后下线，请尽快升级到v2.0.0版本"
            />
          </Form.Item>
        </Form>
      </Modal>

      <style>{`
        .bg-red-50 { background-color: #fff2f0 !important; }
        .bg-yellow-50 { background-color: #fffbe6 !important; }
      `}</style>
    </div>
  );
}
