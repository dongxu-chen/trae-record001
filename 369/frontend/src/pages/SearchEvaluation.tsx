import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  Select,
  Button,
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Spin,
  Alert,
  Space,
  Tooltip,
  Divider,
} from 'antd';
import {
  SearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import type { SearchRequest, EvaluationResult, ModelInfo, Annotation } from '@/types';
import { search, evaluate, getModels, getQueryAnnotations } from '@/services/api';

const { Option } = Select;
const { TextArea } = Input;

const SearchEvaluation: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const res = await getModels();
      setModels(res.data);
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  };

  const loadAnnotations = async (queryText: string) => {
    try {
      const res = await getQueryAnnotations(queryText);
      setAnnotations(res.data);
    } catch (err) {
      console.error('Failed to load annotations:', err);
    }
  };

  const handleSearch = async (values: SearchRequest) => {
    try {
      setLoading(true);
      setError(null);
      const res = await search(values);
      setResult({
        ...res.data,
        evaluation_id: '',
        metrics: {
          recall_at_k: 0,
          precision_at_k: 0,
          f1_at_k: 0,
          hit_rate: 0,
          mrr: 0,
          ndcg_at_k: 0,
          map_at_k: 0,
          average_precision: 0,
        },
        created_at: new Date().toISOString(),
      });
    } catch (err: any) {
      setError('搜索失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluate = async (values: SearchRequest) => {
    try {
      setEvaluating(true);
      setError(null);
      const res = await evaluate(values);
      setResult(res.data);
      await loadAnnotations(res.data.query_text);
    } catch (err: any) {
      setError('评估失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setEvaluating(false);
    }
  };

  const relevanceLabels: Record<number, { label: string; color: string }> = {
    3: { label: '高度相关', color: 'success' },
    2: { label: '相关', color: 'processing' },
    1: { label: '一般相关', color: 'warning' },
    0: { label: '不相关', color: 'error' },
  };

  const getRelevanceForDoc = (docId: string): number | null => {
    const ann = annotations.find(a => a.doc_id === docId);
    return ann ? ann.relevance : null;
  };

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>搜索评估</h2>

      <Card style={{ marginBottom: 24 }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSearch}
          initialValues={{ model_name: 'default', k: 10 }}
        >
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                name="query_text"
                label="搜索查询"
                rules={[{ required: true, message: '请输入搜索查询' }]}
              >
                <TextArea
                  rows={3}
                  placeholder="输入要评估的搜索查询..."
                  prefix={<SearchOutlined />}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item name="model_name" label="检索模型">
                <Select>
                  {models.map(model => (
                    <Option key={model.model_name} value={model.model_name}>
                      {model.model_name}
                      {model.is_active && <Tag color="green" style={{ marginLeft: 8 }}>活跃</Tag>}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item name="k" label="Top-K">
                <Select>
                  {[1, 3, 5, 10, 20, 30, 50, 100].map(k => (
                    <Option key={k} value={k}>Top {k}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SearchOutlined />}
                loading={loading}
              >
                搜索
              </Button>
              <Button
                icon={<PlayCircleOutlined />}
                onClick={() => form.validateFields().then(handleEvaluate)}
                loading={evaluating}
                type="default"
              >
                搜索并评估
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {error && (
        <Alert message={error} type="error" showIcon style={{ marginBottom: 24 }} />
      )}

      {result && (
        <div>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={12} sm={6}>
              <Card className="metric-card">
                <Statistic
                  title="召回率 Recall@K"
                  value={result.metrics.recall_at_k * 100}
                  suffix="%"
                  precision={2}
                  valueStyle={{ color: '#1677ff' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card className="metric-card">
                <Statistic
                  title="精确率 Precision@K"
                  value={result.metrics.precision_at_k * 100}
                  suffix="%"
                  precision={2}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card className="metric-card">
                <Statistic
                  title="F1 Score"
                  value={result.metrics.f1_at_k * 100}
                  suffix="%"
                  precision={2}
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card className="metric-card">
                <Statistic
                  title="命中率 Hit Rate"
                  value={result.metrics.hit_rate * 100}
                  suffix="%"
                  precision={2}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={12} sm={8}>
              <Card className="metric-card">
                <Statistic
                  title="MRR"
                  value={result.metrics.mrr}
                  precision={4}
                  valueStyle={{ color: '#13c2c2' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8}>
              <Card className="metric-card">
                <Statistic
                  title="NDCG@K"
                  value={result.metrics.ndcg_at_k}
                  precision={4}
                  valueStyle={{ color: '#eb2f96' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8}>
              <Card className="metric-card">
                <Statistic
                  title="MAP@K"
                  value={result.metrics.map_at_k}
                  precision={4}
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
          </Row>

          <Card
            title={
              <Space>
                <span>搜索结果</span>
                <Tag color="blue">找到 {result.total} 个结果</Tag>
                <Tag color="green">耗时 {result.took.toFixed(0)}ms</Tag>
              </Space>
            }
            extra={
              <Space>
                <Tag icon={<CheckCircleOutlined />} color="success">
                  相关: {result.results.filter(r => r.relevant).length}
                </Tag>
                <Tag icon={<CloseCircleOutlined />} color="error">
                  不相关: {result.results.filter(r => !r.relevant).length}
                </Tag>
              </Space>
            }
          >
            {result.results.map((item, index) => {
              const relevance = getRelevanceForDoc(item.doc_id);
              return (
                <div
                  key={item.doc_id}
                  className={`result-item ${item.relevant ? 'relevant' : ''} ${item.relevant === false ? 'irrelevant' : ''}`}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ marginBottom: 8 }}>
                        <Space>
                          <Tag color="#1677ff">#{item.rank}</Tag>
                          {item.relevant && (
                            <Tag icon={<CheckCircleOutlined />} color="success">
                              相关
                            </Tag>
                          )}
                          {item.relevant === false && (
                            <Tag icon={<CloseCircleOutlined />} color="error">
                              不相关
                            </Tag>
                          )}
                          {relevance !== null && (
                            <Tag color={relevanceLabels[relevance].color}>
                              {relevanceLabels[relevance].label}
                            </Tag>
                          )}
                        </Space>
                      </div>
                      <h4 style={{ margin: '0 0 8px 0', color: '#1677ff' }}>{item.title}</h4>
                      <p style={{ color: '#666', margin: 0, lineHeight: 1.6 }}>
                        {item.content}...
                      </p>
                    </div>
                    <div style={{ textAlign: 'right', marginLeft: 16 }}>
                      <Tooltip title="相关性得分">
                        <div style={{ fontSize: 18, fontWeight: 600, color: '#1677ff' }}>
                          {item.score.toFixed(3)}
                        </div>
                      </Tooltip>
                      <div style={{ fontSize: 12, color: '#999' }}>doc_id: {item.doc_id}</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </Card>
        </div>
      )}
    </div>
  );
};

export default SearchEvaluation;
