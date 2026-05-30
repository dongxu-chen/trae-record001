import React, { useState, useEffect } from 'react';
import { Card, List, Tag, Alert, Space, Button, message, Collapse } from 'antd';
import { WarningOutlined, CheckCircleOutlined, BulbOutlined, PartitionOutlined } from '@ant-design/icons';
import { slowLogAPI } from '../api/api';

const { Panel } = Collapse;

function getSeverityColor(severity) {
  const colors = {
    critical: '#cf1322',
    high: '#ff4d4f',
    medium: '#faad14',
    low: '#1890ff',
    normal: '#52c41a',
  };
  return colors[severity] || 'default';
}

function getSeverityLabel(severity) {
  const labels = {
    critical: '严重',
    high: '高',
    medium: '中',
    low: '低',
    normal: '正常'
  };
  return labels[severity] || severity?.toUpperCase() || 'MEDIUM';
}

function getSeverityClass(severity) {
  return `severity-${severity}`;
}

function Optimizations() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const response = await slowLogAPI.getOptimizations();
      if (response.data.success) {
        setData(response.data.data);
      }
    } catch (error) {
      message.error('加载优化建议失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  if (!data) return null;

  return (
    <div>
      <div style={{ marginBottom: 16, textAlign: 'right' }}>
        <Button onClick={loadData} loading={loading} type="primary">
          重新分析
        </Button>
      </div>

      <Collapse defaultActiveKey={['1', '2', '3', '4']}>
        <Panel
          header={
            <Space>
              <WarningOutlined style={{ color: '#ff4d4f' }} />
              命令优化建议
              <Tag color="red">{data.command_optimizations.length}</Tag>
            </Space>
          }
          key="1"
        >
          {data.command_optimizations.length > 0 ? (
            <List
              dataSource={data.command_optimizations}
              renderItem={(item) => (
                <List.Item className={getSeverityClass(item.severity)} style={{ paddingLeft: 12 }}>
                  <Card size="small" className="optimization-card" style={{ width: '100%' }}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Space>
                        <Tag color={getSeverityColor(item.severity)}>
                          {item.severity.toUpperCase()}
                        </Tag>
                        <strong>{item.command}</strong>
                        <Tag>执行 {item.count} 次</Tag>
                        <Tag color="orange">总耗时 {item.total_time.toFixed(2)}ms</Tag>
                      </Space>
                      <Alert
                        message={item.issue}
                        description={
                          <div>
                            <p><strong>建议:</strong> {item.suggestion}</p>
                            <p><strong>示例:</strong> <code>{item.example}</code></p>
                          </div>
                        }
                        type="warning"
                        showIcon
                      />
                    </Space>
                  </Card>
                </List.Item>
              )}
            />
          ) : (
            <Alert
              message="未发现需要优化的命令"
              description="当前慢查询日志中的命令使用都比较合理"
              type="success"
              showIcon
              icon={<CheckCircleOutlined />}
            />
          )}
        </Panel>

        <Panel
          header={
            <Space>
              <BulbOutlined style={{ color: '#faad14' }} />
              数据类型优化建议
              <Tag color="gold">{data.data_type_optimizations.length}</Tag>
            </Space>
          }
          key="2"
        >
          {data.data_type_optimizations.length > 0 ? (
            <List
              dataSource={data.data_type_optimizations}
              renderItem={(item) => (
                <List.Item className={getSeverityClass(item.severity)} style={{ paddingLeft: 12 }}>
                  <Card size="small" className="optimization-card" style={{ width: '100%' }}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Space wrap>
                        <Tag color={getSeverityColor(item.risk_level || item.severity)} style={{ fontWeight: 'bold' }}>
                          {getSeverityLabel(item.risk_level || item.severity)}
                        </Tag>
                        {item.composite_score !== undefined && (
                          <Tag color="purple">
                            综合评分: {item.composite_score?.toFixed(2)}
                          </Tag>
                        )}
                        <Tag color="magenta">{item.key}</Tag>
                        <Tag>{item.type}</Tag>
                        {item.elements !== undefined && (
                          <Tag>
                            元素数: {item.elements.toLocaleString()}
                            {item.element_exceeded && <span style={{ color: '#ff4d4f' }}> ⚠</span>}
                          </Tag>
                        )}
                        {item.total_size !== undefined && (
                          <Tag>
                            大小: {(item.total_size / 1024).toFixed(2)}KB
                            {item.size_exceeded && <span style={{ color: '#ff4d4f' }}> ⚠</span>}
                          </Tag>
                        )}
                        {item.access_count && <Tag>访问次数: {item.access_count}</Tag>}
                      </Space>
                      <Alert
                        message={item.issue}
                        description={
                          <div>
                            <p><strong>建议:</strong> {item.suggestion}</p>
                          </div>
                        }
                        type={item.severity === 'high' ? 'error' : 'warning'}
                        showIcon
                      />
                    </Space>
                  </Card>
                </List.Item>
              )}
            />
          ) : (
            <Alert
              message="未发现需要优化的数据类型"
              description="当前Key的数据结构使用都比较合理"
              type="success"
              showIcon
              icon={<CheckCircleOutlined />}
            />
          )}
        </Panel>

        <Panel
          header={
            <Space>
              <PartitionOutlined style={{ color: '#722ed1' }} />
              分片建议
              <Tag color="purple">{data.sharding_suggestions.length}</Tag>
            </Space>
          }
          key="3"
        >
          {data.sharding_suggestions.length > 0 ? (
            <List
              dataSource={data.sharding_suggestions}
              renderItem={(item) => (
                <List.Item>
                  <Card size="small" className="optimization-card" style={{ width: '100%' }}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Space>
                        <Tag color="purple">{item.type}</Tag>
                        <strong>{item.issue}</strong>
                      </Space>
                      <Alert
                        message={item.suggestion}
                        description={
                          <div>
                            {item.hot_key_count && (
                              <p>热点Key数量: {item.hot_key_count}</p>
                            )}
                            {item.large_key_count && (
                              <p>大Key数量: {item.large_key_count}</p>
                            )}
                            {item.total_large_size && (
                              <p>大Key总大小: {(item.total_large_size / 1024 / 1024).toFixed(2)}MB</p>
                            )}
                            {item.risk_distribution && (
                              <div>
                                <p>风险等级分布:</p>
                                <Space wrap>
                                  {Object.entries(item.risk_distribution).map(([level, count]) => (
                                    <Tag key={level} color={getSeverityColor(level)}>
                                      {getSeverityLabel(level)}: {count}
                                    </Tag>
                                  ))}
                                </Space>
                              </div>
                            )}
                            {item.avg_composite_score !== undefined && (
                              <p>平均综合评分: {item.avg_composite_score.toFixed(2)}</p>
                            )}
                            {item.patterns && (
                              <div>
                                <p>Key模式:</p>
                                <ul>
                                  {item.patterns.map((p, i) => (
                                    <li key={i}>{p.pattern} ({p.count}个)</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {item.sharding_strategy && (
                              <div>
                                <p><strong>分片策略:</strong></p>
                                <ul>
                                  {item.sharding_strategy.map((s, i) => (
                                    <li key={i}>{s}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {item.alternatives && (
                              <div>
                                <p><strong>替代方案:</strong></p>
                                <ul>
                                  {item.alternatives.map((a, i) => (
                                    <li key={i}>{a}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        }
                        type="info"
                        showIcon
                      />
                    </Space>
                  </Card>
                </List.Item>
              )}
            />
          ) : (
            <Alert
              message="暂无分片建议"
              description="当前数据规模和访问模式都比较合理，暂不需要分片"
              type="success"
              showIcon
              icon={<CheckCircleOutlined />}
            />
          )}
        </Panel>

        <Panel
          header={
            <Space>
              <CheckCircleOutlined style={{ color: '#52c41a' }} />
              通用建议
              <Tag color="green">{data.general_suggestions.length}</Tag>
            </Space>
          }
          key="4"
        >
          {data.general_suggestions.length > 0 ? (
            <List
              dataSource={data.general_suggestions}
              renderItem={(item) => (
                <List.Item>
                  <Alert
                    message={item.issue}
                    description={item.suggestion}
                    type="info"
                    showIcon
                    style={{ width: '100%' }}
                  />
                </List.Item>
              )}
            />
          ) : (
            <Alert
              message="Redis运行状态良好"
              description="未发现明显的性能问题"
              type="success"
              showIcon
              icon={<CheckCircleOutlined />}
            />
          )}
        </Panel>
      </Collapse>
    </div>
  );
}

export default Optimizations;
