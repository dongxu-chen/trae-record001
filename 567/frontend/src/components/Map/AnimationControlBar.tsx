import { useMemo } from 'react';
import { Play, Pause, SkipBack, SkipForward, RotateCcw, Repeat, Footprints, Gauge, Layers, Shield, ShieldOff, Eye, EyeOff } from 'lucide-react';
import { useStore } from '@/store/useStore';
import { getPhotosSortedByTime, getTimeRange } from '@/utils/cluster';
import { getPrivacyDescription } from '@/utils/privacy';

export default function AnimationControlBar() {
  const { 
    photos, animation, setAnimation, privacy, setPrivacy,
    showClusters, setShowClusters, clusterDistance, setClusterDistance,
  } = useStore();
  
  const sortedPhotos = useMemo(() => getPhotosSortedByTime(photos), [photos]);
  const timeRange = useMemo(() => getTimeRange(photos), [photos]);
  const hasPhotos = sortedPhotos.length > 0;
  
  const currentPhoto = hasPhotos && animation.currentIndex < sortedPhotos.length
    ? sortedPhotos[animation.currentIndex] : null;
  
  const progress = hasPhotos ? ((animation.currentIndex + 1) / sortedPhotos.length) * 100 : 0;

  return (
    <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-lg border border-gray-200 p-4">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setAnimation({ currentIndex: 0 })}
            disabled={!hasPhotos}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-30"
            title="回到开始"
          >
            <SkipBack size={16} className="text-gray-600" />
          </button>
          
          <button
            onClick={() => setAnimation({ isPlaying: !animation.isPlaying })}
            disabled={!hasPhotos}
            className="p-2 bg-gradient-to-r from-accent-500 to-primary-600 text-white rounded-full hover:opacity-90 transition-opacity disabled:opacity-30"
            title={animation.isPlaying ? '暂停' : '播放'}
          >
            {animation.isPlaying ? <Pause size={18} /> : <Play size={18} />}
          </button>
          
          <button
            onClick={() => setAnimation({ currentIndex: Math.min(sortedPhotos.length - 1, animation.currentIndex + 1) })}
            disabled={!hasPhotos}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-30"
            title="下一张"
          >
            <SkipForward size={16} className="text-gray-600" />
          </button>
        </div>
        
        <div className="flex-1">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
            <span>
              {currentPhoto ? currentPhoto.exifData.dateTimeOriginal?.toLocaleTimeString() : '--:--'}
            </span>
            <span className="font-mono">
              {animation.currentIndex + 1} / {sortedPhotos.length}
            </span>
          </div>
          <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden cursor-pointer"
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const ratio = (e.clientX - rect.left) / rect.width;
              setAnimation({ currentIndex: Math.floor(ratio * sortedPhotos.length) });
            }}
          >
            <div className="h-full bg-gradient-to-r from-accent-500 to-primary-600 transition-all duration-200" style={{ width: `${progress}%` }} />
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1" title="播放速度">
            <Gauge size={14} className="text-gray-500" />
            <select
              value={animation.speed}
              onChange={(e) => setAnimation({ speed: parseFloat(e.target.value) })}
              className="text-xs border border-gray-200 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-accent-500"
            >
              <option value="0.5">0.5x</option>
              <option value="1">1x</option>
              <option value="2">2x</option>
              <option value="4">4x</option>
              <option value="8">8x</option>
            </select>
          </div>
          
          <button
            onClick={() => setAnimation({ loop: !animation.loop })}
            className={`p-1.5 rounded-lg transition-colors ${animation.loop ? 'bg-accent-500/10 text-accent-600' : 'text-gray-400 hover:bg-gray-100'}`}
            title="循环播放"
          >
            <Repeat size={16} />
          </button>
          
          <button
            onClick={() => setAnimation({ showTrail: !animation.showTrail })}
            className={`p-1.5 rounded-lg transition-colors ${animation.showTrail ? 'bg-accent-500/10 text-accent-600' : 'text-gray-400 hover:bg-gray-100'}`}
            title="显示轨迹"
          >
            <Footprints size={16} />
          </button>
        </div>
        
        <div className="w-px h-6 bg-gray-200" />
        
        <button
          onClick={() => setShowClusters(!showClusters)}
          className={`p-1.5 rounded-lg transition-colors flex items-center gap-1 ${showClusters ? 'bg-purple-500/10 text-purple-600' : 'text-gray-400 hover:bg-gray-100'}`}
          title="照片聚类"
        >
          <Layers size={16} />
          <span className="text-xs">聚类</span>
        </button>
        
        {showClusters && (
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">{clusterDistance}m</span>
            <input
              type="range"
              min="10"
              max="500"
              step="10"
              value={clusterDistance}
              onChange={(e) => setClusterDistance(parseInt(e.target.value))}
              className="w-16 h-1 bg-gray-200 rounded appearance-none cursor-pointer accent-purple-500"
            />
          </div>
        )}
        
        <div className="w-px h-6 bg-gray-200" />
        
        <button
          onClick={() => setPrivacy({ enabled: !privacy.enabled })}
          className={`p-1.5 rounded-lg transition-colors flex items-center gap-1 ${privacy.enabled ? 'bg-orange-500/10 text-orange-600' : 'text-gray-400 hover:bg-gray-100'}`}
          title="隐私保护"
        >
          {privacy.enabled ? <Shield size={16} /> : <ShieldOff size={16} />}
          <span className="text-xs">隐私</span>
        </button>
        
        {privacy.enabled && (
          <div className="flex items-center gap-2">
            <select
              value={privacy.mode}
              onChange={(e) => setPrivacy({ mode: e.target.value as 'blur' | 'snap' | 'random' | 'remove' })}
              className="text-xs border border-gray-200 rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-orange-500"
            >
              <option value="blur">模糊化</option>
              <option value="snap">网格吸附</option>
              <option value="random">随机偏移</option>
              <option value="remove">降低精度</option>
            </select>
            
            {privacy.mode === 'blur' && (
              <div className="flex items-center gap-1">
                <span className="text-xs text-gray-500">±{privacy.blurRadius}m</span>
                <input
                  type="range" min="10" max="500" step="10"
                  value={privacy.blurRadius}
                  onChange={(e) => setPrivacy({ blurRadius: parseInt(e.target.value) })}
                  className="w-12 h-1 bg-gray-200 rounded appearance-none cursor-pointer accent-orange-500"
                />
              </div>
            )}
            {privacy.mode === 'snap' && (
              <div className="flex items-center gap-1">
                <span className="text-xs text-gray-500">{privacy.snapGridSize}m</span>
                <input
                  type="range" min="50" max="1000" step="50"
                  value={privacy.snapGridSize}
                  onChange={(e) => setPrivacy({ snapGridSize: parseInt(e.target.value) })}
                  className="w-12 h-1 bg-gray-200 rounded appearance-none cursor-pointer accent-orange-500"
                />
              </div>
            )}
            {privacy.mode === 'random' && (
              <div className="flex items-center gap-1">
                <span className="text-xs text-gray-500">±{privacy.randomOffset}m</span>
                <input
                  type="range" min="10" max="500" step="10"
                  value={privacy.randomOffset}
                  onChange={(e) => setPrivacy({ randomOffset: parseInt(e.target.value) })}
                  className="w-12 h-1 bg-gray-200 rounded appearance-none cursor-pointer accent-orange-500"
                />
              </div>
            )}
            {privacy.mode === 'remove' && (
              <select
                value={privacy.removePrecision}
                onChange={(e) => setPrivacy({ removePrecision: parseInt(e.target.value) })}
                className="text-xs border border-gray-200 rounded px-1 py-0.5"
              >
                <option value={0}>0位小数 (~11km)</option>
                <option value={1}>1位小数 (~1.1km)</option>
                <option value={2}>2位小数 (~110m)</option>
                <option value={3}>3位小数 (~11m)</option>
              </select>
            )}
            
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPrivacy({ applyToDisplay: !privacy.applyToDisplay })}
                className={`p-1 rounded transition-colors ${privacy.applyToDisplay ? 'text-orange-500' : 'text-gray-400'}`}
                title="应用到地图显示"
              >
                <Eye size={14} />
              </button>
              <button
                onClick={() => setPrivacy({ applyToExport: !privacy.applyToExport })}
                className={`p-1 rounded transition-colors ${privacy.applyToExport ? 'text-orange-500' : 'text-gray-400'}`}
                title="应用到导出文件"
              >
                <EyeOff size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
      
      {timeRange && (
        <div className="mt-2 text-xs text-gray-400 flex items-center justify-between">
          <span>{timeRange.start.toLocaleString()}</span>
          <span>{timeRange.end.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}
