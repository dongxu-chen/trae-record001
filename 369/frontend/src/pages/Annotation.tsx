import React, { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Button,
  Table,
  Tag,
  Space,
  Rate,
  Modal,
  Form,
  Input,
  message,
  Row,
  Col,
  Statistic,
  Tooltip,
  Spin,
  Alert,
} from 'antd';
import {
  EditOutlined,
  SaveOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  LinkOutlined,
  CopyOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import type { Query, Document, Annotation, SearchRequest, SearchResponse } from '@/types';
import {
  getQueries,
  getDocuments,
  getQueryAnnotations,
  createAnnotation,
  createAnnotationsBatch,
  search,
} from '@/services/api';

const { Option } = Select;
const { TextArea } = Input;

const QUERY_TYPE_LABELS: Record<string, string> = {
  informational: '信息查询',
  navigational: '导航查询',
  transactional: '事务查询',
  exploratory: '探索查询',
  unknown: '未知类型',
};

const QUERY_TYPE_COLORS: Record<string, string> = {
  informational: 'blue',
  navigational: 'green',
  transactional: 'orange',
  exploratory: 'purple',
  unknown: 'default',
};

const AnnotationPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [queries, setQueries] = useState<Query[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedQuery, setSelectedQuery] = useState<string | null>(null);
  const [selectedQueryType, setSelectedQueryType] = useState<string | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [annotationMap, setAnnotationMap] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [showAddDocModal, setShowAddDocModal] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [currentRequestId, setCurrentRequestId] = useState<string | null>(null);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [queryTypeFilter, setQueryTypeFilter] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const generateRequestId = () => {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  const loadData = async () => {
    try {
      setLoading(true);
      const [queriesRes, docsRes] = await Promise.all([
        getQueries(1, 100),
        getDocuments(1, 100),
      ]);
      setQueries(queriesRes.data);
      setDocuments(docsRes.data);
    } catch (err: any) {
      setError('数据加载失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const filteredQueries = queryTypeFilter
    ? queries.filter(q => q.query_type === queryTypeFilter)
    : queries;

  const handleQuerySelect = async (queryId: string) => {
    try {
      setSelectedQuery(queryId);
      setLoading(true);

      const query = queries.find(q => q.query_id === queryId);
      if (query) {
        setSelectedQueryType(query.query_type || null);
        const requestId = generateRequestId();
        setCurrentRequestId(requestId);

        const searchReq: SearchRequest = {
          query_text: query.query_text,
          k: 20,
          request_id: requestId,
          query_type: query.query_type,
        };
        const searchRes = await search(searchReq);
        setSearchResponse(searchRes.data);
        setSearchResults(searchRes.data.results);
      }

      const annRes = await getQueryAnnotations(queryId);
      setAnnotations(annRes.data);

      const map: Record<string, number> = {};
      annRes.data.forEach(ann => {
        map[ann.doc_id] = ann.relevance;
      });
      setAnnotationMap(map);
    } catch (err: any) {
      message.error('加载标注数据失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleRelevanceChange = async (docId: string, relevance: number) => {
    if (!selectedQuery) return;

    try {
      setAnnotationMap(prev => ({ ...prev, [docId]: relevance }));
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveAnnotations = async () => {
    if (!selectedQuery) {
      message.warning('请先选择一个查询');
      return;
    }

    const annotationsToSave = Object.entries(annotationMap)
      .filter(([_, rel]) => rel > 0)
      .map(([docId, relevance]) => ({
        query_id: selectedQuery,
        doc_id: docId,
        relevance,
        annotator: 'user',
        request_id: currentRequestId || undefined,
      }));

    if (annotationsToSave.length === 0) {
      message.warning('没有需要保存的标注');
      return;
    }

    try {
      setSaving(true);
      await createAnnotationsBatch(selectedQuery, annotationsToSave, currentRequestId || undefined);
      message.success(
        <span>
          成功保存 {annotationsToSave.length} 个标注
          {currentRequestId && (
            <Tag color="blue" style={{ marginLeft: 8 }}>
              <LinkOutlined /> Request ID: {currentRequestId}
            </Tag>
          )}
        </span>
      );
      await handleQuerySelect(selectedQuery);
    } catch (err: any) {
      message.error('保存失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const handleSearchDocs = async () => {
    if (!searchText.trim()) return;
    try {
      const requestId = generateRequestId();
      const searchReq: SearchRequest = {
        query_text: searchText,
        k: 20,
        request_id: requestId,
      };
      const searchRes = await search(searchReq);
      setSearchResults(prev => {
        const existingIds = new Set(prev.map(r => r.doc_id));
        const newResults = searchRes.data.results.filter(r => !existingIds.has(r.doc_id));
        return [...prev, ...newResults];
      });
      setShowAddDocModal(false);
      setSearchText('');
      message.info(
        <span>
          搜索完成
          <Tag color="blue" style={{ marginLeft: 8 }}>
            Request ID: {requestId}
          </Tag>
        </span>
      );
    } catch (err: any) {
      message.error('搜索失败：' + (err.response?.data?.detail || err.message));
    }
  };

  const handleCopyRequestId = () => {
    if (currentRequestId) {
      navigator.clipboard.writeText(currentRequestId);
      message.success('Request ID 已复制到剪贴板');
    }
  };

  const getRelevanceLabel = (relevance: number) => {
    const labels: Record<number, { text: string; color: string }> = {
      0: { text: '未标注', color: 'default' },
      1: { text: '一般相关', color: 'warning' },
      2: { text: '相关', color: 'processing' },
      3: { text: '高度相关', color: 'success' },
    };
    return labels[relevance] || labels[0];
  };

  const getQueryTypeStats = () => {
    const stats: Record<string, number> = {};
    queries.forEach(q => {
      const type = q.query_type || 'unknown';
      stats[type] = (stats[type] || 0) + 1;
    });
    return stats;
  };

  const queryTypeStats = getQueryTypeStats();

  const annotatedCount = Object.values(annotationMap).filter(v => v > 0).length;
  const totalCount = searchResults.length;

  if (loading && !selectedQuery) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>人工标注系统</h2>

      {error && (
        <Alert message={error} type="error" showIcon style={{ marginBottom: 24 }} />
      )}

      <Card
        title={
          <Space>
            <BarChartOutlined style={{ color: '#1677ff' }} />
            <span>查询类型统计</span>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={4}>
            <Card
              className="metric-card"
              hoverable
              onClick={() => setQueryTypeFilter(null)}
              style={{ cursor: queryTypeFilter === null ? undefined : 'pointer' }}
              bordered={queryTypeFilter === null}
            >
              <Statistic
                title="全部查询"
                value={queries.length}
                valueStyle={{ color: '#1677ff' }}
              />
            </Card>
          </Col>
          {Object.entries(queryTypeStats).map(([type, count], index) => (
            <Col xs={12} sm={4} key={type}>
              <Card
                className="metric-card"
                hoverable
                onClick={() => setQueryTypeFilter(queryTypeFilter === type ? null : type)}
                style={{ cursor: 'pointer' }}
                bordered={queryTypeFilter === type}
              >
                <Statistic
                  title={
                    <Tag color={QUERY_TYPE_COLORS[type] || 'default'}>
                      {QUERY_TYPE_LABELS[type] || type}
                    </Tag>
                  }
                  value={count}
                />
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8}>
          <Card className="metric-card">
            <Statistic
              title="查询总数"
              value={filteredQueries.length}
              valueStyle={{ color: '#1677ff' }}
              suffix={queryTypeFilter ? ` (${QUERY_TYPE_LABELS[queryTypeFilter] || queryTypeFilter})` : ''}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card className="metric-card">
            <Statistic
              title="文档总数"
              value={documents.length}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card className="metric-card">
            <Statistic
              title="已标注数"
              value={annotations.length}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      {currentRequestId && (
        <Alert
          message={
            <Space>
              <LinkOutlined style={{ color: '#1677ff' }} />
              <span>
                当前请求 ID:
                <code style={{ background: '#f0f2f5', padding: '2px 8px', borderRadius: 4, margin: '0 8px' }}>
                  {currentRequestId}
                </code>
                用于关联此次搜索和标注
              </span>
              <Tooltip title="复制 Request ID">
                <Button
                  type="text"
                  icon={<CopyOutlined />}
                  size="small"
                  onClick={handleCopyRequestId}
                />
              </Tooltip>
            </Space>
          }
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      <Card
        title="选择查询进行标注"
        extra={
          <Space>
            <span style={{ color: '#666' }}>
              {selectedQuery ? `已标注: ${annotatedCount}/${totalCount}` : ''}
            </span>
            {selectedQuery && (
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSaveAnnotations}
                loading={saving}
              >
                保存标注
              </Button>
            )}
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {queryTypeFilter && (
            <Tag color={QUERY_TYPE_COLORS[queryTypeFilter] || 'default'} closable onClose={() => setQueryTypeFilter(null)}>
              筛选: {QUERY_TYPE_LABELS[queryTypeFilter] || queryTypeFilter}
            </Tag>
          )}
          <Select
            style={{ width: '100%' }}
            placeholder="选择一个查询..."
            showSearch
            optionFilterProp="children"
            onSelect={handleQuerySelect}
            loading={loading}
            value={selectedQuery}
          >
            {filteredQueries.map(query => (
              <Option key={query.query_id} value={query.query_id}>
                <Space>
                  <span>{query.query_text}</span>
                  <Tag color="blue">{query.query_id}</Tag>
                  {query.query_type && (
                    <Tag color={QUERY_TYPE_COLORS[query.query_type] || 'default'}>
                      {QUERY_TYPE_LABELS[query.query_type] || query.query_type}
                    </Tag>
                  )}
                </Space>
              </Option>
            ))}
          </Select>
        </Space>

        {selectedQuery && (
          <Alert
            message={
              <Space>
                <InfoCircleOutlined />
                <span>
                  请为以下文档标注相关性等级：
                  <Tag color="default">0=不相关</Tag>
                  <Tag color="warning">1=一般相关</Tag>
                  <Tag color="processing">2=相关</Tag>
                  <Tag color="success">3=高度相关</Tag>
                </span>
                {currentRequestId && (
                  <Tag color="blue" style={{ marginLeft: 8 }}>
                    <LinkOutlined /> Request ID 关联
                  </Tag>
                )}
              </Space>
            }
            type="info"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      {selectedQuery && (
        <Card
          title={
            <Space>
              <span>搜索结果</span>
              {selectedQueryType && (
                <Tag color={QUERY_TYPE_COLORS[selectedQueryType] || 'default'}>
                  {QUERY_TYPE_LABELS[selectedQueryType] || selectedQueryType}
                </Tag>
              )}
              <Button
                type="default"
                size="small"
                icon={<SearchOutlined />}
                onClick={() => setShowAddDocModal(true)}
              >
                添加更多文档
              </Button>
            </Space>
          }
          loading={loading}
        >
          {searchResults.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
              暂无搜索结果
            </div>
          ) : (
            <div>
              {searchResults.map((result, index) => {
                const relevance = annotationMap[result.doc_id] || 0;
                const label = getRelevanceLabel(relevance);
                return (
                  <div key={result.doc_id} className="annotation-item">
                    <Tag color="#1677ff">#{index + 1}</Tag>
                    <div className="doc-info">
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                        <h4 style={{ margin: 0, color: '#1677ff' }}>{result.title}</h4>
                        <Tag color={label.color}>{label.text}</Tag>
                        <span style={{ color: '#999', fontSize: 12 }}>
                          doc_id: {result.doc_id}
                        </span>
                        <span style={{ color: '#999', fontSize: 12 }}>
                          score: {result.score?.toFixed(4)}
                        </span>
                      </div>
                      <p style={{ color: '#666', margin: 0, fontSize: 13 }}>
                        {result.content}...
                      </p>
                    </div>
                    <div>
                      <Tooltip title={relevance > 0 ? '点击修改标注' : '点击进行标注'}>
                        <Rate
                          count={3}
                          value={relevance}
                          onChange={value => handleRelevanceChange(result.doc_id, value)}
                          style={{ fontSize: 24 }}
                          allowHalf={false}
                        />
                      </Tooltip>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      <Modal
        title="搜索文档"
        open={showAddDocModal}
        onCancel={() => setShowAddDocModal(false)}
        footer={null}
      >
        <Form layout="vertical" onFinish={handleSearchDocs}>
          <Form.Item label="搜索关键词">
            <Input
              placeholder="输入关键词搜索文档..."
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              onPressEnter={handleSearchDocs}
              prefix={<SearchOutlined />}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SearchOutlined />} block>
              搜索
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AnnotationPage;
