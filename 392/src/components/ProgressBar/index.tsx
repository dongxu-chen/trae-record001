import React from 'react';

interface ProgressBarProps {
  progress: number;
  isDownloading: boolean;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ progress, isDownloading }) => {
  if (!isDownloading && progress === 0) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 w-80 bg-[#12121a] border border-[#2a2a3a] rounded-xl p-4 shadow-2xl z-50">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-300 font-medium">
          {progress >= 100 ? '下载完成!' : '正在打包下载...'}
        </span>
        <span className="text-sm text-[#4F46E5] font-bold">
          {Math.round(progress)}%
        </span>
      </div>
      <div className="w-full h-2 bg-[#1a1a2a] rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-[#4F46E5] to-[#06B6D4] rounded-full transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      {progress >= 100 && (
        <p className="text-xs text-green-400 mt-2 text-center">
          ✓ 图标包已生成，正在启动下载...
        </p>
      )}
    </div>
  );
};

export default ProgressBar;
