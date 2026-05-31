import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { scanAPI } from '../services/api';

function ScanPage({ onScanComplete }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [scanTypes, setScanTypes] = useState([]);
  const [authTypes, setAuthTypes] = useState([]);
  const [endpoints, setEndpoints] = useState(['']);
  
  const [formData, setFormData] = useState({
    target_url: '',
    auth_type: 'none',
    auth_token: '',
    auth_headers: '',
    concurrency: 5,
    scan_types: ['sql_injection', 'xxe', 'idor', 'privilege_escalation'],
    verify_ssl: false,
    timeout: 10,
    max_retries: 3,
    false_positive_verification: true,
  });

  useEffect(() => {
    loadOptions();
  }, []);

  const loadOptions = async () => {
    try {
      const [scanTypesData, authTypesData] = await Promise.all([
        scanAPI.getScanTypes(),
        scanAPI.getAuthTypes(),
      ]);
      setScanTypes(scanTypesData.scan_types);
      setAuthTypes(authTypesData.auth_types);
    } catch (error) {
      console.error('Failed to load options:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseInt(value) : value,
    }));
  };

  const handleScanTypeChange = (scanTypeId) => {
    setFormData(prev => {
      const currentTypes = prev.scan_types;
      const newTypes = currentTypes.includes(scanTypeId)
        ? currentTypes.filter(t => t !== scanTypeId)
        : [...currentTypes, scanTypeId];
      return { ...prev, scan_types: newTypes };
    });
  };

  const addEndpoint = () => {
    setEndpoints([...endpoints, '']);
  };

  const removeEndpoint = (index) => {
    if (endpoints.length > 1) {
      setEndpoints(endpoints.filter((_, i) => i !== index));
    }
  };

  const updateEndpoint = (index, value) => {
    const newEndpoints = [...endpoints];
    newEndpoints[index] = value;
    setEndpoints(newEndpoints);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const config = {
        ...formData,
        target_url: endpoints[0] || formData.target_url,
        auth_headers: formData.auth_headers ? JSON.parse(formData.auth_headers) : null,
      };

      const validEndpoints = endpoints.filter(e => e.trim());
      
      let result;
      if (validEndpoints.length > 1) {
        result = await scanAPI.startMultipleScan(config, validEndpoints);
      } else {
        result = await scanAPI.startScan(config);
      }

      onScanComplete(result);
      navigate('/results');
    } catch (error) {
      console.error('Scan failed:', error);
      alert('扫描失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <h2>正在扫描中...</h2>
          <p>请稍候，这可能需要几分钟时间</p>
        </div>
      )}

      <div className="card">
        <h2 className="card-title">🚀 开始扫描</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">目标URL</label>
            <div className="endpoint-list">
              {endpoints.map((endpoint, index) => (
                <div key={index} className="endpoint-item">
                  <input
                    type="url"
                    placeholder="https://api.example.com/endpoint?id=1"
                    value={endpoint}
                    onChange={(e) => updateEndpoint(index, e.target.value)}
                    className="form-input"
                    style={{ margin: 0 }}
                  />
                  <button
                    type="button"
                    onClick={() => removeEndpoint(index)}
                    disabled={endpoints.length === 1}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
            <button type="button" className="add-endpoint-btn" onClick={addEndpoint}>
              + 添加更多端点
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">认证方式</label>
            <select
              name="auth_type"
              value={formData.auth_type}
              onChange={handleInputChange}
              className="form-select"
            >
              {authTypes.map(auth => (
                <option key={auth.id} value={auth.id}>{auth.name}</option>
              ))}
            </select>
          </div>

          {formData.auth_type !== 'none' && (
            <div className="auth-config">
              {formData.auth_type === 'bearer' && (
                <div className="form-group">
                  <label className="form-label">Bearer Token</label>
                  <input
                    type="text"
                    name="auth_token"
                    value={formData.auth_token}
                    onChange={handleInputChange}
                    placeholder="your-jwt-token-here"
                    className="form-input"
                  />
                </div>
              )}
              
              {formData.auth_type === 'basic' && (
                <div className="form-group">
                  <label className="form-label">Basic Auth (username:password)</label>
                  <input
                    type="text"
                    name="auth_token"
                    value={formData.auth_token}
                    onChange={handleInputChange}
                    placeholder="admin:password123"
                    className="form-input"
                  />
                </div>
              )}
              
              {formData.auth_type === 'custom' && (
                <div className="form-group">
                  <label className="form-label">自定义头部 (JSON格式)</label>
                  <textarea
                    name="auth_headers"
                    value={formData.auth_headers}
                    onChange={handleInputChange}
                    placeholder='{"X-API-Key": "your-api-key"}'
                    className="form-input"
                    rows="3"
                  />
                </div>
              )}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">扫描类型</label>
            <div className="checkbox-group">
              {scanTypes.map(scanType => (
                <label key={scanType.id} className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={formData.scan_types.includes(scanType.id)}
                    onChange={() => handleScanTypeChange(scanType.id)}
                  />
                  <span>
                    <strong>{scanType.name}</strong>
                    <small style={{ display: 'block', color: '#666' }}>
                      {scanType.description}
                    </small>
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">并发数: {formData.concurrency}</label>
            <input
              type="range"
              name="concurrency"
              min="1"
              max="20"
              value={formData.concurrency}
              onChange={handleInputChange}
              style={{ width: '100%' }}
            />
          </div>

          <div className="form-group">
            <label className="checkbox-item">
              <input
                type="checkbox"
                name="false_positive_verification"
                checked={formData.false_positive_verification}
                onChange={handleInputChange}
              />
              <span>启用误报验证</span>
            </label>
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? (
              <>
                <div className="loading-spinner"></div>
                扫描中...
              </>
            ) : (
              <>🔍 开始扫描</>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default ScanPage;
