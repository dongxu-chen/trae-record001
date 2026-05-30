import { FILTER_DEFINITIONS, FilterType } from '@/utils/shaderManager';
import useFilterStore from '@/store/filterStore';
import { Sparkles, Sun, Zap, Star, Plus, Upload } from 'lucide-react';
import { cn } from '@/lib/utils';

const filterIcons: Record<FilterType, React.ReactNode> = {
  dreamy: <Sparkles size={20} />,
  backlight: <Sun size={20} />,
  neon: <Zap size={20} />,
  starburst: <Star size={20} />,
  custom: <Plus size={20} />,
};

interface FilterPanelProps {
  onUploadCustom: () => void;
}

export default function FilterPanel({ onUploadCustom }: FilterPanelProps) {
  const { activeFilter, setActiveFilter, customFilters } = useFilterStore();

  return (
    <div className="h-full flex flex-col glass-panel rounded-xl overflow-hidden">
      <div className="p-4 border-b border-surface-border">
        <h2 className="font-display font-semibold text-lg neon-text">光效滤镜</h2>
        <p className="text-sm text-gray-400 mt-1">选择滤镜开始创作</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            内置滤镜
          </p>
          {FILTER_DEFINITIONS.map((filter) => (
            <button
              key={filter.id}
              onClick={() => setActiveFilter(filter.id)}
              className={cn(
                'w-full p-3 rounded-lg flex items-center gap-3 transition-all duration-200',
                activeFilter === filter.id
                  ? 'bg-surface-hover neon-border'
                  : 'bg-surface-card hover:bg-surface-hover border border-transparent'
              )}
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center"
                style={{
                  backgroundColor: `${filter.color}20`,
                  color: filter.color,
                  boxShadow: `0 0 12px ${filter.color}30`,
                }}
              >
                {filterIcons[filter.id]}
              </div>
              <div className="text-left flex-1">
                <p className="font-medium">{filter.name}</p>
                <p className="text-xs text-gray-400 line-clamp-1">
                  {filter.description}
                </p>
              </div>
              {activeFilter === filter.id && (
                <div
                  className="w-2 h-2 rounded-full animate-glow-pulse"
                  style={{ backgroundColor: filter.color }}
                />
              )}
            </button>
          ))}
        </div>

        {customFilters.length > 0 && (
          <div className="space-y-2 mt-6">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              自定义滤镜 ({customFilters.length})
            </p>
            {customFilters.map((filter) => (
              <button
                key={filter.id}
                onClick={() => setActiveFilter(filter.id)}
                className={cn(
                  'w-full p-3 rounded-lg flex items-center gap-3 transition-all duration-200',
                  activeFilter === filter.id
                    ? 'bg-surface-hover neon-border'
                    : 'bg-surface-card hover:bg-surface-hover border border-transparent'
                )}
              >
                <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-neon-purple/20 text-neon-purple">
                  <Plus size={20} />
                </div>
                <div className="text-left flex-1">
                  <p className="font-medium">{filter.name}</p>
                  <p className="text-xs text-gray-400">
                    {filter.compiled ? '已编译' : '编译中...'}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}

        <button
          onClick={onUploadCustom}
          className="w-full p-4 rounded-lg border-2 border-dashed border-surface-border hover:border-neon-cyan/50 bg-surface-card/50 hover:bg-surface-hover transition-all duration-200 flex flex-col items-center gap-2 group"
        >
          <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-surface-hover group-hover:bg-neon-cyan/10 text-gray-400 group-hover:text-neon-cyan transition-colors">
            <Upload size={20} />
          </div>
          <p className="text-sm text-gray-400 group-hover:text-gray-300">
            上传自定义滤镜
          </p>
          <p className="text-xs text-gray-500">支持 .frag / .glsl 文件</p>
        </button>
      </div>
    </div>
  );
}
