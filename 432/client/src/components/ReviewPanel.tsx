import React, { useState, useEffect } from 'react';
import { X, Users, UserPlus, Copy, Check, AlertTriangle, Merge, RefreshCw } from 'lucide-react';
import { usePdfContext } from '../contexts/PdfContext';

interface ReviewPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const REVIEWER_COLORS = [
  '#165DFF',
  '#FF7D00',
  '#4CAF50',
  '#9C27B0',
  '#00BCD4',
];

const ReviewPanel: React.FC<ReviewPanelProps> = ({ isOpen, onClose }) => {
  const { state, dispatch } = usePdfContext();
  const { document, currentReviewer, reviewSession, otherAnnotations } = state;
  
  const [reviewerName, setReviewerName] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showMergePanel, setShowMergePanel] = useState(false);
  const [selectedAnnotations, setSelectedAnnotations] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (reviewSession) {
      const interval = setInterval(() => {
        fetchSessionAnnotations();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [reviewSession]);

  const fetchSessionAnnotations = async () => {
    if (!reviewSession) return;
    
    try {
      const res = await fetch(`/api/review/session/${reviewSession.sessionId}`);
      const data = await res.json();
      
      if (data.annotations) {
        const others = data.annotations.filter(
          (a: any) => a.reviewerId !== currentReviewer?.id
        );
        dispatch({ type: 'SET_OTHER_ANNOTATIONS', payload: others });
      }
    } catch (e) {
      console.error('Failed to fetch annotations');
    }
  };

  const handleCreateSession = async () => {
    if (!document || !reviewerName.trim()) {
      setError('请输入审阅者名称');
      return;
    }

    setError(null);
    setIsJoining(true);

    try {
      const res = await fetch('/api/review/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fileId: document.id,
          reviewerName: reviewerName.trim(),
        }),
      });

      const data = await res.json();
      
      const reviewer = {
        id: data.reviewerId,
        name: reviewerName.trim(),
        color: REVIEWER_COLORS[0],
        role: 'owner' as const,
      };

      dispatch({ type: 'SET_CURRENT_REVIEWER', payload: reviewer });
      dispatch({ type: 'SET_REVIEW_SESSION', payload: data.session });
      setSessionId(data.session.sessionId);
    } catch (e) {
      setError('创建会话失败');
    } finally {
      setIsJoining(false);
    }
  };

  const handleJoinSession = async () => {
    if (!reviewerName.trim() || !sessionId.trim()) {
      setError('请输入审阅者名称和会话ID');
      return;
    }

    setError(null);
    setIsJoining(true);

    try {
      const res = await fetch(`/api/review/session/${sessionId}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewerName: reviewerName.trim() }),
      });

      const data = await res.json();
      
      const colorIndex = Math.floor(Math.random() * REVIEWER_COLORS.length);
      const reviewer = {
        id: data.reviewerId,
        name: reviewerName.trim(),
        color: REVIEWER_COLORS[colorIndex],
        role: 'reviewer' as const,
      };

      dispatch({ type: 'SET_CURRENT_REVIEWER', payload: reviewer });
      
      const sessionRes = await fetch(`/api/review/session/${sessionId}`);
      const sessionData = await sessionRes.json();
      dispatch({ type: 'SET_REVIEW_SESSION', payload: sessionData.session });
      
      if (sessionData.annotations) {
        const others = sessionData.annotations.filter(
          (a: any) => a.reviewerId !== data.reviewerId
        );
        dispatch({ type: 'SET_OTHER_ANNOTATIONS', payload: others });
      }
    } catch (e) {
      setError('加入会话失败');
    } finally {
      setIsJoining(false);
    }
  };

  const handleCopySessionId = () => {
    navigator.clipboard.writeText(sessionId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleToggleSelect = (annotationId: string) => {
    setSelectedAnnotations((prev) => {
      const next = new Set(prev);
      if (next.has(annotationId)) {
        next.delete(annotationId);
      } else {
        next.add(annotationId);
      }
      return next;
    });
  };

  const handleMerge = async () => {
    if (!reviewSession) return;

    try {
      const res = await fetch(`/api/review/session/${reviewSession.sessionId}/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selectedIds: Array.from(selectedAnnotations) }),
      });

      const data = await res.json();
      
      if (data.mergedAnnotations) {
        const allAnnotations = [...state.document!.annotations, ...data.mergedAnnotations];
        dispatch({
          type: 'SET_DOCUMENT',
          payload: { ...state.document!, annotations: allAnnotations },
        });
        setShowMergePanel(false);
        alert('合并成功！');
      }
    } catch (e) {
      alert('合并失败');
    }
  };

  const handleSelectAll = () => {
    const allIds = otherAnnotations.map((a: any) => a.id);
    setSelectedAnnotations(new Set(allIds));
  };

  if (!isOpen || !document) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Users className="text-primary-600" size={24} />
            多人审阅
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-4 overflow-auto max-h-[70vh]">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
              <AlertTriangle size={18} />
              {error}
            </div>
          )}

          {!reviewSession ? (
            <div className="space-y-6">
              <div>
                <h4 className="font-medium text-gray-800 mb-3">创建新审阅会话</h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">您的名称</label>
                    <input
                      type="text"
                      value={reviewerName}
                      onChange={(e) => setReviewerName(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="请输入您的名称"
                    />
                  </div>
                  <button
                    onClick={handleCreateSession}
                    disabled={isJoining}
                    className="w-full py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    <UserPlus size={18} />
                    创建审阅会话
                  </button>
                </div>
              </div>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200" />
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-white px-4 text-sm text-gray-500">或者</span>
                </div>
              </div>

              <div>
                <h4 className="font-medium text-gray-800 mb-3">加入已有会话</h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">会话ID</label>
                    <input
                      type="text"
                      value={sessionId}
                      onChange={(e) => setSessionId(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="请输入会话ID"
                    />
                  </div>
                  <button
                    onClick={handleJoinSession}
                    disabled={isJoining}
                    className="w-full py-2.5 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 disabled:opacity-50"
                  >
                    加入会话
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-4 bg-primary-50 rounded-lg border border-primary-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-primary-700">会话ID</span>
                  <button
                    onClick={handleCopySessionId}
                    className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700"
                  >
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                    {copied ? '已复制' : '复制'}
                  </button>
                </div>
                <code className="text-sm bg-white px-2 py-1 rounded block">
                  {reviewSession.sessionId}
                </code>
                <p className="mt-2 text-xs text-gray-500">
                  分享此ID给其他审阅者，让他们加入审阅
                </p>
              </div>

              <div className="flex items-center justify-between">
                <h4 className="font-medium text-gray-800">审阅者列表</h4>
                <button
                  onClick={fetchSessionAnnotations}
                  className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700"
                >
                  <RefreshCw size={14} />
                  刷新
                </button>
              </div>

              <div className="space-y-2">
                {reviewSession.reviewers.map((reviewer: any) => (
                  <div
                    key={reviewer.id}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                  >
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center text-white font-medium text-sm"
                      style={{ backgroundColor: reviewer.color }}
                    >
                      {reviewer.name[0]?.toUpperCase()}
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-gray-800">{reviewer.name}</div>
                      <div className="text-xs text-gray-500">
                        {reviewer.role === 'owner' ? '文档所有者' : '审阅者'}
                      </div>
                    </div>
                    {reviewer.id === currentReviewer?.id && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                        您
                      </span>
                    )}
                  </div>
                ))}
              </div>

              {currentReviewer?.role === 'owner' && otherAnnotations.length > 0 && (
                <div>
                  <button
                    onClick={() => setShowMergePanel(!showMergePanel)}
                    className="w-full py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 flex items-center justify-center gap-2"
                  >
                    <Merge size={18} />
                    合并审阅标注 ({otherAnnotations.length})
                  </button>

                  {showMergePanel && (
                    <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="flex items-center justify-between mb-3">
                        <h5 className="font-medium text-gray-800">选择要合并的标注</h5>
                        <button
                          onClick={handleSelectAll}
                          className="text-sm text-primary-600 hover:text-primary-700"
                        >
                          全选
                        </button>
                      </div>
                      <div className="space-y-2 max-h-48 overflow-auto">
                        {otherAnnotations.map((annotation: any) => (
                          <label
                            key={annotation.id}
                            className="flex items-center gap-3 p-2 hover:bg-white rounded cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={selectedAnnotations.has(annotation.id)}
                              onChange={() => handleToggleSelect(annotation.id)}
                              className="rounded"
                            />
                            <div
                              className="w-4 h-4 rounded-full"
                              style={{ backgroundColor: annotation.reviewerColor }}
                            />
                            <div className="flex-1">
                              <div className="text-sm text-gray-800">
                                {annotation.reviewerName}
                              </div>
                              <div className="text-xs text-gray-500">
                                第{annotation.pageIndex + 1}页 • {annotation.type}
                                {annotation.content && ` • ${annotation.content.substring(0, 20)}`}
                              </div>
                            </div>
                          </label>
                        ))}
                      </div>
                      <button
                        onClick={handleMerge}
                        disabled={selectedAnnotations.size === 0}
                        className="mt-3 w-full py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50"
                      >
                        合并选中标注 ({selectedAnnotations.size})
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReviewPanel;
