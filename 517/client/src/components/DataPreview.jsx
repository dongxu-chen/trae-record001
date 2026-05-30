import { useState, useEffect, useCallback, useRef } from 'react';
import { maskDataWithPermission } from '../utils/maskingUtils.js';

const DataPreview = ({ rules, permission = 'normal', onAuditLog }) => {
  const [inputData, setInputData] = useState({
    phone: '13800138000',
    idCard: '110101199001011234',
    email: 'example@email.com',
    name: '张三',
    address: '北京市朝阳区某某街道123号'
  });
  const [result, setResult] = useState(null);
  const hasLoggedRef = useRef(false);

  const processMasking = useCallback(async () => {
    try {
      const maskedResult = maskDataWithPermission(inputData, rules, permission);
      setResult({
        original: inputData,
        result: maskedResult
      });
    } catch (error) {
      console.error('脱敏处理失败:', error);
    }
  }, [inputData, rules, permission]);

  useEffect(() => {
    const timer = setTimeout(() => {
      processMasking();
    }, 200);

    return () => clearTimeout(timer);
  }, [processMasking]);

  useEffect(() => {
    if (result && !hasLoggedRef.current && onAuditLog) {
      const sensitiveFields = Object.entries(rules)
        .filter(([_, rule]) => rule.enabled)
        .map(([field]) => field);
      
      if (sensitiveFields.length > 0) {
        hasLoggedRef.current = true;
        onAuditLog({
          action: 'mask',
          sensitiveFields,
          dataKeys: Object.keys(inputData)
        });
      }
    }
  }, [result, rules, inputData, onAuditLog]);

  useEffect(() => {
    hasLoggedRef.current = false;
  }, [permission]);

  const handleInputChange = (field, value) => {
    setInputData(prev => ({
      ...prev,
      [field]: value
    }));
    hasLoggedRef.current = false;
  };

  const enabledFields = Object.entries(rules).filter(([_, rule]) => rule.enabled);

  return (
    <div>
      <div className="preview-section">
        <h3>📝 输入原始数据</h3>
        {enabledFields.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">⚠️</div>
            <p>请先开启至少一个脱敏规则</p>
          </div>
        ) : (
          <div className="input-grid">
            {enabledFields.map(([key, rule]) => (
              <div key={key} className="input-row">
                <label>{rule.label}</label>
                <input
                  type="text"
                  className="data-input"
                  value={inputData[key] || ''}
                  onChange={(e) => handleInputChange(key, e.target.value)}
                  placeholder={rule.placeholder || `请输入${rule.label}`}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {result && enabledFields.length > 0 && (
        <div className="preview-section">
          <h3>✅ 脱敏结果对比</h3>
          <table className="comparison-table">
            <thead>
              <tr>
                <th>字段</th>
                <th>原始值</th>
                <th>脱敏后</th>
              </tr>
            </thead>
            <tbody>
              {enabledFields.map(([key, rule]) => (
                <tr key={key}>
                  <td>
                    <strong>{rule.label}</strong>
                    <div style={{ marginTop: '4px' }}>
                      <span className={`method-badge ${rule.method}`}>
                        {rule.method}
                      </span>
                    </div>
                  </td>
                  <td className="original-col">{result.original[key]}</td>
                  <td className="masked-col">{result.result[key]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {result && enabledFields.length > 0 && (
        <div className="preview-section">
          <h3>📋 JSON 输出</h3>
          <JsonViewer data={result.result} />
        </div>
      )}
    </div>
  );
};

const JsonViewer = ({ data }) => {
  const formatJson = (obj, indent = 0) => {
    const spaces = '  '.repeat(indent);
    const nextSpaces = '  '.repeat(indent + 1);
    
    if (typeof obj !== 'object' || obj === null) {
      if (typeof obj === 'string') {
        return <span className="json-string">"{obj}"</span>;
      }
      if (typeof obj === 'number') {
        return <span className="json-number">{obj}</span>;
      }
      return <span>{String(obj)}</span>;
    }

    const isArray = Array.isArray(obj);
    const entries = Object.entries(obj);

    if (entries.length === 0) {
      return <span>{isArray ? '[]' : '{}'}</span>;
    }

    return (
      <>
        <span>{isArray ? '[' : '{'}</span>
        <div style={{ paddingLeft: '20px' }}>
          {entries.map(([key, value], index) => (
            <div key={key}>
              {!isArray && (
                <>
                  <span className="json-key">"{key}"</span>
                  <span>: </span>
                </>
              )}
              {formatJson(value, indent + 1)}
              {index < entries.length - 1 && <span>,</span>}
            </div>
          ))}
        </div>
        <span>{spaces}{isArray ? ']' : '}'}</span>
      </>
    );
  };

  return (
    <div className="json-viewer">
      {formatJson(data)}
    </div>
  );
};

export default DataPreview;
