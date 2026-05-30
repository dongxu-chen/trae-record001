import { useState, useEffect, useCallback } from 'react';
import {
  X,
  Search,
  Upload,
  Star,
  Download,
  TrendingUp,
  Filter,
  Sparkles,
  Sun,
  Zap,
  Star as StarIcon,
  User,
  Tag,
  Plus,
  Send,
  CheckCircle,
} from 'lucide-react';
import { FILTER_DEFINITIONS, FilterType } from '@/utils/shaderManager';
import useFilterStore from '@/store/filterStore';
import { cn } from '@/lib/utils';

interface MarketPreset {
  id: string;
  name: string;
  description: string;
  author: string;
  filterType: string;
  intensity: number;
  customParams: Record<string, number | number[]>;
  thumbnailData: string | null;
  tags: string[];
  downloads: number;
  rating: number;
  ratingCount: number;
  createdAt: string;
}

const filterIcons: Record<string, React.ReactNode> = {
  dreamy: <Sparkles size={14} />,
  backlight: <Sun size={14} />,
  neon: <Zap size={14} />,
  starburst: <StarIcon size={14} />,
};

interface MarketplaceModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function MarketplaceModal({ isOpen, onClose }: MarketplaceModalProps) {
  const [presets, setPresets] = useState<MarketPreset[]>([]);
  const [trending, setTrending] = useState<MarketPreset[]>([]);
  const [search, setSearch] = useState('');
  const [selectedFilter, setSelectedFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<'rating' | 'downloads' | 'newest'>('rating');
  const [activeTab, setActiveTab] = useState<'browse' | 'upload'>('browse');
  const [isLoading, setIsLoading] = useState(false);
  const [userRating, setUserRating] = useState<Record<string, number>>({});
  const [showUploadSuccess, setShowUploadSuccess] = useState(false);

  const { setActiveFilter, setFilterIntensity, setFilterParam, activeFilter, filterIntensity, filterParams } =
    useFilterStore();

  const [uploadForm, setUploadForm] = useState({
    name: '',
    description: '',
    author: '',
    tags: '',
  });

  const fetchPresets = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        sortBy,
        limit: '20',
      });
      if (search) params.append('search', search);
      if (selectedFilter) params.append('filterType', selectedFilter);

      const res = await fetch(`/api/marketplace?${params}`);
      const data = await res.json();
      if (data.success) {
        setPresets(data.data);
      }
    } catch (error) {
      console.error('Failed to fetch presets:', error);
    } finally {
      setIsLoading(false);
    }
  }, [search, selectedFilter, sortBy]);

  const fetchTrending = useCallback(async () => {
    try {
      const res = await fetch('/api/marketplace/trending');
      const data = await res.json();
      if (data.success) {
        setTrending(data.data);
      }
    } catch (error) {
      console.error('Failed to fetch trending:', error);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchPresets();
      fetchTrending();
    }
  }, [isOpen, fetchPresets, fetchTrending]);

  useEffect(() => {
    if (isOpen && (search || selectedFilter || sortBy)) {
      const timer = setTimeout(fetchPresets, 300);
      return () => clearTimeout(timer);
    }
  }, [search, selectedFilter, sortBy, fetchPresets]);

  const handleApplyPreset = (preset: MarketPreset) => {
    setActiveFilter(preset.filterType);
    setFilterIntensity(preset.intensity);
    for (const [key, value] of Object.entries(preset.customParams)) {
      setFilterParam(key, value);
    }
    fetch(`/api/marketplace/${preset.id}`, { method: 'GET' });
    onClose();
  };

  const handleRate = async (presetId: string, rating: number) => {
    setUserRating((prev) => ({ ...prev, [presetId]: rating }));
    try {
      const res = await fetch(`/api/marketplace/${presetId}/rate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: 'local_user', rating }),
      });
      const data = await res.json();
      if (data.success) {
        setPresets((prev) =>
          prev.map((p) =>
            p.id === presetId
              ? { ...p, rating: data.data.rating, ratingCount: data.data.ratingCount }
              : p
          )
        );
      }
    } catch (error) {
      console.error('Failed to rate:', error);
    }
  };

  const handleUpload = async () => {
    if (!uploadForm.name.trim()) return;

    try {
      const res = await fetch('/api/marketplace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: uploadForm.name.trim(),
          description: uploadForm.description.trim(),
          author: uploadForm.author.trim() || 'Anonymous',
          filterType: activeFilter,
          intensity: filterIntensity,
          customParams: filterParams,
          tags: uploadForm.tags
            .split(',')
            .map((t) => t.trim())
            .filter((t) => t),
        }),
      });
      const data = await res.json();
      if (data.success) {
        setShowUploadSuccess(true);
        setUploadForm({ name: '', description: '', author: '', tags: '' });
        setTimeout(() => {
          setShowUploadSuccess(false);
          setActiveTab('browse');
          fetchPresets();
          fetchTrending();
        }, 1500);
      }
    } catch (error) {
      console.error('Failed to upload:', error);
    }
  };

  const renderStars = (rating: number, presetId: string) => {
    const currentRating = userRating[presetId] ?? Math.round(rating);
    return (
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onClick={() => handleRate(presetId, star)}
            className="transition-transform hover:scale-110"
          >
            <Star
              size={14}
              className={cn(
                star <= currentRating ? 'text-neon-amber fill-neon-amber' : 'text-gray-600'
              )}
            />
          </button>
        ))}
      </div>
    );
  };

  const renderPresetCard = (preset: MarketPreset, isTrending = false) => {
    const filterDef = FILTER_DEFINITIONS.find((f) => f.id === preset.filterType);
    const filterColor = filterDef?.color || '#B24BF3';
    const icon = filterIcons[preset.filterType] || <Sparkles size={14} />;

    return (
      <div
        key={preset.id}
        className={cn(
          'bg-surface-card rounded-xl overflow-hidden border border-surface-border hover:border-neon-purple/40 transition-all duration-200 group',
          isTrending && 'border-neon-amber/30'
        )}
      >
        <div
          className="h-24 relative overflow-hidden"
          style={{
            background: `linear-gradient(135deg, ${filterColor}30, ${filterColor}10)`,
          }}
        >
          <div className="absolute inset-0 flex items-center justify-center">
            <div
              className="w-12 h-12 rounded-full flex items-center justify-center"
              style={{ backgroundColor: `${filterColor}40`, color: filterColor }}
            >
              {icon}
            </div>
          </div>
          {isTrending && (
            <div className="absolute top-2 right-2 px-2 py-0.5 bg-neon-amber/20 rounded-full text-[10px] text-neon-amber font-medium flex items-center gap-1">
              <TrendingUp size={10} />
              热门
            </div>
          )}
        </div>

        <div className="p-3 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h4 className="font-medium text-sm truncate">{preset.name}</h4>
              <div className="flex items-center gap-1 text-[10px] text-gray-500 mt-0.5">
                <User size={10} />
                <span className="truncate">{preset.author}</span>
              </div>
            </div>
            <button
              onClick={() => handleApplyPreset(preset)}
              className="p-1.5 rounded-md bg-neon-purple/10 text-neon-purple opacity-0 group-hover:opacity-100 transition-opacity"
              title="应用预设"
            >
              <Download size={14} />
            </button>
          </div>

          {preset.description && (
            <p className="text-xs text-gray-500 line-clamp-2">{preset.description}</p>
          )}

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1">
              {renderStars(preset.rating, preset.id)}
              <span className="text-[10px] text-gray-500 ml-1">({preset.ratingCount})</span>
            </div>
            <div className="flex items-center gap-1 text-[10px] text-gray-500">
              <Download size={10} />
              {preset.downloads}
            </div>
          </div>

          {preset.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {preset.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 bg-surface-hover rounded text-[10px] text-gray-400 flex items-center gap-0.5"
                >
                  <Tag size={8} />
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-4xl max-h-[85vh] glass-panel rounded-2xl overflow-hidden animate-fade-in flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-surface-border flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-neon-cyan to-neon-amber flex items-center justify-center">
              <Download size={20} className="text-white" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-lg neon-text">滤镜市场</h3>
              <p className="text-sm text-gray-400">发现、分享、下载优秀滤镜预设</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-hover transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex border-b border-surface-border flex-shrink-0">
          <button
            onClick={() => setActiveTab('browse')}
            className={cn(
              'px-6 py-3 text-sm font-medium transition-colors relative',
              activeTab === 'browse' ? 'text-neon-cyan' : 'text-gray-400 hover:text-white'
            )}
          >
            浏览预设
            {activeTab === 'browse' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-neon-cyan" />
            )}
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            className={cn(
              'px-6 py-3 text-sm font-medium transition-colors relative',
              activeTab === 'upload' ? 'text-neon-purple' : 'text-gray-400 hover:text-white'
            )}
          >
            上传预设
            {activeTab === 'upload' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-neon-purple" />
            )}
          </button>
        </div>

        {activeTab === 'browse' ? (
          <div className="flex-1 overflow-y-auto">
            <div className="p-4 space-y-4">
              <div className="flex flex-wrap gap-3">
                <div className="flex-1 min-w-[200px] relative">
                  <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="搜索预设、作者..."
                    className="w-full pl-10 pr-4 py-2 bg-surface-card border border-surface-border rounded-lg text-sm focus:outline-none focus:border-neon-cyan/50"
                  />
                </div>
                <div className="flex gap-2">
                  <select
                    value={selectedFilter}
                    onChange={(e) => setSelectedFilter(e.target.value)}
                    className="px-3 py-2 bg-surface-card border border-surface-border rounded-lg text-sm focus:outline-none"
                  >
                    <option value="">全部滤镜</option>
                    {FILTER_DEFINITIONS.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name}
                      </option>
                    ))}
                  </select>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as 'rating' | 'downloads' | 'newest')}
                    className="px-3 py-2 bg-surface-card border border-surface-border rounded-lg text-sm focus:outline-none"
                  >
                    <option value="rating">评分最高</option>
                    <option value="downloads">下载最多</option>
                    <option value="newest">最新上传</option>
                  </select>
                </div>
              </div>

              {trending.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                    <TrendingUp size={16} className="text-neon-amber" />
                    热门趋势
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {trending.map((preset) => renderPresetCard(preset, true))}
                  </div>
                </div>
              )}

              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                  <Filter size={16} className="text-neon-cyan" />
                  全部预设
                </h4>
                {isLoading ? (
                  <div className="flex items-center justify-center py-12 text-gray-500">
                    <div className="animate-spin rounded-full h-8 w-8 border-2 border-neon-cyan border-t-transparent" />
                  </div>
                ) : presets.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {presets.map((preset) => renderPresetCard(preset))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <Filter size={48} className="mx-auto mb-3 opacity-30" />
                    <p>暂无预设</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            <div className="p-6 max-w-xl mx-auto">
              {showUploadSuccess ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mb-4">
                    <CheckCircle size={32} className="text-green-400" />
                  </div>
                  <h4 className="text-lg font-medium mb-2">上传成功！</h4>
                  <p className="text-sm text-gray-400">您的预设已分享到市场</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="p-4 bg-neon-purple/10 rounded-lg border border-neon-purple/30">
                    <p className="text-xs text-gray-300">
                      将当前滤镜配置（{FILTER_DEFINITIONS.find((f) => f.id === activeFilter)?.name || '未选择'} · 强度 {Math.round(filterIntensity * 100)}%）
                      分享到市场供他人使用。
                    </p>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-gray-300 block mb-1.5">预设名称 *</label>
                      <input
                        type="text"
                        value={uploadForm.name}
                        onChange={(e) => setUploadForm((f) => ({ ...f, name: e.target.value }))}
                        placeholder="给您的预设起个名字..."
                        className="w-full px-4 py-2.5 bg-surface-card border border-surface-border rounded-lg text-sm focus:outline-none focus:border-neon-purple/50"
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium text-gray-300 block mb-1.5">作者</label>
                      <input
                        type="text"
                        value={uploadForm.author}
                        onChange={(e) => setUploadForm((f) => ({ ...f, author: e.target.value }))}
                        placeholder="您的昵称（选填）"
                        className="w-full px-4 py-2.5 bg-surface-card border border-surface-border rounded-lg text-sm focus:outline-none focus:border-neon-purple/50"
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium text-gray-300 block mb-1.5">描述</label>
                      <textarea
                        value={uploadForm.description}
                        onChange={(e) => setUploadForm((f) => ({ ...f, description: e.target.value }))}
                        placeholder="描述这个预设的效果和适用场景..."
                        rows={3}
                        className="w-full px-4 py-2.5 bg-surface-card border border-surface-border rounded-lg text-sm focus:outline-none focus:border-neon-purple/50 resize-none"
                      />
                    </div>

                    <div>
                      <label className="text-sm font-medium text-gray-300 block mb-1.5">标签（逗号分隔）</label>
                      <input
                        type="text"
                        value={uploadForm.tags}
                        onChange={(e) => setUploadForm((f) => ({ ...f, tags: e.target.value }))}
                        placeholder="例如: 人像, 风景, 赛博朋克"
                        className="w-full px-4 py-2.5 bg-surface-card border border-surface-border rounded-lg text-sm focus:outline-none focus:border-neon-purple/50"
                      />
                    </div>

                    <div className="p-4 bg-surface-card rounded-lg">
                      <p className="text-xs text-gray-400 mb-2">当前配置预览</p>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-gray-500">滤镜:</span>{' '}
                          <span className="text-white">
                            {FILTER_DEFINITIONS.find((f) => f.id === activeFilter)?.name || '-'}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500">强度:</span>{' '}
                          <span className="text-white">{Math.round(filterIntensity * 100)}%</span>
                        </div>
                        {Object.entries(filterParams).length > 0 &&
                          Object.entries(filterParams).map(([key, value]) => (
                            <div key={key}>
                              <span className="text-gray-500">
                                {key.replace('u', '').replace(/([A-Z])/g, ' $1')}:
                              </span>{' '}
                              <span className="text-white">
                                {Array.isArray(value) ? value.map((v) => v.toFixed(2)).join(', ') : value.toFixed(2)}
                              </span>
                            </div>
                          ))}
                      </div>
                    </div>

                    <button
                      onClick={handleUpload}
                      disabled={!uploadForm.name.trim()}
                      className="w-full py-3 bg-gradient-to-r from-neon-purple to-neon-amber rounded-lg text-sm font-medium text-white hover:shadow-lg hover:shadow-neon-purple/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      <Plus size={16} />
                      分享预设
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
