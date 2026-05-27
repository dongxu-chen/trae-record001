import React, { useMemo, useState } from 'react';
import { useIconStore, getIconById, getAllIcons } from '../../store/iconStore';
import { analyzeProjectIcons, generateUpdatePlan, outdatedIcons } from '../../utils/iconReplacement';
import { AlertTriangle, X, ArrowRight, Check, RefreshCw } from 'lucide-react';

interface ReplacementPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const ReplacementPanel: React.FC<ReplacementPanelProps> = ({ isOpen, onClose }) => {
  const { favorites, recent, setActiveIcon, addToRecent } = useIconStore();
  const [scanComplete, setScanComplete] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);

  const allUsedIconIds = useMemo(() => {
    return [...Object.keys(favorites), ...Object.keys(recent)];
  }, [favorites, recent]);

  const analysis = useMemo(() => {
    if (!scanComplete) return null;
    return analyzeProjectIcons(allUsedIconIds);
  }, [allUsedIconIds, scanComplete]);

  const updatePlan = useMemo(() => {
    if (!analysis) return null;
    return generateUpdatePlan(analysis.suggestions);
  }, [analysis]);

  const handleScan = () => {
    setScanning(true);
    setScanProgress(0);
    
    const totalSteps = 10;
    let currentStep = 0;
    
    const interval = setInterval(() => {
      currentStep++;
      setScanProgress((currentStep / totalSteps) * 100);
      
      if (currentStep >= totalSteps) {
        clearInterval(interval);
        setScanning(false);
        setScanComplete(true);
      }
    }, 200);
  };

  const handleReplace = (oldId: string, newId: string) => {
    setActiveIcon(newId);
    addToRecent(newId);
  };

  if (!isOpen) return null;

  return (
    <div className="w-80 bg-[#12121a] border-l border-[#2a2a3a] flex flex-col">
      <div className="p-4 border-b border-[#2a2a3a] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-[#F59E0B]" />
          <h3 className="text-sm font-semibold text-gray-200">图标替换建议</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-gray-500 hover:text-gray-300 hover:bg-[#1a1a2a] transition-all"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {!scanComplete && !scanning && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 rounded-full bg-[#1a1a2a] flex items-center justify-center mb-4">
              <RefreshCw size={32} className="text-gray-600" />
            </div>
            <h4 className="text-lg font-medium text-gray-300 mb-2">检测过时图标</h4>
            <p className="text-sm text-gray-500 mb-6 max-w-xs">
              扫描您收藏和使用的图标，发现可以优化的过时设计
            </p>
            <button
              onClick={handleScan}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-[#4F46E5] to-[#06B6D4] text-white font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              <RefreshCw size={16} />
              开始扫描
            </button>
            <p className="text-xs text-gray-600 mt-4">
              内置 {outdatedIcons.length} 个过时图标检测规则
            </p>
          </div>
        )}

        {scanning && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 mb-4 relative">
              <svg className="w-full h-full animate-spin" viewBox="0 0 36 36">
                <path
                  className="text-gray-700"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                />
                <path
                  className="text-[#4F46E5]"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  style={{
                    strokeDasharray: `${scanProgress * 1.0} 100`,
                    transition: 'stroke-dasharray 0.3s ease'
                  }}
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-xs text-gray-400">
                {Math.round(scanProgress)}%
              </span>
            </div>
            <p className="text-sm text-gray-400">正在分析图标库...</p>
            <p className="text-xs text-gray-600 mt-1">检查 {allUsedIconIds.length} 个图标</p>
          </div>
        )}

        {scanComplete && analysis && (
          <div className="space-y-4">
            <div className={`p-4 rounded-xl ${
              analysis.outdatedCount === 0 
                ? 'bg-green-500/10 border border-green-500/20' 
                : analysis.outdatedCount <= 3
                ? 'bg-yellow-500/10 border border-yellow-500/20'
                : 'bg-red-500/10 border border-red-500/20'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                {analysis.outdatedCount === 0 ? (
                  <Check size={18} className="text-green-400" />
                ) : (
                  <AlertTriangle size={18} className={analysis.outdatedCount <= 3 ? 'text-yellow-400' : 'text-red-400'} />
                )}
                <span className={`font-semibold ${
                  analysis.outdatedCount === 0 
                    ? 'text-green-400' 
                    : analysis.outdatedCount <= 3
                    ? 'text-yellow-400'
                    : 'text-red-400'
                }`}>
                  {analysis.outdatedCount === 0 ? '图标库状态良好' : `发现 ${analysis.outdatedCount} 个过时图标`}
                </span>
              </div>
              <p className="text-xs text-gray-400">{analysis.summary}</p>
            </div>

            {updatePlan && (
              <div className="p-4 rounded-xl bg-[#1a1a2a]">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-300">更新建议</span>
                  <span className={`px-2 py-0.5 text-xs rounded-full ${
                    updatePlan.priority === 'high'
                      ? 'bg-red-500/20 text-red-400'
                      : updatePlan.priority === 'medium'
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-green-500/20 text-green-400'
                  }`}>
                    {updatePlan.priority === 'high' ? '高优先级' : updatePlan.priority === 'medium' ? '中优先级' : '低优先级'}
                  </span>
                </div>
                <ul className="space-y-2 mb-3">
                  {updatePlan.steps.map((step, i) => (
                    <li key={i} className="text-xs text-gray-400 flex items-start gap-2">
                      <span className="text-[#4F46E5] mt-0.5">•</span>
                      {step}
                    </li>
                  ))}
                </ul>
                <p className="text-xs text-gray-500">
                  预计时间: {updatePlan.estimatedTime}
                </p>
              </div>
            )}

            {analysis.suggestions.length > 0 && (
              <div>
                <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  替换建议
                </h5>
                <div className="space-y-3">
                  {analysis.suggestions.slice(0, 8).map((suggestion, index) => {
                    const oldIcon = getIconById(suggestion.oldIconId);
                    const newIcon = getIconById(suggestion.newIconId);
                    
                    return (
                      <div key={index} className="p-3 rounded-xl bg-[#1a1a2a]">
                        <div className="flex items-center gap-3 mb-2">
                          {oldIcon && (
                            <div className="flex items-center gap-2">
                              <svg width={20} height={20} viewBox="0 0 24 24" fill="#6B7280">
                                <path d={oldIcon.svgPath} />
                              </svg>
                              <span className="text-xs text-gray-500 line-through">
                                {suggestion.oldIconName}
                              </span>
                            </div>
                          )}
                          <ArrowRight size={14} className="text-gray-600" />
                          {newIcon && (
                            <div className="flex items-center gap-2">
                              <svg width={20} height={20} viewBox="0 0 24 24" fill="#4F46E5">
                                <path d={newIcon.svgPath} />
                              </svg>
                              <span className="text-xs text-[#4F46E5] font-medium">
                                {suggestion.newIconName}
                              </span>
                            </div>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mb-2">{suggestion.reason}</p>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-600">
                            改进: {suggestion.improvement}
                          </span>
                          <button
                            onClick={() => handleReplace(suggestion.oldIconId, suggestion.newIconId)}
                            className="px-2 py-1 text-xs rounded-md bg-[#4F46E5]/20 text-[#4F46E5] hover:bg-[#4F46E5]/30 transition-colors"
                          >
                            查看
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReplacementPanel;
