import React, { useState, useEffect } from 'react'
import {
  Card,
  Typography,
  Table,
  Select,
  Button,
  Space,
  Alert,
  Tag,
  Tabs,
  Row,
  Col,
  Statistic,
  Modal,
  Form,
  Input,
  InputNumber,
  message,
  Spin,
  Progress,
  Switch,
  List,
  Divider,
} from 'antd'
import {
  PartitionOutlined,
  SplitCellsOutlined,
  MergeCellsOutlined,
  ReloadOutlined,
  FireOutlined,
  SnowflakeOutlined,
  BarChartOutlined,
  ArrowRightOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
  CopyOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { TableInfo, PartitionDef, HotColdAnalysis, PerformanceComparison, PerformanceMetric, MigrationResult } from '../types'
import { partitionApi, tablesApi } from '../services/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts'

const { Title, Text } = Typography
const { TabPane } = Tabs
const { Option } = Select
const { TextArea } = Input

const COLORS = ['#ff7a45', '#ffa940', '#595959', '#52c41a']

const AdvancedPartitionPage: React.FC = () => {
  const [tables, setTables] = useState<TableInfo[]>([])
  const [selectedTable, setSelectedTable] = useState<string>('')
  const [tableInfo, setTableInfo] = useState<TableInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)

  const [splitPartition, setSplitPartition] = useState<string>('')
  const [targetRows, setTargetRows] = useState<number>(500000)
  const [mergePartitions, setMergePartitions] = useState<string[]>([])
  const [splitResult, setSplitResult] = useState<string[]>([])
  const [mergeResult, setMergeResult] = useState<string[]>([])
  const [rebalanceResult, setRebalanceResult] = useState<string[]>([])

  const [hotColdAnalysis, setHotColdAnalysis] = useState<HotColdAnalysis | null>(null)
  const [thresholdDays, setThresholdDays] = useState<number>(90)
  const [archivePath, setArchivePath] = useState<string>('/tmp/archive')
  const [hotColdMigrationSQL, setHotColdMigrationSQL] = useState<string[]>([])

  const [benchmarkQueries, setBenchmarkQueries] = useState<string[]>([
    'SELECT * FROM orders WHERE created_at >= NOW() - INTERVAL 7 DAY',
    'SELECT COUNT(*) FROM orders WHERE created_at BETWEEN NOW() - INTERVAL 30 DAY AND NOW()',
    'SELECT * FROM orders WHERE id > 1000000 LIMIT 1000',
  ])
  const [runCount, setRunCount] = useState<number>(3)
  const [benchmarkResult, setBenchmarkResult] = useState<PerformanceComparison | null>(null)
  const [benchmarkRunning, setBenchmarkRunning] = useState(false)

  const [migrationSource, setMigrationSource] = useState<string>('')
  const [migrationTarget, setMigrationTarget] = useState<string>('')
  const [migrationCondition, setMigrationCondition] = useState<string>('1=1')
  const [migrationBatchSize, setMigrationBatchSize] = useState<number>(1000)
  const [migrationVerify, setMigrationVerify] = useState<boolean>(true)
  const [migrationResult, setMigrationResult] = useState<MigrationResult | null>(null)
  const [migrationRunning, setMigrationRunning] = useState(false)

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
      setLoading(true)
      const response = await tablesApi.getList()
      setTables(response.data || [])
    } catch (error) {
      message.error('加载表列表失败')
    } finally {
      setLoading(false)
    }
  }

  const loadTableInfo = async () => {
    try {
      setLoading(true)
      const response = await tablesApi.getInfo(selectedTable)
      setTableInfo(response.data)
    } catch (error) {
      message.error('加载表信息失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSplitPartition = async () => {
    if (!selectedTable || !splitPartition) {
      message.warning('请选择要拆分的分区')
      return
    }

    try {
      setGenerating(true)
      const response = await partitionApi.splitPartition(selectedTable, splitPartition, targetRows)
      setSplitResult(response.data.sqlStatements)
      message.success('拆分SQL生成成功')
    } catch (error) {
      message.error('生成分区拆分SQL失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleMergePartitions = async () => {
    if (!selectedTable || mergePartitions.length < 2) {
      message.warning('请至少选择2个分区进行合并')
      return
    }

    try {
      setGenerating(true)
      const response = await partitionApi.mergePartitions(selectedTable, mergePartitions)
      setMergeResult(response.data.sqlStatements)
      message.success('合并SQL生成成功')
    } catch (error) {
      message.error('生成分区合并SQL失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleRebalancePartitions = async () => {
    if (!selectedTable) {
      message.warning('请选择表')
      return
    }

    try {
      setGenerating(true)
      const response = await partitionApi.rebalancePartitions(selectedTable, targetRows)
      setRebalanceResult(response.data.sqlStatements)
      message.success('重平衡SQL生成成功')
    } catch (error) {
      message.error('生成分区重平衡SQL失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleHotColdAnalysis = async () => {
    if (!selectedTable) {
      message.warning('请选择表')
      return
    }

    try {
      setGenerating(true)
      const response = await partitionApi.analyzeHotCold(selectedTable, thresholdDays)
      setHotColdAnalysis(response.data)
      message.success('冷热分析完成')
    } catch (error) {
      message.error('冷热分析失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleGenerateHotColdMigration = async () => {
    if (!hotColdAnalysis || hotColdAnalysis.coldPartitions.length === 0) {
      message.warning('没有冷分区需要迁移')
      return
    }

    try {
      setGenerating(true)
      const coldPartitionNames = hotColdAnalysis.coldPartitions.map(p => p.partitionName)
      const response = await partitionApi.generateHotColdMigration(selectedTable, coldPartitionNames, archivePath)
      setHotColdMigrationSQL(response.data.sqlStatements)
      message.success('迁移SQL生成成功')
    } catch (error) {
      message.error('生成迁移SQL失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleRunBenchmark = async () => {
    if (!selectedTable) {
      message.warning('请选择表')
      return
    }

    try {
      setBenchmarkRunning(true)
      const response = await partitionApi.runBenchmark({
        tableName: selectedTable,
        queries: benchmarkQueries.filter(q => q.trim() !== ''),
        beforePartition: true,
        afterPartition: true,
        runCount,
      })
      setBenchmarkResult(response.data)
      message.success('性能测试完成')
    } catch (error) {
      message.error('性能测试失败')
    } finally {
      setBenchmarkRunning(false)
    }
  }

  const handleExecuteMigration = async () => {
    if (!migrationSource || !migrationTarget) {
      message.warning('请选择源分区和目标分区')
      return
    }

    try {
      setMigrationRunning(true)
      const response = await partitionApi.migratePartition({
        tableName: selectedTable,
        sourcePartition: migrationSource,
        targetPartition: migrationTarget,
        whereCondition: migrationCondition,
        batchSize: migrationBatchSize,
        verifyData: migrationVerify,
      })
      setMigrationResult(response.data)
      message.success(response.data.success ? '数据迁移成功' : '数据迁移失败')
    } catch (error) {
      message.error('数据迁移失败')
    } finally {
      setMigrationRunning(false)
    }
  }

  const copySQL = (sql: string) => {
    navigator.clipboard.writeText(sql)
    message.success('已复制到剪贴板')
  }

  const copyAllSQL = (sqls: string[]) => {
    navigator.clipboard.writeText(sqls.join('\n\n'))
    message.success('已复制全部SQL')
  }

  const downloadSQL = (sqls: string[], filename: string) => {
    const blob = new Blob([sqls.join('\n\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const getPartitionRowsData = () => {
    if (!tableInfo?.partitionInfo?.partitions) return []
    return tableInfo.partitionInfo.partitions.map(p => ({
      name: p.partitionName,
      rows: p.tableRows,
      size: p.dataLength / (1024 * 1024),
    }))
  }

  const getBenchmarkChartData = () => {
    if (!benchmarkResult) return []
    return benchmarkResult.beforeMetrics.map((metric, index) => ({
      query: `Q${index + 1}`,
      before: metric.avgTimeMs,
      after: benchmarkResult.afterMetrics[index]?.avgTimeMs || 0,
      improvement: benchmarkResult.improvements[metric.query] || 0,
    }))
  }

  const getHotColdPieData = () => {
    if (!hotColdAnalysis) return []
    return [
      { name: '热数据', value: hotColdAnalysis.hotRows, size: hotColdAnalysis.hotSizeMB },
      { name: '冷数据', value: hotColdAnalysis.coldRows, size: hotColdAnalysis.coldSizeMB },
    ]
  }

  const partitions = tableInfo?.partitionInfo?.partitions || []

  if (loading && !tableInfo) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="advanced-partition-page">
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={8}>
            <Form layout="inline">
              <Form.Item label="选择表" required>
                <Select
                  style={{ width: 300 }}
                  value={selectedTable}
                  onChange={setSelectedTable}
                  showSearch
                  placeholder="请选择数据表"
                >
                  {tables.map(t => (
                    <Option key={t.tableName} value={t.tableName}>
                      {t.tableName} ({t.tableRows.toLocaleString()} 行)
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Form>
          </Col>
          {tableInfo && (
            <Col span={16}>
              <Space wrap>
                <Statistic
                  title="总分区数"
                  value={partitions.length}
                  prefix={<PartitionOutlined />}
                />
                <Statistic
                  title="总行数"
                  value={tableInfo.tableRows}
                  formatter={v => Number(v).toLocaleString()}
                />
                <Statistic
                  title="总大小"
                  value={tableInfo.totalSize}
                  suffix="MB"
                  formatter={v => (Number(v) / (1024 * 1024)).toFixed(2)}
                />
                {tableInfo.partitionInfo && (
                  <Statistic
                    title="分区方式"
                    value={tableInfo.partitionInfo.partitionMethod}
                    prefix={<BarChartOutlined />}
                  />
                )}
              </Space>
            </Col>
          )}
        </Row>
      </Card>

      <Tabs defaultActiveKey="1" size="large">
        <TabPane
          tab={
            <span>
              <SplitCellsOutlined /> 分区拆分/合并
            </span>
          }
          key="1"
        >
          {partitions.length > 0 ? (
            <Row gutter={16}>
              <Col span={12}>
                <Card title="分区拆分" size="small">
                  <Form layout="vertical">
                    <Form.Item label="选择要拆分的分区">
                      <Select
                        value={splitPartition}
                        onChange={setSplitPartition}
                        placeholder="请选择分区"
                      >
                        {partitions.filter(p => p.partitionDescription !== 'MAXVALUE').map(p => (
                          <Option key={p.partitionName} value={p.partitionName}>
                            {p.partitionName} ({p.tableRows.toLocaleString()} 行)
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                    <Form.Item label="目标分区行数">
                      <InputNumber
                        style={{ width: '100%' }}
                        value={targetRows}
                        onChange={setTargetRows}
                        min={10000}
                        step={10000}
                      />
                    </Form.Item>
                    <Form.Item>
                      <Button
                        type="primary"
                        icon={<SplitCellsOutlined />}
                        onClick={handleSplitPartition}
                        loading={generating}
                        block
                      >
                        生成拆分SQL
                      </Button>
                    </Form.Item>
                  </Form>

                  {splitResult.length > 0 && (
                    <Card
                      size="small"
                      title="拆分SQL"
                      extra={
                        <Space>
                          <Button size="small" icon={<CopyOutlined />} onClick={() => copyAllSQL(splitResult)}>
                            复制全部
                          </Button>
                          <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadSQL(splitResult, 'split_partitions.sql')}>
                            下载
                          </Button>
                        </Space>
                      }
                      style={{ marginTop: 16 }}
                    >
                      <pre className="code-block" style={{ maxHeight: 400, overflow: 'auto' }}>
                        {splitResult.join('\n')}
                      </pre>
                    </Card>
                  )}
                </Card>
              </Col>

              <Col span={12}>
                <Card title="分区合并" size="small">
                  <Form layout="vertical">
                    <Form.Item label="选择要合并的分区 (至少2个)">
                      <Select
                        mode="multiple"
                        value={mergePartitions}
                        onChange={setMergePartitions}
                        placeholder="请选择分区"
                        style={{ width: '100%' }}
                      >
                        {partitions.filter(p => p.partitionDescription !== 'MAXVALUE').map(p => (
                          <Option key={p.partitionName} value={p.partitionName}>
                            {p.partitionName} ({p.tableRows.toLocaleString()} 行)
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                    <Form.Item>
                      <Button
                        type="primary"
                        icon={<MergeCellsOutlined />}
                        onClick={handleMergePartitions}
                        loading={generating}
                        block
                      >
                        生成合并SQL
                      </Button>
                    </Form.Item>
                  </Form>

                  {mergeResult.length > 0 && (
                    <Card
                      size="small"
                      title="合并SQL"
                      extra={
                        <Space>
                          <Button size="small" icon={<CopyOutlined />} onClick={() => copyAllSQL(mergeResult)}>
                            复制全部
                          </Button>
                          <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadSQL(mergeResult, 'merge_partitions.sql')}>
                            下载
                          </Button>
                        </Space>
                      }
                      style={{ marginTop: 16 }}
                    >
                      <pre className="code-block" style={{ maxHeight: 400, overflow: 'auto' }}>
                        {mergeResult.join('\n')}
                      </pre>
                    </Card>
                  )}
                </Card>
              </Col>

              <Col span={24} style={{ marginTop: 16 }}>
                <Card title="分区重平衡" size="small">
                  <Space align="center">
                    <Text>目标每个分区行数:</Text>
                    <InputNumber
                      value={targetRows}
                      onChange={setTargetRows}
                      min={10000}
                      step={10000}
                    />
                    <Button
                      type="primary"
                      icon={<ReloadOutlined />}
                      onClick={handleRebalancePartitions}
                      loading={generating}
                    >
                      自动生成分区重平衡方案
                    </Button>
                  </Space>

                  {rebalanceResult.length > 0 && (
                    <Card
                      size="small"
                      title="重平衡SQL"
                      style={{ marginTop: 16 }}
                      extra={
                        <Space>
                          <Button size="small" icon={<CopyOutlined />} onClick={() => copyAllSQL(rebalanceResult)}>
                            复制全部
                          </Button>
                          <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadSQL(rebalanceResult, 'rebalance_partitions.sql')}>
                            下载
                          </Button>
                        </Space>
                      }
                    >
                      <pre className="code-block" style={{ maxHeight: 400, overflow: 'auto' }}>
                        {rebalanceResult.join('\n')}
                      </pre>
                    </Card>
                  )}
                </Card>
              </Col>

              <Col span={24} style={{ marginTop: 16 }}>
                <Card title="分区数据分布" size="small">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={getPartitionRowsData()}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="rows" name="行数" fill="#1890ff" />
                      <Bar dataKey="size" name="大小 (MB)" fill="#52c41a" />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </Col>
            </Row>
          ) : (
            <Alert
              type="info"
              message="该表尚未分区"
              description="请先在分区推荐页面创建分区，然后再进行拆分合并操作。"
              showIcon
            />
          )}
        </TabPane>

        <TabPane
          tab={
            <span>
              <ThunderboltOutlined /> 分区热迁移
            </span>
          }
          key="2"
        >
          {partitions.length > 0 ? (
            <Row gutter={16}>
              <Col span={12}>
                <Card title="热迁移配置" size="small">
                  <Form layout="vertical">
                    <Form.Item label="源分区">
                      <Select
                        value={migrationSource}
                        onChange={setMigrationSource}
                        placeholder="选择源分区"
                      >
                        {partitions.map(p => (
                          <Option key={p.partitionName} value={p.partitionName}>
                            {p.partitionName} ({p.tableRows.toLocaleString()} 行)
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                    <Form.Item label="目标分区">
                      <Select
                        value={migrationTarget}
                        onChange={setMigrationTarget}
                        placeholder="选择目标分区"
                      >
                        {partitions.filter(p => p.partitionName !== migrationSource).map(p => (
                          <Option key={p.partitionName} value={p.partitionName}>
                            {p.partitionName} ({p.tableRows.toLocaleString()} 行)
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                    <Form.Item label="迁移条件">
                      <TextArea
                        value={migrationCondition}
                        onChange={e => setMigrationCondition(e.target.value)}
                        placeholder="WHERE 条件，如: created_at < '2024-01-01'"
                        rows={2}
                      />
                    </Form.Item>
                    <Row gutter={8}>
                      <Col span={12}>
                        <Form.Item label="批量大小">
                          <InputNumber
                            style={{ width: '100%' }}
                            value={migrationBatchSize}
                            onChange={setMigrationBatchSize}
                            min={100}
                            step={100}
                          />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item label="数据校验">
                          <Switch
                            checked={migrationVerify}
                            onChange={setMigrationVerify}
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Form.Item>
                      <Button
                        type="primary"
                        danger
                        icon={<PlayCircleOutlined />}
                        onClick={handleExecuteMigration}
                        loading={migrationRunning}
                        block
                      >
                        执行数据热迁移
                      </Button>
                    </Form.Item>
                  </Form>

                  {migrationResult && (
                    <Alert
                      type={migrationResult.success ? 'success' : 'error'}
                      message={migrationResult.success ? '迁移成功' : '迁移失败'}
                      description={
                        <div>
                          <p>迁移行数: {migrationResult.migratedRows.toLocaleString()}</p>
                          {migrationVerify && <p>校验行数: {migrationResult.verifiedRows.toLocaleString()}</p>}
                          <p>执行时间: {migrationResult.executionTime} 秒</p>
                          <p>源分区是否为空: {migrationResult.sourceEmpty ? '是' : '否'}</p>
                        </div>
                      }
                      showIcon
                      style={{ marginTop: 16 }}
                    />
                  )}
                </Card>
              </Col>

              <Col span={12}>
                <Card title="分区列表" size="small">
                  <Table
                    size="small"
                    dataSource={partitions}
                    rowKey="partitionName"
                    pagination={false}
                    columns={[
                      { title: '分区名', dataIndex: 'partitionName', key: 'name' },
                      { title: '行数', dataIndex: 'tableRows', key: 'rows', render: v => v.toLocaleString() },
                      { title: '描述', dataIndex: 'partitionDescription', key: 'desc', ellipsis: true },
                    ]}
                  />
                </Card>

                <Alert
                  type="warning"
                  message="热迁移注意事项"
                  description={
                    <List
                      size="small"
                      dataSource={[
                        '热迁移过程中源分区数据不会被自动删除',
                        '请确保目标分区可以容纳迁移的数据',
                        '建议在业务低峰期执行迁移操作',
                        '迁移完成后请验证数据完整性',
                        '验证通过后可手动删除源分区数据',
                      ]}
                      renderItem={item => <List.Item>• {item}</List.Item>}
                    />
                  }
                  style={{ marginTop: 16 }}
                />
              </Col>
            </Row>
          ) : (
            <Alert
              type="info"
              message="该表尚未分区"
              description="请先在分区推荐页面创建分区，然后再进行热迁移操作。"
              showIcon
            />
          )}
        </TabPane>

        <TabPane
          tab={
            <span>
              <FireOutlined /> 冷热数据分离
            </span>
          }
          key="3"
        >
          {partitions.length > 0 ? (
            <Row gutter={16}>
              <Col span={8}>
                <Card title="冷热分析配置" size="small">
                  <Form layout="vertical">
                    <Form.Item label="冷数据阈值 (天)">
                      <InputNumber
                        style={{ width: '100%' }}
                        value={thresholdDays}
                        onChange={setThresholdDays}
                        min={7}
                        step={7}
                      />
                      <Text type="secondary">超过此天数的数据将被视为冷数据</Text>
                    </Form.Item>
                    <Form.Item>
                      <Button
                        type="primary"
                        icon={<BarChartOutlined />}
                        onClick={handleHotColdAnalysis}
                        loading={generating}
                        block
                      >
                        分析冷热数据
                      </Button>
                    </Form.Item>
                  </Form>
                </Card>

                {hotColdAnalysis && (
                  <Card
                    title="归档配置"
                    size="small"
                    style={{ marginTop: 16 }}
                  >
                    <Form layout="vertical">
                      <Form.Item label="归档路径">
                        <Input
                          value={archivePath}
                          onChange={e => setArchivePath(e.target.value)}
                          placeholder="/path/to/archive"
                        />
                      </Form.Item>
                      <Form.Item>
                        <Button
                          type="primary"
                          icon={<DownloadOutlined />}
                          onClick={handleGenerateHotColdMigration}
                          loading={generating}
                          block
                          disabled={hotColdAnalysis.coldPartitions.length === 0}
                        >
                          生成归档SQL
                        </Button>
                      </Form.Item>
                    </Form>
                  </Card>
                )}
              </Col>

              <Col span={16}>
                {hotColdAnalysis ? (
                  <Card title="冷热分析结果" size="small">
                    <Row gutter={16}>
                      <Col span={12}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Statistic
                            title={
                              <span><FireOutlined style={{ color: '#ff7a45' }} /> 热数据</span>
                            }
                            value={hotColdAnalysis.hotRows}
                            formatter={v => Number(v).toLocaleString()}
                            valueStyle={{ color: '#ff7a45' }}
                          />
                          <Text type="secondary">
                            大小: {hotColdAnalysis.hotSizeMB.toFixed(2)} MB | 分区数: {hotColdAnalysis.hotPartitions.length}
                          </Text>
                        </Space>
                      </Col>
                      <Col span={12}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Statistic
                            title={
                              <span><SnowflakeOutlined style={{ color: '#1890ff' }} /> 冷数据</span>
                            }
                            value={hotColdAnalysis.coldRows}
                            formatter={v => Number(v).toLocaleString()}
                            valueStyle={{ color: '#1890ff' }}
                          />
                          <Text type="secondary">
                            大小: {hotColdAnalysis.coldSizeMB.toFixed(2)} MB | 分区数: {hotColdAnalysis.coldPartitions.length}
                          </Text>
                        </Space>
                      </Col>
                    </Row>

                    <Row style={{ marginTop: 24 }}>
                      <Col span={12}>
                        <ResponsiveContainer width="100%" height={200}>
                          <PieChart>
                            <Pie
                              data={getHotColdPieData()}
                              cx="50%"
                              cy="50%"
                              outerRadius={80}
                              fill="#8884d8"
                              dataKey="value"
                              label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                            >
                              {getHotColdPieData().map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip />
                          </PieChart>
                        </ResponsiveContainer>
                      </Col>
                      <Col span={12}>
                        <Alert
                          type={hotColdAnalysis.coldPartitions.length > 0 ? 'info' : 'success'}
                          message="建议"
                          description={hotColdAnalysis.recommendedAction}
                          showIcon
                        />

                        {hotColdAnalysis.coldPartitions.length > 0 && (
                          <div style={{ marginTop: 16 }}>
                            <Text strong>冷分区列表:</Text>
                            <Tag color="blue" style={{ marginTop: 8 }}>
                              {hotColdAnalysis.coldPartitions.map(p => p.partitionName).join(', ')}
                            </Tag>
                          </div>
                        )}
                      </Col>
                    </Row>
                  </Card>
                ) : (
                  <Card size="small">
                    <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                      <FireOutlined style={{ fontSize: 48 }} />
                      <p style={{ marginTop: 16 }}>请点击左侧"分析冷热数据"按钮开始分析</p>
                    </div>
                  </Card>
                )}

                {hotColdMigrationSQL.length > 0 && (
                  <Card
                    title="归档SQL脚本"
                    size="small"
                    style={{ marginTop: 16 }}
                    extra={
                      <Space>
                        <Button size="small" icon={<CopyOutlined />} onClick={() => copyAllSQL(hotColdMigrationSQL)}>
                          复制全部
                        </Button>
                        <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadSQL(hotColdMigrationSQL, 'hot_cold_migration.sql')}>
                          下载
                        </Button>
                      </Space>
                    }
                  >
                    <pre className="code-block" style={{ maxHeight: 300, overflow: 'auto' }}>
                      {hotColdMigrationSQL.join('\n')}
                    </pre>
                  </Card>
                )}
              </Col>
            </Row>
          ) : (
            <Alert
              type="info"
              message="该表尚未分区"
              description="请先在分区推荐页面创建分区，然后再进行冷热分离操作。"
              showIcon
            />
          )}
        </TabPane>

        <TabPane
          tab={
            <span>
              <BarChartOutlined /> 性能评估
            </span>
          }
          key="4"
        >
          <Row gutter={16}>
            <Col span={8}>
              <Card title="性能测试配置" size="small">
                <Form layout="vertical">
                  <Form.Item label="测试查询 SQL">
                    {benchmarkQueries.map((q, index) => (
                      <TextArea
                        key={index}
                        value={q}
                        onChange={e => {
                          const newQueries = [...benchmarkQueries]
                          newQueries[index] = e.target.value
                          setBenchmarkQueries(newQueries)
                        }}
                        placeholder="SELECT 查询语句"
                        rows={2}
                        style={{ marginBottom: 8 }}
                      />
                    ))}
                    <Button
                      size="small"
                      onClick={() => setBenchmarkQueries([...benchmarkQueries, ''])}
                    >
                      + 添加查询
                    </Button>
                  </Form.Item>
                  <Form.Item label="每个查询运行次数">
                    <InputNumber
                      style={{ width: '100%' }}
                      value={runCount}
                      onChange={setRunCount}
                      min={1}
                      max={10}
                    />
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      icon={<PlayCircleOutlined />}
                      onClick={handleRunBenchmark}
                      loading={benchmarkRunning}
                      block
                    >
                      运行性能测试
                    </Button>
                  </Form.Item>
                </Form>

                <Alert
                  type="info"
                  message="测试说明"
                  description={
                    <List size="small">
                      <List.Item>• 每个查询会运行多次取平均值</List.Item>
                      <List.Item>• 自动收集执行时间和扫描行数</List.Item>
                      <List.Item>• 对比分区前后的性能差异</List.Item>
                      <List.Item>• 建议在业务低峰期测试</List.Item>
                    </List>
                  }
                  style={{ marginTop: 16 }}
                />
              </Card>
            </Col>

            <Col span={16}>
              {benchmarkResult ? (
                <Card title="性能测试结果" size="small">
                  <Row gutter={16}>
                    <Col span={8}>
                      <Statistic
                        title="整体性能提升"
                        value={benchmarkResult.overallGain}
                        suffix="%"
                        valueStyle={{ color: benchmarkResult.overallGain > 0 ? '#52c41a' : '#ff4d4f' }}
                        prefix={benchmarkResult.overallGain > 0 ? '+' : ''}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="测试查询数"
                        value={benchmarkResult.beforeMetrics.length}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="每次运行次数"
                        value={runCount}
                      />
                    </Col>
                  </Row>

                  <Divider />

                  <Title level={5}>性能对比图</Title>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={getBenchmarkChartData()}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="query" />
                      <YAxis label={{ value: '执行时间 (ms)', angle: -90, position: 'insideLeft' }} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="before" name="分区前" fill="#ff7a45" />
                      <Bar dataKey="after" name="分区后" fill="#52c41a" />
                    </BarChart>
                  </ResponsiveContainer>

                  <Title level={5} style={{ marginTop: 24 }}>性能提升趋势</Title>
                  <ResponsiveContainer width="100%" height={250}>
                    <LineChart data={getBenchmarkChartData()}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="query" />
                      <YAxis label={{ value: '提升 (%)', angle: -90, position: 'insideLeft' }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="improvement" stroke="#1890ff" strokeWidth={2} dot={{ r: 6 }} />
                    </LineChart>
                  </ResponsiveContainer>

                  <Title level={5} style={{ marginTop: 24 }}>详细指标</Title>
                  <Table
                    size="small"
                    dataSource={benchmarkResult.beforeMetrics.map((m: PerformanceMetric, i: number) => ({
                      key: i,
                      query: m.query,
                      beforeTime: m.avgTimeMs,
                      afterTime: benchmarkResult.afterMetrics[i]?.avgTimeMs || 0,
                      improvement: benchmarkResult.improvements[m.query] || 0,
                      beforePartitions: m.partitionsScan,
                      afterPartitions: benchmarkResult.afterMetrics[i]?.partitionsScan || 0,
                    }))}
                    columns={[
                      { title: '查询', dataIndex: 'query', key: 'query', ellipsis: true },
                      { title: '分区前 (ms)', dataIndex: 'beforeTime', key: 'beforeTime', render: v => v.toFixed(2) },
                      { title: '分区后 (ms)', dataIndex: 'afterTime', key: 'afterTime', render: v => v.toFixed(2) },
                      {
                        title: '提升',
                        dataIndex: 'improvement',
                        key: 'improvement',
                        render: v => (
                          <Tag color={v > 0 ? 'green' : 'red'}>
                            {v > 0 ? '+' : ''}{v.toFixed(1)}%
                          </Tag>
                        ),
                      },
                      { title: '扫描分区数 (前/后)', key: 'partitions', render: (_, r) => `${r.beforePartitions} → ${r.afterPartitions}` },
                    ]}
                    pagination={false}
                  />
                </Card>
              ) : (
                <Card size="small">
                  <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
                    <BarChartOutlined style={{ fontSize: 64 }} />
                    <p style={{ marginTop: 16 }}>配置查询并点击"运行性能测试"开始评估</p>
                  </div>
                </Card>
              )}
            </Col>
          </Row>
        </TabPane>
      </Tabs>
    </div>
  )
}

export default AdvancedPartitionPage
