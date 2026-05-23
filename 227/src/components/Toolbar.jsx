export function Toolbar({ 
  tool, 
  setTool, 
  color, 
  setColor, 
  strokeWidth, 
  setStrokeWidth,
  currentPage,
  numPages,
  prevPage,
  nextPage,
  zoom,
  zoomIn,
  zoomOut,
  addPage
}) {
  const tools = [
    { id: 'select', icon: '🖱️', label: '选择' },
    { id: 'text', icon: 'T', label: '文本' },
    { id: 'highlight', icon: '🖍️', label: '高亮' },
    { id: 'rect', icon: '▢', label: '矩形' },
    { id: 'ellipse', icon: '○', label: '椭圆' },
    { id: 'arrow', icon: '➤', label: '箭头' },
    { id: 'line', icon: '／', label: '直线' }
  ];

  return (
    <div className="toolbar">
      <div className="tool-group">
        {tools.map(t => (
          <button
            key={t.id}
            className={`tool-btn ${tool === t.id ? 'active' : ''}`}
            onClick={() => setTool(t.id)}
            title={t.label}
          >
            {t.icon}
          </button>
        ))}
      </div>

      <div className="tool-group">
        <label>颜色:</label>
        <input
          type="color"
          className="color-picker"
          value={color}
          onChange={(e) => setColor(e.target.value)}
        />
      </div>

      <div className="tool-group">
        <label>粗细:</label>
        <input
          type="range"
          className="size-slider"
          min="1"
          max="20"
          value={strokeWidth}
          onChange={(e) => setStrokeWidth(Number(e.target.value))}
        />
        <span>{strokeWidth}</span>
      </div>

      <div className="tool-group">
        <div className="zoom-controls">
          <button onClick={zoomOut}>-</button>
          <span>{Math.round(zoom * 100)}%</span>
          <button onClick={zoomIn}>+</button>
        </div>
      </div>

      <div className="tool-group">
        <div className="page-navigation">
          <button onClick={prevPage} disabled={currentPage <= 1}>
            ◀
          </button>
          <span>
            {currentPage} / {numPages}
          </span>
          <button onClick={nextPage} disabled={currentPage >= numPages}>
            ▶
          </button>
        </div>
      </div>

      <div className="tool-group">
        <button className="tool-btn" onClick={addPage} title="添加页面">
          ➕ 页面
        </button>
      </div>
    </div>
  );
}
