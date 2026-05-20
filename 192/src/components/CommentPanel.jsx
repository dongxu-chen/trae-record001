import React, { useState } from 'react';
import { format } from 'date-fns';
import { v4 as uuidv4 } from 'uuid';

export const CommentPanel = ({ comments, onAddComment, onResolveComment, currentUser }) => {
  const [newComment, setNewComment] = useState('');
  const [selectedText, setSelectedText] = useState('');

  const handleAddComment = () => {
    if (!newComment.trim()) return;
    
    const comment = {
      id: uuidv4(),
      text: newComment,
      author: currentUser || '匿名用户',
      timestamp: Date.now(),
      selectedText: selectedText || window.getSelection()?.toString() || '',
      resolved: false,
    };
    
    onAddComment && onAddComment(comment);
    setNewComment('');
    setSelectedText('');
  };

  return (
    <div className="comment-panel">
      <div className="comment-header">
        <h3>💬 评论批注</h3>
        <span className="comment-count">{comments.filter(c => !c.resolved).length} 条</span>
      </div>
      
      <div className="comment-input-section">
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="选中文字后添加评论..."
          className="comment-input"
          rows={3}
        />
        <button onClick={handleAddComment} className="comment-submit-btn">
          添加评论
        </button>
      </div>

      <div className="comments-list">
        {comments.length === 0 ? (
          <div className="empty-comments">
            暂无评论，选中文字后可添加批注
          </div>
        ) : (
          comments
            .filter(c => !c.resolved)
            .map(comment => (
              <div key={comment.id} className="comment-item">
                <div className="comment-header-row">
                  <span className="comment-author">{comment.author}</span>
                  <span className="comment-time">
                    {format(comment.timestamp, 'MM-dd HH:mm')}
                  </span>
                </div>
                {comment.selectedText && (
                  <div className="comment-selected-text">
                    "{comment.selectedText}"
                  </div>
                )}
                <div className="comment-text">{comment.text}</div>
                <button
                  onClick={() => onResolveComment && onResolveComment(comment.id)}
                  className="resolve-btn"
                >
                  ✓ 已解决
                </button>
              </div>
            ))
        )}
      </div>

      {comments.filter(c => c.resolved).length > 0 && (
        <div className="resolved-comments-section">
          <details>
            <summary>
              已解决 ({comments.filter(c => c.resolved).length})
            </summary>
            {comments
              .filter(c => c.resolved)
              .map(comment => (
                <div key={comment.id} className="comment-item resolved">
                  <div className="comment-header-row">
                    <span className="comment-author">{comment.author}</span>
                    <span className="comment-time">
                      {format(comment.timestamp, 'MM-dd HH:mm')}
                    </span>
                  </div>
                  <div className="comment-text">{comment.text}</div>
                </div>
              ))}
          </details>
        </div>
      )}
    </div>
  );
};
