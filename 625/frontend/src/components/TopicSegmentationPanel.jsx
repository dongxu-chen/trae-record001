import { Layers, Hash, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

const TopicSegmentationPanel = ({ topicSummary }) => {
  const [expandedTopics, setExpandedTopics] = useState(new Set([0]));

  if (!topicSummary || !topicSummary.topics || topicSummary.topics.length === 0) {
    return null;
  }

  const toggleTopic = (topicId) => {
    const newExpanded = new Set(expandedTopics);
    if (newExpanded.has(topicId)) {
      newExpanded.delete(topicId);
    } else {
      newExpanded.add(topicId);
    }
    setExpandedTopics(newExpanded);
  };

  const topicColors = [
    'from-purple-500 to-indigo-500',
    'from-blue-500 to-cyan-500',
    'from-green-500 to-emerald-500',
    'from-orange-500 to-amber-500',
    'from-pink-500 to-rose-500',
  ];

  return (
    <div className="bg-white rounded-2xl p-6 card-shadow">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
          <Layers className="w-6 h-6 text-purple-600" />
          话题分段摘要
        </h3>
        <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
          {topicSummary.num_topics} 个话题 · {topicSummary.method.toUpperCase()}
        </span>
      </div>

      <div className="space-y-4">
        {topicSummary.topics.map((topic, idx) => (
          <div
            key={topic.topic_id}
            className="border border-gray-100 rounded-xl overflow-hidden"
          >
            <button
              onClick={() => toggleTopic(topic.topic_id)}
              className="w-full p-4 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full bg-gradient-to-r ${topicColors[idx % topicColors.length]}`} />
                <div className="text-left">
                  <div className="font-semibold text-gray-800">
                    话题 {idx + 1}
                  </div>
                  <div className="text-sm text-gray-500">
                    {topic.num_sentences} 个句子
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="hidden md:flex gap-1">
                  {topic.keywords.slice(0, 3).map((kw, kidx) => (
                    <span
                      key={kidx}
                      className="px-2 py-1 bg-white rounded-md text-xs text-gray-600 border border-gray-200"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
                {expandedTopics.has(topic.topic_id) ? (
                  <ChevronDown className="w-5 h-5 text-gray-500" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-gray-500" />
                )}
              </div>
            </button>

            {expandedTopics.has(topic.topic_id) && (
              <div className="p-4 border-t border-gray-100">
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Hash className="w-4 h-4 text-purple-600" />
                    <span className="text-sm font-medium text-gray-700">关键词</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {topic.keywords.map((kw, kidx) => (
                      <span
                        key={kidx}
                        className="px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-xs font-medium"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="text-sm font-medium text-gray-700 mb-2">话题摘要</div>
                  <p className="text-gray-600 leading-relaxed bg-gray-50 p-4 rounded-lg">
                    {topic.topic_summary}
                  </p>
                </div>

                <div className="mt-4">
                  <details className="text-sm">
                    <summary className="cursor-pointer text-purple-600 hover:text-purple-700 font-medium">
                      查看原文内容
                    </summary>
                    <p className="mt-2 text-gray-500 bg-gray-50 p-3 rounded-lg text-xs leading-relaxed">
                      {topic.topic_text}
                    </p>
                  </details>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default TopicSegmentationPanel;
