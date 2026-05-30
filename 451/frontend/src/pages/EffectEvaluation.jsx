import { useState } from 'react'
import { Card, Table, Button, Tag, Row, Col, Statistic, Select, InputNumber, Space, Alert, Spin } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, LineChartOutlined } from '@ant-design/icons'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, Cell, ReferenceLine } from 'recharts'
import { evaluationApi } from '../services/api'

export default function EffectEvaluation() {
  const [evaluations, setEvaluations] = useState([])
  const [loading, setLoading] = useState(false)
  const [evaluated, setEvaluated] = useState(false)
  const [beforeHours, setBeforeHours] = useState(24)
  const [afterHours, setAfterHours] = useState(24)

  const evaluateAll = async () => {
    try {
      setLoading(true)
      const data = await evaluationApi.evaluateAll(beforeHours, afterHours)
      setEvaluations(data || [])
      setEvaluated(true)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '规则编码',
      dataIndex: 'ruleCode',
      key: 'ruleCode',
      width: 160,
      render: (text) => <code style={{ color: '#1677ff', fontFamily: 'monospace' }}>{text}</code>,
    },
    {
      title: '规则名称',
      dataIndex: 'ruleName',
      key: 'ruleName',
      width: 180,
    },
    {
      title: '上线前命中率',
      dataIndex: 'beforeHitRate',
      key: 'beforeHitRate',
      width: 130,
      sorter: (a, b) => a.beforeHitRate - b.beforeHitRate,
      render: (v) => <span style={{ color: '#999' }}>{Number(v).toFixed(2)}%</span>,
    },
    {
      title: '上线后命中率',
      dataIndex: 'afterHitRate',
      key: 'afterHitRate',
      width: 130,
      sorter: (a, b) => a.afterHitRate - b.afterHitRate,
      render: (v) => <span style={{ color: '#1677ff', fontWeight: 500 }}>{Number(v).toFixed(2)}%</span>,
    },
    {
      title: '命中率变化',
      dataIndex: 'hitRateChange',
      key: 'hitRateChange',
      width: 120,
      sorter: (a, b) => a.hitRateChange - b.hitRateChange,
      render: (change) => {
        const v = Number(change).toFixed(2)
        if (change > 0.5) return <Tag color="green" icon={<ArrowUpOutlined />}>+{v}%</Tag>
        if (change < -0.5) return <Tag color="red" icon={<ArrowDownOutlined />}>{v}%</Tag>
        return <Tag icon={<MinusOutlined />}>{v}%</Tag>
      },
    },
    {
      title: '拦截率变化',
      dataIndex: 'rejectRateChange',
      key: 'rejectRateChange',
      width: 120,
      render: (change) => {
        const v = Number(change).toFixed(2)
        if (change > 0.5) return <Tag color="green">+{v}%</Tag>
        if (change < -0.5) return <Tag color="red">{v}%</Tag>
        return <Tag>{v}%</Tag>
      },
    },
    {
      title: '结论',
      dataIndex: 'conclusion',
      key: 'conclusion',
      ellipsis: true,
      render: (text) => <span style={{ fontSize: 12, color: '#722ed1' }}>{text}</span>,
    },
  ]

  const improvedCount = evaluations.filter(e => e.hitRateChange > 0.5).length
  const degradedCount = evaluations.filter(e => e.hitRateChange < -0.5).length
  const stableCount = evaluations.length - improvedCount - degradedCount

  const chartData = evaluations.slice(0, 15).map(e => ({
    name: e.ruleCode,
    上线前: Number(Number(e.beforeHitRate).toFixed(2)),
    上线后: Number(Number(e.afterHitRate).toFixed(2)),
  }))

  return (
    <div>
      <Card
        title={
          <Space>
            <span>规则效果评估</span>
            <Tag color="blue">上线前 {beforeHours}h vs 上线后 {afterHours}h</Tag>
          </Space>
        }
        extra={
          <Space>
            <span style={{ fontSize: 12, color: '#999' }}>对比时间:</span>
            <InputNumber addonBefore="前" addonAfter="小时" min={1} max={168} value={beforeHours} onChange={setBeforeHours} style={{ width: 140 }} />
            <InputNumber addonBefore="后" addonAfter="小时" min={1} max={168} value={afterHours} onChange={setAfterHours} style={{ width: 140 }} />
            <Button type="primary" icon={<LineChartOutlined />} loading={loading} onClick={evaluateAll}>
              评估全部规则
            </Button>
          </Space>
        }
      >
        {!evaluated && !loading && (
          <Alert
            type="info"
            showIcon
            message={'设置对比时间段，点击"评估全部规则"对比上线前后的风险拦截率变化'}
            description="评估指标：命中率变化、拦截率变化、综合结论。基于 Redis 中按小时粒度存储的历史数据计算。"
          />
        )}
      </Card>

      {evaluated && evaluations.length > 0 && (
        <>
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={8}>
              <Card>
                <Statistic
                  title="效果提升"
                  value={improvedCount}
                  suffix={`/ ${evaluations.length} 条`}
                  valueStyle={{ color: '#52c41a' }}
                  prefix="📈"
                />
              </Card>
            </Col>
            <Col xs={8}>
              <Card>
                <Statistic
                  title="效果下降"
                  value={degradedCount}
                  suffix={`/ ${evaluations.length} 条`}
                  valueStyle={{ color: '#ff4d4f' }}
                  prefix="📉"
                />
              </Card>
            </Col>
            <Col xs={8}>
              <Card>
                <Statistic
                  title="效果持平"
                  value={stableCount}
                  suffix={`/ ${evaluations.length} 条`}
                  valueStyle={{ color: '#999' }}
                  prefix="➡️"
                />
              </Card>
            </Col>
          </Row>

          <Card title="上线前后命中率对比" style={{ marginTop: 16 }}>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-30} textAnchor="end" height={80} fontSize={11} />
                <YAxis unit="%" />
                <Tooltip formatter={(value) => `${value}%`} />
                <Legend />
                <ReferenceLine y={0} stroke="#000" />
                <Bar dataKey="上线前" fill="#d9d9d9" radius={[2, 2, 0, 0]} />
                <Bar dataKey="上线后" fill="#1677ff" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card title="详细评估结果" style={{ marginTop: 16 }}>
            <Table
              columns={columns}
              dataSource={evaluations}
              rowKey="ruleCode"
              pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条` }}
            />
          </Card>
        </>
      )}

      {evaluated && evaluations.length === 0 && (
        <Alert
          style={{ marginTop: 16 }}
          type="warning"
          showIcon
          message="暂无评估数据"
          description="可能是 Redis 中没有历史统计数据，请确保系统已运行一段时间后再评估"
        />
      )}
    </div>
  )
}
