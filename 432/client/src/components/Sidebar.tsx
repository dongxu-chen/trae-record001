import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Search, MessageSquare, FileText, X } from 'lucide-react';
import { usePdfContext } from '../contexts/PdfContext';
import { OutlineNode } from '../types';

const Sidebar: React.FC = () => {
  const { state, dispatch } = usePdfContext();
  const { document, viewer } = state;
  const { sidebarOpen, sidebarTab, currentPage } = viewer;
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  const toggleNode = (nodeId: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const handleOutlineClick = (pageIndex: number) => {
    dispatch({ type: 'SET_CURRENT_PAGE', payload: pageIndex });
  };

  const handleSearch = async () => {
    if (!searchQuery.trim() || !document) {
      setSearchResults([]);
      return;
    }

    const results: any[] = [];
    const annotations = document.annotations.filter(
      (a) =>
        a.content?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        a.type.toLowerCase().includes(searchQuery.toLowerCase())
    );

    annotations.forEach((a) => {
      results.push({
        pageIndex: a.pageIndex,
        text: a.content || a.type,
        type: a.type,
      });
    });

    setSearchResults(results);
  };

  const renderOutlineNode = (node: OutlineNode, depth: number = 0) => {
    const hasChildren = node.children.length > 0;
    const isExpanded = expandedNodes.has(node.id);
    const isActive = node.pageIndex === currentPage;

    return (
      <div key={node.id}>
        <div
          className={`outline-item flex items-center gap-1 ${isActive ? 'active' : ''}`}
          style={{ paddingLeft: `${depth * 12 + 12}px` }}
          onClick={() => handleOutlineClick(node.pageIndex)}
        >
          {hasChildren ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleNode(node.id);
              }}
              className="p-0.5 hover:bg-gray-200 rounded"
            >
              {isExpanded ? (
                <ChevronDown size={14} className="text-gray-500" />
              ) : (
                <ChevronRight size={14} className="text-gray-500" />
              )}
            </button>
          ) : (
            <span className="w-5" />
          )}
          <span className="flex-1 truncate">{node.title}</span>
        </div>
        {hasChildren && isExpanded && (
          <div>
            {node.children.map((child) => renderOutlineNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (!sidebarOpen) {
    return (
      <button
        className="w-8 bg-white border-l border-gray-200 flex items-center justify-center hover:bg-gray-50"
        onClick={() => dispatch({ type: 'TOGGLE_SIDEBAR' })}
      >
        <ChevronRight size={18} className="text-gray-500" />
      </button>
    );
  }

  return (
    <div className="w-72 bg-white border-l border-gray-200 flex flex-col">
      <div className="flex items-center justify-between px-4 h-12 border-b border-gray-200">
        <div className="flex gap-1">
          <button
            className={`sidebar-tab ${sidebarTab === 'outline' ? 'active' : ''}`}
            onClick={() => dispatch({ type: 'SET_SIDEBAR_TAB', payload: 'outline' })}
          >
            <FileText size={16} className="inline mr-1" />
            目录
          </button>
          <button
            className={`sidebar-tab ${sidebarTab === 'search' ? 'active' : ''}`}
            onClick={() => dispatch({ type: 'SET_SIDEBAR_TAB', payload: 'search' })}
          >
            <Search size={16} className="inline mr-1" />
            搜索
          </button>
          <button
            className={`sidebar-tab ${sidebarTab === 'annotations' ? 'active' : ''}`}
            onClick={() => dispatch({ type: 'SET_SIDEBAR_TAB', payload: 'annotations' })}
          >
            <MessageSquare size={16} className="inline mr-1" />
            批注
          </button>
        </div>
        <button
          className="p-1 hover:bg-gray-100 rounded"
          onClick={() => dispatch({ type: 'TOGGLE_SIDEBAR' })}
        >
          <X size={16} className="text-gray-500" />
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        {sidebarTab === 'outline' && (
          <div className="py-2">
            {document && document.outlines.length > 0 ? (
              document.outlines.map((node) => renderOutlineNode(node))
            ) : (
              <div className="text-center py-8 text-gray-400 text-sm">
                暂无目录
              </div>
            )}
          </div>
        )}

        {sidebarTab === 'search' && (
          <div className="p-4">
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                placeholder="搜索批注内容..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button
                className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                onClick={handleSearch}
              >
                <Search size={16} />
              </button>
            </div>
            {searchResults.length > 0 ? (
              <div className="space-y-2">
                {searchResults.map((result, index) => (
                  <div
                    key={index}
                    className="p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100"
                    onClick={() => dispatch({ type: 'SET_CURRENT_PAGE', payload: result.pageIndex })}
                  >
                    <div className="text-xs text-gray-500 mb-1">第 {result.pageIndex + 1} 页</div>
                    <div className="text-sm">{result.text}</div>
                  </div>
                ))}
              </div>
            ) : searchQuery ? (
              <div className="text-center py-8 text-gray-400 text-sm">
                未找到匹配结果
              </div>
            ) : null}
          </div>
        )}

        {sidebarTab === 'annotations' && (
          <div className="py-2">
            {document && document.annotations.length > 0 ? (
              document.annotations.map((annotation) => (
                <div
                  key={annotation.id}
                  className="px-4 py-3 border-b border-gray-100 cursor-pointer hover:bg-gray-50"
                  onClick={() => dispatch({ type: 'SET_CURRENT_PAGE', payload: annotation.pageIndex })}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: annotation.color }}
                    />
                    <span className="text-xs text-gray-500">
                      第 {annotation.pageIndex + 1} 页
                    </span>
                    <span className="text-xs text-gray-400 capitalize">
                      {annotation.type}
                    </span>
                  </div>
                  {annotation.content && (
                    <div className="text-sm text-gray-700 ml-5">
                      {annotation.content}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-400 text-sm">
                暂无批注
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
