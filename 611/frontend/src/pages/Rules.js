import React, { useState, useEffect } from 'react';
import { mockData } from '../services/api';

const Rules = () => {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [useNaturalLanguage, setUseNaturalLanguage] = useState(true);
  const [naturalInput, setNaturalInput] = useState('');
  const [parseResult, setParseResult] = useState(null);
  const [isParsing, setIsParsing] = useState(false);
  const [newRule, setNewRule] = useState({
    id: '',
    name: '',
    type: 'required_tag',
    description: '',
    key: '',
    value: '',
    values: '',
    severity: 'medium',
    enabled: true,
  });

  const ruleTemplates = [
    { name: '必填标签', example: '所有资源必须包含 Environment 标签', type: 'required_tag' },
    { name: '禁用标签', example: '禁止使用 Owner 标签', type: 'forbidden_tag' },
    { name: '标签值枚举', example: 'Environment 标签的值必须是 [Production, Development] 之一', type: 'tag_value_in_list' },
    { name: '标签值正则', example: 'CostCenter 标签的值必须匹配正则 ^CC\\d{3}$', type: 'tag_value_regex' },
    { name: '大小写敏感', example: 'Environment 标签的值大小写敏感', type: 'case_sensitive' },
  ];

  const parseNaturalRule = (text) => {
    setIsParsing(true);
    setParseResult(null);

    setTimeout(() => {
      let result = {
        success: false,
        rule: null,
        interpretation: '',
        confidence: 0,
        warning: '',
        isValid: false,
        validationMsg: '',
      };

      const lowerText = text.toLowerCase();

      if (text.includes('必须包含') || text.includes('must have') || text.includes('must contain')) {
        const keyMatch = text.match(/(?:包含|have|contain)\s+["']?([A-Za-z_][A-Za-z0-9_-]*)["']?/);
        if (keyMatch) {
          result.success = true;
          result.rule = {
            name: `必填 ${keyMatch[1]} 标签`,
            type: 'required_tag',
            key: keyMatch[1],
            severity: 'medium',
            enabled: true,
            description: text,
          };
          result.interpretation = `解析为必填标签规则: 所有资源必须包含 ${keyMatch[1]} 标签`;
          result.confidence = 0.9;
          result.isValid = true;
        }
      } else if (text.includes('禁止') || text.includes('禁用') || text.includes('forbidden') || text.includes('not allow')) {
        const keyMatch = text.match(/(?:禁止|禁用|forbidden|not allow)(?:使用)?\s*["']?([A-Za-z_][A-Za-z0-9_-]*)["']?/);
        if (keyMatch) {
          result.success = true;
          result.rule = {
            name: `禁用 ${keyMatch[1]} 标签`,
            type: 'forbidden_tag',
            key: keyMatch[1],
            severity: 'medium',
            enabled: true,
            description: text,
          };
          result.interpretation = `解析为禁用标签规则: 禁止使用 ${keyMatch[1]} 标签`;
          result.confidence = 0.85;
          result.isValid = true;
        }
      } else if (text.includes('[') && text.includes(']') && (text.includes('之一') || text.includes('in [') || text.includes('must be'))) {
        const keyMatch = text.match(/["']?([A-Za-z_][A-Za-z0-9_-]*)["']?\s*标签/);
        const valuesMatch = text.match(/\[([^\]]+)\]/);
        if (keyMatch && valuesMatch) {
          const values = valuesMatch[1].split(',').map(v => v.trim().replace(/^["']|["']$/g, ''));
          result.success = true;
          result.rule = {
            name: `${keyMatch[1]} 标签值限制`,
            type: 'tag_value_in_list',
            key: keyMatch[1],
            values: values,
            severity: 'medium',
            enabled: true,
            description: text,
          };
          result.interpretation = `解析为标签值枚举规则: ${keyMatch[1]} 的值必须是 [${values.join(', ')}] 之一`;
          result.confidence = 0.92;
          result.isValid = true;
        }
      } else if (text.includes('正则') || text.includes('regex') || text.includes('匹配')) {
        const keyMatch = text.match(/["']?([A-Za-z_][A-Za-z0-9_-]*)["']?\s*标签/);
        const regexMatch = text.match(/(?:正则|regex|匹配)\s*["']?([^"'\s]+)["']?/);
        if (keyMatch && regexMatch) {
          result.success = true;
          result.rule = {
            name: `${keyMatch[1]} 标签格式校验`,
            type: 'tag_value_regex',
            key: keyMatch[1],
            value: regexMatch[1],
            severity: 'medium',
            enabled: true,
            description: text,
          };
          result.interpretation = `解析为正则匹配规则: ${keyMatch[1]} 的值必须匹配 ${regexMatch[1]}`;
          result.confidence = 0.88;
          result.isValid = true;
        }
      } else if (text.includes('大小写') || text.includes('case sensitive')) {
        const keyMatch = text.match(/["']?([A-Za-z_][A-Za-z0-9_-]*)["']?\s*标签/);
        if (keyMatch) {
          result.success = true;
          result.rule = {
            name: `${keyMatch[1]} 大小写敏感`,
            type: 'case_sensitive',
            key: keyMatch[1],
            severity: 'low',
            enabled: true,
            description: text,
          };
          result.interpretation = `解析为大小写敏感规则: ${keyMatch[1]} 标签的值区分大小写`;
          result.confidence = 0.95;
          result.isValid = true;
        }
      }

      if (!result.success) {
        result.interpretation = '无法识别的规则描述，请参考模板调整描述方式';
        result.confidence = 0.2;
        result.warning = '建议使用模板中的句式描述规则，或切换到手动配置模式';
      }

      setParseResult(result);

      if (result.success && result.rule) {
        setNewRule({
          ...newRule,
          ...result.rule,
          values: result.rule.values ? result.rule.values.join(', ') : '',
        });
      }

      setIsParsing(false);
    }, 800);
  };

  const applyTemplate = (template) => {
    setNaturalInput(template.example);
    setUseNaturalLanguage(true);
    parseNaturalRule(template.example);
  };

  useEffect(() => {
    setTimeout(() => {
      setRules(mockData.rules);
      setLoading(false);
    }, 500);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    const ruleToSave = {
      ...newRule,
      id: newRule.id || `rule-${Date.now()}`,
      values: newRule.values ? newRule.values.split(',').map((v) => v.trim()) : [],
    };

    if (editingRule) {
      setRules(rules.map((r) => (r.id === editingRule.id ? ruleToSave : r)));
    } else {
      setRules([...rules, ruleToSave]);
    }

    setShowModal(false);
    setEditingRule(null);
    setNewRule({
      id: '',
      name: '',
      type: 'required_tag',
      description: '',
      key: '',
      value: '',
      values: '',
      severity: 'medium',
      enabled: true,
    });
    setNaturalInput('');
    setParseResult(null);
    setUseNaturalLanguage(true);
  };

  const handleEdit = (rule) => {
    setEditingRule(rule);
    setNewRule({
      ...rule,
      values: rule.values ? rule.values.join(', ') : '',
    });
    setUseNaturalLanguage(false);
    setShowModal(true);
  };

  const handleDelete = (ruleId) => {
    setRules(rules.map((r) => (r.id === ruleId ? { ...r, enabled: false } : r)));
  };

  const toggleRule = (ruleId) => {
    setRules(rules.map((r) => (r.id === ruleId ? { ...r, enabled: !r.enabled } : r)));
  };

  const getRuleTypeName = (type) => {
    const types = {
      required_tag: '必填标签',
      forbidden_tag: '禁止标签',
      tag_value_regex: '正则匹配',
      tag_value_in_list: '值列表',
      case_sensitive: '大小写敏感',
    };
    return types[type] || type;
  };

  if (loading) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '3rem' }}>加载中...</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: '700' }}>规则管理</h1>
        <button
          className="btn btn-primary"
          onClick={() => {
            setEditingRule(null);
            setShowModal(true);
          }}
        >
          + 新建规则
        </button>
      </div>

      <div className="card">
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>状态</th>
                <th>规则名称</th>
                <th>类型</th>
                <th>标签键</th>
                <th>严重程度</th>
                <th>描述</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td>
                    <button
                      onClick={() => toggleRule(rule.id)}
                      style={{
                        width: '40px',
                        height: '20px',
                        borderRadius: '10px',
                        border: 'none',
                        cursor: 'pointer',
                        backgroundColor: rule.enabled ? '#10b981' : '#d1d5db',
                        position: 'relative',
                        transition: 'all 0.3s',
                      }}
                    >
                      <div
                        style={{
                          width: '16px',
                          height: '16px',
                          borderRadius: '50%',
                          backgroundColor: 'white',
                          position: 'absolute',
                          top: '2px',
                          left: rule.enabled ? '22px' : '2px',
                          transition: 'all 0.3s',
                        }}
                      />
                    </button>
                  </td>
                  <td style={{ fontWeight: '500' }}>{rule.name}</td>
                  <td>
                    <span className="badge" style={{ backgroundColor: '#e0e7ff', color: '#4f46e5' }}>
                      {getRuleTypeName(rule.type)}
                    </span>
                  </td>
                  <td style={{ fontFamily: 'monospace' }}>{rule.key}</td>
                  <td>
                    <span className={`badge badge-${rule.severity}`} style={{ textTransform: 'capitalize' }}>
                      {rule.severity === 'high' ? '高' : rule.severity === 'medium' ? '中' : '低'}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.875rem', color: '#6b7280', maxWidth: '300px' }}>{rule.description}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
                        onClick={() => handleEdit(rule)}
                      >
                        编辑
                      </button>
                      <button
                        className="btn btn-danger"
                        style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
                        onClick={() => handleDelete(rule.id)}
                      >
                        禁用
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '700px' }}>
            <div className="modal-header">
              <span className="modal-title">{editingRule ? '编辑规则' : '新建规则'}</span>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              {!editingRule && (
                <div style={{ marginBottom: '1.5rem' }}>
                  <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                    <button
                      type="button"
                      style={{
                        flex: 1,
                        padding: '0.75rem 1rem',
                        border: '2px solid',
                        borderRadius: '8px',
                        background: useNaturalLanguage ? '#3b82f6' : 'white',
                        color: useNaturalLanguage ? 'white' : '#374151',
                        borderColor: useNaturalLanguage ? '#3b82f6' : '#d1d5db',
                        cursor: 'pointer',
                        fontWeight: '500',
                        transition: 'all 0.2s',
                      }}
                      onClick={() => setUseNaturalLanguage(true)}
                    >
                      ✨ 自然语言配置
                    </button>
                    <button
                      type="button"
                      style={{
                        flex: 1,
                        padding: '0.75rem 1rem',
                        border: '2px solid',
                        borderRadius: '8px',
                        background: !useNaturalLanguage ? '#3b82f6' : 'white',
                        color: !useNaturalLanguage ? 'white' : '#374151',
                        borderColor: !useNaturalLanguage ? '#3b82f6' : '#d1d5db',
                        cursor: 'pointer',
                        fontWeight: '500',
                        transition: 'all 0.2s',
                      }}
                      onClick={() => setUseNaturalLanguage(false)}
                    >
                      ⚙️ 手动配置
                    </button>
                  </div>

                  {useNaturalLanguage && (
                    <div>
                      <div style={{ marginBottom: '1rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#374151' }}>
                          用自然语言描述你的规则
                        </label>
                        <div style={{ position: 'relative' }}>
                          <textarea
                            value={naturalInput}
                            onChange={(e) => setNaturalInput(e.target.value)}
                            placeholder="例如: 所有资源必须包含 Environment 标签，且值只能是 Production 或 Development"
                            rows="3"
                            style={{
                              width: '100%',
                              padding: '0.75rem',
                              border: '2px solid #e5e7eb',
                              borderRadius: '8px',
                              fontSize: '0.95rem',
                              resize: 'vertical',
                              fontFamily: 'inherit',
                              transition: 'border-color 0.2s',
                            }}
                            onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
                            onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
                          />
                          <button
                            type="button"
                            onClick={() => parseNaturalRule(naturalInput)}
                            disabled={isParsing || !naturalInput.trim()}
                            style={{
                              position: 'absolute',
                              right: '0.75rem',
                              bottom: '0.75rem',
                              padding: '0.5rem 1rem',
                              background: '#3b82f6',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              cursor: isParsing || !naturalInput.trim() ? 'not-allowed' : 'pointer',
                              fontSize: '0.875rem',
                              fontWeight: '500',
                              opacity: isParsing || !naturalInput.trim() ? 0.5 : 1,
                            }}
                          >
                            {isParsing ? '⏳ 解析中...' : '🔍 解析规则'}
                          </button>
                        </div>
                      </div>

                      <div style={{ marginBottom: '1rem' }}>
                        <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '0.5rem', fontWeight: '500' }}>
                          💡 快速模板（点击使用）：
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                          {ruleTemplates.map((template, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => applyTemplate(template)}
                              style={{
                                padding: '0.375rem 0.75rem',
                                background: '#f3f4f6',
                                border: '1px solid #e5e7eb',
                                borderRadius: '16px',
                                fontSize: '0.75rem',
                                color: '#374151',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                              }}
                              onMouseEnter={(e) => {
                                e.target.style.background = '#3b82f6';
                                e.target.style.color = 'white';
                                e.target.style.borderColor = '#3b82f6';
                              }}
                              onMouseLeave={(e) => {
                                e.target.style.background = '#f3f4f6';
                                e.target.style.color = '#374151';
                                e.target.style.borderColor = '#e5e7eb';
                              }}
                            >
                              {template.name}
                            </button>
                          ))}
                        </div>
                      </div>

                      {parseResult && (
                        <div style={{
                          padding: '1rem',
                          borderRadius: '8px',
                          background: parseResult.success ? '#f0fdf4' : '#fef2f2',
                          border: `1px solid ${parseResult.success ? '#bbf7d0' : '#fecaca'}`,
                          marginBottom: '1rem',
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <span style={{ fontSize: '1.25rem' }}>
                                {parseResult.success ? '✅' : '⚠️'}
                              </span>
                              <span style={{ fontWeight: '600', color: parseResult.success ? '#166534' : '#991b1b' }}>
                                {parseResult.success ? '解析成功' : '解析失败'}
                              </span>
                            </div>
                            <span className={`badge ${parseResult.confidence >= 0.8 ? 'badge-compliant' : parseResult.confidence >= 0.5 ? '' : 'badge-noncompliant'}`} style={{ fontSize: '0.7rem' }}>
                              置信度 {Math.round(parseResult.confidence * 100)}%
                            </span>
                          </div>
                          <div style={{ fontSize: '0.875rem', color: parseResult.success ? '#15803d' : '#b91c1c', lineHeight: '1.6' }}>
                            {parseResult.interpretation}
                          </div>
                          {parseResult.warning && (
                            <div style={{ fontSize: '0.8rem', color: '#92400e', marginTop: '0.5rem' }}>
                              ⚠️ {parseResult.warning}
                            </div>
                          )}
                          {parseResult.isValid !== undefined && (
                            <div style={{ fontSize: '0.8rem', color: parseResult.isValid ? '#166534' : '#991b1b', marginTop: '0.5rem' }}>
                              {parseResult.isValid ? '✓ 规则验证通过' : `✗ 规则验证失败: ${parseResult.validationMsg}`}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {(!useNaturalLanguage || editingRule) && (
                <>
                  <div className="form-group">
                    <label>规则名称</label>
                    <input
                      type="text"
                      value={newRule.name}
                      onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                      placeholder="例如: Required Environment Tag"
                      required
                    />
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>规则类型</label>
                      <select
                        value={newRule.type}
                        onChange={(e) => setNewRule({ ...newRule, type: e.target.value })}
                      >
                        <option value="required_tag">必填标签</option>
                        <option value="forbidden_tag">禁止标签</option>
                        <option value="tag_value_regex">正则匹配</option>
                        <option value="tag_value_in_list">值列表</option>
                        <option value="case_sensitive">大小写敏感</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>严重程度</label>
                      <select
                        value={newRule.severity}
                        onChange={(e) => setNewRule({ ...newRule, severity: e.target.value })}
                      >
                        <option value="high">高</option>
                        <option value="medium">中</option>
                        <option value="low">低</option>
                      </select>
                    </div>
                  </div>
                  <div className="form-group">
                    <label>标签键 (Tag Key)</label>
                    <input
                      type="text"
                      value={newRule.key}
                      onChange={(e) => setNewRule({ ...newRule, key: e.target.value })}
                      placeholder="例如: Environment"
                      required
                    />
                  </div>
                  {(newRule.type === 'tag_value_regex') && (
                    <div className="form-group">
                      <label>正则表达式</label>
                      <input
                        type="text"
                        value={newRule.value}
                        onChange={(e) => setNewRule({ ...newRule, value: e.target.value })}
                        placeholder="例如: ^CC\d{3}$"
                      />
                    </div>
                  )}
                  {(newRule.type === 'tag_value_in_list' || newRule.type === 'required_tag') && (
                    <div className="form-group">
                      <label>允许的值 (用逗号分隔)</label>
                      <input
                        type="text"
                        value={newRule.values}
                        onChange={(e) => setNewRule({ ...newRule, values: e.target.value })}
                        placeholder="例如: Production, Development, Testing"
                      />
                    </div>
                  )}
                  <div className="form-group">
                    <label>描述</label>
                    <textarea
                      value={newRule.description}
                      onChange={(e) => setNewRule({ ...newRule, description: e.target.value })}
                      placeholder="规则描述..."
                      rows="3"
                    />
                  </div>
                </>
              )}

              {useNaturalLanguage && !editingRule && parseResult && parseResult.success && (
                <div style={{
                  padding: '1rem',
                  background: '#fafafa',
                  borderRadius: '8px',
                  border: '1px solid #e5e7eb',
                  marginBottom: '1rem',
                }}>
                  <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '0.5rem', fontWeight: '500' }}>
                    🔍 解析生成的规则（可修改）：
                  </div>
                  <div className="form-row">
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label>规则类型</label>
                      <select
                        value={newRule.type}
                        onChange={(e) => setNewRule({ ...newRule, type: e.target.value })}
                      >
                        <option value="required_tag">必填标签</option>
                        <option value="forbidden_tag">禁止标签</option>
                        <option value="tag_value_regex">正则匹配</option>
                        <option value="tag_value_in_list">值列表</option>
                        <option value="case_sensitive">大小写敏感</option>
                      </select>
                    </div>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label>严重程度</label>
                      <select
                        value={newRule.severity}
                        onChange={(e) => setNewRule({ ...newRule, severity: e.target.value })}
                      >
                        <option value="high">高</option>
                        <option value="medium">中</option>
                        <option value="low">低</option>
                      </select>
                    </div>
                  </div>
                  <div className="form-group">
                    <label>标签键 (Tag Key)</label>
                    <input
                      type="text"
                      value={newRule.key}
                      onChange={(e) => setNewRule({ ...newRule, key: e.target.value })}
                    />
                  </div>
                </div>
              )}

              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  取消
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={useNaturalLanguage && !editingRule && (!parseResult || !parseResult.success)}
                  style={{
                    opacity: useNaturalLanguage && !editingRule && (!parseResult || !parseResult.success) ? 0.5 : 1,
                    cursor: useNaturalLanguage && !editingRule && (!parseResult || !parseResult.success) ? 'not-allowed' : 'pointer',
                  }}
                >
                  {editingRule ? '保存' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Rules;
