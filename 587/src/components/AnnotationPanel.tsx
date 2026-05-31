import React, { useMemo, useState } from 'react';
import { MessageSquare, ArrowRight, Square, Trash2, Edit3, Search, Filter, Sparkles, BookTemplate, X, ChevronDown, ChevronUp, Check } from 'lucide-react';
import { Annotation, AnnotationType } from '../../shared/types';
import { useStore } from '../store/useStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { searchAnnotations, annotationTemplates } from '../utils/aiAnalysis';

interface AnnotationPanelProps {
  onAIAnalysis?: () => void;
}

const AnnotationPanel: React.FC<AnnotationPanelProps> = ({ onAIAnalysis }) => {
  const {
    annotations,
    selectedAnnotationId,
    setSelectedAnnotationId,
    deleteAnnotation,
    searchQuery,
    setSearchQuery,
    searchFilters,
    setSearchFilters,
    showTemplates,
    setShowTemplates,
    selectedTemplateCategory,
    setSelectedTemplateCategory,
    permissions,
    currentUser,
  } = useStore();

  const { sendAnnotationDelete, sendAnnotationUpdate, sendAnnotationAdd } = useWebSocket();
  const [showFilters, setShowFilters] = useState(false);

  const filteredAnnotations = useMemo(() => {
    return searchAnnotations(annotations, searchQuery, searchFilters);
  }, [annotations, searchQuery, searchFilters]);

  const templateCategories = useMemo(() => {
    const categories = ['全部', ...new Set(annotationTemplates.map(t => t.category))];
    return categories;
  }, []);

  const filteredTemplates = useMemo(() => {
    if (selectedTemplateCategory === '全部') return annotationTemplates;
    return annotationTemplates.filter(t => t.category === selectedTemplateCategory);
  }, [selectedTemplateCategory]);

  const getTypeIcon = (type: AnnotationType) => {
    switch (type) {
      case 'text':
        return <MessageSquare size={16} />;
      case 'arrow':
        return <ArrowRight size={16} />;
      case 'highlight':
        return <Square size={16} />;
    }
  };

  const getTypeName = (type: AnnotationType) => {
    switch (type) {
      case 'text':
        return '文本';
      case 'arrow':
        return '箭头';
      case 'highlight':
        return '高亮';
    }
  };

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    sendAnnotationDelete(id);
    deleteAnnotation(id);
  };

  const handleEditContent = (annotation: Annotation) => {
    if (annotation.type === 'text') {
      const newContent = prompt('编辑注释内容:', annotation.content);
      if (newContent !== null && newContent !== undefined) {
        sendAnnotationUpdate(annotation.id, { content: newContent });
      }
    }
  };

  const handleTemplateClick = (template: typeof annotationTemplates[0]) => {
    if (!currentUser || permissions === 'read') return;

    const annotation = {
      type: 'text' as AnnotationType,
      position: { x: 0.3 + Math.random() * 0.4, y: 0.3 + Math.random() * 0.4 },
      content: `${template.icon} ${template.content}`,
      color: template.color,
      authorId: currentUser.id,
      authorName: currentUser.name,
    };

    sendAnnotationAdd(annotation);
    setShowTemplates(false);
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="w-80 bg-gray-50 border-l border-gray-200 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-800">注释列表</h2>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowTemplates(!showTemplates)}
              className={`p-1.5 rounded-md transition-colors ${
                showTemplates ? 'bg-purple-100 text-purple-600' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
              }`}
              title="注释模板"
            >
              <BookTemplate size={18} />
            </button>
            <button
              onClick={onAIAnalysis}
              className="p-1.5 rounded-md text-gray-400 hover:text-purple-600 hover:bg-purple-50 transition-colors"
              title="AI 智能推荐"
            >
              <Sparkles size={18} />
            </button>
          </div>
        </div>

        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索注释内容、作者、类型..."
            className="w-full pl-9 pr-9 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X size={14} />
            </button>
          )}
        </div>

        <div className="flex items-center justify-between mt-2">
          <span className="text-sm text-gray-500">
            共 {filteredAnnotations.length} / {annotations.length} 条
          </span>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-1 text-xs transition-colors ${
              showFilters ? 'text-blue-600' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Filter size={14} />
            筛选
            {showFilters ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>

        {showFilters && (
          <div className="mt-3 p-3 bg-gray-50 rounded-lg space-y-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={searchFilters.searchContent}
                onChange={(e) => setSearchFilters({ searchContent: e.target.checked })}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              搜索内容
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={searchFilters.searchAuthor}
                onChange={(e) => setSearchFilters({ searchAuthor: e.target.checked })}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              搜索作者
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={searchFilters.searchType}
                onChange={(e) => setSearchFilters({ searchType: e.target.checked })}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              搜索类型
            </label>
          </div>
        )}
      </div>

      {showTemplates && (
        <div className="p-3 border-b border-gray-200 bg-white">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-700">快速注释模板</h3>
            <button
              onClick={() => setShowTemplates(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X size={14} />
            </button>
          </div>
          
          <div className="flex gap-1 mb-2 overflow-x-auto pb-1">
            {templateCategories.map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedTemplateCategory(cat)}
                className={`px-2 py-1 text-xs rounded-full whitespace-nowrap transition-colors ${
                  selectedTemplateCategory === cat
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
          
          <div className="grid grid-cols-2 gap-1.5 max-h-32 overflow-y-auto">
            {filteredTemplates.map(template => (
              <button
                key={template.id}
                onClick={() => handleTemplateClick(template)}
                disabled={permissions === 'read'}
                className={`flex items-center gap-1.5 p-2 text-left text-xs rounded-lg border transition-all ${
                  permissions === 'read'
                    ? 'opacity-50 cursor-not-allowed border-gray-200'
                    : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                }`}
              >
                <span>{template.icon}</span>
                <span className="truncate">{template.content}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filteredAnnotations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <MessageSquare size={48} className="mb-3 opacity-50" />
            <p className="text-sm">
              {searchQuery ? '没有找到匹配的注释' : '暂无注释'}
            </p>
            <p className="text-xs mt-1">
              {searchQuery ? '尝试调整搜索条件' : '选择工具在图表上添加注释'}
            </p>
          </div>
        ) : (
          filteredAnnotations.map((annotation) => (
            <div
              key={annotation.id}
              onClick={() => setSelectedAnnotationId(annotation.id)}
              className={`p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                selectedAnnotationId === annotation.id
                  ? 'bg-blue-50 border-2 border-blue-500 shadow-sm'
                  : 'bg-white border border-gray-200 hover:border-gray-300 hover:shadow-sm'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="p-1.5 rounded-md"
                    style={{ backgroundColor: annotation.color + '20', color: annotation.color }}
                  >
                    {getTypeIcon(annotation.type)}
                  </span>
                  <div className="min-w-0">
                    <span className="text-xs font-medium text-gray-500">
                      {getTypeName(annotation.type)}
                    </span>
                    {annotation.content && (
                      <p className="text-sm text-gray-700 mt-0.5 line-clamp-2">
                        {annotation.content}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-100">
                <div className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: annotation.color }}
                  />
                  <span className="text-xs text-gray-500">{annotation.authorName}</span>
                </div>
                <span className="text-xs text-gray-400">
                  {formatTime(annotation.createdAt)}
                </span>
              </div>

              {permissions !== 'read' && (
                <div className="flex items-center gap-1 mt-2 pt-2 border-t border-gray-100">
                  {annotation.type === 'text' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditContent(annotation);
                      }}
                      className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded transition-colors"
                    >
                      <Edit3 size={12} />
                      编辑
                    </button>
                  )}
                  <button
                    onClick={(e) => handleDelete(e, annotation.id)}
                    className="flex items-center gap-1 px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded transition-colors"
                  >
                    <Trash2 size={12} />
                    删除
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="p-3 border-t border-gray-200 bg-white">
        <div className="text-xs text-gray-500 space-y-1">
          <p>💡 双击文本注释可编辑内容</p>
          <p>⌨️ 按 Delete 键删除选中的注释</p>
          <p>✨ 点击 ✨ 按钮获取AI智能推荐</p>
        </div>
      </div>
    </div>
  );
};

export default AnnotationPanel;
