import { Copy, Check, ThumbsUp, ThumbsDown } from 'lucide-react';
import { motion } from 'framer-motion';
import type { Recommendation } from '../../shared/types';
import { cn } from '../lib/utils';

interface RecommendationCardProps {
  recommendation: Recommendation;
  index: number;
  copiedId: string | null;
  showConfidence: boolean;
  onCopy: (id: string, name: string) => void;
  onFeedback?: (name: string, style: string, feedback: 'like' | 'dislike') => void;
}

const RecommendationCard = ({
  recommendation,
  index,
  copiedId,
  showConfidence,
  onCopy,
  onFeedback
}: RecommendationCardProps) => {
  const isCopied = copiedId === recommendation.id;
  const confidenceColor = recommendation.confidence >= 0.8 
    ? 'from-green-400 to-emerald-500'
    : recommendation.confidence >= 0.6
    ? 'from-blue-400 to-cyan-500'
    : 'from-yellow-400 to-orange-500';

  const typeLabels: Record<string, { label: string; color: string }> = {
    variable: { label: '变量', color: 'bg-gray-100 text-gray-600' },
    function: { label: '函数', color: 'bg-blue-100 text-blue-700' },
    class: { label: '类', color: 'bg-purple-100 text-purple-700' },
    constant: { label: '常量', color: 'bg-amber-100 text-amber-700' },
    boolean: { label: '布尔', color: 'bg-green-100 text-green-700' }
  };

  const typeInfo = typeLabels[recommendation.type] || typeLabels.variable;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      className="group relative bg-white rounded-xl border border-gray-200 p-4 hover:border-blue-300 hover:shadow-lg transition-all duration-300"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <code className="text-lg font-mono font-semibold text-gray-900 break-all">
              {recommendation.name}
            </code>
            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full font-mono">
              {recommendation.style}
            </span>
            <span className={cn('px-2 py-0.5 text-xs rounded-full', typeInfo.color)}>
              {typeInfo.label}
            </span>
          </div>
          
          <p className="text-sm text-gray-500 mb-3">{recommendation.description}</p>
          
          {showConfidence && (
            <div className="flex items-center space-x-2">
              <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={cn('h-full bg-gradient-to-r rounded-full', confidenceColor)}
                  style={{ width: `${recommendation.confidence * 100}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 font-medium">
                {Math.round(recommendation.confidence * 100)}%
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 ml-4">
          {onFeedback && (
            <div className="flex items-center gap-1 mr-2">
              <button
                onClick={() => onFeedback(recommendation.name, recommendation.style, 'like')}
                className="p-1.5 rounded-lg bg-gray-100 text-gray-400 hover:bg-green-100 hover:text-green-600 transition-all duration-200"
                title="有用"
              >
                <ThumbsUp className="w-4 h-4" />
              </button>
              <button
                onClick={() => onFeedback(recommendation.name, recommendation.style, 'dislike')}
                className="p-1.5 rounded-lg bg-gray-100 text-gray-400 hover:bg-red-100 hover:text-red-600 transition-all duration-200"
                title="无用"
              >
                <ThumbsDown className="w-4 h-4" />
              </button>
            </div>
          )}
          
          <button
            onClick={() => onCopy(recommendation.id, recommendation.name)}
            className={cn(
              'p-2 rounded-lg transition-all duration-200',
              isCopied
                ? 'bg-green-100 text-green-600'
                : 'bg-gray-100 text-gray-500 hover:bg-blue-100 hover:text-blue-600'
            )}
            title={isCopied ? '已复制' : '复制'}
          >
            {isCopied ? (
              <Check className="w-4 h-4" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default RecommendationCard;
