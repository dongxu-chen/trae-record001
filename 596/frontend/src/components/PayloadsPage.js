import React, { useState, useEffect } from 'react';
import { scanAPI } from '../services/api';

function PayloadsPage() {
  const [activeType, setActiveType] = useState('sql_injection');
  const [payloads, setPayloads] = useState([]);
  const [loading, setLoading] = useState(false);

  const payloadTypes = [
    { id: 'sql_injection', name: 'SQL注入' },
    { id: 'xxe', name: 'XXE注入' },
    { id: 'idor', name: 'IDOR' },
  ];

  useEffect(() => {
    loadPayloads(activeType);
  }, [activeType]);

  const loadPayloads = async (type) => {
    setLoading(true);
    try {
      const data = await scanAPI.getPayloads(type);
      setPayloads(data.payloads || []);
    } catch (error) {
      console.error('Failed to load payloads:', error);
      setPayloads([]);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      alert('已复制到剪贴板!');
    });
  };

  return (
    <div className="card">
      <h2 className="card-title">📚 漏洞载荷库</h2>

      <div className="tabs">
        {payloadTypes.map(type => (
          <div
            key={type.id}
            className={`tab ${activeType === type.id ? 'active' : ''}`}
            onClick={() => setActiveType(type.id)}
          >
            {type.name} ({payloads.length})
          </div>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <div className="loading-spinner"></div>
          <p>加载中...</p>
        </div>
      ) : (
        <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
          {payloads.map((payload, index) => (
            <div
              key={index}
              style={{
                background: '#f8f9fa',
                padding: '12px',
                marginBottom: '8px',
                borderRadius: '8px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                gap: '12px',
              }}
            >
              <pre
                style={{
                  margin: 0,
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  flex: 1,
                }}
              >
                {payload}
              </pre>
              <button
                onClick={() => copyToClipboard(payload)}
                style={{
                  padding: '6px 12px',
                  background: '#667eea',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
              >
                复制
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default PayloadsPage;
