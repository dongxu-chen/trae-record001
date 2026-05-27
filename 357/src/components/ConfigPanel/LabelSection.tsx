import React from 'react';
import { Tag } from 'lucide-react';
import { CollapsibleSection } from './ColorSection';
import ColorPicker from '@/components/ColorPicker';
import { useTheme, useThemeActions } from '@/store/useThemeStore';
import './ConfigSection.less';

const LabelSection: React.FC = () => {
  const theme = useTheme();
  const { updateTheme } = useThemeActions();

  return (
    <CollapsibleSection title="标签配置" icon={<Tag size={16} />}>
      <div className="config-divider">
        <span>图例</span>
      </div>

      <div className="config-item">
        <label className="config-label">显示图例</label>
        <label className="config-switch">
          <input
            type="checkbox"
            checked={theme.legend?.show || true}
            onChange={(e) => updateTheme('legend.show', e.target.checked)}
          />
          <span className="switch-slider" />
        </label>
      </div>

      <div className="config-item">
        <label className="config-label">图例文字颜色</label>
        <ColorPicker
          color={theme.legend?.textStyle?.color || '#333333'}
          onChange={(color) => updateTheme('legend.textStyle.color', color)}
        />
      </div>

      <div className="config-divider">
        <span>提示框</span>
      </div>

      <div className="config-item">
        <label className="config-label">提示框背景</label>
        <ColorPicker
          color={theme.tooltip?.backgroundColor || 'rgba(50, 50, 50, 0.9)'}
          onChange={(color) => updateTheme('tooltip.backgroundColor', color)}
        />
      </div>

      <div className="config-item">
        <label className="config-label">提示框文字颜色</label>
        <ColorPicker
          color={theme.tooltip?.textStyle?.color || '#ffffff'}
          onChange={(color) => updateTheme('tooltip.textStyle.color', color)}
        />
      </div>

      <div className="config-item">
        <label className="config-label">提示框边框宽度</label>
        <input
          type="range"
          className="config-range"
          min="0"
          max="4"
          value={theme.tooltip?.borderWidth || 0}
          onChange={(e) => updateTheme('tooltip.borderWidth', Number(e.target.value))}
        />
      </div>

      <div className="config-divider">
        <span>坐标轴标签</span>
      </div>

      <div className="config-item">
        <label className="config-label">显示X轴标签</label>
        <label className="config-switch">
          <input
            type="checkbox"
            checked={theme.categoryAxis?.axisLabel?.show || true}
            onChange={(e) => updateTheme('categoryAxis.axisLabel.show', e.target.checked)}
          />
          <span className="switch-slider" />
        </label>
      </div>

      <div className="config-item">
        <label className="config-label">X轴标签颜色</label>
        <ColorPicker
          color={theme.categoryAxis?.axisLabel?.color || '#666666'}
          onChange={(color) => updateTheme('categoryAxis.axisLabel.color', color)}
        />
      </div>

      <div className="config-item">
        <label className="config-label">显示Y轴标签</label>
        <label className="config-switch">
          <input
            type="checkbox"
            checked={theme.valueAxis?.axisLabel?.show || true}
            onChange={(e) => updateTheme('valueAxis.axisLabel.show', e.target.checked)}
          />
          <span className="switch-slider" />
        </label>
      </div>

      <div className="config-item">
        <label className="config-label">Y轴标签颜色</label>
        <ColorPicker
          color={theme.valueAxis?.axisLabel?.color || '#666666'}
          onChange={(color) => {
            updateTheme('valueAxis.axisLabel.color', color);
          }}
        />
      </div>

      <div className="config-divider">
        <span>折线图</span>
      </div>

      <div className="config-item">
        <label className="config-label">平滑曲线</label>
        <label className="config-switch">
          <input
            type="checkbox"
            checked={theme.line?.smooth || false}
            onChange={(e) => updateTheme('line.smooth', e.target.checked)}
          />
          <span className="switch-slider" />
        </label>
      </div>

      <div className="config-item">
        <label className="config-label">
          线条宽度: {theme.line?.lineStyle?.width || 2}px
        </label>
        <input
          type="range"
          className="config-range"
          min="1"
          max="8"
          value={theme.line?.lineStyle?.width || 2}
          onChange={(e) => updateTheme('line.lineStyle.width', Number(e.target.value))}
        />
      </div>

      <div className="config-item">
        <label className="config-label">
          数据点大小: {theme.line?.symbolSize || 6}px
        </label>
        <input
          type="range"
          className="config-range"
          min="2"
          max="20"
          value={theme.line?.symbolSize || 6}
          onChange={(e) => updateTheme('line.symbolSize', Number(e.target.value))}
        />
      </div>
    </CollapsibleSection>
  );
};

export default React.memo(LabelSection);
