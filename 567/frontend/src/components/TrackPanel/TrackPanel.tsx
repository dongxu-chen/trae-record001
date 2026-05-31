import { useRef, useState, useCallback } from 'react';
import { 
  Upload, X, Route, Play, Clock, Settings, Trash2, Zap, 
  Cpu, Target, Sliders, ChevronDown, ChevronUp, Camera, 
  Check, AlertTriangle, RefreshCw
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { parseGPX } from '@/utils/gpx';
import { matchAllPhotos, preprocessTracksWithKalman } from '@/utils/matching';
import { autoCalibrateDevices } from '@/utils/calibration';
import { analyzeDrift } from '@/utils/kalman';

export default function TrackPanel() {
  const { 
    tracks, 
    photos, 
    devices,
    matchConfig, 
    setMatchConfig, 
    addTrack, 
    removeTrack,
    clearTracks,
    setMatchedGps,
    setPhotoMatched,
    setPhotoMatchConfidence,
    setIsMatching,
    setIsCalibrating,
    setCalibrationResults,
    updateDevice,
    isMatching,
    isCalibrating,
    calibrationResults,
  } = useStore();
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showDeviceSettings, setShowDeviceSettings] = useState(false);
  const [selectedDeviceForEdit, setSelectedDeviceForEdit] = useState<string | null>(null);

  const handleFileSelect = useCallback(async (files: FileList) => {
    setIsLoading(true);
    const gpxFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.gpx'));
    
    for (const file of gpxFiles) {
      try {
        const track = await parseGPX(file);
        addTrack(track);
      } catch (error) {
        console.error(`解析 GPX 文件 ${file.name} 失败:`, error);
      }
    }
    
    setIsLoading(false);
  }, [addTrack]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files) {
      handleFileSelect(e.dataTransfer.files);
    }
  }, [handleFileSelect]);

  const handleMatch = useCallback(() => {
    setIsMatching(true);
    
    setTimeout(() => {
      let processedTracks = tracks;
      
      if (matchConfig.enableKalmanFilter) {
        processedTracks = preprocessTracksWithKalman(
          tracks,
          matchConfig.kalmanProcessNoise,
          matchConfig.kalmanMeasurementNoise
        );
      }
      
      const results = matchAllPhotos(photos, processedTracks, matchConfig, devices);
      
      results.forEach((result, photoId) => {
        setMatchedGps(photoId, result.gps);
        setPhotoMatched(photoId, true);
        setPhotoMatchConfidence(photoId, result.confidence, result.timeDiff);
      });
      
      setIsMatching(false);
    }, 100);
  }, [photos, tracks, matchConfig, devices, setMatchedGps, setPhotoMatched, setPhotoMatchConfidence, setIsMatching]);

  const handleAutoCalibrate = useCallback(() => {
    if (!matchConfig.enableAutoCalibration) return;
    
    setIsCalibrating(true);
    
    setTimeout(() => {
      const results = autoCalibrateDevices(
        photos,
        tracks,
        devices,
        {
          maxDistance: matchConfig.maxCalibrationDistance,
          maxTimeDiff: matchConfig.globalMaxTimeDiff,
          minConfidence: matchConfig.minCalibrationConfidence,
          minPoints: matchConfig.minCalibrationPoints,
        }
      );
      
      setCalibrationResults(results);
      
      results.forEach((result, deviceId) => {
        if (result.confidence >= matchConfig.minCalibrationConfidence) {
          updateDevice(deviceId, {
            timeOffset: Math.round(result.timeOffset),
          });
        }
      });
      
      setIsCalibrating(false);
    }, 100);
  }, [photos, tracks, devices, matchConfig, setCalibrationResults, setIsCalibrating, updateDevice]);

  const matchedCount = photos.filter(p => p.matchedGps || p.manualGps || p.originalGps).length;

  const getDriftAnalysis = () => {
    if (tracks.length === 0) return null;
    const allPoints = tracks.flatMap(t => t.points);
    return analyzeDrift(allPoints);
  };

  const driftAnalysis = getDriftAnalysis();

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <Route size={20} />
            轨迹
            <span className="text-sm font-normal text-gray-500">({tracks.length})</span>
          </h2>
          {tracks.length > 0 && (
            <button
              onClick={() => clearTracks()}
              className="text-gray-400 hover:text-red-500 transition-colors"
              title="清空所有轨迹"
            >
              <Trash2 size={18} />
            </button>
          )}
        </div>
        
        <div
          className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-all ${
            dragOver 
              ? 'border-accent-500 bg-accent-500/10' 
              : 'border-gray-300 hover:border-gray-400 bg-gray-50'
          }`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <Upload size={24} className="mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-600">
            拖放 GPX 文件到这里或点击上传
          </p>
          <p className="text-xs text-gray-400 mt-1">支持 .gpx 格式</p>
        </div>
        
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".gpx"
          className="hidden"
          onChange={(e) => e.target.files && handleFileSelect(e.target.files)}
        />
      </div>
      
      {driftAnalysis && driftAnalysis.hasLargeDrift && (
        <div className="mx-4 mt-3 p-3 bg-orange-50 border border-orange-200 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="text-orange-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-xs font-medium text-orange-700">检测到大漂移</p>
              <p className="text-xs text-orange-600 mt-1">
                建议启用卡尔曼滤波进行平滑处理
              </p>
            </div>
          </div>
        </div>
      )}
      
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {isLoading ? (
          <div className="p-4 text-center text-gray-500">
            <div className="animate-spin w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full mx-auto mb-2" />
            正在解析轨迹...
          </div>
        ) : tracks.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <Route size={48} className="mx-auto mb-2 opacity-50" />
            <p>暂无轨迹</p>
          </div>
        ) : (
          <div className="p-3 space-y-2">
            {tracks.map(track => (
              <div
                key={track.id}
                className="p-3 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-800 truncate">
                    {track.name}
                  </span>
                  <button
                    onClick={() => removeTrack(track.id)}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <X size={16} />
                  </button>
                </div>
                <div className="text-xs text-gray-500 space-y-1">
                  <p className="flex items-center gap-1">
                    <Route size={12} />
                    {track.points.length} 个轨迹点
                    {track.filteredPoints && (
                      <span className="ml-2 text-green-600 flex items-center gap-1">
                        <Check size={12} />
                        已滤波
                      </span>
                    )}
                  </p>
                  <p className="flex items-center gap-1">
                    <Clock size={12} />
                    {track.startTime.toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="border-t border-gray-200">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full px-4 py-2 flex items-center justify-between text-sm text-gray-600 hover:bg-gray-50 transition-colors"
        >
          <span className="flex items-center gap-2">
            <Sliders size={16} />
            高级设置
          </span>
          {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        
        {showAdvanced && (
          <div className="px-4 pb-4 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-700 flex items-center gap-2">
                <Cpu size={16} className="text-accent-500" />
                启用卡尔曼滤波
              </label>
              <button
                onClick={() => setMatchConfig({ enableKalmanFilter: !matchConfig.enableKalmanFilter })}
                className={`w-10 h-6 rounded-full transition-colors ${
                  matchConfig.enableKalmanFilter ? 'bg-accent-500' : 'bg-gray-300'
                }`}
              >
                <div className={`w-4 h-4 bg-white rounded-full shadow transition-transform ${
                  matchConfig.enableKalmanFilter ? 'translate-x-5' : 'translate-x-1'
                }`} />
              </button>
            </div>
            
            {matchConfig.enableKalmanFilter && (
              <div className="pl-6 space-y-2">
                <div>
                  <label className="flex items-center justify-between text-xs text-gray-600 mb-1">
                    <span>过程噪声</span>
                    <span className="font-mono">{matchConfig.kalmanProcessNoise}</span>
                  </label>
                  <input
                    type="range"
                    min="0.01"
                    max="1"
                    step="0.01"
                    value={matchConfig.kalmanProcessNoise}
                    onChange={(e) => setMatchConfig({ kalmanProcessNoise: parseFloat(e.target.value) })}
                    className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-accent-500"
                  />
                </div>
                <div>
                  <label className="flex items-center justify-between text-xs text-gray-600 mb-1">
                    <span>测量噪声</span>
                    <span className="font-mono">{matchConfig.kalmanMeasurementNoise}</span>
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="20"
                    step="0.5"
                    value={matchConfig.kalmanMeasurementNoise}
                    onChange={(e) => setMatchConfig({ kalmanMeasurementNoise: parseFloat(e.target.value) })}
                    className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-accent-500"
                  />
                </div>
              </div>
            )}
            
            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-700 flex items-center gap-2">
                <Target size={16} className="text-green-500" />
                自动时间校准
              </label>
              <button
                onClick={() => setMatchConfig({ enableAutoCalibration: !matchConfig.enableAutoCalibration })}
                className={`w-10 h-6 rounded-full transition-colors ${
                  matchConfig.enableAutoCalibration ? 'bg-green-500' : 'bg-gray-300'
                }`}
              >
                <div className={`w-4 h-4 bg-white rounded-full shadow transition-transform ${
                  matchConfig.enableAutoCalibration ? 'translate-x-5' : 'translate-x-1'
                }`} />
              </button>
            </div>
            
            {matchConfig.enableAutoCalibration && (
              <div className="pl-6 space-y-2">
                <div>
                  <label className="flex items-center justify-between text-xs text-gray-600 mb-1">
                    <span>最小置信度</span>
                    <span className="font-mono">{(matchConfig.minCalibrationConfidence * 100).toFixed(0)}%</span>
                  </label>
                  <input
                    type="range"
                    min="0.5"
                    max="0.95"
                    step="0.05"
                    value={matchConfig.minCalibrationConfidence}
                    onChange={(e) => setMatchConfig({ minCalibrationConfidence: parseFloat(e.target.value) })}
                    className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-500"
                  />
                </div>
                <div>
                  <label className="flex items-center justify-between text-xs text-gray-600 mb-1">
                    <span>最大距离 (米)</span>
                    <span className="font-mono">{matchConfig.maxCalibrationDistance}m</span>
                  </label>
                  <input
                    type="range"
                    min="10"
                    max="200"
                    step="10"
                    value={matchConfig.maxCalibrationDistance}
                    onChange={(e) => setMatchConfig({ maxCalibrationDistance: parseInt(e.target.value) })}
                    className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-500"
                  />
                </div>
              </div>
            )}
            
            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-700 flex items-center gap-2">
                <Camera size={16} className="text-purple-500" />
                按设备独立配置
              </label>
              <button
                onClick={() => setMatchConfig({ useDeviceConfig: !matchConfig.useDeviceConfig })}
                className={`w-10 h-6 rounded-full transition-colors ${
                  matchConfig.useDeviceConfig ? 'bg-purple-500' : 'bg-gray-300'
                }`}
              >
                <div className={`w-4 h-4 bg-white rounded-full shadow transition-transform ${
                  matchConfig.useDeviceConfig ? 'translate-x-5' : 'translate-x-1'
                }`} />
              </button>
            </div>
          </div>
        )}
        
        <button
          onClick={() => setShowDeviceSettings(!showDeviceSettings)}
          className="w-full px-4 py-2 flex items-center justify-between text-sm text-gray-600 hover:bg-gray-50 transition-colors border-t border-gray-100"
        >
          <span className="flex items-center gap-2">
            <Camera size={16} />
            设备管理
            <span className="text-xs bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full">
              {devices.length}
            </span>
          </span>
          {showDeviceSettings ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        
        {showDeviceSettings && devices.length > 0 && (
          <div className="px-4 pb-4 space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
            {devices.map(device => {
              const calibrationResult = calibrationResults.get(device.id);
              const isEditing = selectedDeviceForEdit === device.id;
              
              return (
                <div
                  key={device.id}
                  className={`p-3 rounded-lg border transition-colors ${
                    isEditing 
                      ? 'border-purple-300 bg-purple-50' 
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: device.color }}
                      />
                      <span className="text-sm font-medium text-gray-800">
                        {device.name}
                      </span>
                    </div>
                    <button
                      onClick={() => setSelectedDeviceForEdit(isEditing ? null : device.id)}
                      className="text-gray-400 hover:text-purple-500 transition-colors"
                    >
                      <Settings size={14} />
                    </button>
                  </div>
                  
                  {calibrationResult && (
                    <div className="text-xs text-green-600 flex items-center gap-1 mb-2">
                      <Check size={12} />
                      已校准: {calibrationResult.timeOffset.toFixed(1)}s 
                      (置信度: {(calibrationResult.confidence * 100).toFixed(0)}%)
                    </div>
                  )}
                  
                  {isEditing && (
                    <div className="space-y-2 mt-2 pt-2 border-t border-purple-200">
                      <div>
                        <label className="flex items-center justify-between text-xs text-gray-600 mb-1">
                          <span>时间偏移</span>
                          <span className="font-mono">{device.timeOffset}s</span>
                        </label>
                        <input
                          type="range"
                          min="-3600"
                          max="3600"
                          value={device.timeOffset}
                          onChange={(e) => updateDevice(device.id, { timeOffset: parseInt(e.target.value) })}
                          className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-500"
                        />
                      </div>
                      <div>
                        <label className="flex items-center justify-between text-xs text-gray-600 mb-1">
                          <span>最大时间差</span>
                          <span className="font-mono">{device.maxTimeDiff}s</span>
                        </label>
                        <input
                          type="range"
                          min="60"
                          max="3600"
                          step="60"
                          value={device.maxTimeDiff}
                          onChange={(e) => updateDevice(device.id, { maxTimeDiff: parseInt(e.target.value) })}
                          className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-500"
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-xs text-gray-600">自动校准</label>
                        <button
                          onClick={() => updateDevice(device.id, { autoCalibrationEnabled: !device.autoCalibrationEnabled })}
                          className={`w-8 h-4 rounded-full transition-colors ${
                            device.autoCalibrationEnabled ? 'bg-green-500' : 'bg-gray-300'
                          }`}
                        >
                          <div className={`w-3 h-3 bg-white rounded-full shadow transition-transform ${
                            device.autoCalibrationEnabled ? 'translate-x-4' : 'translate-x-0.5'
                          }`} />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center gap-2 mb-3">
          <Settings size={16} className="text-gray-500" />
          <h3 className="text-sm font-semibold text-gray-700">匹配设置</h3>
        </div>
        
        <div className="space-y-3">
          <div>
            <label className="flex items-center justify-between text-xs text-gray-600 mb-1">
              <span>全局时间偏移 (秒)</span>
              <span className="font-mono">{matchConfig.globalTimeOffset}s</span>
            </label>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min="-3600"
                max="3600"
                value={matchConfig.globalTimeOffset}
                onChange={(e) => setMatchConfig({ globalTimeOffset: parseInt(e.target.value) })}
                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-accent-500"
              />
              {matchConfig.enableAutoCalibration && (
                <button
                  onClick={handleAutoCalibrate}
                  disabled={isCalibrating || photos.filter(p => p.originalGps).length < 3}
                  className="px-2 py-1 text-xs bg-green-100 hover:bg-green-200 text-green-700 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                  title="基于GPS信号质量自动校准"
                >
                  {isCalibrating ? (
                    <RefreshCw size={14} className="animate-spin" />
                  ) : (
                    <Target size={14} />
                  )}
                  校准
                </button>
              )}
            </div>
          </div>
          
          <div>
            <label className="flex items-center justify-between text-xs text-gray-600 mb-1">
              <span>最大时间差 (秒)</span>
              <span className="font-mono">{matchConfig.globalMaxTimeDiff}s</span>
            </label>
            <input
              type="range"
              min="60"
              max="3600"
              step="60"
              value={matchConfig.globalMaxTimeDiff}
              onChange={(e) => setMatchConfig({ globalMaxTimeDiff: parseInt(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-accent-500"
            />
          </div>
          
          <div>
            <label className="text-xs text-gray-600 mb-1 block">插值方式</label>
            <select
              value={matchConfig.interpolation}
              onChange={(e) => setMatchConfig({ interpolation: e.target.value as 'linear' | 'nearest' | 'spline' })}
              className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-500/50"
            >
              <option value="linear">线性插值</option>
              <option value="nearest">最近点</option>
              <option value="spline">样条插值</option>
            </select>
          </div>
        </div>
        
        <button
          onClick={handleMatch}
          disabled={photos.length === 0 || tracks.length === 0 || isMatching}
          className="w-full mt-4 py-2.5 bg-gradient-to-r from-accent-500 to-primary-600 text-white rounded-lg font-medium flex items-center justify-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isMatching ? (
            <RefreshCw size={18} className="animate-spin" />
          ) : (
            <Play size={18} />
          )}
          {isMatching ? '匹配中...' : '开始匹配'}
        </button>
        
        <div className="mt-3 text-center text-sm">
          <span className="text-gray-500">匹配进度: </span>
          <span className="font-semibold text-accent-600">
            {matchedCount} / {photos.length}
          </span>
        </div>
      </div>
    </div>
  );
}
