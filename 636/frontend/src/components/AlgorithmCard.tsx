import React from 'react';
import { IdAlgorithm } from '../types';

interface AlgorithmCardProps {
  algorithm: IdAlgorithm;
  selected: boolean;
  onClick: () => void;
}

const algorithmInfo: Record<IdAlgorithm, { name: string; description: string; icon: string; color: string }> = {
  SNOWFLAKE: {
    name: '雪花算法',
    description: 'Twitter Snowflake，64位有序ID，包含时间戳、机器ID和序列号',
    icon: '❄️',
    color: 'from-blue-400 to-cyan-400',
  },
  SEGMENT: {
    name: '号段模式',
    description: '基于数据库号段的递增ID，预分配号段提升性能',
    icon: '📦',
    color: 'from-green-400 to-emerald-400',
  },
  RANDOM: {
    name: '随机ID',
    description: '安全随机数生成，固定长度，无序但唯一性高',
    icon: '🎲',
    color: 'from-purple-400 to-pink-400',
  },
};

const AlgorithmCard: React.FC<AlgorithmCardProps> = ({ algorithm, selected, onClick }) => {
  const info = algorithmInfo[algorithm];

  return (
    <div
      onClick={onClick}
      className={`relative p-6 rounded-xl cursor-pointer transition-all duration-300 transform hover:scale-102 ${
        selected
          ? 'bg-white shadow-xl border-2 border-primary ring-4 ring-primary/10'
          : 'bg-white shadow-md border-2 border-transparent hover:shadow-lg'
      }`}
    >
      {selected && (
        <div className="absolute top-4 right-4">
          <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
            <span className="text-white text-sm">✓</span>
          </div>
        </div>
      )}
      <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${info.color} flex items-center justify-center mb-4 shadow-lg`}>
        <span className="text-2xl">{info.icon}</span>
      </div>
      <h3 className="text-lg font-bold text-gray-900 mb-2">{info.name}</h3>
      <p className="text-sm text-gray-500 leading-relaxed">{info.description}</p>
      <div className="mt-4 text-xs font-mono text-gray-400">
        {algorithm}
      </div>
    </div>
  );
};

export default AlgorithmCard;
