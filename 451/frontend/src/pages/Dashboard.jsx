import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Tag, Spin } from 'antd'
import {
  SafetyOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  StopOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { statsApi } from '../services/api'

const COLORS = ['#52c41a', '#faad14', '#ff4d4f', '#8c8c8c']
const ACTION_LABELS = { PASS: '通过', REVIEW: '审核', REJECT: '拒绝', BLOCK: '阻断' }

export default function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [dashboard, setDashboard] = useState({})
  const [actionCounts, setActionCounts] = useState({})

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [dashData, actionData] = await Promise.all([
        statsApi.getDashboard(),
        statsApi.getActionCounts(),
      ])
      setDashboard(dashData)
      setActionCounts(actionData)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const totalEvents = dashboard.totalEvents || 0
  const todayTotal = Number(dashboard.todayTotal) || 0
  const todayHit = Number(dashboard.todayHit) || 0

  const pieData = Object.entries(actionCounts).map(([key, value]) => ({
    name: ACTION_LABELS[key] || key,
    value: value,
  }))

  const barData = Object.entries(actionCounts).map(([key, value]) => ({
    name: ACTION_LABELS[key] || key,
    count: value,
  }))

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="总事件数"
              value={totalEvents}
              prefix={<ThunderboltOutlined style={{ color: '#1677ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="今日事件"
              value={todayTotal}
              prefix={<SafetyOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="今日命中"
              value={todayHit}
              prefix={<WarningOutlined style={{ color: '#faad14' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="今日命中率"
              value={todayTotal > 0 ? ((todayHit / todayTotal) * 100).toFixed(2) : 0}
              suffix="%"
              prefix={<StopOutlined style={{ color: '#ff4d4f' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="决策分布" loading={loading}>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
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
        <Col xs={24} lg={12}>
          <Card title="决策统计" loading={loading}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData}>
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill="#1677ff" name="数量" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="风控状态概览">
            <Row gutter={16}>
              {Object.entries(actionCounts).map(([key, value], idx) => (
                <Col xs={12} sm={6} key={key}>
                  <Card size="small" style={{ textAlign: 'center', borderColor: COLORS[idx] }}>
                    <Tag color={COLORS[idx]} style={{ fontSize: 14, padding: '4px 12px' }}>
                      {ACTION_LABELS[key]}: {value}
                    </Tag>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
