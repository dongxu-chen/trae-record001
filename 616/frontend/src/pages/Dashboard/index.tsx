import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Table, Tag, Button, Space, Spin } from 'antd'
import {
  RiseOutlined,
  ClockCircleOutlined,
  PlusCircleOutlined,
  CheckCircleOutlined,
  InboxOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useNavigate } from 'react-router-dom'
import {
  getDashboardStats,
  getTrendData,
  getReasonPieData,
  getMqTypePieData,
  getRecentDeadLetters,
} from '@/services/api'
import type { DashboardStats, TrendData, PieData, DeadLetterMessage } from '@/types'
import type { DeadReasonTypeEnum, MqTypeEnum, ProcessStatusEnum } from '@/types'

const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [trendData, setTrendData] = useState<TrendData[]>([])
  const [reasonPieData, setReasonPieData] = useState<PieData[]>([])
  const [mqTypePieData, setMqTypePieData] = useState<PieData[]>([])
  const [recentList, setRecentList] = useState<DeadLetterMessage[]>([])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [statsRes, trendRes, reasonRes, mqTypeRes, recentRes] = await Promise.all([
        getDashboardStats(),
        getTrendData(7),
        getReasonPieData(),
        getMqTypePieData(),
        getRecentDeadLetters(10),
      ])
      setStats(statsRes)
      setTrendData(trendRes)
      setReasonPieData(reasonRes)
      setMqTypePieData(mqTypeRes)
      setRecentList(recentRes)
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      setStats({
        totalCount: 0,
        pendingCount: 0,
        todayNewCount: 0,
        replayedCount: 0,
        archivedCount: 0,
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const getTrendChartOption = () => ({
    tooltip: {
      trigger: 'axis',
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trendData.map((item) => item.date),
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        name: '死信数量',
        type: 'line',
        smooth: true,
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
              { offset: 1, color: 'rgba(24, 144, 255, 0.05)' },
            ],
          },
        },
        lineStyle: {
          color: '#1890ff',
          width: 2,
        },
        itemStyle: {
          color: '#1890ff',
        },
        data: trendData.map((item) => item.count),
      },
    ],
  })

  const getPieChartOption = (data: PieData[], title: string, colors: string[]) => ({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      left: 'left',
    },
    color: colors,
    series: [
      {
        name: title,
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: '{b}: {c}',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold',
          },
        },
        data: data,
      },
    ],
  })

  const getReasonTypeColor = (type: DeadReasonTypeEnum) => {
    const colorMap: Record<string, string> = {
      BIZ_EXCEPTION: 'red',
      TIMEOUT: 'orange',
      REJECTED: 'gold',
      FORMAT_ERROR: 'purple',
      NULL_POINTER: 'magenta',
      DATABASE_ERROR: 'volcano',
      OTHER: 'default',
    }
    return colorMap[type] || 'default'
  }

  const getReasonTypeName = (type: DeadReasonTypeEnum) => {
    const nameMap: Record<string, string> = {
      BIZ_EXCEPTION: '业务异常',
      TIMEOUT: '超时异常',
      REJECTED: '被拒绝',
      FORMAT_ERROR: '格式错误',
      NULL_POINTER: '空指针',
      DATABASE_ERROR: '数据库错误',
      OTHER: '其他',
    }
    return nameMap[type] || type
  }

  const getMqTypeName = (type: MqTypeEnum) => {
    const nameMap: Record<string, string> = {
      RABBITMQ: 'RabbitMQ',
      ROCKETMQ: 'RocketMQ',
      KAFKA: 'Kafka',
    }
    return nameMap[type] || type
  }

  const getStatusColor = (status: ProcessStatusEnum) => {
    const colorMap: Record<string, string> = {
      PENDING: 'processing',
      REPLAYED: 'success',
      ARCHIVED: 'default',
      IGNORED: 'warning',
    }
    return colorMap[status] || 'default'
  }

  const getStatusName = (status: ProcessStatusEnum) => {
    const nameMap: Record<string, string> = {
      PENDING: '待处理',
      REPLAYED: '已重放',
      ARCHIVED: '已归档',
      IGNORED: '已忽略',
    }
    return nameMap[status] || status
  }

  const columns = [
    {
      title: '消息ID',
      dataIndex: 'messageId',
      key: 'messageId',
      ellipsis: true,
      width: 180,
      render: (text: string) => <span style={{ fontFamily: 'monospace' }}>{text}</span>,
    },
    {
      title: 'MQ类型',
      dataIndex: 'mqType',
      key: 'mqType',
      width: 100,
      render: (text: MqTypeEnum) => <Tag>{getMqTypeName(text)}</Tag>,
    },
    {
      title: 'Topic',
      dataIndex: 'topic',
      key: 'topic',
      ellipsis: true,
      width: 150,
    },
    {
      title: '原因类型',
      dataIndex: 'deadReasonType',
      key: 'deadReasonType',
      width: 100,
      render: (type: DeadReasonTypeEnum) => (
        <Tag color={getReasonTypeColor(type)}>{getReasonTypeName(type)}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'processStatus',
      key: 'processStatus',
      width: 90,
      render: (status: ProcessStatusEnum) => (
        <Tag color={getStatusColor(status)}>{getStatusName(status)}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      key: 'createTime',
      width: 170,
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, record: DeadLetterMessage) => (
        <Button type="link" size="small" onClick={() => navigate(`/dead-letter/${record.id}`)}>
          详情
        </Button>
      ),
    },
  ]

  const statCards = stats ? [
    { title: '总死信数', value: stats.totalCount, icon: <InboxOutlined style={{ color: '#722ed1' }} />, color: '#722ed1' },
    { title: '待处理数', value: stats.pendingCount, icon: <ClockCircleOutlined style={{ color: '#fa8c16' }} />, color: '#fa8c16' },
    { title: '今日新增', value: stats.todayNewCount, icon: <PlusCircleOutlined style={{ color: '#1890ff' }} />, color: '#1890ff' },
    { title: '已重放数', value: stats.replayedCount, icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />, color: '#52c41a' },
    { title: '已归档数', value: stats.archivedCount, icon: <RiseOutlined style={{ color: '#13c2c2' }} />, color: '#13c2c2' },
  ] : []

  return (
    <Spin spinning={loading}>
      <Row gutter={[16, 16]}>
        {statCards.map((stat, index) => (
          <Col xs={24} sm={12} md={8} lg={24 / 5} key={index}>
            <Card>
              <Statistic
                title={
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {stat.icon}
                    {stat.title}
                  </span>
                }
                value={stat.value}
                valueStyle={{ color: stat.color }}
              />
            </Card>
          </Col>
        ))}

        <Col xs={24} lg={12}>
          <Card
            title="最近7天死信趋势"
            extra={
              <Button type="link" size="small" onClick={() => navigate('/dead-letter')}>
                查看全部 <ArrowRightOutlined />
              </Button>
            }
          >
            <ReactECharts option={getTrendChartOption()} style={{ height: 300 }} />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Card title="死信原因分布">
                <ReactECharts
                  option={getPieChartOption(reasonPieData, '原因分布', [
                    '#f5222d',
                    '#fa8c16',
                    '#faad14',
                    '#722ed1',
                    '#eb2f96',
                    '#fa541c',
                    '#8c8c8c',
                  ])}
                  style={{ height: 280 }}
                />
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card title="MQ类型分布">
                <ReactECharts
                  option={getPieChartOption(mqTypePieData, 'MQ类型', ['#1890ff', '#52c41a', '#fa8c16'])}
                  style={{ height: 280 }}
                />
              </Card>
            </Col>
          </Row>
        </Col>

        <Col xs={24}>
          <Card
            title="最近死信列表"
            extra={
              <Space>
                <Button type="link" size="small" onClick={() => navigate('/dead-letter')}>
                  查看全部 <ArrowRightOutlined />
                </Button>
              </Space>
            }
          >
            <Table
              columns={columns}
              dataSource={recentList}
              rowKey="id"
              pagination={false}
              size="middle"
              scroll={{ x: 800 }}
            />
          </Card>
        </Col>
      </Row>
    </Spin>
  )
}

export default Dashboard
