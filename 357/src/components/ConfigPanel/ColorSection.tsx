import React, { useCallback } from 'react';
import { Palette, Plus, Trash2 } from 'lucide-react';
import ColorPicker from '@/components/ColorPicker';
import { useTheme, useThemeActions } from '@/store/useThemeStore';
import './ConfigSection.less';

interface SectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

const CollapsibleSection: React.FC<SectionProps> = ({ title, icon, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = React.useState(defaultOpen);

  return (
    <div className={`config-section ${isOpen ? 'open' : ''}`}>
      <button className="section-header" onClick={() => setIsOpen(!isOpen)}>
        <div className="section-title">
          {icon}
          <span>{title}</span>
        </div>
        <div className={`section-arrow ${isOpen ? 'expanded' : ''}`}>▼</div>
      </button>
      {isOpen && <div className="section-content">{children}</div>}
    </div>
  );
};

const ColorSection: React.FC = () => {
  const theme = useTheme();
  const { setColorPalette, updateTheme } = useThemeActions();

  const handleColorChange = useCallback(
    (index: number, color: string) => {
      const newColors = [...theme.color];
      newColors[index] = color;
      setColorPalette(newColors);
    },
    [theme.color, setColorPalette],
  );

  const handleAddColor = useCallback(() => {
    const newColors = [...theme.color, '#1890ff'];
    setColorPalette(newColors);
  }, [theme.color, setColorPalette]);

  const handleRemoveColor = useCallback(
    (index: number) => {
      if (theme.color.length > 2) {
        const newColors = theme.color.filter((_, i) => i !== index);
        setColorPalette(newColors);
      }
    },
    [theme.color, setColorPalette],
  );

  return (
    <CollapsibleSection title="颜色配置" icon={<Palette size={16} />}>
      <div className="config-item">
        <label className="config-label">背景颜色</label>
        <ColorPicker
          color={theme.backgroundColor || '#ffffff'}
          onChange={(color) => updateTheme('backgroundColor', color)}
        />
      </div>

      <div className="config-item">
        <label className="config-label">全局色板</label>
        <div className="color-palette-grid">
          {theme.color.map((color, index) => (
            <div key={index} className="color-palette-item">
              <ColorPicker color={color} onChange={(c) => handleColorChange(index, c)} />
              {theme.color.length > 2 && (
                <button
                  className="color-remove-btn"
                  onClick={() => handleRemoveColor(index)}
                  title="删除颜色"
                >
                  <Trash2 size={12} />
                </button>
              )}
              <span className="color-index">{index + 1}</span>
            </div>
          ))}
          <button className="color-add-btn" onClick={handleAddColor} title="添加颜色">
            <Plus size={16} />
          </button>
        </div>
        <p className="config-hint">
          修改全局色板时，所有系列颜色会自动重新映射
        </p>
      </div>

      <div className="config-item">
        <label className="config-label">坐标轴文字颜色</label>
        <ColorPicker
          color={theme.textStyle?.color || '#333333'}
          onChange={(color) => updateTheme('textStyle.color', color)}
        />
      </div>

      <div className="config-item">
        <label className="config-label">标题颜色</label>
        <ColorPicker
          color={theme.title?.textStyle?.color || '#333333'}
          onChange={(color) => updateTheme('title.textStyle.color', color)}
        />
      </div>
    </CollapsibleSection>
  );
};

export default React.memo(ColorSection);
export { CollapsibleSection };
