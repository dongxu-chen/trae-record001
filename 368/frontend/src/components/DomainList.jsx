import React, { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Card,
  Table,
  Tag,
  Button,
  Space,
  Input,
  Modal,
  Form,
  Select,
  Switch,
  Upload,
  message,
  Popconfirm,
  Tooltip,
  Drawer,
  Descriptions,
  Badge,
  Divider,
} from 'antd'
import {
  PlusOutlined,
  UploadOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  EyeOutlined,
  SwapOutlined,
  ImportOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'
import { api } from '../services/api.js'
import dayjs from 'dayjs'

const { TextArea } = Input

const DomainList = () => {
  const [domains, setDomains] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [keyword, setKeyword] = useState('')
  const [tag, setTag] = useState('')
  const [tags, setTags] = useState([])
  const [createModal, setCreateModal] = useState(false)
  const [editModal, setEditModal] = useState(false)
  const [importModal, setImportModal] = useState(false)
  const [batchModal, setBatchModal] = useState(false)
  const [detailDrawer, setDetailDrawer] = useState(false)
  const [currentDomain, setCurrentDomain] = useState(null)
  const [currentCert, setCurrentCert] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [history, setHistory] = useState([])

  const [createForm] = Form.useForm()
  const [editForm] = Form.useForm()
  const [batchForm] = Form.useForm()

  useEffect(() => {
    fetchDomains()
    fetchTags()
  }, [page, pageSize, keyword, tag])

  const fetchDomains = async () => {
    setLoading(true)
    try {
      const res = await api.getDomains({
        page,
        page_size: pageSize,
        keyword,
        tag,
      })
      setDomains(res.data.domains)
      setTotal(res.data.total)
    } catch (error) {
      message.error('获取域名列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchTags = async () => {
    try {
      const res = await api.getTags()
      setTags(res.data)
    } catch (error) {
      console.error('获取标签失败:', error)
    }
  }

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields()
      await api.createDomain(values)
      message.success('添加成功')
      setCreateModal(false)
      createForm.resetFields()
      fetchDomains()
    } catch (error) {
      if (error.errorFields) return
      message.error(error.message || '添加失败')
    }
  }

  const handleEdit = async () => {
    try {
      const values = await editForm.validateFields()
      await api.updateDomain(currentDomain.id, values)
      message.success('更新成功')
      setEditModal(false)
      fetchDomains()
    } catch (error) {
      if (error.errorFields) return
      message.error(error.message || '更新失败')
    }
  }

  const handleDelete = async (id) => {
    try {
      await api.deleteDomain(id)
      message.success('删除成功')
      fetchDomains()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleToggle = async (domain) => {
    try {
      await api.toggleDomain(domain.id)
      message.success('更新成功')
      fetchDomains()
    } catch (error) {
      message.error('更新失败')
    }
  }

  const handleCheck = async (domain) => {
    try {
      message.loading({ content: '正在检查...', key: 'check' })
      await api.checkDomain(domain.id)
      message.success({ content: '检查完成', key: 'check' })
      fetchDomains()
    } catch (error) {
      message.error({ content: error.message || '检查失败', key: 'check' })
    }
  }

  const handleViewDetail = async (domain) => {
    setCurrentDomain(domain)
    setDetailDrawer(true)
    setDetailLoading(true)
    try {
      const res = await api.getDomainDetail(domain.id)
      setCurrentCert(res.data.cert)
      if (res.data.cert) {
        const historyRes = await api.getCertHistory(domain.id, 30)
        setHistory(historyRes.data)
      }
    } catch (error) {
      message.error('获取详情失败')
    } finally {
      setDetailLoading(false)
    }
  }

  const handleImport = async (info) => {
    try {
      const formData = new FormData()
      formData.append('file', info.file)
      const res = await api.importDomains(formData)
      message.success(`导入成功: ${res.data.success_count}个, 失败: ${res.data.fail_count}个`)
      setImportModal(false)
      fetchDomains()
    } catch (error) {
      message.error('导入失败: ' + error.message)
    }
  }

  const handleBatchCreate = async () => {
    try {
      const values = await batchForm.validateFields()
      const domainsList = values.domains.split('\n').filter(d => d.trim())
      await api.batchCreateDomains({
        domains: domainsList,
        tag: values.tag,
        port: values.port,
      })
      message.success('批量添加成功')
      setBatchModal(false)
      batchForm.resetFields()
      fetchDomains()
    } catch (error) {
      if (error.errorFields) return
      message.error(error.message || '批量添加失败')
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

  const columns = [
    {
      title: '域名',
      dataIndex: 'domain_name',
      key: 'domain_name',
      render: (text, record) => (
        <a onClick={() => handleViewDetail(record)}>{text}</a>
      ),
    },
    {
      title: '端口',
      dataIndex: 'port',
      key: 'port',
      width: 80,
    },
    {
      title: '标签',
      dataIndex: 'tag',
      key: 'tag',
      render: (text) => text ? <Tag color="blue">{text}</Tag> : '-',
    },
    {
      title: '备注',
      dataIndex: 'remark',
      key: 'remark',
      ellipsis: true,
      render: (text) => text || '-',
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled) => (
        <Badge status={enabled ? 'success' : 'default'} text={enabled ? '启用' : '禁用'} />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="检查证书">
            <Button
              type="link"
              size="small"
              icon={<SafetyCertificateOutlined />}
              onClick={() => handleCheck(record)}
            />
          </Tooltip>
          <Tooltip title="查看详情">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => {
                setCurrentDomain(record)
                editForm.setFieldsValue(record)
                setEditModal(true)
              }}
            />
          </Tooltip>
          <Popconfirm
            title={record.enabled ? '确定禁用该域名？' : '确定启用该域名？'}
            onConfirm={() => handleToggle(record)}
          >
            <Button
              type="link"
              size="small"
              icon={<SwapOutlined />}
            />
          </Popconfirm>
          <Popconfirm
            title="确定删除该域名？"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <Input
              placeholder="搜索域名"
              prefix={<SearchOutlined />}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              style={{ width: 200 }}
              allowClear
            />
            <Select
              placeholder="选择标签"
              value={tag || undefined}
              onChange={setTag}
              style={{ width: 150 }}
              allowClear
            >
              {tags.map(t => (
                <Select.Option key={t} value={t}>{t}</Select.Option>
              ))}
            </Select>
          </Space>
        </Col>
        <Col flex="auto" style={{ textAlign: 'right' }}>
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModal(true)}
            >
              添加域名
            </Button>
            <Button
              icon={<ImportOutlined />}
              onClick={() => setBatchModal(true)}
            >
              批量添加
            </Button>
            <Button
              icon={<UploadOutlined />}
              onClick={() => setImportModal(true)}
            >
              CSV导入
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchDomains}
            >
              刷新
            </Button>
          </Space>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={domains}
        rowKey="id"
        loading={loading}
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
        title="添加域名"
        open={createModal}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModal(false)
          createForm.resetFields()
        }}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="domain_name"
            label="域名"
            rules={[{ required: true, message: '请输入域名' }]}
          >
            <Input placeholder="例如: example.com" />
          </Form.Item>
          <Form.Item
            name="port"
            label="端口"
            initialValue={443}
          >
            <Input type="number" min={1} max={65535} />
          </Form.Item>
          <Form.Item name="tag" label="标签">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <TextArea rows={2} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="编辑域名"
        open={editModal}
        onOk={handleEdit}
        onCancel={() => setEditModal(false)}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="domain_name" label="域名">
            <Input disabled />
          </Form.Item>
          <Form.Item name="port" label="端口">
            <Input type="number" min={1} max={65535} />
          </Form.Item>
          <Form.Item name="tag" label="标签">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <TextArea rows={2} placeholder="可选" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="批量添加域名"
        open={batchModal}
        onOk={handleBatchCreate}
        onCancel={() => {
          setBatchModal(false)
          batchForm.resetFields()
        }}
        width={500}
      >
        <Form form={batchForm} layout="vertical">
          <Form.Item
            name="domains"
            label="域名列表"
            rules={[{ required: true, message: '请输入域名列表' }]}
          >
            <TextArea
              rows={6}
              placeholder="每行一个域名，例如：&#10;example.com&#10;test.com&#10;api.example.com"
            />
          </Form.Item>
          <Form.Item name="port" label="端口" initialValue={443}>
            <Input type="number" min={1} max={65535} />
          </Form.Item>
          <Form.Item name="tag" label="标签">
            <Input placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="CSV导入"
        open={importModal}
        footer={null}
        onCancel={() => setImportModal(false)}
      >
        <p style={{ marginBottom: 16 }}>
          CSV格式：域名,端口,备注,标签（第一行为表头）
        </p>
        <Upload
          accept=".csv"
          showUploadList={false}
          customRequest={handleImport}
        >
          <Button icon={<UploadOutlined />}>选择CSV文件</Button>
        </Upload>
      </Modal>

      <Drawer
        title="域名详情"
        width={600}
        open={detailDrawer}
        onClose={() => setDetailDrawer(false)}
      >
        {detailLoading ? (
          <div>加载中...</div>
        ) : currentDomain ? (
          <>
            <Descriptions title="域名信息" bordered column={1} size="small">
              <Descriptions.Item label="域名">{currentDomain.domain_name}</Descriptions.Item>
              <Descriptions.Item label="端口">{currentDomain.port}</Descriptions.Item>
              <Descriptions.Item label="标签">{currentDomain.tag || '-'}</Descriptions.Item>
              <Descriptions.Item label="备注">{currentDomain.remark || '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge status={currentDomain.enabled ? 'success' : 'default'} text={currentDomain.enabled ? '启用' : '禁用'} />
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(currentDomain.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            {currentCert && (
              <>
                <Divider />
                <Descriptions title="证书信息" bordered column={1} size="small">
                  <Descriptions.Item label="状态">
                    <Tag color={getStatusColor(currentCert.status)}>
                      {getStatusText(currentCert.status)}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="主题">{currentCert.subject}</Descriptions.Item>
                  <Descriptions.Item label="签发机构">{currentCert.issuer}</Descriptions.Item>
                  <Descriptions.Item label="有效期">
                    {dayjs(currentCert.not_before).format('YYYY-MM-DD')} 至 {dayjs(currentCert.not_after).format('YYYY-MM-DD')}
                  </Descriptions.Item>
                  <Descriptions.Item label="剩余天数">
                    <span className={`status-${currentCert.status}`}>
                      {currentCert.days_left} 天
                    </span>
                  </Descriptions.Item>
                  <Descriptions.Item label="加密算法">
                    {currentCert.public_key_algo} ({currentCert.public_key_bits}位)
                  </Descriptions.Item>
                  <Descriptions.Item label="签名算法">{currentCert.signature_algo}</Descriptions.Item>
                  <Descriptions.Item label="指纹">{currentCert.fingerprint}</Descriptions.Item>
                  <Descriptions.Item label="SANs">{currentCert.sans || '-'}</Descriptions.Item>
                  <Descriptions.Item label="最后检查">
                    {dayjs(currentCert.last_checked_at).format('YYYY-MM-DD HH:mm:ss')}
                  </Descriptions.Item>
                </Descriptions>
              </>
            )}

            {history.length > 0 && (
              <>
                <Divider />
                <h4>历史记录</h4>
                <Table
                  size="small"
                  dataSource={history}
                  rowKey="id"
                  pagination={false}
                  columns={[
                    {
                      title: '状态',
                      dataIndex: 'status',
                      key: 'status',
                      render: (status) => (
                        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
                      ),
                    },
                    {
                      title: '剩余天数',
                      dataIndex: 'days_left',
                      key: 'days_left',
                    },
                    {
                      title: '签发机构',
                      dataIndex: 'issuer',
                      key: 'issuer',
                    },
                    {
                      title: '检查时间',
                      dataIndex: 'last_checked_at',
                      key: 'last_checked_at',
                      render: (time) => dayjs(time).format('MM-DD HH:mm'),
                    },
                  ]}
                />
              </>
            )}
          </>
        ) : null}
      </Drawer>
    </div>
  )
}

export default DomainList
