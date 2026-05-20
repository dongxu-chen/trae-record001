import React, { useState, useRef } from 'react';
import { CollaborativeEditor } from './components/CollaborativeEditor';
import { CommentPanel } from './components/CommentPanel';
import { VersionHistory } from './components/VersionHistory';
import { UserList } from './components/UserList';
import { AIAssistant } from './components/AIAssistant';
import { TemplateLibrary } from './components/TemplateLibrary';
import { ExportMenu } from './components/ExportMenu';
import collaborationClient from './utils/collaborationClient';

function App() {
  const [users, setUsers] = useState([]);
  const [comments, setComments] = useState([]);
  const [oplog, setOplog] = useState([]);
  const [activeTab, setActiveTab] = useState('comments');
  const [currentUserId] = useState(() => Math.random().toString(36).substr(2, 9));
  const [showAIAssistant, setShowAIAssistant] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [editorValue, setEditorValue] = useState([]);
  const editorRef = useRef(null);

  const handleUsersChange = (userList) => {
    setUsers(userList);
  };

  const handleCommentAdd = (comment) => {
    setComments(prev => [...prev, comment]);
    collaborationClient.submitComment(comment);
  };

  const handleCommentResolve = (commentId) => {
    setComments(prev =>
      prev.map(c =>
        c.id === commentId ? { ...c, resolved: true } : c
      )
    );
    collaborationClient.resolveComment(commentId);
  };

  const handleOplogUpdate = (oplogEntries) => {
    setOplog(oplogEntries);
  };

  const handleRevert = (version) => {
    if (confirm('确定要恢复到此版本吗？当前的未保存更改将丢失。')) {
      collaborationClient.revertToVersion(version);
    }
  };

  const handleApplyTemplate = (template) => {
    if (editorRef.current && editorRef.current.editor) {
      const editor = editorRef.current.editor;
      if (editor && editor.children) {
        editor.children = template.content;
        editor.onChange();
      }
    }
  };

  const handleEditorValueChange = (value) => {
    setEditorValue(value);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">
          <span className="logo-icon">📝</span>
          <h1>协同富文本编辑器</h1>
        </div>
        <div className="header-actions">
          <button
            className="header-btn"
            onClick={() => setShowTemplates(true)}
          >
            📚 模板库
          </button>
          <button
            className="header-btn"
            onClick={() => setShowAIAssistant(!showAIAssistant)}
          >
            🤖 AI助手
          </button>
          <button
            className="header-btn primary"
            onClick={() => setShowExport(true)}
          >
            📤 导出
          </button>
          <span className="user-badge">
            你: 用户 {currentUserId.slice(0, 6)}
          </span>
        </div>
      </header>

      <div className="main-content">
        <div className="editor-section">
          <CollaborativeEditor
            ref={editorRef}
            onUsersChange={handleUsersChange}
            onCommentAdd={handleCommentAdd}
            onCommentResolve={handleCommentResolve}
            onOplogUpdate={handleOplogUpdate}
            onValueChange={handleEditorValueChange}
          />
          
          {showAIAssistant && (
            <AIAssistant
              editor={editorRef.current?.editor}
              isVisible={showAIAssistant}
              onClose={() => setShowAIAssistant(false)}
            />
          )}
        </div>

        <div className="sidebar">
          <UserList users={users} currentUserId={currentUserId} />

          <div className="sidebar-tabs">
            <button
              className={`tab-btn ${activeTab === 'comments' ? 'active' : ''}`}
              onClick={() => setActiveTab('comments')}
            >
              💬 评论 ({comments.filter(c => !c.resolved).length})
            </button>
            <button
              className={`tab-btn ${activeTab === 'versions' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('versions');
                collaborationClient.getOplog();
              }}
            >
              📜 历史
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'comments' && (
              <CommentPanel
                comments={comments}
                onAddComment={handleCommentAdd}
                onResolveComment={handleCommentResolve}
                currentUser={`用户 ${currentUserId.slice(0, 6)}`}
              />
            )}
            {activeTab === 'versions' && (
              <VersionHistory
                oplog={oplog}
                onRevert={handleRevert}
              />
            )}
          </div>
        </div>
      </div>

      <footer className="app-footer">
        <div className="shortcuts">
          <strong>快捷键:</strong>
          <span>Ctrl/Cmd+B 加粗</span>
          <span>Ctrl/Cmd+I 斜体</span>
          <span>Ctrl/Cmd+U 下划线</span>
          <span>支持 Markdown 快捷输入</span>
        </div>
      </footer>

      <TemplateLibrary
        isVisible={showTemplates}
        onClose={() => setShowTemplates(false)}
        onApplyTemplate={handleApplyTemplate}
      />

      <ExportMenu
        editorValue={editorValue}
        isVisible={showExport}
        onClose={() => setShowExport(false)}
      />
    </div>
  );
}

export default App;
