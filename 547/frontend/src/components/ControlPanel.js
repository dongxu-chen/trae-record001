import React from 'react';

function ControlPanel({
  settings,
  onSettingsChange,
  onFileUpload,
  onGenerate,
  onLoadSample,
  status,
  isProcessing,
  demFile,
  fileInputRef
}) {
  return (
    <>
      <div className="control-group">
        <h3>📁 数据导入</h3>
        <label className="file-upload">
          <input
            type="file"
            accept=".tif,.tiff,.asc,.dem,.json,.geojson"
            onChange={onFileUpload}
            ref={fileInputRef}
          />
          <div>点击或拖拽上传DEM文件</div>
          <div style={{ fontSize: '12px', color: '#999', marginTop: '5px' }}>
            支持 TIFF, ASC, DEM, GeoJSON 格式
          </div>
        </label>
        {demFile && (
          <div className="file-info">
            ✓ {demFile.name}
          </div>
        )}
        <button
          className="btn"
          style={{ marginTop: '10px', background: '#4CAF50', color: 'white' }}
          onClick={onLoadSample}
          disabled={isProcessing}
        >
          📊 加载示例数据
        </button>
      </div>

      <div className="control-group">
        <h3>⚙️ 等高线参数</h3>
        <div className="form-group">
          <label>等高距 (米)</label>
          <input
            type="number"
            min="1"
            max="1000"
            value={settings.interval}
            onChange={(e) => onSettingsChange('interval', Number(e.target.value))}
          />
        </div>
        <div className="form-group">
          <label>
            最小长度过滤: <span className="value-display">{settings.minLength} 个点</span>
          </label>
          <input
            type="range"
            min="2"
            max="20"
            step="1"
            value={settings.minLength}
            onChange={(e) => onSettingsChange('minLength', Number(e.target.value))}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#999' }}>
            <span>不过滤</span>
            <span>严格过滤</span>
          </div>
        </div>
        <div className="form-group">
          <label>
            平滑程度: <span className="value-display">{settings.smoothing}</span>
          </label>
          <input
            type="range"
            min="0"
            max="5"
            step="0.5"
            value={settings.smoothing}
            onChange={(e) => onSettingsChange('smoothing', Number(e.target.value))}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#999' }}>
            <span>原始</span>
            <span>平滑</span>
          </div>
        </div>
        <div className="form-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={settings.adaptiveSmoothing}
              onChange={(e) => onSettingsChange('adaptiveSmoothing', e.target.checked)}
            />
            自适应平滑（高梯度地形减少平滑）
          </label>
        </div>
      </div>

      <div className="control-group">
        <h3>🏷️ 标注设置</h3>
        <div className="form-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={settings.enableLabels}
              onChange={(e) => onSettingsChange('enableLabels', e.target.checked)}
            />
            启用高程标注
          </label>
        </div>
        {settings.enableLabels && (
          <div className="form-group">
            <label>标注间隔 (每N条等高线)</label>
            <input
              type="number"
              min="1"
              max="20"
              value={settings.labelInterval}
              onChange={(e) => onSettingsChange('labelInterval', Number(e.target.value))}
            />
          </div>
        )}
      </div>

      <button
        className="btn btn-primary"
        onClick={onGenerate}
        disabled={isProcessing}
      >
        {isProcessing ? '⏳ 处理中...' : '🚀 生成等高线'}
      </button>

      {status.message && (
        <div className={`status ${status.type}`}>
          {status.type === 'error' && '❌ '}
          {status.type === 'success' && '✅ '}
          {status.message}
        </div>
      )}

      <div className="control-group" style={{ marginTop: '20px', fontSize: '12px', color: '#666' }}>
        <h3>💡 使用说明</h3>
        <ul style={{ paddingLeft: '20px', lineHeight: '1.6' }}>
          <li>上传DEM高程数据文件或使用示例数据</li>
          <li>调整等高距控制等高线密度</li>
          <li>最小长度过滤可移除平坦区域短假线</li>
          <li>自适应平滑：陡坡保留细节，平坡更平滑</li>
          <li>标注沿等高线方向旋转，提升可读性</li>
          <li>3D地形视图：拖拽旋转，滚轮缩放</li>
          <li>动画模式：动态绘制等高线生成过程</li>
          <li>导出GeoJSON：支持2D/3D格式，GIS无缝对接</li>
        </ul>
      </div>
    </>
  );
}

export default ControlPanel;
