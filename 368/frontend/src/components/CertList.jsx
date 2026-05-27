import React, { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Table,
  Tag,
  Button,
  Space,
  Select,
  Card,
  Statistic,
  Tooltip,
  Modal,
  Descriptions,
  List,
  Divider,
  Badge,
  Alert,
} from 'antd'
import {
  ReloadOutlined,
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  LinkOutlined,
  EyeOutlined,
  HistoryOutlined,
  FileSearchOutlined,
  UnlockOutlined,
  LockOutlined,
  DiffOutlined,
} from '@ant-design/icons'
import { api } from '../services/api.js'
import dayjs from 'dayjs'

const CertList = () => {
  const [records, setRecords] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [status, setStatus] = useState('')
  const [unloggedCount, setUnloggedCount] = useState(0)
  const [incompleteChainCount, setIncompleteChainCount] = useState(0)
  const [detailModal, setDetailModal] = useState(false)
  const [currentCert, setCurrentCert] = useState(null)
  const [compareModal, setCompareModal] = useState(false)
  const [compareResult, setCompareResult] = useState(null)
  const [chainModal, setChainModal] = useState(false)
  const [chainInfo, setChainInfo] = useState(null)

  useEffect(() => {
    fetchRecords()
    fetchStats()
  }, [page, pageSize, status])

  const fetchRecords = async () => {
    setLoading(true)
    try {
      const res = await api.getCertRecords({
        page,
        page_size: pageSize,
        status,
      })
      setRecords(res.data.records)
      setTotal(res.data.total)
    } catch (error) {
      console.error('获取证书列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const [unloggedRes, incompleteRes] = await Promise.all([
        api.getUnloggedCerts(),
        api.getIncompleteChainCerts(),
      ])
      setUnloggedCount(unloggedRes.data.count)
      setIncompleteChainCount(incompleteRes.data.count)
    } catch (error) {
      console.error('获取统计失败:', error)
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      valid: 'green',
      warning: 'orange',
      critical: 'red',
      expired: 'default',
      error: 'red',
    }
    return colors[status] || 'default'
  }

  const getStatusText = (status) => {
    const texts = {
      valid: '正常',
      warning: '即将过期',
      critical: '严重',
      expired: '已过期',
      error: '检查失败',
    }
    return texts[status] || status
  }

  const getAlgoStrengthColor = (algo, bits) => {
    if (algo.includes('RSA')) {
      if (bits >= 4096) return 'green'
      if (bits >= 2048) return 'blue'
      return 'orange'
    }
    if (algo.includes('ECDSA')) {
      if (bits >= 384) return 'green'
      return 'blue'
    }
    return 'default'
  }

  const isWeakSignature = (algo) => {
    const weakAlgos = ['MD5', 'SHA1', 'DSA']
    return weakAlgos.some(weak => algo.includes(weak))
  }

  const getChangeTypeColor = (type) => {
    const colors = {
      added: 'green',
      removed: 'red',
      modified: 'orange',
    }
    return colors[type] || 'default'
  }

  const getChangeTypeText = (type) => {
    const texts = {
      added: '新增',
      removed: '移除',
      modified: '修改',
    }
    return texts[type] || type
  }

  const getFieldName = (field) => {
    const names = {
      subject: '证书主题',
      issuer: '签发机构',
      not_before: '有效期开始',
      not_after: '有效期结束',
      signature_algo: '签名算法',
      public_key_algo: '公钥算法',
      public_key_bits: '密钥位数',
      serial_number: '序列号',
      fingerprint: '指纹',
      sans: 'SAN列表',
      version: '版本',
      cert_chain_complete: '证书链完整性',
      ct_logged: 'CT日志备案',
    }
    return names[field] || field
  }

  const handleShowDetail = (record) => {
    setCurrentCert(record)
    setDetailModal(true)
  }

  const handleShowChain = async (domainId) => {
    try {
      const res = await api.getCertChainInfo(domainId)
      setChainInfo(res.data)
      setChainModal(true)
    } catch (error) {
      console.error('获取证书链信息失败:', error)
    }
  }

  const handleCompare = async (domainId) => {
    try {
      const res = await api.compareCertWithPrevious(domainId)
      setCompareResult(res.data)
      setCompareModal(true)
    } catch (error) {
      console.error('证书对比失败:', error)
    }
  }

  const columns = [
    {
      title: '域名',
      dataIndex: 'domain',
      key: 'domain',
      fixed: 'left',
      width: 180,
      render: (text, record) => (
        <Button type="link" onClick={() => handleShowDetail(record)}>
          {text}
        </Button>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => (
        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
      ),
    },
    {
      title: '剩余天数',
      dataIndex: 'days_left',
      key: 'days_left',
      width: 100,
      sorter: (a, b) => a.days_left - b.days_left,
      render: (days, record) => (
        <span className={`status-${record.status}`}>
          {days} 天
        </span>
      ),
    },
    {
      title: '签发机构',
      dataIndex: 'issuer',
      key: 'issuer',
      width: 140,
      ellipsis: true,
    },
    {
      title: '证书链',
      dataIndex: 'cert_chain_complete',
      key: 'cert_chain_complete',
      width: 100,
      render: (complete, record) => (
        <Tooltip title={complete ? '证书链完整' : '证书链不完整'}>
          <Button
            type="link"
            size="small"
            icon={complete ? <LockOutlined style={{ color: '#52c41a' }} /> : <UnlockOutlined style={{ color: '#ff4d4f' }} />}
            onClick={() => handleShowChain(record.domain_id)}
          >
            {complete ? '完整' : '不完整'}
          </Button>
        </Tooltip>
      ),
    },
    {
      title: 'CT备案',
      dataIndex: 'ct_logged',
      key: 'ct_logged',
      width: 100,
      render: (logged, record) => (
        <Tooltip title={logged ? '已在CT日志备案' : '未在CT日志备案，可能存在风险'}>
          <Badge
            status={logged ? 'success' : 'warning'}
            text={logged ? '已备案' : '未备案'}
          />
        </Tooltip>
      ),
    },
    {
      title: '有效期至',
      dataIndex: 'not_after',
      key: 'not_after',
      width: 140,
      sorter: (a, b) => new Date(a.not_after) - new Date(b.not_after),
      render: (time) => dayjs(time).format('YYYY-MM-DD'),
    },
    {
      title: '加密算法',
      dataIndex: 'public_key_algo',
      key: 'public_key_algo',
      width: 120,
      render: (algo, record) => (
        <Tooltip title={`密钥位数: ${record.public_key_bits}位`}>
          <Tag color={getAlgoStrengthColor(algo, record.public_key_bits)}>
            {algo}
          </Tag>
        </Tooltip>
      ),
    },
    {
      title: '签名算法',
      dataIndex: 'signature_algo',
      key: 'signature_algo',
      width: 130,
      render: (algo) => (
        <Tooltip title={isWeakSignature(algo) ? '该算法已被认为不安全' : ''}>
          <Tag color={isWeakSignature(algo) ? 'red' : 'default'}>
            {algo}
          </Tag>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleShowDetail(record)}
            />
          </Tooltip>
          <Tooltip title="证书对比">
            <Button
              type="link"
              size="small"
              icon={<DiffOutlined />}
              onClick={() => handleCompare(record.domain_id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <Select
              placeholder="状态筛选"
              value={status || undefined}
              onChange={setStatus}
              style={{ width: 150 }}
              allowClear
            >
              <Select.Option value="valid">正常</Select.Option>
              <Select.Option value="warning">即将过期</Select.Option>
              <Select.Option value="critical">严重</Select.Option>
              <Select.Option value="expired">已过期</Select.Option>
              <Select.Option value="error">检查失败</Select.Option>
            </Select>
          </Space>
        </Col>
        <Col flex="auto" style={{ textAlign: 'right' }}>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              fetchRecords()
              fetchStats()
            }}
          >
            刷新
          </Button>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={4}>
          <Card size="small">
            <Statistic
              title="正常"
              value={records.filter(r => r.status === 'valid').length}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={4}>
          <Card size="small">
            <Statistic
              title="即将过期"
              value={records.filter(r => r.status === 'warning').length}
              prefix={<WarningOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={4}>
          <Card size="small">
            <Statistic
              title="严重"
              value={records.filter(r => r.status === 'critical').length}
              prefix={<ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={4}>
          <Card size="small">
            <Statistic
              title="已过期"
              value={records.filter(r => r.status === 'expired').length}
              prefix={<ClockCircleOutlined style={{ color: '#8c8c8c' }} />}
              valueStyle={{ color: '#8c8c8c' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={4}>
          <Card size="small">
            <Statistic
              title="证书链不完整"
              value={incompleteChainCount}
              prefix={<UnlockOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={4}>
          <Card size="small">
            <Statistic
              title="未CT备案"
              value={unloggedCount}
              prefix={<FileSearchOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={records}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1400 }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (p, ps) => {
            setPage(p)
            setPageSize(ps)
          },
        }}
      />

      <Modal
        title="证书详情"
        open={detailModal}
        onCancel={() => setDetailModal(false)}
        footer={null}
        width={800}
      >
        {currentCert && (
          <div>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="域名">{currentCert.domain}</Descriptions.Item>
              <Descriptions.Item label="端口">{currentCert.port}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(currentCert.status)}>
                  {getStatusText(currentCert.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="剩余天数">{currentCert.days_left} 天</Descriptions.Item>
              <Descriptions.Item label="证书主题">{currentCert.subject}</Descriptions.Item>
              <Descriptions.Item label="签发机构">{currentCert.issuer}</Descriptions.Item>
              <Descriptions.Item label="有效期开始">
                {dayjs(currentCert.not_before).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="有效期结束">
                {dayjs(currentCert.not_after).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="公钥算法">{currentCert.public_key_algo}</Descriptions.Item>
              <Descriptions.Item label="密钥位数">{currentCert.public_key_bits} 位</Descriptions.Item>
              <Descriptions.Item label="签名算法">{currentCert.signature_algo}</Descriptions.Item>
              <Descriptions.Item label="版本">v{currentCert.version}</Descriptions.Item>
              <Descriptions.Item label="序列号" span={2}>
                <code style={{ wordBreak: 'break-all' }}>{currentCert.serial_number}</code>
              </Descriptions.Item>
              <Descriptions.Item label="指纹 (SHA256)" span={2}>
                <code style={{ wordBreak: 'break-all' }}>{currentCert.fingerprint}</code>
              </Descriptions.Item>
              <Descriptions.Item label="证书链" span={2}>
                {currentCert.cert_chain_complete ? (
                  <Tag color="green"><LockOutlined /> 完整</Tag>
                ) : (
                  <Tag color="red"><UnlockOutlined /> 不完整</Tag>
                )}
                {currentCert.missing_certs && (
                  <span style={{ marginLeft: 8, color: '#ff4d4f' }}>
                    缺失: {currentCert.missing_certs}
                  </span>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="CT日志备案" span={2}>
                {currentCert.ct_logged ? (
                  <Tag color="green"><CheckCircleOutlined /> 已备案 ({currentCert.ct_log_count}个日志)</Tag>
                ) : (
                  <Tag color="orange"><WarningOutlined /> 未备案</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="SAN列表" span={2}>
                {currentCert.sans}
              </Descriptions.Item>
              <Descriptions.Item label="最后检查时间" span={2}>
                {dayjs(currentCert.last_checked_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            {currentCert.error_msg && (
              <Alert
                message="错误信息"
                description={currentCert.error_msg}
                type="error"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}

            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Space>
                <Button
                  icon={<DiffOutlined />}
                  onClick={() => {
                    setDetailModal(false)
                    handleCompare(currentCert.domain_id)
                  }}
                >
                  与上一版本对比
                </Button>
                <Button
                  icon={<LinkOutlined />}
                  onClick={() => {
                    setDetailModal(false)
                    handleShowChain(currentCert.domain_id)
                  }}
                >
                  查看证书链
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        title="证书链信息"
        open={chainModal}
        onCancel={() => setChainModal(false)}
        footer={null}
        width={600}
      >
        {chainInfo && (
          <div>
            <Alert
              message={chainInfo.complete ? '证书链完整' : '证书链不完整'}
              type={chainInfo.complete ? 'success' : 'error'}
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="链长度">{chainInfo.chain_length}</Descriptions.Item>
              <Descriptions.Item label="根CA">
                {chainInfo.root_ca || '未知'}
              </Descriptions.Item>
              <Descriptions.Item label="中间证书">
                {chainInfo.intermediates && chainInfo.intermediates.length > 0 ? (
                  <List
                    size="small"
                    dataSource={chainInfo.intermediates}
                    renderItem={item => <List.Item>{item}</List.Item>}
                  />
                ) : '无'}
              </Descriptions.Item>
              <Descriptions.Item label="缺失证书">
                {chainInfo.missing_certs && chainInfo.missing_certs.length > 0 ? (
                  <List
                    size="small"
                    dataSource={chainInfo.missing_certs}
                    renderItem={item => (
                      <List.Item style={{ color: '#ff4d4f' }}>{item}</List.Item>
                    )}
                  />
                ) : '无'}
              </Descriptions.Item>
              <Descriptions.Item label="错误信息">
                {chainInfo.errors && chainInfo.errors.length > 0 ? (
                  <List
                    size="small"
                    dataSource={chainInfo.errors}
                    renderItem={item => (
                      <List.Item style={{ color: '#ff4d4f' }}>{item}</List.Item>
                    )}
                  />
                ) : '无'}
              </Descriptions.Item>
            </Descriptions>
          </div>
        )}
      </Modal>

      <Modal
        title="证书变更对比"
        open={compareModal}
        onCancel={() => setCompareModal(false)}
        footer={null}
        width={800}
      >
        {compareResult && (
          <div>
            {compareResult.is_renewal && (
              <Alert
                message="证书已续期"
                description="检测到这是一次正常的证书续期操作"
                type="success"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            {compareResult.is_issuer_changed && (
              <Alert
                message="签发机构变更"
                description="证书的签发机构发生了变化，请确认是否为正常变更"
                type="warning"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            {compareResult.is_algo_changed && (
              <Alert
                message="加密算法变更"
                description="证书使用的加密算法发生了变化"
                type="warning"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            <Descriptions bordered column={2} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="域名">{compareResult.domain}</Descriptions.Item>
              <Descriptions.Item label="变更数">
                <Tag color="orange">{compareResult.diff_count} 项</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="旧证书指纹" span={2}>
                <code style={{ wordBreak: 'break-all', fontSize: '12px' }}>
                  {compareResult.old_fingerprint}
                </code>
              </Descriptions.Item>
              <Descriptions.Item label="新证书指纹" span={2}>
                <code style={{ wordBreak: 'break-all', fontSize: '12px' }}>
                  {compareResult.new_fingerprint}
                </code>
              </Descriptions.Item>
            </Descriptions>

            <Divider orientation="left">详细变更</Divider>

            {compareResult.important_diffs && compareResult.important_diffs.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <h4 style={{ color: '#faad14' }}>重要变更</h4>
                <List
                  bordered
                  dataSource={compareResult.important_diffs}
                  renderItem={diff => (
                    <List.Item>
                      <Space>
                        <Tag color={getChangeTypeColor(diff.change_type)}>
                          {getChangeTypeText(diff.change_type)}
                        </Tag>
                        <strong>{getFieldName(diff.field)}:</strong>
                        <span style={{ textDecoration: 'line-through', color: '#8c8c8c' }}>
                          {String(diff.old_value)}
                        </span>
                        <span>→</span>
                        <span style={{ color: '#52c41a' }}>
                          {String(diff.new_value)}
                        </span>
                      </Space>
                    </List.Item>
                  )}
                />
              </div>
            )}

            <h4>所有变更</h4>
            <List
              bordered
              dataSource={compareResult.diffs}
              renderItem={diff => (
                <List.Item>
                  <Space>
                    <Tag color={getChangeTypeColor(diff.change_type)}>
                      {getChangeTypeText(diff.change_type)}
                    </Tag>
                    <strong>{getFieldName(diff.field)}:</strong>
                    <span style={{ textDecoration: 'line-through', color: '#8c8c8c' }}>
                      {String(diff.old_value)}
                    </span>
                    <span>→</span>
                    <span style={{ color: '#52c41a' }}>
                      {String(diff.new_value)}
                    </span>
                  </Space>
                </List.Item>
              )}
            />
          </div>
        )}
      </Modal>
    </div>
  )
}

export default CertList
