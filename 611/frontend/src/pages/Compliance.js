import React, { useState, useEffect } from 'react';
import { mockData } from '../services/api';

const Compliance = () => {
  const [violations, setViolations] = useState([]);
  const [filteredViolations, setFilteredViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    severity: '',
    resourceType: '',
    ruleId: '',
  });
  const [summary, setSummary] = useState(null);

  const checkCompliance = () => {
    const allViolations = [];
    const rules = mockData.rules.filter((r) => r.enabled);

    mockData.resources.forEach((resource) => {
      rules.forEach((rule) => {
        const violation = checkRule(rule, resource);
        if (violation) {
          allViolations.push(violation);
        }
      });
    });

    setViolations(allViolations);
    setFilteredViolations(allViolations);

    const nonCompliantResources = new Set(allViolations.map((v) => v.resourceId)).size;
    setSummary({
      totalResources: mockData.resources.length,
      compliant: mockData.resources.length - nonCompliantResources,
      nonCompliant: nonCompliantResources,
      complianceRate: ((mockData.resources.length - nonCompliantResources) / mockData.resources.length) * 100,
      totalViolations: allViolations.length,
    });

    setLoading(false);
  };

  const checkRule = (rule, resource) => {
    const tags = resource.tags;

    switch (rule.type) {
      case 'required_tag':
        if (!tags[rule.key]) {
          return {
            id: `${resource.id}-${rule.id}`,
            resourceId: resource.id,
            resourceName: resource.name,
            resourceType: resource.type,
            accountId: resource.accountId,
            accountName: resource.accountName,
            ruleId: rule.id,
            ruleName: rule.name,
            severity: rule.severity,
            message: '缺少必填标签',
            tagKey: rule.key,
            expected: `${rule.key} 标签必须存在`,
          };
        }
        break;

      case 'forbidden_tag':
        if (tags[rule.key]) {
          return {
            id: `${resource.id}-${rule.id}`,
            resourceId: resource.id,
            resourceName: resource.name,
            resourceType: resource.type,
            accountId: resource.accountId,
            accountName: resource.accountName,
            ruleId: rule.id,
            ruleName: rule.name,
            severity: rule.severity,
            message: '存在禁止的标签',
            tagKey: rule.key,
            expected: `${rule.key} 标签不应存在`,
            actual: tags[rule.key],
          };
        }
        break;

      case 'tag_value_in_list':
        if (tags[rule.key] && rule.values && !rule.values.includes(tags[rule.key])) {
          return {
            id: `${resource.id}-${rule.id}`,
            resourceId: resource.id,
            resourceName: resource.name,
            resourceType: resource.type,
            accountId: resource.accountId,
            accountName: resource.accountName,
            ruleId: rule.id,
            ruleName: rule.name,
            severity: rule.severity,
            message: '标签值不在允许列表中',
            tagKey: rule.key,
            expected: `允许值: ${rule.values.join(', ')}`,
            actual: tags[rule.key],
          };
        }
        break;

      case 'tag_value_regex':
        if (tags[rule.key] && rule.value) {
          try {
            const regex = new RegExp(rule.value);
            if (!regex.test(tags[rule.key])) {
              return {
                id: `${resource.id}-${rule.id}`,
                resourceId: resource.id,
                resourceName: resource.name,
                resourceType: resource.type,
                accountId: resource.accountId,
                accountName: resource.accountName,
                ruleId: rule.id,
                ruleName: rule.name,
                severity: rule.severity,
                message: '标签值不符合格式要求',
                tagKey: rule.key,
                expected: `匹配正则: ${rule.value}`,
                actual: tags[rule.key],
              };
            }
          } catch (e) {
            console.error('Regex error:', e);
          }
        }
        break;

      case 'case_sensitive':
        Object.keys(tags).forEach((key) => {
          if (key.toLowerCase() === rule.key.toLowerCase() && key !== rule.key) {
            return {
              id: `${resource.id}-${rule.id}`,
              resourceId: resource.id,
              resourceName: resource.name,
              resourceType: resource.type,
              accountId: resource.accountId,
              accountName: resource.accountName,
              ruleId: rule.id,
              ruleName: rule.name,
              severity: rule.severity,
              message: '标签键大小写不正确',
              tagKey: key,
              expected: rule.key,
              actual: key,
            };
          }
        });
        break;
    }

    return null;
  };

  useEffect(() => {
    checkCompliance();
  }, []);

  useEffect(() => {
    let result = violations;

    if (filters.severity) {
      result = result.filter((v) => v && v.severity === filters.severity);
    }
    if (filters.resourceType) {
      result = result.filter((v) => v && v.resourceType === filters.resourceType);
    }
    if (filters.ruleId) {
      result = result.filter((v) => v && v.ruleId === filters.ruleId);
    }

    setFilteredViolations(result);
  }, [filters, violations]);

  if (loading) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '3rem' }}>检查中...</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: '700' }}>合规检查</h1>
        <button className="btn btn-success" onClick={checkCompliance}>
          🔄 重新检查
        </button>
      </div>

      {summary && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value stat-total">{summary.totalResources}</div>
            <div className="stat-label">资源总数</div>
          </div>
          <div className="stat-card">
            <div className="stat-value stat-compliant">{summary.compliant}</div>
            <div className="stat-label">合规资源</div>
          </div>
          <div className="stat-card">
            <div className="stat-value stat-noncompliant">{summary.nonCompliant}</div>
            <div className="stat-label">不合规资源</div>
          </div>
          <div className="stat-card">
            <div className="stat-value stat-rate">{summary.complianceRate.toFixed(1)}%</div>
            <div className="stat-label">合规率</div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="filter-bar">
          <div className="filter-group">
            <label>严重程度</label>
            <select
              value={filters.severity}
              onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
            >
              <option value="">全部</option>
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </div>
          <div className="filter-group">
            <label>资源类型</label>
            <select
              value={filters.resourceType}
              onChange={(e) => setFilters({ ...filters, resourceType: e.target.value })}
            >
              <option value="">全部类型</option>
              <option value="ECS">ECS</option>
              <option value="RDS">RDS</option>
              <option value="OSS">OSS</option>
            </select>
          </div>
          <div className="filter-group">
            <label>规则</label>
            <select
              value={filters.ruleId}
              onChange={(e) => setFilters({ ...filters, ruleId: e.target.value })}
            >
              <option value="">全部规则</option>
              {mockData.rules.map((rule) => (
                <option key={rule.id} value={rule.id}>
                  {rule.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span>违规列表 ({filteredViolations.filter(Boolean).length})</span>
        </div>
        {filteredViolations.filter(Boolean).length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">✅</div>
            <div>没有发现违规项</div>
          </div>
        ) : (
          <div>
            {filteredViolations.filter(Boolean).map((violation) => (
              <div key={violation.id} className="violation-item">
                <div className="violation-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className={`badge badge-${violation.severity}`}>
                      {violation.severity === 'high' ? '高' : violation.severity === 'medium' ? '中' : '低'}
                    </span>
                    <span className={`badge badge-${violation.resourceType.toLowerCase()}`}>
                      {violation.resourceType}
                    </span>
                    <strong>{violation.resourceName}</strong>
                  </div>
                  <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                    {violation.accountName}
                  </span>
                </div>
                <div className="violation-message">{violation.message}</div>
                <div className="violation-detail">
                  <div>规则: {violation.ruleName}</div>
                  <div>标签键: <code style={{ background: '#f3f4f6', padding: '0.125rem 0.375rem', borderRadius: '3px' }}>{violation.tagKey}</code></div>
                  {violation.expected && <div>期望: {violation.expected}</div>}
                  {violation.actual && <div>当前: <span style={{ color: '#dc2626' }}>{violation.actual}</span></div>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Compliance;
