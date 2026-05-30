import { useState, useEffect } from 'react';
import {
  Select,
  Card,
  Row,
  Col,
  Button,
  Space,
  Typography,
  Tag,
  List,
  Progress,
  Divider,
  Empty,
  Spin,
  message,
  Badge,
  Collapse,
  Alert,
  Descriptions,
} from 'antd';
import {
  EditOutlined,
  SwapOutlined,
  ReloadOutlined,
  DashboardOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import {
  GitCompare,
  ArrowLeftRight,
  AlertTriangle,
  CheckCircle,
  Info,
  MinusCircle,
  PlusCircle,
  ArrowDown,
  ArrowUp,
} from 'lucide-react';
import type { ApiVersion, VersionDiff, CompatibilityReport, Change, ChangeType } from '../types';
import compareApi from '../api/compareApi';
import versionApi from '../api/versionApi';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { Panel } = Collapse;

const changeTypeMap: Record<ChangeType, { icon: React.ReactNode; color: string; text: string }> = {
  ADD: { icon: <PlusCircle size={16} style={{ color: '#52c41a' }} />, color: 'success', text: '新增' },
  REMOVE: { icon: <MinusCircle size={16} style={{ color: '#ff4d4f' }} />, color: 'error', text: '移除' },
  MODIFY: { icon: <EditOutlined style={{ color: '#faad14' }} />, color: 'warning', text: '修改' },
};

const changeLevelColor: Record<string, string> = {
  ERROR: '#ff4d4f',
  WARNING: '#faad14',
  INFO: '#1677ff',
};

const backwardLevelMap: Record<string, { text: string; color: string; bgColor: string }> = {
  EXCELLENT: { text: '优秀', color: '#52c41a', bgColor: '#f6ffed' },
  GOOD: { text: '良好', color: '#1677ff', bgColor: '#e6f4ff' },
  MODERATE: { text: '一般', color: '#faad14', bgColor: '#fffbe6' },
  POOR: { text: '较差', color: '#fa8c16', bgColor: '#fff7e6' },
  CRITICAL: { text: '严重', color: '#ff4d4f', bgColor: '#fff2f0' },
};

export default function Compare() {
  const [versions, setVersions] = useState<ApiVersion[]>([]);
  const [baseVersionId, setBaseVersionId] = useState<string | null>(null);
  const [targetVersionId, setTargetVersionId] = useState<string | null>(null);
  const [diffResult, setDiffResult] = useState<VersionDiff | null>(null);
  const [compatibilityReport, setCompatibilityReport] = useState<CompatibilityReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [comparing, setComparing] = useState(false);

  const fetchVersions = async () => {
    setLoading(true);
    try {
      const result = await versionApi.getList();
      setVersions(result.list);
    } catch (error) {
      message.error('获取版本列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVersions();
  }, []);

  const handleCompare = async () => {
    if (!baseVersionId || !targetVersionId) {
      message.warning('请选择两个版本进行对比');
      return;
    }

    if (baseVersionId === targetVersionId) {
      message.warning('请选择两个不同的版本');
      return;
    }

    setComparing(true);
    try {
      const request = { baseVersionId, targetVersionId };
      const [diff, compatibility] = await Promise.all([
        compareApi.diff(request),
        compareApi.compatibility(request),
      ]);
      setDiffResult(diff);
      setCompatibilityReport(compatibility);
      message.success('对比完成');
    } catch (error) {
      message.error('对比失败');
    } finally {
      setComparing(false);
    }
  };

  const handleSwap = () => {
    setBaseVersionId(targetVersionId);
    setTargetVersionId(baseVersionId);
    setDiffResult(null);
    setCompatibilityReport(null);
  };

  const handleReset = () => {
    setBaseVersionId(null);
    setTargetVersionId(null);
    setDiffResult(null);
    setCompatibilityReport(null);
  };

  const getVersionName = (id: string) => {
    const v = versions.find((item) => item.id === id);
    return v ? `${v.name} ${v.version}` : '';
  };

  const getCompatibilityScore = () => {
    if (!compatibilityReport) return 0;
    const { breakingChangeCount, warningCount } = compatibilityReport;
    const totalIssues = breakingChangeCount * 10 + warningCount * 5;
    return Math.max(0, 100 - totalIssues);
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#52c41a';
    if (score >= 60) return '#faad14';
    return '#ff4d4f';
  };

  const renderChangeItem = (change: Change, index: number) => {
    const typeInfo = changeTypeMap[change.type];
    return (
      <List.Item
        key={index}
        style={{
          padding: '12px 16px',
          marginBottom: 8,
          background: change.level === 'ERROR' ? '#fff2f0' : change.level === 'WARNING' ? '#fffbe6' : '#e6f4ff',
          borderRadius: 8,
          borderLeft: `3px solid ${changeLevelColor[change.level]}`,
        }}
      >
        <List.Item.Meta
          avatar={typeInfo.icon}
          title={
            <Space>
              <Tag color={typeInfo.color}>{typeInfo.text}</Tag>
              <code className="bg-gray-100 px-2 py-0.5 rounded text-sm">{change.path}</code>
              <Text strong>{change.field}</Text>
            </Space>
          }
          description={
            <div style={{ marginTop: 8 }}>
              <Paragraph style={{ marginBottom: 8 }}>
                <Info size={16} style={{ marginRight: 4, color: '#1677ff' }} />
                {change.description}
              </Paragraph>
              {(change.oldValue || change.newValue) && (
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  {change.oldValue && (
                    <div>
                      <Text type="secondary" style={{ marginRight: 8 }}>旧值：</Text>
                      <Text delete style={{ color: '#ff4d4f' }}>{change.oldValue}</Text>
                    </div>
                  )}
                  {change.newValue && (
                    <div>
                      <Text type="secondary" style={{ marginRight: 8 }}>新值：</Text>
                      <Text strong style={{ color: '#52c41a' }}>{change.newValue}</Text>
                    </div>
                  )}
                </Space>
              )}
            </div>
          }
        />
      </List.Item>
    );
  };

  const baseVersion = versions.find((v) => v.id === baseVersionId);
  const targetVersion = versions.find((v) => v.id === targetVersionId);

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <Title level={3} style={{ margin: 0 }}>
              <Space>
                <GitCompare />
                版本对比
              </Space>
            </Title>
            <Text type="secondary">选择两个版本进行API差异对比和兼容性分析</Text>
          </Col>
          <Col>
            <Space>
              <Button icon={<SwapOutlined />} onClick={handleSwap} disabled={!baseVersionId || !targetVersionId}>
                交换
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重置
              </Button>
            </Space>
          </Col>
        </Row>

        <Row gutter={16} align="middle" style={{ marginBottom: 24 }}>
          <Col span={10}>
            <Card
              size="small"
              style={{
                borderColor: baseVersion ? '#1677ff' : '#d9d9d9',
                borderWidth: 2,
              }}
            >
              <Text strong style={{ color: '#1677ff' }}>基准版本</Text>
              <Select
                style={{ width: '100%', marginTop: 8 }}
                placeholder="请选择基准版本"
                value={baseVersionId}
                onChange={setBaseVersionId}
                loading={loading}
                showSearch
                optionFilterProp="children"
                filterOption={(input, option) =>
                  (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
                }
              >
                {versions.map((v) => (
                  <Option key={v.id} value={v.id}>
                    <Space>
                      <Tag color={v.status === 'ACTIVE' ? 'success' : v.status === 'DEPRECATED' ? 'warning' : 'default'}>
                        {v.status}
                      </Tag>
                      {v.name} {v.version}
                    </Space>
                  </Option>
                ))}
              </Select>
              {baseVersion && (
                <div style={{ marginTop: 8, fontSize: 12 }}>
                  <Text type="secondary">{baseVersion.description}</Text>
                </div>
              )}
            </Card>
          </Col>
          <Col span={4} style={{ textAlign: 'center' }}>
            <Button
              type="primary"
              size="large"
              icon={<ArrowLeftRight />}
              onClick={handleCompare}
              loading={comparing}
              disabled={!baseVersionId || !targetVersionId}
              style={{ borderRadius: '50%', width: 56, height: 56 }}
            />
          </Col>
          <Col span={10}>
            <Card
              size="small"
              style={{
                borderColor: targetVersion ? '#52c41a' : '#d9d9d9',
                borderWidth: 2,
              }}
            >
              <Text strong style={{ color: '#52c41a' }}>目标版本</Text>
              <Select
                style={{ width: '100%', marginTop: 8 }}
                placeholder="请选择目标版本"
                value={targetVersionId}
                onChange={setTargetVersionId}
                loading={loading}
                showSearch
                optionFilterProp="children"
                filterOption={(input, option) =>
                  (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
                }
              >
                {versions.map((v) => (
                  <Option key={v.id} value={v.id}>
                    <Space>
                      <Tag color={v.status === 'ACTIVE' ? 'success' : v.status === 'DEPRECATED' ? 'warning' : 'default'}>
                        {v.status}
                      </Tag>
                      {v.name} {v.version}
                    </Space>
                  </Option>
                ))}
              </Select>
              {targetVersion && (
                <div style={{ marginTop: 8, fontSize: 12 }}>
                  <Text type="secondary">{targetVersion.description}</Text>
                </div>
              )}
            </Card>
          </Col>
        </Row>

        {!baseVersionId && !targetVersionId && (
          <Empty
            image={<GitCompare style={{ fontSize: 64, color: '#d9d9d9' }} />}
            description="请选择两个版本开始对比"
          />
        )}

        {comparing && (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Spin size="large" tip="正在对比版本差异..." />
          </div>
        )}

        {diffResult && compatibilityReport && !comparing && (
          <div>
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Card>
                  <div style={{ textAlign: 'center' }}>
                    <Badge
                      count={compatibilityReport.breakingChangeCount}
                      showZero
                      color="#ff4d4f"
                      style={{ marginRight: 8 }}
                    >
                      <AlertTriangle size={24} style={{ color: '#ff4d4f' }} />
                    </Badge>
                    <Title level={4} style={{ marginTop: 12, marginBottom: 4, fontSize: 14 }}>
                      破坏性变更
                    </Title>
                    <Text type="secondary" style={{ fontSize: 12 }}>可能导致现有客户端中断</Text>
                    <div style={{ marginTop: 8, fontSize: 28, fontWeight: 'bold', color: '#ff4d4f' }}>
                      {compatibilityReport.breakingChangeCount}
                    </div>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <div style={{ textAlign: 'center' }}>
                    <Badge
                      count={compatibilityReport.warningCount}
                      showZero
                      color="#faad14"
                      style={{ marginRight: 8 }}
                    >
                      <AlertTriangle size={24} style={{ color: '#faad14' }} />
                    </Badge>
                    <Title level={4} style={{ marginTop: 12, marginBottom: 4, fontSize: 14 }}>
                      废弃警告
                    </Title>
                    <Text type="secondary" style={{ fontSize: 12 }}>建议在未来版本迁移</Text>
                    <div style={{ marginTop: 8, fontSize: 28, fontWeight: 'bold', color: '#faad14' }}>
                      {compatibilityReport.warningCount}
                    </div>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <div style={{ textAlign: 'center' }}>
                    <CheckCircle size={24} style={{ color: '#1677ff' }} />
                    <Title level={4} style={{ marginTop: 12, marginBottom: 4, fontSize: 14 }}>
                      向后兼容性
                    </Title>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {compatibilityReport.backwardCompatibilityLevel
                        ? backwardLevelMap[compatibilityReport.backwardCompatibilityLevel].text
                        : '未评估'}
                    </Text>
                    <div style={{ marginTop: 8 }}>
                      <Progress
                        type="dashboard"
                        percent={compatibilityReport.backwardCompatibilityScore || 0}
                        strokeColor={getScoreColor(compatibilityReport.backwardCompatibilityScore || 0)}
                        width={80}
                      />
                    </div>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <div style={{ textAlign: 'center' }}>
                    <DashboardOutlined style={{ fontSize: 24, color: '#722ed1' }} />
                    <Title level={4} style={{ marginTop: 12, marginBottom: 4, fontSize: 14 }}>
                      迁移复杂度
                    </Title>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      预估迁移难度
                    </Text>
                    <div style={{ marginTop: 8, fontSize: 28, fontWeight: 'bold', color: '#722ed1' }}>
                      {compatibilityReport.migrationComplexity || 0}
                      <span style={{ fontSize: 14, fontWeight: 'normal', color: '#999' }}>/100</span>
                    </div>
                  </div>
                </Card>
              </Col>
            </Row>

            {compatibilityReport.backwardCompatibilityLevel && (
              <Alert
                message={
                  <Space>
                    <ThunderboltOutlined />
                    向后兼容性评估：{backwardLevelMap[compatibilityReport.backwardCompatibilityLevel].text}
                    （{compatibilityReport.backwardCompatibilityScore}分）
                  </Space>
                }
                description={
                  <div>
                    <Text>检测到 {compatibilityReport.backwardCompatibleChanges?.length || 0} 项向后兼容的变更</Text>
                    {compatibilityReport.backwardCompatibleChanges && compatibilityReport.backwardCompatibleChanges.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        {compatibilityReport.backwardCompatibleChanges.map((change, idx) => (
                          <Tag key={idx} color="success" style={{ marginBottom: 4 }}>
                            <CheckCircle size={12} style={{ marginRight: 4 }} />
                            {change.description}
                          </Tag>
                        ))}
                      </div>
                    )}
                  </div>
                }
                type={compatibilityReport.backwardCompatibilityScore && compatibilityReport.backwardCompatibilityScore >= 80 ? 'success' : 'warning'}
                showIcon
                style={{ marginBottom: 24 }}
              />
            )}

            {!compatibilityReport.isCompatible && (
              <Alert
                message="检测到破坏性变更"
                description="目标版本包含不兼容的API变更，可能会影响现有客户端的正常运行。建议在升级前仔细阅读以下变更详情，并提供适当的过渡期。"
                type="error"
                showIcon
                style={{ marginBottom: 24 }}
              />
            )}

            <Collapse defaultActiveKey={['breaking', 'response', 'backward']} style={{ marginBottom: 24 }}>
              <Panel
                header={
                  <Space>
                    <AlertTriangle size={16} style={{ color: '#ff4d4f' }} />
                    <span>破坏性变更</span>
                    <Tag color="error">{diffResult.breakingChanges.length} 项</Tag>
                  </Space>
                }
                key="breaking"
              >
                {diffResult.breakingChanges.length > 0 ? (
                  <List
                    dataSource={diffResult.breakingChanges}
                    renderItem={(item, index) => renderChangeItem(item, index)}
                  />
                ) : (
                  <Empty description="未检测到破坏性变更" />
                )}
              </Panel>
              <Panel
                header={
                  <Space>
                    <ArrowDown size={16} style={{ color: '#1677ff' }} />
                    <span>返回值变更</span>
                    <Tag color="primary">{diffResult.responseChanges?.length || 0} 项</Tag>
                  </Space>
                }
                key="response"
              >
                {diffResult.responseChanges && diffResult.responseChanges.length > 0 ? (
                  <List
                    dataSource={diffResult.responseChanges}
                    renderItem={(item, index) => renderChangeItem(item, index)}
                  />
                ) : (
                  <Empty description="未检测到返回值变更" />
                )}
              </Panel>
              <Panel
                header={
                  <Space>
                    <Info size={16} style={{ color: '#1677ff' }} />
                    <span>非破坏性变更</span>
                    <Tag color="primary">{diffResult.nonBreakingChanges.length} 项</Tag>
                  </Space>
                }
                key="nonBreaking"
              >
                {diffResult.nonBreakingChanges.length > 0 ? (
                  <List
                    dataSource={diffResult.nonBreakingChanges}
                    renderItem={(item, index) => renderChangeItem(item, index)}
                  />
                ) : (
                  <Empty description="未检测到非破坏性变更" />
                )}
              </Panel>
              <Panel
                header={
                  <Space>
                    <AlertTriangle size={16} style={{ color: '#faad14' }} />
                    <span>废弃变更</span>
                    <Tag color="warning">{diffResult.deprecatedChanges.length} 项</Tag>
                  </Space>
                }
                key="deprecated"
              >
                {diffResult.deprecatedChanges.length > 0 ? (
                  <List
                    dataSource={diffResult.deprecatedChanges}
                    renderItem={(item, index) => renderChangeItem(item, index)}
                  />
                ) : (
                  <Empty description="未检测到废弃变更" />
                )}
              </Panel>
              <Panel
                header={
                  <Space>
                    <ArrowUp size={16} style={{ color: '#52c41a' }} />
                    <span>向后兼容的变更</span>
                    <Tag color="success">{compatibilityReport.backwardCompatibleChanges?.length || 0} 项</Tag>
                  </Space>
                }
                key="backward"
              >
                {compatibilityReport.backwardCompatibleChanges && compatibilityReport.backwardCompatibleChanges.length > 0 ? (
                  <List
                    dataSource={compatibilityReport.backwardCompatibleChanges}
                    renderItem={(item, index) => renderChangeItem(item, index)}
                  />
                ) : (
                  <Empty description="未检测到向后兼容的变更" />
                )}
              </Panel>
            </Collapse>

            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col span={12}>
                <Card
                  title={
                    <Space>
                      <Info size={16} style={{ color: '#1677ff' }} />
                      变更详情
                    </Space>
                  }
                  size="small"
                >
                  <List
                    dataSource={compatibilityReport.details}
                    renderItem={(item) => (
                      <List.Item>
                        <List.Item.Meta
                          avatar={<AlertTriangle size={16} style={{ color: '#faad14' }} />}
                          description={item}
                        />
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card
                  title={
                    <Space>
                      <CheckCircle size={16} style={{ color: '#52c41a' }} />
                      升级建议
                    </Space>
                  }
                  size="small"
                >
                  <List
                    dataSource={compatibilityReport.recommendations}
                    renderItem={(item) => (
                      <List.Item>
                        <List.Item.Meta
                          avatar={<CheckCircle size={16} style={{ color: '#52c41a' }} />}
                          description={item}
                        />
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
            </Row>

            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Card
                  title={
                    <Space>
                      <ArrowUp size={16} style={{ color: '#52c41a' }} />
                      向后兼容性分析
                    </Space>
                  }
                  size="small"
                  extra={
                    <Tag color={backwardLevelMap[compatibilityReport.backwardCompatibilityLevel || 'MODERATE'].color}>
                      {compatibilityReport.backwardCompatibilityLevel
                        ? backwardLevelMap[compatibilityReport.backwardCompatibilityLevel].text
                        : '未评估'}
                    </Tag>
                  }
                >
                  <pre
                    style={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      background: '#fafafa',
                      padding: 12,
                      borderRadius: 8,
                      margin: 0,
                      fontSize: 13,
                      lineHeight: 1.8,
                    }}
                  >
                    {compatibilityReport.backwardCompatibilityAnalysis || '暂无分析数据'}
                  </pre>
                </Card>
              </Col>
              <Col span={12}>
                <Card
                  title={
                    <Space>
                      <ThunderboltOutlined style={{ color: '#722ed1' }} />
                      分批限流推送建议
                    </Space>
                  }
                  size="small"
                >
                  <pre
                    style={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      background: '#fafafa',
                      padding: 12,
                      borderRadius: 8,
                      margin: 0,
                      fontSize: 13,
                      lineHeight: 1.8,
                    }}
                  >
                    {compatibilityReport.rateLimitingRecommendation || '暂无推荐配置'}
                  </pre>
                  {compatibilityReport.migrationComplexity !== undefined && (
                    <div style={{ marginTop: 12 }}>
                      <Descriptions size="small" column={2}>
                        <Descriptions.Item label="迁移复杂度">
                          <Progress
                            percent={compatibilityReport.migrationComplexity}
                            size="small"
                            strokeColor={
                              compatibilityReport.migrationComplexity <= 30
                                ? '#52c41a'
                                : compatibilityReport.migrationComplexity <= 60
                                ? '#faad14'
                                : '#ff4d4f'
                            }
                          />
                        </Descriptions.Item>
                        <Descriptions.Item label="推荐批次">
                          <Tag color="blue">{Math.ceil(100 / Math.max(5, 100 - compatibilityReport.migrationComplexity))} 批</Tag>
                        </Descriptions.Item>
                      </Descriptions>
                    </div>
                  )}
                </Card>
              </Col>
            </Row>

            <Divider />

            <div style={{ textAlign: 'center' }}>
              <Text type="secondary">
                对比结果：{getVersionName(baseVersionId!)} → {getVersionName(targetVersionId!)}
              </Text>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
