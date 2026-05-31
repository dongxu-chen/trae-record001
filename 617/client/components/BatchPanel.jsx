import React from 'react';

function BatchPanel({
  config,
  onConfigChange,
  batchUrls,
  onBatchUrlsChange,
  batchResults,
  onBatchGenerate,
  batchLoading,
  sitemapUrl,
  onSitemapUrlChange,
  onParseSitemap,
  sitemapLoading,
  error,
  animationTypes
}) {
  const addUrl = () => {
    const input = document.getElementById('batch-url-input');
    if (input && input.value.trim()) {
      const newUrls = [...batchUrls, input.value.trim()];
      onBatchUrlsChange(newUrls);
      input.value = '';
    }
  };

  const removeUrl = (index) => {
    const newUrls = batchUrls.filter((_, i) => i !== index);
    onBatchUrlsChange(newUrls);
  };

  const bulkAddUrls = () => {
    const input = prompt('请输入URL列表（每行一个）：');
    if (input) {
      const urls = input.split('\n')
        .map(u => u.trim())
        .filter(u => u.startsWith('http'));
      if (urls.length > 0) {
        onBatchUrlsChange([...batchUrls, ...urls]);
      }
    }
  };

  const downloadAllResults = () => {
    const successResults = batchResults.filter(r => r.success);
    successResults.forEach(result => {
      const htmlBlob = new Blob([result.html], { type: 'text/html' });
      const cssBlob = new Blob([result.css], { type: 'text/css' });
      
      const htmlUrl = URL.createObjectURL(htmlBlob);
      const cssUrl = URL.createObjectURL(cssBlob);
      
      const htmlLink = document.createElement('a');
      htmlLink.href = htmlUrl;
      htmlLink.download = `${result.name}-skeleton.html`;
      htmlLink.click();
      
      const cssLink = document.createElement('a');
      cssLink.href = cssUrl;
      cssLink.download = `${result.name}-skeleton.css`;
      cssLink.click();
      
      URL.revokeObjectURL(htmlUrl);
      URL.revokeObjectURL(cssUrl);
    });
  };

  return (
    <div className="batch-panel">
      <div className="config-panel">
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
        
        <div className="config-section">
          <h3>站点地图解析</h3>
          <div className="form-group">
            <label>输入sitemap.xml URL</label>
            <div className="url-input-wrapper">
              <input
                id="sitemap-url-input"
                type="text"
                placeholder="https://example.com/sitemap.xml"
                value={sitemapUrl}
                onChange={(e) => onSitemapUrlChange(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && onParseSitemap()}
              />
              <button
                className="generate-btn"
                onClick={onParseSitemap}
                disabled={sitemapLoading || !sitemapUrl}
              >
                {sitemapLoading ? '解析中...' : '解析'}
              </button>
            </div>
          </div>
        </div>
        
        <div className="config-section">
          <h3>URL列表</h3>
          <div className="form-group">
            <div className="url-input-wrapper">
              <input
                id="batch-url-input"
                type="text"
                placeholder="https://example.com/page"
                onKeyDown={(e) => e.key === 'Enter' && addUrl()}
              />
              <button
                className="generate-btn"
                onClick={addUrl}
              >
                添加
              </button>
            </div>
          </div>
          
          <div className="form-group">
            <button
              className="action-btn"
              style={{ width: '100%', marginBottom: '8px' }}
              onClick={bulkAddUrls}
            >
              📋 批量添加URL
            </button>
          </div>
          
          <div className="url-list">
            {batchUrls.length === 0 ? (
              <div className="empty-url-list">
                暂无URL，请添加或解析站点地图
              </div>
            ) : (
              <div className="url-items">
                {batchUrls.map((url, index) => (
                  <div key={index} className="url-item">
                    <span className="url-index">{index + 1}</span>
                    <span className="url-text">{url}</span>
                    <button
                      className="remove-url-btn"
                      onClick={() => removeUrl(index)}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {batchUrls.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <button
                className="generate-btn"
                style={{ width: '100%' }}
                onClick={onBatchGenerate}
                disabled={batchLoading}
              >
                {batchLoading ? `生成中... (${batchResults.length}/${batchUrls.length})` : `批量生成 (${batchUrls.length}个页面)`}
              </button>
            </div>
          )}
        </div>
        
        <div className="config-section">
          <h3>设备类型</h3>
          <div className="form-group">
            <div className="device-selector">
              <button
                className={`device-btn ${config.device === 'desktop' ? 'active' : ''}`}
                onClick={() => onConfigChange('device', 'desktop')}
              >
                💻 桌面端
              </button>
              <button
                className={`device-btn ${config.device === 'mobile' ? 'active' : ''}`}
                onClick={() => onConfigChange('device', 'mobile')}
              >
                📱 移动端
              </button>
            </div>
          </div>
        </div>
        
        <div className="config-section">
          <h3>动画效果</h3>
          <div className="form-group">
            <div className="toggle-group">
              <div className="toggle-item">
                <span>启用骨架动画</span>
                <div
                  className={`toggle-switch ${config.animation ? 'active' : ''}`}
                  onClick={() => onConfigChange('animation', !config.animation)}
                />
              </div>
            </div>
          </div>
          
          {config.animation && (
            <div className="form-group">
              <label>动画类型</label>
              <select
                className="select-input"
                value={config.animationType}
                onChange={(e) => onConfigChange('animationType', e.target.value)}
              >
                {animationTypes.map(type => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
          )}
          
          {config.animation && (
            <div className="form-group">
              <label>动画速度: {config.animationSpeed}s</label>
              <input
                type="range"
                min="0.5"
                max="3"
                step="0.1"
                value={config.animationSpeed}
                onChange={(e) => onConfigChange('animationSpeed', parseFloat(e.target.value))}
                className="range-input"
              />
            </div>
          )}
        </div>
      </div>
      
      <div className="batch-results-panel">
        <div className="preview-header">
          <h2>批量生成结果</h2>
          {batchResults.filter(r => r.success).length > 0 && (
            <button
              className="action-btn primary"
              onClick={downloadAllResults}
            >
              ⬇️ 下载全部
            </button>
          )}
        </div>
        
        {batchResults.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📦</div>
            <p>添加URL后点击"批量生成"<br />生成骨架屏</p>
          </div>
        ) : (
          <div className="batch-results">
            {batchResults.map((result, index) => (
              <div key={index} className={`batch-result-item ${result.success ? 'success' : 'error'}`}>
                <div className="result-header">
                  <span className="result-index">{index + 1}</span>
                  <span className="result-name">{result.name}</span>
                  {result.success ? (
                    <span className="result-status success">✓ 成功</span>
                  ) : (
                    <span className="result-status error">✗ 失败</span>
                  )}
                </div>
                <div className="result-url">{result.url}</div>
                {result.success ? (
                  <div className="result-actions">
                    <button
                      className="action-btn"
                      onClick={() => {
                        const htmlBlob = new Blob([result.html], { type: 'text/html' });
                        const url = URL.createObjectURL(htmlBlob);
                        window.open(url, '_blank');
                      }}
                    >
                      👁️ 预览
                    </button>
                    <button
                      className="action-btn"
                      onClick={() => {
                        const htmlBlob = new Blob([result.html], { type: 'text/html' });
                        const cssBlob = new Blob([result.css], { type: 'text/css' });
                        const htmlUrl = URL.createObjectURL(htmlBlob);
                        const cssUrl = URL.createObjectURL(cssBlob);
                        
                        const htmlLink = document.createElement('a');
                        htmlLink.href = htmlUrl;
                        htmlLink.download = `${result.name}-skeleton.html`;
                        htmlLink.click();
                        
                        const cssLink = document.createElement('a');
                        cssLink.href = cssUrl;
                        cssLink.download = `${result.name}-skeleton.css`;
                        cssLink.click();
                      }}
                    >
                      ⬇️ 下载
                    </button>
                    <button
                      className="action-btn"
                      onClick={() => {
                        navigator.clipboard.writeText(result.html + '\n\n<style>\n' + result.css + '\n</style>');
                        alert('已复制到剪贴板！');
                      }}
                    >
                      📋 复制
                    </button>
                  </div>
                ) : (
                  <div className="result-error">{result.error}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default BatchPanel;
