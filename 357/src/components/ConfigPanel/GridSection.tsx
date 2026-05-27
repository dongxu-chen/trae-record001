import React from 'react';
import { Grid3X3 } from 'lucide-react';
import { CollapsibleSection } from './ColorSection';
import ColorPicker from '@/components/ColorPicker';
import { useTheme, useThemeActions } from '@/store/useThemeStore';
import './ConfigSection.less';

const lineTypes = [
  { label: '实线', value: 'solid' },
  { label: '虚线', value: 'dashed' },
  { label: '点线', value: 'dotted' },
];

const GridSection: React.FC = () => {
  const theme = useTheme();
  const { updateTheme } = useThemeActions();

  return (
    <CollapsibleSection title="网格线配置" icon={<Grid3X3 size={16} />}>
      <div className="config-item">
        <label className="config-label">显示边框</label>
        <label className="config-switch">
          <input
            type="checkbox"
            checked={theme.grid?.show || false}
            onChange={(e) => updateTheme('grid.show', e.target.checked)}
          />
          <span className="switch-slider" />
        </label>
      </div>

      <div className="config-item">
        <label className="config-label">边框颜色</label>
        <ColorPicker
          color={theme.grid?.borderColor || '#e0e0e0'}
          onChange={(color) => updateTheme('grid.borderColor', color)}
        />
      </div>

      <div className="config-item">
        <label className="config-label">
          边框宽度: {theme.grid?.borderWidth || 1}px
        </label>
        <input
          type="range"
          className="config-range"
          min="0"
          max="4"
          value={theme.grid?.borderWidth || 1}
          onChange={(e) => updateTheme('grid.borderWidth', Number(e.target.value))}
        />
      </div>

      <div className="config-divider">
        <span>X轴分割线</span>
      </div>

      <div className="config-item">
        <label className="config-label">显示X轴分割线</label>
        <label className="config-switch">
          <input
            type="checkbox"
            checked={theme.categoryAxis?.splitLine?.show || false}
            onChange={(e) => updateTheme('categoryAxis.splitLine.show', e.target.checked)}
          />
          <span className="switch-slider" />
        </label>
      </div>

      <div className="config-item">
        <label className="config-label">X轴分割线颜色</label>
        <ColorPicker
          color={theme.categoryAxis?.splitLine?.lineStyle?.color || '#e0e0e0'}
          onChange={(color) => updateTheme('categoryAxis.splitLine.lineStyle.color', color)}
        />
      </div>

      <div className="config-item">
        <label className="config-label">X轴分割线类型</label>
        <select
          className="config-select"
          value={theme.categoryAxis?.splitLine?.lineStyle?.type || 'dashed'}
          onChange={(e) =>
            updateTheme('categoryAxis.splitLine.lineStyle.type', e.target.value)
          }
        >
          {lineTypes.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
      </div>

      <div className="config-divider">
        <span>Y轴分割线</span>
      </div>

      <div className="config-item">
        <label className="config-label">显示Y轴分割线</label>
        <label className="config-switch">
          <input
            type="checkbox"
            checked={theme.valueAxis?.splitLine?.show || true}
            onChange={(e) => updateTheme('valueAxis.splitLine.show', e.target.checked)}
          />
          <span className="switch-slider" />
        </label>
      </div>

      <div className="config-item">
        <label className="config-label">Y轴分割线颜色</label>
        <ColorPicker
          color={theme.valueAxis?.splitLine?.lineStyle?.color || '#e0e0e0'}
          onChange={(color) => updateTheme('valueAxis.splitLine.lineStyle.color', color)}
        />
      </div>

      <div className="config-item">
        <label className="config-label">Y轴分割线类型</label>
        <select
          className="config-select"
          value={theme.valueAxis?.splitLine?.lineStyle?.type || 'solid'}
          onChange={(e) => updateTheme('valueAxis.splitLine.lineStyle.type', e.target.value)}
        >
          {lineTypes.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
      </div>

      <div className="config-divider">
        <span>坐标轴</span>
      </div>

      <div className="config-item">
        <label className="config-label">显示X轴线</label>
        <label className="config-switch">
          <input
            type="checkbox"
            checked={theme.categoryAxis?.axisLine?.show || true}
            onChange={(e) => updateTheme('categoryAxis.axisLine.show', e.target.checked)}
          />
          <span className="switch-slider" />
        </label>
      </div>

      <div className="config-item">
        <label className="config-label">显示Y轴线</label>
        <label className="config-switch">
          <input
            type="checkbox"
            checked={theme.valueAxis?.axisLine?.show || false}
            onChange={(e) => updateTheme('valueAxis.axisLine.show', e.target.checked)}
          />
          <span className="switch-slider" />
        </label>
      </div>
    </CollapsibleSection>
  );
};

export default React.memo(GridSection);
