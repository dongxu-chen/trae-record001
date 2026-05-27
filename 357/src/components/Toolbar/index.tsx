import React, { useRef, useState } from 'react';
import {
  BarChart3,
  LineChart,
  PieChart,
  TrendingUp,
  Circle,
  Download,
  Upload,
  RotateCcw,
  RotateCw,
  Undo2,
  Redo2,
  Sun,
  Moon,
} from 'lucide-react';
import type { ChartType } from '@/types/theme';
import { useChartType, useThemeStore, useThemeActions, useIsDarkMode } from '@/store/useThemeStore';
import './index.less';

const chartTypes: { type: ChartType; label: string; icon: React.ReactNode }[] = [
  { type: 'line', label: '折线图', icon: <LineChart size={16} /> },
  { type: 'bar', label: '柱状图', icon: <BarChart3 size={16} /> },
  { type: 'area', label: '面积图', icon: <TrendingUp size={16} /> },
  { type: 'pie', label: '饼图', icon: <PieChart size={16} /> },
  { type: 'scatter', label: '散点图', icon: <Circle size={16} /> },
];

const Toolbar: React.FC = () => {
  const chartType = useChartType();
  const isDarkMode = useIsDarkMode();
  const { setChartType, resetTheme, undo, redo, importTheme, exportTheme, toggleDarkMode } = useThemeActions();
  const canUndo = useThemeStore((state) => state.historyIndex > 0);
  const canRedo = useThemeStore(
    (state) => state.historyIndex < state.history.length - 1,
  );
  const [importError, setImportError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExport = (format: 'pretty' | 'minified') => {
    const json = exportTheme(format);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chart-theme-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const success = importTheme(text);
      if (success) {
        setImportError(null);
      } else {
        setImportError('主题文件格式不正确');
        setTimeout(() => setImportError(null), 3000);
      }
    } catch {
      setImportError('文件读取失败');
      setTimeout(() => setImportError(null), 3000);
    }

    e.target.value = '';
  };

  return (
    <header className="toolbar">
      <div className="toolbar-left">
        <div className="app-logo">
          <BarChart3 size={24} className="logo-icon" />
          <h1 className="app-title">图表主题编辑器</h1>
        </div>
      </div>

      <div className="toolbar-center">
        <div className="chart-type-tabs">
          {chartTypes.map(({ type, label, icon }) => (
            <button
              key={type}
              className={`chart-type-tab ${chartType === type ? 'active' : ''}`}
              onClick={() => setChartType(type)}
              title={label}
            >
              {icon}
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="toolbar-right">
        <div className="toolbar-actions">
          <button
            className="toolbar-btn"
            onClick={undo}
            disabled={!canUndo}
            title="撤销"
          >
            <Undo2 size={18} />
          </button>
          <button
            className="toolbar-btn"
            onClick={redo}
            disabled={!canRedo}
            title="重做"
          >
            <Redo2 size={18} />
          </button>
          <button className="toolbar-btn" onClick={resetTheme} title="重置主题">
            <RotateCcw size={18} />
          </button>

          <button
            className={`toolbar-btn ${isDarkMode ? 'dark-mode-active' : ''}`}
            onClick={toggleDarkMode}
            title={isDarkMode ? '切换亮色模式' : '切换暗色模式'}
          >
            {isDarkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          <div className="toolbar-divider" />

          <button className="toolbar-btn" onClick={handleImportClick} title="导入主题">
            <Upload size={18} />
            <span>导入</span>
          </button>

          <div className="export-dropdown">
            <button className="toolbar-btn primary" title="导出主题">
              <Download size={18} />
              <span>导出</span>
            </button>
            <div className="export-menu">
              <button onClick={() => handleExport('pretty')}>
                <RotateCw size={14} />
                格式化导出
              </button>
              <button onClick={() => handleExport('minified')}>
                <Download size={14} />
                压缩导出
              </button>
            </div>
          </div>
        </div>

        {importError && <div className="import-error">{importError}</div>}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".json,application/json"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
    </header>
  );
};

export default React.memo(Toolbar);
