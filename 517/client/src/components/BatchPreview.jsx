import { useState } from 'react';
import { maskDataWithPermission } from '../utils/maskingUtils.js';

const sampleBatchData = [
  {
    phone: '13800138001',
    idCard: '110101199001011231',
    email: 'user1@email.com',
    name: '张三',
    address: '北京市朝阳区某某街道123号'
  },
  {
    phone: '13900139002',
    idCard: '310101198505155678',
    email: 'user2@email.com',
    name: '李四',
    address: '上海市浦东新区某某路456号'
  },
  {
    phone: '13700137003',
    idCard: '440101199212209012',
    email: 'user3@email.com',
    name: '王五',
    address: '广州市天河区某某大道789号'
  }
];

const BatchPreview = ({ rules, permission = 'normal', onAuditLog }) => {
  const [batchData, setBatchData] = useState(JSON.stringify(sampleBatchData, null, 2));
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  const handleProcess = () => {
    try {
      setError('');
      const dataList = JSON.parse(batchData);
      
      if (!Array.isArray(dataList)) {
        throw new Error('请输入有效的JSON数组');
      }

      const maskedResults = dataList.map(data => maskDataWithPermission(data, rules, permission));
      
      setResults({
        original: dataList,
        results: maskedResults
      });

      if (onAuditLog) {
        const sensitiveFields = Object.entries(rules)
          .filter(([_, rule]) => rule.enabled)
          .map(([field]) => field);
        
        if (sensitiveFields.length > 0) {
          onAuditLog({
            action: 'mask_batch',
            sensitiveFields,
            recordCount: dataList.length
          });
        }
      }
    } catch (err) {
      setError(err.message);
      setResults(null);
    }
  };

  const handleReset = () => {
    setBatchData(JSON.stringify(sampleBatchData, null, 2));
    setResults(null);
    setError('');
  };

  const enabledFields = Object.entries(rules).filter(([_, rule]) => rule.enabled);

  return (
    <div>
      <div className="preview-section">
        <h3>📊 批量数据输入 (JSON格式)</h3>
        <div className="batch-data">
          <textarea
            value={batchData}
            onChange={(e) => setBatchData(e.target.value)}
            placeholder="请输入JSON数组格式的数据..."
          />
        </div>
        {error && (
          <div style={{ color: '#dc2626', marginTop: '8px', fontSize: '0.9rem' }}>
            ⚠️ {error}
          </div>
        )}
        <div className="batch-actions">
          <button className="btn btn-primary" onClick={handleProcess}>
            🔍 执行脱敏
          </button>
          <button className="btn btn-secondary" onClick={handleReset}>
            🔄 重置示例
          </button>
        </div>
      </div>

      {enabledFields.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">⚠️</div>
          <p>请先开启至少一个脱敏规则</p>
        </div>
      )}

      {results && enabledFields.length > 0 && (
        <div className="preview-section">
          <h3>✅ 批量脱敏结果</h3>
          <div style={{ overflowX: 'auto' }}>
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>序号</th>
                  {enabledFields.map(([key, rule]) => (
                    <th key={key}>
                      {rule.label}
                      <div style={{ marginTop: '4px' }}>
                        <span className={`method-badge ${rule.method}`}>
                          {rule.method}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.results.map((item, index) => (
                  <tr key={index}>
                    <td>{index + 1}</td>
                    {enabledFields.map(([key]) => (
                      <td key={key} className="masked-col">
                        {item[key]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {results && enabledFields.length > 0 && (
        <div className="preview-section">
          <h3>📋 批量 JSON 输出</h3>
          <div className="json-viewer">
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {JSON.stringify(results.results, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default BatchPreview;
