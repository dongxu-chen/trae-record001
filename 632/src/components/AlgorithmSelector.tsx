import { motion } from 'framer-motion';
import { Zap, Scan, Grid3x3 } from 'lucide-react';
import { AlgorithmType, ALGORITHMS } from '../types';
import { useImageStore } from '../store/useImageStore';

const iconMap: Record<string, React.ReactNode> = {
  Zap: <Zap className="w-5 h-5" />,
  Scan: <Scan className="w-5 h-5" />,
  Grid3x3: <Grid3x3 className="w-5 h-5" />
};

export function AlgorithmSelector() {
  const { params, setParams } = useImageStore();

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-deep-space-200">
        抗锯齿算法
      </label>
      <div className="grid grid-cols-3 gap-2">
        {ALGORITHMS.map((algo) => (
          <motion.button
            key={algo.id}
            onClick={() => setParams({ algorithm: algo.id as AlgorithmType })}
            className={`relative p-3 rounded-xl border-2 transition-all duration-200 ${
              params.algorithm === algo.id
                ? 'border-neon-blue-400 bg-neon-blue-500/10 neon-glow'
                : 'border-deep-space-700 bg-deep-space-800/50 hover:border-deep-space-600'
            }`}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <div className="flex flex-col items-center gap-1">
              <span className={params.algorithm === algo.id ? 'text-neon-blue-400' : 'text-deep-space-400'}>
                {iconMap[algo.icon]}
              </span>
              <span className={`text-sm font-bold ${
                params.algorithm === algo.id ? 'text-neon-blue-400' : 'text-deep-space-200'
              }`}>
                {algo.name}
              </span>
              <span className="text-[10px] text-deep-space-500 text-center leading-tight">
                {algo.description.split(' - ')[1]}
              </span>
            </div>
            {params.algorithm === algo.id && (
              <motion.div
                className="absolute -top-1 -right-1 w-3 h-3 bg-neon-blue-400 rounded-full"
                layoutId="algorithm-indicator"
              />
            )}
          </motion.button>
        ))}
      </div>
    </div>
  );
}
