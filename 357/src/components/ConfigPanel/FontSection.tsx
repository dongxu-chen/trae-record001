import React from 'react';
import { Type } from 'lucide-react';
import { CollapsibleSection } from './ColorSection';
import { useTheme, useThemeActions } from '@/store/useThemeStore';
import './ConfigSection.less';

const fontFamilies = [
  { label: '系统默认', value: 'system-ui, -apple-system, sans-serif' },
  { label: '微软雅黑', value: '"Microsoft YaHei", sans-serif' },
  { label: '宋体', value: 'SimSun, serif' },
  { label: '黑体', value: 'SimHei, sans-serif' },
  { label: 'Arial', value: 'Arial, sans-serif' },
  { label: 'Georgia', value: 'Georgia, serif' },
  { label: 'Monospace', value: 'Consolas, Monaco, monospace' },
];

const FontSection: React.FC = () => {
  const theme = useTheme();
  const { updateTheme } = useThemeActions();

  return (
    <CollapsibleSection title="字体配置" icon={<Type size={16} />}>
      <div className="config-item">
        <label className="config-label">字体类型</label>
        <select
          className="config-select"
          value={theme.textStyle?.fontFamily || 'system-ui, -apple-system, sans-serif'}
          onChange={(e) => updateTheme('textStyle.fontFamily', e.target.value)}
        >
          {fontFamilies.map((font) => (
            <option key={font.value} value={font.value}>
              {font.label}
            </option>
          ))}
        </select>
      </div>

      <div className="config-item">
        <label className="config-label">
          基础字号: {theme.textStyle?.fontSize || 12}px
        </label>
        <input
          type="range"
          className="config-range"
          min="10"
          max="24"
          value={theme.textStyle?.fontSize || 12}
          onChange={(e) => updateTheme('textStyle.fontSize', Number(e.target.value))}
        />
      </div>

      <div className="config-item">
        <label className="config-label">
          标题字号: {theme.title?.textStyle?.fontSize || 18}px
        </label>
        <input
          type="range"
          className="config-range"
          min="14"
          max="32"
          value={theme.title?.textStyle?.fontSize || 18}
          onChange={(e) => updateTheme('title.textStyle.fontSize', Number(e.target.value))}
        />
      </div>

      <div className="config-item">
        <label className="config-label">
          图例字号: {theme.legend?.textStyle?.fontSize || 12}px
        </label>
        <input
          type="range"
          className="config-range"
          min="10"
          max="20"
          value={theme.legend?.textStyle?.fontSize || 12}
          onChange={(e) => updateTheme('legend.textStyle.fontSize', Number(e.target.value))}
        />
      </div>

      <div className="config-item">
        <label className="config-label">
          坐标轴字号: {theme.categoryAxis?.axisLabel?.fontSize || 12}px
        </label>
        <input
          type="range"
          className="config-range"
          min="10"
          max="20"
          value={theme.categoryAxis?.axisLabel?.fontSize || 12}
          onChange={(e) => {
            updateTheme('categoryAxis.axisLabel.fontSize', Number(e.target.value));
            updateTheme('valueAxis.axisLabel.fontSize', Number(e.target.value));
          }}
        />
      </div>
    </CollapsibleSection>
  );
};

export default React.memo(FontSection);
