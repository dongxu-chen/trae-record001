import React, { useState, useEffect } from 'react'
import {
  Card,
  Typography,
  Select,
  Button,
  Space,
  Form,
  Input,
  Alert,
  List,
  Tag,
  Row,
  Col,
  Statistic,
  message,
  Spin,
  Divider,
  Tabs,
} from 'antd'
import {
  ThunderboltOutlined,
  DatabaseOutlined,
  PlayCircleOutlined,
  CopyOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons'
import Editor from 'react-simple-code-editor'
import hljs from 'highlight.js/lib/core'
import sql from 'highlight.js/lib/languages/sql'
import 'highlight.js/styles/atom-one-dark.css'
import { tablesApi, queryApi } from '../services/api'
import type { TableInfo, QueryRewriteResponse } from '../types'

const { Title, Paragraph, Text } = Typography
const { Option } = Select
const { TextArea } = Input

hljs.registerLanguage('sql', sql)

const QueryRewritePage: React.FC = () => {
  const [tables, setTables] = useState<TableInfo[]>([])
  const [selectedTable, setSelectedTable] = useState<string>('')
  const [originalSQL, setOriginalSQL] = useState<string>(
    'SELECT * FROM orders WHERE created_at >= "2024-01-01" AND created_at < "2024-02-01"'
  )
  const [rewriteResult, setRewriteResult] = useState<QueryRewriteResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [tableInfo, setTableInfo] = useState<TableInfo | null>(null)

  useEffect(() => {
    loadTables()
  }, [])

  useEffect(() => {
    if (selectedTable) {
      loadTableInfo()
    }
  }, [selectedTable])

  const loadTables = async () => {
    try {
      const response = await tablesApi.getList()
      setTables(response.data || [])
    } catch (error) {
      message.error('加载表列表失败')
    }
  }

  const loadTableInfo = async () => {
    try {
      const response = await tablesApi.getInfo(selectedTable)
      setTableInfo(response.data)
    } catch (error) {
      console.error('Load table info error:', error)
    }
  }

  const analyzeQuery = async () => {
    if (!originalSQL.trim()) {
      message.warning('请输入SQL查询')
      return
    }

    try {
      setAnalyzing(true)
      const response = await queryApi.analyze(originalSQL, selectedTable)
      setAnalysisResult(response.data)
    } catch (error) {
      message.error('查询分析失败')
    } finally {
      setAnalyzing(false)
    }
  }

  const rewriteQuery = async () => {
    if (!originalSQL.trim()) {
      message.warning('请输入SQL查询')
      return
    }

    if (!selectedTable) {
      message.warning('请选择表')
      return
    }

    try {
      setLoading(true)
      const response = await queryApi.rewrite({
        originalSql: originalSQL,
        tableName: selectedTable,
      })
      setRewriteResult(response.data)
    } catch (error) {
      message.error('查询改写失败')
    } finally {
      setLoading(false)
    }
  }

  const copySQL = (sql: string) => {
    navigator.clipboard.writeText(sql)
    message.success('已复制到剪贴板')
  }

  const highlightSQL = (code: string) => {
    return hljs.highlight(code, { language: 'sql' }).value
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={1} style={{ margin: 0 }}>
          <ThunderboltOutlined style={{ marginRight: 12 }} />
          查询优化工具
        </Title>
        <Paragraph className="description">
          分析查询模式，自动改写SQL以利用分区剪枝，提升查询性能
        </Paragraph>
      </div>

      {tableInfo?.partitionInfo && (
        <Alert
          type="info"
          showIcon
          icon={<DatabaseOutlined />}
          message={`表 ${selectedTable} 已使用 ${tableInfo.partitionInfo.partitionMethod} 分区`}
          description={`分区字段: ${tableInfo.partitionInfo.partitionExpr}`}
          style={{ marginBottom: 24 }}
        />
      )}

      {tableInfo && !tableInfo.partitionInfo && (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message={`表 ${selectedTable} 尚未分区`}
          description="建议先创建分区以获得查询性能提升"
          style={{ marginBottom: 24 }}
        />
      )}

      <Row gutter={24}>
        <Col span={12}>
          <Card
            title="原始查询"
            extra={
              <Space>
                <Select
                  style={{ width: 200 }}
                  value={selectedTable}
                  onChange={setSelectedTable}
                  showSearch
                  placeholder="选择表"
                >
                  {tables.map((table) => (
                    <Option key={table.tableName} value={table.tableName}>
                      {table.tableName}
                    </Option>
                  ))}
                </Select>
                <Button icon={<PlayCircleOutlined />} onClick={analyzeQuery} loading={analyzing}>
                  分析
                </Button>
                <Button type="primary" onClick={rewriteQuery} loading={loading}>
                  优化查询
                </Button>
              </Space>
            }
          >
            <Editor
              value={originalSQL}
              onValueChange={setOriginalSQL}
              highlight={(code) => highlightSQL(code)}
              padding={16}
              className="sql-editor"
              style={{
                fontFamily: '"Fira Code", "Consolas", monospace',
                fontSize: 14,
                minHeight: 200,
                background: '#282c34',
                borderRadius: 8,
              }}
            />

            {analysisResult && (
              <div style={{ marginTop: 16 }}>
                <Divider orientation="left">查询分析</Divider>
                <Row gutter={16}>
                  <Col span={6}>
                    <Card size="small" className="stat-card">
                      <Statistic
                        title="查询类型"
                        value={analysisResult.type}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card size="small" className="stat-card">
                      <Statistic
                        title="WHERE条件"
                        value={analysisResult.hasWhere ? '有' : '无'}
                        valueStyle={{ color: analysisResult.hasWhere ? '#52c41a' : '#f5222d', fontSize: 14 }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card size="small" className="stat-card">
                      <Statistic
                        title="SELECT *"
                        value={analysisResult.selectStar ? '是' : '否'}
                        valueStyle={{ color: analysisResult.selectStar ? '#faad14' : '#52c41a', fontSize: 14 }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card size="small" className="stat-card">
                      <Statistic
                        title="LIMIT"
                        value={analysisResult.hasLimit ? '有' : '无'}
                        valueStyle={{ color: analysisResult.hasLimit ? '#52c41a' : '#faad14', fontSize: 14 }}
                      />
                    </Card>
                  </Col>
                </Row>
                <Row gutter={16} style={{ marginTop: 8 }}>
                  <Col span={8}>
                    <Card size="small" className="stat-card">
                      <Statistic
                        title="ORDER BY"
                        value={analysisResult.hasOrderBy ? '有' : '无'}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" className="stat-card">
                      <Statistic
                        title="GROUP BY"
                        value={analysisResult.hasGroupBy ? '有' : '无'}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" className="stat-card">
                      <Statistic
                        title="JOIN"
                        value={analysisResult.hasJoin ? '有' : '无'}
                        valueStyle={{ fontSize: 14 }}
                      />
                    </Card>
                  </Col>
                </Row>
              </div>
            )}
          </Card>
        </Col>

        <Col span={12}>
          <Card
            title="优化后查询"
            extra={
              <Button
                icon={<CopyOutlined />}
                onClick={() => rewriteResult && copySQL(rewriteResult.rewrittenSql)}
                disabled={!rewriteResult}
              >
                复制
              </Button>
            }
          >
            {rewriteResult ? (
              <Spin spinning={loading}>
                <div
                  className="code-block"
                  style={{ minHeight: 200, marginBottom: 16 }}
                >
                  <pre
                    dangerouslySetInnerHTML={{
                      __html: highlightSQL(rewriteResult.rewrittenSql),
                    }}
                  />
                </div>

                {rewriteResult.rewrittenSql !== rewriteResult.originalSql && (
                  <Alert
                    type="success"
                    showIcon
                    icon={<ArrowRightOutlined />}
                    message="查询已优化"
                    description="点击复制按钮使用优化后的查询"
                    style={{ marginBottom: 16 }}
                  />
                )}

                <Tabs
                  size="small"
                  items={[
                    {
                      key: 'rules',
                      label: '应用的规则',
                      children: (
                        <List
                          size="small"
                          dataSource={rewriteResult.appliedRules}
                          renderItem={(item) => (
                            <List.Item>
                              <Space>
                                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                                <Text>{item}</Text>
                              </Space>
                            </List.Item>
                          )}
                        />
                      ),
                    },
                    {
                      key: 'explanation',
                      label: '详细说明',
                      children: (
                        <div style={{ padding: 16, background: '#fafafa', borderRadius: 8 }}>
                          <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                            {rewriteResult.explanation}
                          </pre>
                        </div>
                      ),
                    },
                    {
                      key: 'performance',
                      label: '性能提示',
                      children: (
                        <Alert
                          type="info"
                          showIcon
                          icon={<InfoCircleOutlined />}
                          message="性能优化建议"
                          description={rewriteResult.performanceHint}
                        />
                      ),
                    },
                  ]}
                />
              </Spin>
            ) : (
              <div
                style={{
                  minHeight: 200,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#8c8c8c',
                }}
              >
                <Text type="secondary">点击"优化查询"按钮生成优化后的SQL</Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="分区剪枝最佳实践" style={{ marginTop: 24 }}>
        <Row gutter={24}>
          <Col span={8}>
            <Alert
              type="success"
              showIcon
              message="推荐做法"
              description={
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li>在WHERE子句中包含分区键</li>
                  <li>使用直接的范围比较（&gt;=, &lt;=, BETWEEN）</li>
                  <li>避免在分区键上使用函数</li>
                  <li>使用 AND 连接分区键条件</li>
                  <li>为常用查询创建覆盖索引</li>
                </ul>
              }
            />
          </Col>
          <Col span={8}>
            <Alert
              type="error"
              showIcon
              message="避免的做法"
              description={
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li>WHERE DATE(created_at) = '...'</li>
                  <li>WHERE YEAR(created_at) = 2024</li>
                  <li>使用 OR 连接非分区键条件</li>
                  <li>SELECT * 查询所有列</li>
                  <li>不带 LIMIT 的 ORDER BY</li>
                </ul>
              }
            />
          </Col>
          <Col span={8}>
            <Alert
              type="info"
              showIcon
              message="验证方法"
              description={
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li>EXPLAIN PARTITIONS 查看分区</li>
                  <li>检查 rows 列扫描的分区数</li>
                  <li>对比优化前后的执行时间</li>
                  <li>监控慢查询日志</li>
                  <li>定期分析表统计信息</li>
                </ul>
              }
            />
          </Col>
        </Row>

        <Divider orientation="left">示例对比</Divider>

        <Row gutter={24}>
          <Col span={12}>
            <Text type="danger" strong>
              <WarningOutlined /> 不推荐的写法（无法使用分区剪枝）
            </Text>
            <div className="code-block" style={{ marginTop: 8 }}>
              <pre
                dangerouslySetInnerHTML={{
                  __html: highlightSQL(
                    `SELECT * FROM orders \nWHERE DATE(created_at) = '2024-01-01';`
                  ),
                }}
              />
            </div>
          </Col>
          <Col span={12}>
            <Text type="success" strong>
              <CheckCircleOutlined /> 推荐的写法（可以使用分区剪枝）
            </Text>
            <div className="code-block" style={{ marginTop: 8 }}>
              <pre
                dangerouslySetInnerHTML={{
                  __html: highlightSQL(
                    `SELECT id, order_no, amount \nFROM orders \nWHERE created_at >= '2024-01-01 00:00:00' \n  AND created_at < '2024-01-02 00:00:00';`
                  ),
                }}
              />
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  )
}

export default QueryRewritePage
