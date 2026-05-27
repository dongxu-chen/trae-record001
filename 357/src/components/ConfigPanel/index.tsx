import React from 'react';
import ColorSection from './ColorSection';
import FontSection from './FontSection';
import GridSection from './GridSection';
import LabelSection from './LabelSection';
import ThemeRecommendations from './ThemeRecommendations';
import ThemeLibrary from './ThemeLibrary';
import './index.less';

const ConfigPanel: React.FC = () => {
  return (
    <aside className="config-panel">
      <div className="config-panel-header">
        <h2 className="config-panel-title">主题配置</h2>
        <p className="config-panel-subtitle">自定义图表样式，实时预览效果</p>
      </div>
      <div className="config-panel-content">
        <ThemeRecommendations />
        <ThemeLibrary />
        <ColorSection />
        <FontSection />
        <GridSection />
        <LabelSection />
      </div>
    </aside>
  );
};

export default ConfigPanel;
