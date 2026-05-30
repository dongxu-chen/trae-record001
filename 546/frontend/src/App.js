import React, { useState } from 'react';
import './App.css';
import ValidationPanel from './components/ValidationPanel';
import ComparisonPanel from './components/ComparisonPanel';
import ReportPanel from './components/ReportPanel';
import MockPanel from './components/MockPanel';
import CompatibilityPanel from './components/CompatibilityPanel';
import FixPanel from './components/FixPanel';

function App() {
  const [activeTab, setActiveTab] = useState('validation');
  const [openApiSpec, setOpenApiSpec] = useState('');
  const [parsedEndpoints, setParsedEndpoints] = useState([]);
  const [apiInfo, setApiInfo] = useState(null);

  return (
    <div className="App">
      <header className="App-header">
        <h1>API响应校验工具</h1>
        <p className="subtitle">基于OpenAPI规范的响应结构校验与多环境对比</p>
      </header>

      <div className="main-container">
        <div className="left-panel">
          <div className="panel">
            <h3>OpenAPI规范</h3>
            <textarea
              className="spec-textarea"
              placeholder="粘贴OpenAPI 3.0规范内容 (YAML或JSON)..."
              value={openApiSpec}
              onChange={(e) => setOpenApiSpec(e.target.value)}
            />
            <button 
              className="btn btn-primary"
              onClick={() => parseOpenApiSpec(openApiSpec, setParsedEndpoints, setApiInfo)}
            >
              解析规范
            </button>
            
            {apiInfo && (
              <div className="api-info">
                <h4>{apiInfo.title} ({apiInfo.version})</h4>
                {apiInfo.description && <p>{apiInfo.description}</p>}
              </div>
            )}
          </div>

          {parsedEndpoints.length > 0 && (
            <div className="panel">
              <h3>API端点列表</h3>
              <div className="endpoint-list">
                {parsedEndpoints.map((ep, idx) => (
                  <div key={idx} className="endpoint-item">
                    <span className={`method method-${ep.method.toLowerCase()}`}>
                      {ep.method}
                    </span>
                    <span className="endpoint-path">{ep.path}</span>
                    {ep.summary && <span className="endpoint-summary">{ep.summary}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="right-panel">
          <div className="tabs">
            <button 
              className={`tab ${activeTab === 'validation' ? 'active' : ''}`}
              onClick={() => setActiveTab('validation')}
            >
              响应校验
            </button>
            <button 
              className={`tab ${activeTab === 'comparison' ? 'active' : ''}`}
              onClick={() => setActiveTab('comparison')}
            >
              环境对比
            </button>
            <button 
              className={`tab ${activeTab === 'report' ? 'active' : ''}`}
              onClick={() => setActiveTab('report')}
            >
              差异报告
            </button>
            <button 
              className={`tab ${activeTab === 'mock' ? 'active' : ''}`}
              onClick={() => setActiveTab('mock')}
            >
              Mock生成
            </button>
            <button 
              className={`tab ${activeTab === 'compatibility' ? 'active' : ''}`}
              onClick={() => setActiveTab('compatibility')}
            >
              兼容检测
            </button>
            <button 
              className={`tab ${activeTab === 'fix' ? 'active' : ''}`}
              onClick={() => setActiveTab('fix')}
            >
              修复建议
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'validation' && (
              <ValidationPanel 
                openApiSpec={openApiSpec} 
                endpoints={parsedEndpoints}
              />
            )}
            {activeTab === 'comparison' && (
              <ComparisonPanel 
                openApiSpec={openApiSpec}
                endpoints={parsedEndpoints}
              />
            )}
            {activeTab === 'report' && (
              <ReportPanel 
                openApiSpec={openApiSpec}
                endpoints={parsedEndpoints}
              />
            )}
            {activeTab === 'mock' && (
              <MockPanel 
                openApiSpec={openApiSpec}
                endpoints={parsedEndpoints}
              />
            )}
            {activeTab === 'compatibility' && (
              <CompatibilityPanel 
                openApiSpec={openApiSpec}
                endpoints={parsedEndpoints}
              />
            )}
            {activeTab === 'fix' && (
              <FixPanel 
                openApiSpec={openApiSpec}
                endpoints={parsedEndpoints}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

async function parseOpenApiSpec(spec, setEndpoints, setApiInfo) {
  if (!spec.trim()) {
    alert('请输入OpenAPI规范内容');
    return;
  }

  try {
    const response = await fetch('/api/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ openApiSpec: spec })
    });

    const data = await response.json();
    if (response.ok) {
      setEndpoints(data.endpoints || []);
      setApiInfo({
        title: data.title,
        version: data.version,
        description: data.description
      });
    } else {
      alert('解析失败: ' + data.error);
    }
  } catch (error) {
    alert('请求失败: ' + error.message);
  }
}

export default App;
