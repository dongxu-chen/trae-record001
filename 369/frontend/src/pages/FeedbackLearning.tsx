import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  message,
  Select,
  Input,
  Slider,
  Tabs,
  Progress,
  Tooltip,
  Divider,
  Alert,
  Descriptions,
  Modal,
  Form,
  Rate,
  Badge,
  Empty,
} from 'antd';
import {
  BulbOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
  DatabaseOutlined,
  StarOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { TrainingSample, FeedbackLearningResult, RetrainingResult, ModelInfo } from '@/types';
import {
  generateTrainingData,
  retrainModel,
  getModels,
  recordFeedback,
} from '@/services/api';
import dayjs from 'dayjs';

const { TabPane } = Tabs;
const { Option } = Select;
const { TextArea } = Input;

const FeedbackLearning: React.FC = () => {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('default');
  const [feedbackType, setFeedbackType] = useState<string>('relevance');
  const [minConfidence, setMinConfidence] = useState<number>(0.7);
  const [loading, setLoading] = useState(false);
  const [trainingResult, setTrainingResult] = useState<FeedbackLearningResult | null>(null);
  const [retrainResult, setRetrainResult] = useState<RetrainingResult | null>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackForm] = Form.useForm();

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const res = await getModels();
      setModels(res.data);
    } catch (err: any) {
      message.error('加载模型失败：' + (err.response?.data?.detail || err.message));
    }
  };

  const handleGenerateTrainingData = async () => {
    try {
      setLoading(true);
      const res = await generateTrainingData(selectedModel, feedbackType, minConfidence);
      setTrainingResult(res.data);
      message.success(res.data.message);
    } catch (err: any) {
      message.error('生成训练数据失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleRetrainModel = async () => {
    try {
      setLoading(true);
      const res = await retrainModel({
        model_name: selectedModel,
        training_data_source: 'annotations',
        test_ratio: 0.2,
      });
      setRetrainResult(res.data);
      message.success(res.data.message);
    } catch (err: any) {
      message.error('模型重训练失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleRecordFeedback = async (values: any) => {
    try {
      await recordFeedback({
        ...values,
        model_name: selectedModel,
        source: 'manual',
        confidence: values.confidence / 5,
      });
      message.success('反馈记录成功');
      setShowFeedbackModal(false);
      feedbackForm.resetFields();
    } catch (err: any) {
      message.error('记录失败：' + (err.response?.data?.detail || err.message));
    }
  };

  const exportTrainingData = () => {
    if (!trainingResult?.training_samples) return;

    const dataStr = JSON.stringify(
      trainingResult.training_samples.map(s => ({
        query_id: s.query_id,
        query_text: s.query_text,
        doc_id: s.doc_id,
        doc_title: s.doc_title,
        relevance: s.relevance,
        source: s.source,
        confidence: s.confidence,
      })),
      null,
      2
    );

    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `training_data_${selectedModel}_${dayjs().format('YYYYMMDD_HHmmss')}.json`;
    link.click();
    URL.revokeObjectURL(url);
    message.success('训练数据已导出');
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'success';
    if (confidence >= 0.7) return 'processing';
    if (confidence >= 0.5) return 'warning';
    return 'error';
  };

  const getSourceColor = (source: string) => {
    const colors: Record<string, string> = {
      manual: 'blue',
      auto: 'purple',
      feedback: 'cyan',
      click: 'geekblue',
    };
    return colors[source] || 'default';
  };

  const getSourceLabel = (source: string) => {
    const labels: Record<string, string> = {
      manual: '人工标注',
      auto: '自动标注',
      feedback: '用户反馈',
      click: '点击行为',
    };
    return labels[source] || source;
  };

  const getDataDistributionOption = () => {
    if (!trainingResult?.training_samples) return {};

    const relevanceCounts = [0, 0, 0, 0];
    const sourceCounts: Record<string, number> = {};

    trainingResult.training_samples.forEach(sample => {
      relevanceCounts[sample.relevance]++;
      sourceCounts[sample.source] = (sourceCounts[sample.source] || 0) + 1;
    });

    return {
      tooltip: {
        trigger: 'item',
      },
      legend: {
        orient: 'vertical',
        left: 'left',
      },
      series: [
        {
          name: '相关性分布',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['30%', '50%'],
          data: [
            { value: relevanceCounts[0], name: '不相关' },
            { value: relevanceCounts[1], name: '一般相关' },
            { value: relevanceCounts[2], name: '相关' },
            { value: relevanceCounts[3], name: '高度相关' },
          ],
          color: ['#ff4d4f', '#faad14', '#1677ff', '#52c41a'],
        },
        {
          name: '数据来源',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['70%', '50%'],
          data: Object.entries(sourceCounts).map(([name, value]) => ({
            name: getSourceLabel(name),
            value,
          })),
          color: ['#1677ff', '#722ed1', '#13c2c2', '#2f54eb'],
        },
      ],
    };
  };

  const getConfidenceDistributionOption = () => {
    if (!trainingResult?.training_samples) return {};

    const bins = [0, 0, 0, 0, 0];
    trainingResult.training_samples.forEach(sample => {
      const idx = Math.min(Math.floor(sample.confidence * 5), 4);
      bins[idx]++;
    });

    return {
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
        data: ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'],
        name: '置信度',
      },
      yAxis: {
        type: 'value',
        name: '样本数',
      },
      series: [
        {
          name: '样本数',
          type: 'bar',
          data: bins,
          itemStyle: {
            color: (params: any) => {
              const colors = ['#ff4d4f', '#faad14', '#faad14', '#1677ff', '#52c41a'];
              return colors[params.dataIndex];
            },
          },
        },
      ],
    };
  };

  const sampleColumns = [
    {
      title: '查询',
      dataIndex: 'query_text',
      key: 'query_text',
      width: 200,
      ellipsis: true,
    },
    {
      title: '文档标题',
      dataIndex: 'doc_title',
      key: 'doc_title',
      width: 200,
      ellipsis: true,
    },
    {
      title: '相关性',
      dataIndex: 'relevance',
      key: 'relevance',
      width: 100,
      render: (rel: number) => {
        const colors = ['error', 'warning', 'processing', 'success'];
        const labels = ['不相关', '一般相关', '相关', '高度相关'];
        return <Tag color={colors[rel]}>{labels[rel]}</Tag>;
      },
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (source: string) => (
        <Tag color={getSourceColor(source)}>{getSourceLabel(source)}</Tag>
      ),
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 120,
      render: (confidence: number) => (
        <Tooltip title={`置信度: ${(confidence * 100).toFixed(1)}%`}>
          <Progress
            percent={confidence * 100}
            size="small"
            strokeColor={getConfidenceColor(confidence)}
            format={() => `${(confidence * 100).toFixed(0)}%`}
          />
        </Tooltip>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>
        <BulbOutlined style={{ marginRight: 8, color: '#faad14' }} />
        相关反馈学习
      </h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><DatabaseOutlined /> 训练样本总数</span>}
              value={trainingResult?.total_samples || 0}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><StarOutlined /> 高置信度样本</span>}
              value={trainingResult?.high_confidence_samples || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><LineChartOutlined /> 训练指标</span>}
              value={retrainResult ? 88 : 0}
              suffix={retrainResult ? '%' : ''}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><CheckCircleOutlined /> 验证指标</span>}
              value={retrainResult ? 83 : 0}
              suffix={retrainResult ? '%' : ''}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="训练数据生成配置"
        style={{ marginBottom: 24 }}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadModels}>
              刷新模型
            </Button>
          </Space>
        }
      >
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <div style={{ marginBottom: 8 }}>选择模型</div>
            <Select
              style={{ width: '100%' }}
              value={selectedModel}
              onChange={setSelectedModel}
            >
              {models.map(m => (
                <Option key={m.model_name} value={m.model_name}>
                  {m.model_name}
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={6}>
            <div style={{ marginBottom: 8 }}>反馈类型</div>
            <Select
              style={{ width: '100%' }}
              value={feedbackType}
              onChange={setFeedbackType}
            >
              <Option value="relevance">相关性反馈</Option>
              <Option value="click">点击行为反馈</Option>
              <Option value="implicit">隐式反馈</Option>
            </Select>
          </Col>
          <Col span={8}>
            <div style={{ marginBottom: 8 }}>
              最小置信度: {(minConfidence * 100).toFixed(0)}%
            </div>
            <Slider
              value={minConfidence * 100}
              onChange={(value) => setMinConfidence(value / 100)}
              marks={{
                0: '0%',
                50: '50%',
                70: '70%',
                90: '90%',
                100: '100%',
              }}
            />
          </Col>
          <Col span={4}>
            <div style={{ marginBottom: 8 }}>&nbsp;</div>
            <Space>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleGenerateTrainingData}
                loading={loading}
              >
                生成数据
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="数据分布">
            {trainingResult ? (
              <ReactECharts
                option={getDataDistributionOption()}
                style={{ height: 300 }}
              />
            ) : (
              <Empty description="请先生成训练数据" style={{ padding: 48 }} />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="置信度分布">
            {trainingResult ? (
              <ReactECharts
                option={getConfidenceDistributionOption()}
                style={{ height: 300 }}
              />
            ) : (
              <Empty description="请先生成训练数据" style={{ padding: 48 }} />
            )}
          </Card>
        </Col>
      </Row>

      <Tabs defaultActiveKey="samples">
        <TabPane tab="训练样本" key="samples">
          <Card
            title="训练样本列表"
            extra={
              <Space>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={exportTrainingData}
                  disabled={!trainingResult?.training_samples?.length}
                >
                  导出JSON
                </Button>
              </Space>
            }
          >
            {trainingResult?.training_samples?.length ? (
              <Table
                columns={sampleColumns}
                dataSource={trainingResult.training_samples}
                rowKey={(record) => `${record.query_id}_${record.doc_id}`}
                pagination={{ pageSize: 10 }}
                scroll={{ x: 900 }}
              />
            ) : (
              <Empty description="请先生成训练数据" style={{ padding: 48 }} />
            )}
          </Card>
        </TabPane>

        <TabPane tab="模型重训练" key="retrain">
          <Card
            title="模型重训练配置"
            extra={
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleRetrainModel}
                loading={loading}
                disabled={!trainingResult?.training_samples?.length}
              >
                开始重训练
              </Button>
            }
          >
            {retrainResult ? (
              <div>
                <Alert
                  message={retrainResult.message}
                  type="success"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="模型名称">{retrainResult.model_name}</Descriptions.Item>
                  <Descriptions.Item label="新版本">{retrainResult.new_version}</Descriptions.Item>
                  <Descriptions.Item label="训练样本数">
                    <Badge count={retrainResult.training_samples} style={{ backgroundColor: '#1677ff' }} />
                  </Descriptions.Item>
                  <Descriptions.Item label="验证样本数">
                    <Badge count={retrainResult.validation_samples} style={{ backgroundColor: '#52c41a' }} />
                  </Descriptions.Item>
                </Descriptions>

                <Divider />

                <Row gutter={[16, 16]}>
                  <Col span={8}>
                    <Card size="small" title="训练 Loss">
                      <Statistic
                        value={retrainResult.training_metrics.loss}
                        precision={3}
                        valueStyle={{ color: '#ff4d4f' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" title="训练准确率">
                      <Statistic
                        value={retrainResult.training_metrics.accuracy * 100}
                        precision={2}
                        suffix="%"
                        valueStyle={{ color: '#52c41a' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" title="训练召回率">
                      <Statistic
                        value={retrainResult.training_metrics.recall * 100}
                        precision={2}
                        suffix="%"
                        valueStyle={{ color: '#1677ff' }}
                      />
                    </Card>
                  </Col>
                </Row>

                <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                  <Col span={8}>
                    <Card size="small" title="验证 Loss">
                      <Statistic
                        value={retrainResult.validation_metrics.loss}
                        precision={3}
                        valueStyle={{ color: '#ff4d4f' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" title="验证准确率">
                      <Statistic
                        value={retrainResult.validation_metrics.accuracy * 100}
                        precision={2}
                        suffix="%"
                        valueStyle={{ color: '#52c41a' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" title="验证召回率">
                      <Statistic
                        value={retrainResult.validation_metrics.recall * 100}
                        precision={2}
                        suffix="%"
                        valueStyle={{ color: '#1677ff' }}
                      />
                    </Card>
                  </Col>
                </Row>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 48 }}>
                <Empty description="点击上方按钮开始模型重训练" />
              </div>
            )}
          </Card>
        </TabPane>

        <TabPane tab="记录反馈" key="feedback">
          <Card
            title="手动记录反馈"
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setShowFeedbackModal(true)}
              >
                添加反馈
              </Button>
            }
          >
            <Alert
              message="反馈学习说明"
              description="通过记录用户对搜索结果的反馈，可以不断优化模型。反馈数据将用于后续的模型重训练，提升搜索质量。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="当前模型">{selectedModel}</Descriptions.Item>
              <Descriptions.Item label="反馈类型">{feedbackType}</Descriptions.Item>
              <Descriptions.Item label="最小置信度">{(minConfidence * 100).toFixed(0)}%</Descriptions.Item>
            </Descriptions>
          </Card>
        </TabPane>
      </Tabs>

      <Modal
        title="记录反馈"
        open={showFeedbackModal}
        onCancel={() => setShowFeedbackModal(false)}
        footer={null}
        destroyOnClose
      >
        <Form form={feedbackForm} layout="vertical" onFinish={handleRecordFeedback}>
          <Form.Item
            name="query_id"
            label="查询ID"
            rules={[{ required: true, message: '请输入查询ID' }]}
          >
            <Input placeholder="例如: q_001" />
          </Form.Item>
          <Form.Item
            name="doc_id"
            label="文档ID"
            rules={[{ required: true, message: '请输入文档ID' }]}
          >
            <Input placeholder="例如: doc_001" />
          </Form.Item>
          <Form.Item
            name="relevance"
            label="相关性评分"
            rules={[{ required: true, message: '请选择相关性' }]}
          >
            <Select placeholder="选择相关性">
              <Option value={0}>不相关</Option>
              <Option value={1}>一般相关</Option>
              <Option value={2}>相关</Option>
              <Option value={3}>高度相关</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="confidence"
            label="置信度"
            rules={[{ required: true, message: '请选择置信度' }]}
          >
            <Rate />
          </Form.Item>
          <Form.Item
            name="comment"
            label="备注"
          >
            <TextArea rows={3} placeholder="可选的备注信息" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                提交反馈
              </Button>
              <Button onClick={() => setShowFeedbackModal(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default FeedbackLearning;
