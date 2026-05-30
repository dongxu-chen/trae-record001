import { useEffect, useState } from 'react'
import { Card, Table, Row, Col, Tag, Spin, Statistic, Progress, Radio, Segmented, Select, Space, Alert } from 'antd'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts'
import { statsApi, ruleApi } from '../services/api'

const COLORS = ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16']

const GRANULARITY_OPTIONS = [
  { label: '按分钟', value: 'minute', desc: '最近120分钟' },
  { label: '按小时', value: 'hour', desc: '最近24小时' },
  { label: '按天', value: 'day', desc: '最近30天' },
]

const ACTION_LABELS = { PASS: '通过', REVIEW: '审核', REJECT: '拒绝', BLOCK: '阻断' }

export default function HitAnalysis() {
  const [loading, setLoading] = useState(true)
  const [hitStats, setHitStats] = useState([])
  const [actionCounts, setActionCounts] = useState({})
  const [granularity, setGranularity] = useState('hour')
  const [timeSeriesData, setTimeSeriesData] = useState(null)
  const [selectedRules, setSelectedRules] = useState([])
  const [allRules, setAllRules] = useState([])
  const [chartMode, setChartMode] = useState('bar')

  useEffect(() => {
    loadBasicData()
  }, [])

  useEffect(() => {
    if (selectedRules.length > 0) {
      loadTimeSeriesData()
    }
  }, [granularity, selectedRules])

  const loadBasicData = async () => {
    try {
      setLoading(true)
      const [hitData, actionData, ruleData] = await Promise.all([
        statsApi.getHitStats(),
        statsApi.getActionCounts(),
        ruleApi.getAll(),
      ])
      setHitStats(hitData || [])
      setActionCounts(actionData || {})
      setAllRules(ruleData || [])
      if (ruleData && ruleData.length > 0) {
        setSelectedRules(ruleData.slice(0, 5).map(r => r.ruleCode))
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const loadTimeSeriesData = async () => {
    try {
      const data = await statsApi.getHitStatsByGranularity(granularity, selectedRules)
      setTimeSeriesData(data)
    } catch (e) {
      console.error(e)
    }
  }

  const handleGranularityChange = (val) => {
    setGranularity(val)
  }

  const buildLineChartData = () => {
    if (!timeSeriesData) return []
    const { labels, datasets } = timeSeriesData
    return labels.map((label, idx) => {
      const point = { time: label }
      datasets.forEach(ds => {
        point[ds.ruleCode] = ds.data[idx]
      })
      return point
    })
  }

  const buildBarChartData = () => {
    if (!timeSeriesData || !timeSeriesData.series) return []
    return timeSeriesData.series.map(s => ({
      name: s.ruleCode,
      命中次数: s.total,
    }))
  }

  const columns = [
    {
      title: '规则编码',
      dataIndex: 'ruleCode',
      key: 'ruleCode',
      width: 180,
      render: (text) => <span style={{ fontFamily: 'monospace', color: '#1677ff' }}>{text}</span>,
    },
    {
      title: '总事件数',
      dataIndex: 'totalEvents',
      key: 'totalEvents',
      width: 120,
      sorter: (a, b) => a.totalEvents - b.totalEvents,
    },
    {
      title: '命中次数',
      dataIndex: 'hitCount',
      key: 'hitCount',
      width: 120,
      sorter: (a, b) => a.hitCount - b.hitCount,
    },
    {
      title: '命中率',
      dataIndex: 'hitRate',
      key: 'hitRate',
      width: 200,
      sorter: (a, b) => a.hitRate - b.hitRate,
      render: (rate) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Progress
            percent={Number(rate).toFixed(1)}
            size="small"
            style={{ width: 100, marginBottom: 0 }}
            strokeColor={rate > 50 ? '#ff4d4f' : rate > 20 ? '#faad14' : '#52c41a'}
          />
          <span style={{ fontSize: 12, color: '#666' }}>{Number(rate).toFixed(2)}%</span>
        </div>
      ),
    },
    {
      title: '平均风险分',
      dataIndex: 'avgRiskScore',
      key: 'avgRiskScore',
      width: 120,
      sorter: (a, b) => a.avgRiskScore - b.avgRiskScore,
      render: (score) => (
        <Tag color={score > 200 ? 'red' : score > 100 ? 'orange' : 'green'}>
          {Number(score).toFixed(1)}
        </Tag>
      ),
    },
  ]

  const pieData = Object.entries(actionCounts).map(([key, value]) => ({
    name: ACTION_LABELS[key] || key,
    value: value,
  }))

  const totalHits = hitStats.reduce((sum, s) => sum + s.hitCount, 0)
  const totalEvents = hitStats.length > 0 ? hitStats[0].totalEvents : 0
  const avgHitRate = totalEvents > 0 ? ((totalHits / totalEvents) * 100).toFixed(2) : 0

  const granConfig = GRANULARITY_OPTIONS.find(g => g.value === granularity)

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="总命中次数" value={totalHits} valueStyle={{ color: '#1677ff' }} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="总事件数" value={totalEvents} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="平均命中率"
              value={avgHitRate}
              suffix="%"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        style={{ marginTop: 16 }}
        title={
          <Space>
            <span>时间序列趋势</span>
            <Tag color="blue">{granConfig?.label} · {granConfig?.desc}</Tag>
          </Space>
        }
        extra={
          <Space>
            <Select
              mode="multiple"
              style={{ minWidth: 300 }}
              placeholder="选择要对比的规则"
              value={selectedRules}
              onChange={setSelectedRules}
              options={allRules.map(r => ({ label: r.ruleName, value: r.ruleCode }))}
              maxTagCount={5}
            />
            <Segmented
              options={GRANULARITY_OPTIONS.map(g => ({ label: g.label, value: g.value }))}
              value={granularity}
              onChange={handleGranularityChange}
            />
            <Radio.Group value={chartMode} onChange={e => setChartMode(e.target.value)} size="small">
              <Radio.Button value="line">折线图</Radio.Button>
              <Radio.Button value="bar">柱状图</Radio.Button>
            </Radio.Group>
          </Space>
        }
      >
        {selectedRules.length === 0 ? (
          <Alert
            type="info"
            showIcon
            message="请在上方选择要查看的规则"
            style={{ margin: 40 }}
          />
        ) : (
          <div>
            <ResponsiveContainer width="100%" height={380}>
              {chartMode === 'line' ? (
                <LineChart data={buildLineChartData()} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" angle={-30} textAnchor="end" height={80} fontSize={11} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {timeSeriesData?.datasets?.map(ds => (
                    <Line
                      key={ds.ruleCode}
                      type="monotone"
                      dataKey={ds.ruleCode}
                      stroke={ds.color}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      activeDot={{ r: 6 }}
                    />
                  ))}
                </LineChart>
              ) : (
                <BarChart data={buildBarChartData()} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" angle={-20} textAnchor="end" height={70} fontSize={11} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="命中次数" fill="#1677ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              )}
            </ResponsiveContainer>

            {timeSeriesData?.totals && (
              <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                <Col xs={24} lg={16}>
                  <Card size="small" title="各时间段决策分布">
                    <Row gutter={8}>
                      {Object.entries(timeSeriesData.totals).map(([key, value], idx) => (
                        <Col xs={12} sm={6} key={key}>
                          <Statistic
                            title={ACTION_LABELS[key]}
                            value={value}
                            valueStyle={{ color: COLORS[idx % COLORS.length], fontSize: 20 }}
                          />
                        </Col>
                      ))}
                    </Row>
                  </Card>
                </Col>
                <Col xs={24} lg={8}>
                  <Card size="small" title="数据范围">
                    <div style={{ fontSize: 13, lineHeight: 2 }}>
                      <p><strong>粒度:</strong> {granConfig?.label}</p>
                      <p><strong>时间范围:</strong></p>
                      <p style={{ paddingLeft: 16, color: '#666', fontFamily: 'monospace', fontSize: 12 }}>
                        {timeSeriesData.timeKeys?.[0]}
                        <br />
                        → {timeSeriesData.timeKeys?.[timeSeriesData.timeKeys.length - 1]}
                      </p>
                      <p><strong>时间点数:</strong> {timeSeriesData.timeKeys?.length || 0}</p>
                    </div>
                  </Card>
                </Col>
              </Row>
            )}
          </div>
        )}
      </Card>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={8}>
          <Card title="决策动作分布" loading={loading}>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`}
                >
                  {pieData.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card title="规则命中率排行" loading={loading}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={hitStats.map(s => ({
                  name: s.ruleCode,
                  命中次数: s.hitCount,
                  总事件数: s.totalEvents,
                })).sort((a, b) => b.命中次数 - a.命中次数).slice(0, 15)}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-30} textAnchor="end" height={80} fontSize={11} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="命中次数" fill="#1677ff" name="命中次数" radius={[4, 4, 0, 0]} />
                <Bar dataKey="总事件数" fill="#e6f7ff" name="总事件数" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Card title="命中率详情" style={{ marginTop: 16 }} loading={loading}>
        <Table
          columns={columns}
          dataSource={hitStats}
          rowKey="ruleCode"
          pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条` }}
        />
      </Card>
    </div>
  )
}
