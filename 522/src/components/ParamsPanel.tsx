import { useState } from 'react';
import { FILTER_DEFINITIONS, ShaderUniformDef } from '@/utils/shaderManager';
import useFilterStore from '@/store/filterStore';
import { Save, Download, Trash2, Play } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ParamsPanelProps {
  onExport: () => void;
}

export default function ParamsPanel({ onExport }: ParamsPanelProps) {
  const {
    activeFilter,
    filterIntensity,
    setFilterIntensity,
    filterParams,
    setFilterParam,
    presets,
    savePreset,
    loadPreset,
    deletePreset,
  } = useFilterStore();

  const [presetName, setPresetName] = useState('');
  const [showPresetInput, setShowPresetInput] = useState(false);

  const currentFilter = FILTER_DEFINITIONS.find((f) => f.id === activeFilter);

  const handleSavePreset = () => {
    if (presetName.trim()) {
      savePreset(presetName.trim());
      setPresetName('');
      setShowPresetInput(false);
    }
  };

  const renderUniformSlider = (uniform: ShaderUniformDef) => {
    const value = filterParams[uniform.name] ?? uniform.defaultValue;
    const min = uniform.min ?? 0;
    const max = uniform.max ?? 1;

    if (uniform.type === 'vec3') {
      const vecValue = Array.isArray(value) ? value : (uniform.defaultValue as number[]);
      return (
        <div key={uniform.name} className="space-y-2">
          <label className="text-sm font-medium text-gray-300">
            {uniform.name.replace('u', '')}
          </label>
          <div className="space-y-2">
            {['R', 'G', 'B'].map((channel, index) => (
              <div key={channel} className="flex items-center gap-3">
                <span className="text-xs text-gray-500 w-6">{channel}</span>
                <input
                  type="range"
                  min={min}
                  max={max}
                  step={0.01}
                  value={vecValue[index]}
                  onChange={(e) => {
                    const newValue = [...vecValue];
                    newValue[index] = parseFloat(e.target.value);
                    setFilterParam(uniform.name, newValue);
                  }}
                  className="range-neon flex-1"
                />
                <span className="text-xs text-gray-400 w-10 text-right">
                  {vecValue[index].toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    if (uniform.type === 'vec2') {
      const vecValue = Array.isArray(value) ? value : (uniform.defaultValue as number[]);
      return (
        <div key={uniform.name} className="space-y-2">
          <label className="text-sm font-medium text-gray-300">
            {uniform.name.replace('u', '')}
          </label>
          <div className="space-y-2">
            {['X', 'Y'].map((channel, index) => (
              <div key={channel} className="flex items-center gap-3">
                <span className="text-xs text-gray-500 w-6">{channel}</span>
                <input
                  type="range"
                  min={min}
                  max={max}
                  step={0.01}
                  value={vecValue[index]}
                  onChange={(e) => {
                    const newValue = [...vecValue];
                    newValue[index] = parseFloat(e.target.value);
                    setFilterParam(uniform.name, newValue);
                  }}
                  className="range-neon flex-1"
                />
                <span className="text-xs text-gray-400 w-10 text-right">
                  {vecValue[index].toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    const numValue = typeof value === 'number' ? value : (uniform.defaultValue as number);

    return (
      <div key={uniform.name} className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">
            {uniform.name.replace('u', '').replace(/([A-Z])/g, ' $1')}
          </label>
          <span className="text-xs text-neon-cyan font-mono">
            {numValue.toFixed(2)}
          </span>
        </div>
        <input
          type="range"
          min={min}
          max={max}
          step={0.01}
          value={numValue}
          onChange={(e) => setFilterParam(uniform.name, parseFloat(e.target.value))}
          className="range-neon w-full"
        />
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col glass-panel rounded-xl overflow-hidden">
      <div className="p-4 border-b border-surface-border">
        <h2 className="font-display font-semibold text-lg neon-text">参数调节</h2>
        <p className="text-sm text-gray-400 mt-1">
          当前: {currentFilter?.name || '未选择'}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">滤镜强度</label>
            <span className="text-xs text-neon-cyan font-mono">
              {Math.round(filterIntensity * 100)}%
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={filterIntensity}
            onChange={(e) => setFilterIntensity(parseFloat(e.target.value))}
            className="range-neon w-full"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
        </div>

        {currentFilter?.uniforms && currentFilter.uniforms.length > 0 && (
          <div className="space-y-4">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              高级参数
            </p>
            {currentFilter.uniforms.map(renderUniformSlider)}
          </div>
        )}

        <div className="space-y-3">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            预设管理
          </p>

          {showPresetInput ? (
            <div className="space-y-2">
              <input
                type="text"
                value={presetName}
                onChange={(e) => setPresetName(e.target.value)}
                placeholder="输入预设名称..."
                className="w-full px-3 py-2 bg-surface-card border border-surface-border rounded-lg text-sm focus:outline-none focus:border-neon-cyan/50"
                autoFocus
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSavePreset}
                  className="flex-1 px-3 py-2 bg-neon-cyan/20 text-neon-cyan rounded-lg text-sm font-medium hover:bg-neon-cyan/30 transition-colors"
                >
                  保存
                </button>
                <button
                  onClick={() => setShowPresetInput(false)}
                  className="px-3 py-2 bg-surface-card rounded-lg text-sm hover:bg-surface-hover transition-colors"
                >
                  取消
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowPresetInput(true)}
              className="w-full px-4 py-2 bg-surface-card border border-surface-border rounded-lg text-sm font-medium hover:bg-surface-hover transition-colors flex items-center justify-center gap-2"
            >
              <Save size={16} />
              保存当前配置
            </button>
          )}

          {presets.length > 0 && (
            <div className="space-y-2">
              {presets.map((preset) => (
                <div
                  key={preset.id}
                  className="flex items-center gap-2 p-2 bg-surface-card rounded-lg group"
                >
                  <button
                    onClick={() => loadPreset(preset.id)}
                    className="flex-1 text-left"
                  >
                    <p className="text-sm font-medium truncate">{preset.name}</p>
                    <p className="text-xs text-gray-500">
                      {FILTER_DEFINITIONS.find((f) => f.id === preset.config.filterType)?.name} ·{' '}
                      {Math.round(preset.config.intensity * 100)}%
                    </p>
                  </button>
                  <button
                    onClick={() => loadPreset(preset.id)}
                    className="p-1.5 rounded-md hover:bg-neon-cyan/20 text-gray-400 hover:text-neon-cyan opacity-0 group-hover:opacity-100 transition-opacity"
                    title="应用预设"
                  >
                    <Play size={14} />
                  </button>
                  <button
                    onClick={() => deletePreset(preset.id)}
                    className="p-1.5 rounded-md hover:bg-red-500/20 text-gray-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="删除预设"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="p-4 border-t border-surface-border">
        <button
          onClick={onExport}
          className={cn(
            'w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-all duration-200',
            'bg-gradient-to-r from-neon-cyan to-neon-purple text-white hover:shadow-lg hover:shadow-neon-cyan/25'
          )}
        >
          <Download size={18} />
          导出图片
        </button>
      </div>
    </div>
  );
}
