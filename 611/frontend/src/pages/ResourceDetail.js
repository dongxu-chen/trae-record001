import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { mockData } from '../services/api';

const ResourceDetail = () => {
  const { id } = useParams();
  const [resource, setResource] = useState(null);
  const [violations, setViolations] = useState([]);
  const [suggestions, setSuggestions] = useState({});
  const [smartSuggestions, setSmartSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('info');

  const generateSmartSuggestions = (resource) => {
    const suggestions = [];
    const name = resource.name.toLowerCase();

    if (!resource.tags.Environment) {
      let envValue = 'Development';
      let confidence = 0.6;
      let reason = '默认环境推测';
      let source = 'environment_inference';

      if (name.includes('prod') || name.includes('production')) {
        envValue = 'Production';
        confidence = 0.9;
        reason = '资源名称包含 "prod" 标识，推测为生产环境';
        source = 'name_pattern';
      } else if (name.includes('dev') || name.includes('development')) {
        envValue = 'Development';
        confidence = 0.85;
        reason = '资源名称包含 "dev" 标识，推测为开发环境';
        source = 'name_pattern';
      } else if (name.includes('test') || name.includes('staging')) {
        envValue = 'Testing';
        confidence = 0.8;
        reason = '资源名称包含 "test" 标识，推测为测试环境';
        source = 'name_pattern';
      }

      suggestions.push({
        key: 'Environment',
        value: envValue,
        confidence: confidence,
        reason: reason,
        source: source,
        alternatives: ['Production', 'Development', 'Testing', 'Staging'],
      });
    }

    if (!resource.tags.Department) {
      let deptValue = 'Engineering';
      let confidence = 0.5;
      let reason = '基于资源类型推测';
      let source = 'department_inference';

      if (name.includes('finance') || name.includes('fin')) {
        deptValue = 'Finance';
        confidence = 0.85;
        reason = '资源名称包含 "finance" 标识，推测为财务部门';
        source = 'name_pattern';
      } else if (name.includes('hr') || name.includes('human')) {
        deptValue = 'HR';
        confidence = 0.85;
        reason = '资源名称包含 "hr" 标识，推测为人力资源部门';
        source = 'name_pattern';
      } else if (name.includes('sales') || name.includes('marketing')) {
        deptValue = 'Sales';
        confidence = 0.8;
        reason = '资源名称包含业务标识，推测为销售/市场部门';
        source = 'name_pattern';
      } else if (resource.type === 'ECS' || resource.type === 'RDS' || resource.type === 'OSS') {
        deptValue = 'Engineering';
        confidence = 0.7;
        reason = '技术类资源，推测为工程部门';
        source = 'resource_type';
      }

      suggestions.push({
        key: 'Department',
        value: deptValue,
        confidence: confidence,
        reason: reason,
        source: source,
        alternatives: ['Engineering', 'Finance', 'HR', 'Sales', 'Marketing', 'Operations'],
      });
    }

    if (!resource.tags.CostCenter) {
      let ccValue = 'CC001';
      let confidence = 0.5;
      let reason = '默认成本中心';
      let source = 'default';

      const ccMatch = resource.name.match(/cc(\d{3})/i);
      if (ccMatch) {
        ccValue = `CC${ccMatch[1]}`;
        confidence = 0.95;
        reason = `从资源名称中提取到成本中心编码: ${ccValue}`;
        source = 'name_extraction';
      } else if (name.includes('prod')) {
        ccValue = 'CC100';
        confidence = 0.75;
        reason = '生产环境资源，使用生产环境成本中心 CC100';
        source = 'environment_inference';
      } else if (name.includes('dev')) {
        ccValue = 'CC200';
        confidence = 0.75;
        reason = '开发环境资源，使用开发环境成本中心 CC200';
        source = 'environment_inference';
      }

      suggestions.push({
        key: 'CostCenter',
        value: ccValue,
        confidence: confidence,
        reason: reason,
        source: source,
        alternatives: ['CC001', 'CC100', 'CC200', 'CC300', 'CC400'],
      });
    }

    if (!resource.tags.Project) {
      let projValue = 'General';
      let confidence = 0.5;
      let reason = '默认项目';
      let source = 'default';

      const projMatch = resource.name.match(/project[-_]?([a-z0-9]+)/i);
      if (projMatch) {
        projValue = projMatch[1].charAt(0).toUpperCase() + projMatch[1].slice(1);
        confidence = 0.9;
        reason = `从资源名称中提取到项目标识: ${projValue}`;
        source = 'name_extraction';
      } else if (name.includes('api') || name.includes('backend')) {
        projValue = 'API-Gateway';
        confidence = 0.7;
        reason = '资源名称包含 API/Backend，推测为API网关项目';
        source = 'name_pattern';
      } else if (name.includes('web') || name.includes('frontend')) {
        projValue = 'Web-Frontend';
        confidence = 0.7;
        reason = '资源名称包含 Web/Frontend，推测为Web前端项目';
        source = 'name_pattern';
      }

      suggestions.push({
        key: 'Project',
        value: projValue,
        confidence: confidence,
        reason: reason,
        source: source,
        alternatives: ['General', 'API-Gateway', 'Web-Frontend', 'Data-Analytics', 'Mobile-App'],
      });
    }

    if (!resource.tags.Owner) {
      suggestions.push({
        key: 'Owner',
        value: 'admin@example.com',
        confidence: 0.4,
        reason: '未找到所有者信息，建议补充资源负责人',
        source: 'rule_based',
        alternatives: ['admin@example.com', 'devops@example.com', 'team-lead@example.com'],
      });
    }

    return suggestions.sort((a, b) => b.confidence - a.confidence);
  };

  useEffect(() => {
    setTimeout(() => {
      const found = mockData.resources.find((r) => r.id === id);
      setResource(found);

      if (found) {
        const resourceViolations = [];
        const resourceSuggestions = {};

        mockData.rules.filter((r) => r.enabled).forEach((rule) => {
          const violation = checkRule(rule, found);
          if (violation) {
            resourceViolations.push(violation);
          }

          if (rule.type === 'required_tag' && !found.tags[rule.key]) {
            resourceSuggestions[rule.key] = rule.values || ['Add this tag'];
          }
        });

        setViolations(resourceViolations);
        setSuggestions(resourceSuggestions);
        setSmartSuggestions(generateSmartSuggestions(found));
      }

      setLoading(false);
    }, 500);
  }, [id]);

  const checkRule = (rule, resource) => {
    const tags = resource.tags;

    switch (rule.type) {
      case 'required_tag':
        if (!tags[rule.key]) {
          return {
            id: `${resource.id}-${rule.id}`,
            ruleId: rule.id,
            ruleName: rule.name,
            severity: rule.severity,
            message: '缺少必填标签',
            tagKey: rule.key,
          };
        }
        break;

      case 'forbidden_tag':
        if (tags[rule.key]) {
          return {
            id: `${resource.id}-${rule.id}`,
            ruleId: rule.id,
            ruleName: rule.name,
            severity: rule.severity,
            message: '存在禁止的标签',
            tagKey: rule.key,
          };
        }
        break;

      case 'tag_value_in_list':
        if (tags[rule.key] && rule.values && !rule.values.includes(tags[rule.key])) {
          return {
            id: `${resource.id}-${rule.id}`,
            ruleId: rule.id,
            ruleName: rule.name,
            severity: rule.severity,
            message: '标签值不在允许列表中',
            tagKey: rule.key,
          };
        }
        break;
    }

    return null;
  };

  if (loading) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '3rem' }}>加载中...</div>
      </div>
    );
  }

  if (!resource) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>❓</div>
          <div>资源未找到</div>
          <Link to="/resources" style={{ marginTop: '1rem', display: 'inline-block' }}>
            返回资源列表
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <Link to="/resources" style={{ color: '#3b82f6', textDecoration: 'none', fontSize: '0.875rem' }}>
            ← 返回资源列表
          </Link>
          <h1 style={{ fontSize: '1.75rem', fontWeight: '700', marginTop: '0.5rem' }}>{resource.name}</h1>
        </div>
        <span className={`badge badge-${resource.type.toLowerCase()}`} style={{ fontSize: '1rem', padding: '0.5rem 1rem' }}>
          {resource.type}
        </span>
      </div>

      <div className="tabs">
        <div className={`tab ${activeTab === 'info' ? 'active' : ''}`} onClick={() => setActiveTab('info')}>
          基本信息
        </div>
        <div className={`tab ${activeTab === 'violations' ? 'active' : ''}`} onClick={() => setActiveTab('violations')}>
          违规 ({violations.length})
        </div>
        <div className={`tab ${activeTab === 'suggestions' ? 'active' : ''}`} onClick={() => setActiveTab('suggestions')}>
          智能标签建议 ({smartSuggestions.length})
        </div>
      </div>

      {activeTab === 'info' && (
        <div className="card">
          <div className="card-header">资源详情</div>
          <div className="resource-detail">
            <div>
              <div className="detail-section">
                <div className="detail-label">资源ID</div>
                <div className="detail-value" style={{ fontFamily: 'monospace' }}>{resource.id}</div>
              </div>
              <div className="detail-section">
                <div className="detail-label">资源名称</div>
                <div className="detail-value">{resource.name}</div>
              </div>
              <div className="detail-section">
                <div className="detail-label">资源类型</div>
                <div className="detail-value">{resource.type}</div>
              </div>
              <div className="detail-section">
                <div className="detail-label">区域</div>
                <div className="detail-value">{resource.region}</div>
              </div>
            </div>
            <div>
              <div className="detail-section">
                <div className="detail-label">账号</div>
                <div className="detail-value">{resource.accountName}</div>
              </div>
              <div className="detail-section">
                <div className="detail-label">状态</div>
                <div className="detail-value">
                  <span
                    style={{
                      color: resource.status === 'Running' || resource.status === 'Active' ? '#10b981' : '#6b7280',
                      fontWeight: '500',
                    }}
                  >
                    {resource.status}
                  </span>
                </div>
              </div>
              <div className="detail-section">
                <div className="detail-label">创建时间</div>
                <div className="detail-value">{new Date(resource.createdAt).toLocaleString()}</div>
              </div>
              <div className="detail-section">
                <div className="detail-label">合规状态</div>
                <div className="detail-value">
                  <span className={`badge ${violations.length === 0 ? 'badge-compliant' : 'badge-noncompliant'}`}>
                    {violations.length === 0 ? '合规' : `${violations.length} 项违规`}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="detail-section" style={{ marginTop: '1.5rem' }}>
            <div className="detail-label" style={{ marginBottom: '0.75rem' }}>当前标签</div>
            {Object.entries(resource.tags).length === 0 ? (
              <span style={{ color: '#9ca3af', fontStyle: 'italic' }}>无标签</span>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {Object.entries(resource.tags).map(([key, value]) => (
                  <span key={key} className="tag" style={{ padding: '0.5rem 0.75rem', fontSize: '0.875rem' }}>
                    <span className="tag-key">{key}:</span>
                    <span className="tag-value">{value}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'violations' && (
        <div className="card">
          <div className="card-header">违规列表</div>
          {violations.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">✅</div>
              <div>没有发现违规项</div>
            </div>
          ) : (
            <div>
              {violations.map((violation) => (
                <div key={violation.id} className="violation-item">
                  <div className="violation-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span className={`badge badge-${violation.severity}`}>
                        {violation.severity === 'high' ? '高' : violation.severity === 'medium' ? '中' : '低'}
                      </span>
                      <strong>{violation.ruleName}</strong>
                    </div>
                  </div>
                  <div className="violation-message">{violation.message}</div>
                  <div className="violation-detail">
                    <div>标签键: <code style={{ background: '#f3f4f6', padding: '0.125rem 0.375rem', borderRadius: '3px' }}>{violation.tagKey}</code></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'suggestions' && (
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>🤖 智能标签建议</span>
              <span className="badge" style={{ backgroundColor: '#e0e7ff', color: '#4f46e5', fontSize: '0.75rem' }}>
                基于资源名称/环境推测
              </span>
            </div>
          </div>
          {smartSuggestions.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🎉</div>
              <div>没有需要添加的标签建议</div>
            </div>
          ) : (
            <div>
              <div style={{ marginBottom: '1.5rem', padding: '1rem', background: '#f0fdf4', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
                <div style={{ color: '#166534', fontWeight: '500', marginBottom: '0.5rem' }}>
                  💡 智能推测说明
                </div>
                <div style={{ fontSize: '0.875rem', color: '#15803d', lineHeight: '1.6' }}>
                  系统通过分析资源名称 <code style={{ background: '#dcfce7', padding: '0.125rem 0.375rem', borderRadius: '3px', fontFamily: 'monospace' }}>{resource?.name}</code> 的命名模式、
                  资源类型特征以及环境规则，自动推测缺失的标签值。置信度越高，推测越准确。
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {smartSuggestions.map((suggestion, sIndex) => (
                  <div key={suggestion.key} style={{
                    padding: '1.25rem',
                    border: '1px solid #e5e7eb',
                    borderRadius: '12px',
                    background: '#fafafa',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#f5f5f5'}
                  onMouseLeave={(e) => e.currentTarget.style.background = '#fafafa'}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                          <span style={{ fontFamily: 'monospace', fontWeight: '600', color: '#1f2937', fontSize: '1rem' }}>
                            {suggestion.key}
                          </span>
                          <span className={`badge ${
                            suggestion.confidence >= 0.8 ? 'badge-compliant' :
                            suggestion.confidence >= 0.6 ? '' : 'badge-noncompliant'
                          }`} style={{ fontSize: '0.7rem', padding: '0.125rem 0.5rem' }}>
                            置信度 {Math.round(suggestion.confidence * 100)}%
                          </span>
                          <span className="badge" style={{ fontSize: '0.7rem', padding: '0.125rem 0.5rem', background: '#f3e8ff', color: '#7c3aed' }}>
                            {suggestion.source}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                          {suggestion.reason}
                        </div>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
                        <div style={{ width: '100px', height: '8px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${suggestion.confidence * 100}%`,
                            height: '100%',
                            background: suggestion.confidence >= 0.8 ? '#10b981' :
                                       suggestion.confidence >= 0.6 ? '#f59e0b' : '#ef4444',
                            transition: 'width 0.5s',
                          }} />
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#9ca3af', fontFamily: 'monospace' }}>
                          {Math.round(suggestion.confidence * 100)}%
                        </div>
                      </div>
                    </div>

                    <div style={{ marginBottom: '0.75rem' }}>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem', fontWeight: '500' }}>
                        推荐值：
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <span
                          className="suggestion-value"
                          style={{
                            background: '#3b82f6',
                            color: 'white',
                            fontWeight: '600',
                            padding: '0.5rem 1rem',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontSize: '0.875rem',
                            boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)',
                          }}
                          onClick={() => alert(`点击添加标签: ${suggestion.key} = ${suggestion.value}`)}
                        >
                          ✨ {suggestion.value} (推荐)
                        </span>
                      </div>
                    </div>

                    {suggestion.alternatives && suggestion.alternatives.length > 0 && (
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem', fontWeight: '500' }}>
                          其他可选值：
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                          {suggestion.alternatives.filter(a => a !== suggestion.value).map((alt, idx) => (
                            <span
                              key={idx}
                              className="suggestion-value"
                              style={{
                                background: 'white',
                                color: '#374151',
                                border: '1px solid #d1d5db',
                                padding: '0.375rem 0.75rem',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                fontSize: '0.8rem',
                              }}
                              onClick={() => alert(`点击添加标签: ${suggestion.key} = ${alt}`)}
                            >
                              {alt}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px dashed #e5e7eb' }}>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          className="btn btn-primary"
                          style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
                          onClick={() => alert(`应用标签: ${suggestion.key} = ${suggestion.value}`)}
                        >
                          ✓ 应用推荐值
                        </button>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
                          onClick={() => alert('跳过此建议')}
                        >
                          跳过
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe' }}>
                <div style={{ color: '#1e40af', fontWeight: '500', marginBottom: '0.5rem' }}>
                  📊 推测来源说明
                </div>
                <div style={{ fontSize: '0.8rem', color: '#1e3a8a', lineHeight: '1.8' }}>
                  <div><code style={{ background: '#dbeafe', padding: '0.125rem 0.375rem', borderRadius: '3px' }}>name_pattern</code>: 资源名称模式匹配</div>
                  <div><code style={{ background: '#dbeafe', padding: '0.125rem 0.375rem', borderRadius: '3px' }}>name_extraction</code>: 从资源名称中提取信息</div>
                  <div><code style={{ background: '#dbeafe', padding: '0.125rem 0.375rem', borderRadius: '3px' }}>resource_type</code>: 基于资源类型推测</div>
                  <div><code style={{ background: '#dbeafe', padding: '0.125rem 0.375rem', borderRadius: '3px' }}>environment_inference</code>: 基于环境规则推测</div>
                  <div><code style={{ background: '#dbeafe', padding: '0.125rem 0.375rem', borderRadius: '3px' }}>rule_based</code>: 基于合规规则推荐</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ResourceDetail;
