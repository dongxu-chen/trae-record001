import { useState } from 'react'
import { Card, Table, Button, Tag, Space, Statistic, Row, Col, Alert, Spin } from 'antd'
import { WarningOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { conflictApi } from '../services/api'

const CONFLICT_TYPE_MAP = {
  MUTEX: { color: 'red', label: '互斥', icon: '⛔' },
  REDUNDANT: { color: 'orange', label: '冗余', icon: '🔄' },
  OVERLAP: { color: 'blue', label: '重叠', icon: '🔍' },
}

const SEVERITY_MAP = {
  HIGH: { color: '#ff4d4f', label: '高' },
  MEDIUM: { color: '#faad14', label: '中' },
  LOW: { color: '#1677ff', label: '低' },
}

export default function ConflictDetection() {
  const [conflicts, setConflicts] = useState([])
  const [loading, setLoading] = useState(false)
  const [detected, setDetected] = useState(false)

  const detect = async () => {
    try {
      setLoading(true)
      const data = await conflictApi.detect()
      setConflicts(data || [])
      setDetected(true)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const highCount = conflicts.filter(c => c.severity === 'HIGH').length
  const mediumCount = conflicts.filter(c => c.severity === 'MEDIUM').length
  const lowCount = conflicts.filter(c => c.severity === 'LOW').length
  const mutexCount = conflicts.filter(c => c.conflictType === 'MUTEX').length
  const redundantCount = conflicts.filter(c => c.conflictType === 'REDUNDANT').length
  const overlapCount = conflicts.filter(c => c.conflictType === 'OVERLAP').length

  const columns = [
    {
      title: '严重度',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (s) => <Tag color={SEVERITY_MAP[s]?.color}>{SEVERITY_MAP[s]?.label}</Tag>,
      sorter: (a, b) => a.severity.localeCompare(b.severity),
    },
    {
      title: '冲突类型',
      dataIndex: 'conflictType',
      key: 'conflictType',
      width: 100,
      render: (t) => {
        const config = CONFLICT_TYPE_MAP[t] || { color: 'default', label: t }
        return <Tag color={config.color}>{config.icon} {config.label}</Tag>
      },
    },
    {
      title: '规则A',
      key: 'ruleA',
      width: 160,
      render: (_, r) => (
        <span>
          <code style={{ color: '#1677ff' }}>{r.ruleCodeA}</code>
          <br />
          <span style={{ fontSize: 11, color: '#999' }}>{r.ruleNameA}</span>
        </span>
      ),
    },
    {
      title: '规则B',
      key: 'ruleB',
      width: 160,
      render: (_, r) => (
        <span>
          <code style={{ color: '#1677ff' }}>{r.ruleCodeB}</code>
          <br />
          <span style={{ fontSize: 11, color: '#999' }}>{r.ruleNameB}</span>
        </span>
      ),
    },
    {
      title: '冲突描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '建议',
      dataIndex: 'suggestion',
      key: 'suggestion',
      width: 240,
      ellipsis: true,
      render: (text) => <span style={{ color: '#722ed1', fontSize: 12 }}>{text}</span>,
    },
  ]

  return (
    <div>
      <Card
        title="规则冲突检测"
        extra={
          <Button type="primary" loading={loading} onClick={detect}>
            开始检测
          </Button>
        }
      >
        {!detected && !loading && (
          <Alert
            type="info"
            showIcon
            icon={<ExclamationCircleOutlined />}
            message={'点击"开始检测"按钮，扫描所有规则之间的互斥、冗余和条件重叠问题'}
            description="检测范围：条件互斥（同一字段上矛盾条件）、规则冗余（同场景同条件）、条件重叠（多字段部分重叠）"
          />
        )}

        {detected && conflicts.length === 0 && (
          <Alert
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
            message="未发现规则冲突"
            description="当前所有启用的规则之间不存在互斥、冗余或条件重叠问题"
          />
        )}

        {detected && conflicts.length > 0 && (
          <Alert
            type="warning"
            showIcon
            icon={<WarningOutlined />}
            message={`发现 ${conflicts.length} 个规则冲突`}
            description={`包含 ${mutexCount} 个互斥冲突、${redundantCount} 个冗余规则、${overlapCount} 个条件重叠，请检查并处理高严重度问题`}
            style={{ marginBottom: 16 }}
          />
        )}
      </Card>

      {detected && conflicts.length > 0 && (
        <>
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={8}>
              <Card>
                <Statistic
                  title="高严重度"
                  value={highCount}
                  valueStyle={{ color: '#ff4d4f' }}
                  prefix="⛔"
                />
              </Card>
            </Col>
            <Col xs={8}>
              <Card>
                <Statistic
                  title="中严重度"
                  value={mediumCount}
                  valueStyle={{ color: '#faad14' }}
                  prefix="⚠️"
                />
              </Card>
            </Col>
            <Col xs={8}>
              <Card>
                <Statistic
                  title="低严重度"
                  value={lowCount}
                  valueStyle={{ color: '#1677ff' }}
                  prefix="ℹ️"
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={8}>
              <Card size="small">
                <Statistic title="互斥规则" value={mutexCount} prefix={<Tag color="red">MUTEX</Tag>} />
              </Card>
            </Col>
            <Col xs={8}>
              <Card size="small">
                <Statistic title="冗余规则" value={redundantCount} prefix={<Tag color="orange">REDUNDANT</Tag>} />
              </Card>
            </Col>
            <Col xs={8}>
              <Card size="small">
                <Statistic title="条件重叠" value={overlapCount} prefix={<Tag color="blue">OVERLAP</Tag>} />
              </Card>
            </Col>
          </Row>

          <Card title="冲突详情" style={{ marginTop: 16 }}>
            <Table
              columns={columns}
              dataSource={conflicts}
              rowKey={(r) => `${r.ruleCodeA}-${r.ruleCodeB}-${r.conflictType}`}
              pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条` }}
            />
          </Card>
        </>
      )}
    </div>
  )
}
