import React, { useState, useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { QuillBinding } from 'y-quill';
import Quill from 'quill';
import QuillCursors from 'quill-cursors';
import 'quill/dist/quill.snow.css';
import { v4 as uuidv4 } from 'uuid';
import { openDB } from 'idb';

Quill.register('modules/cursors', QuillCursors);

const SOCKET_SERVER = 'http://localhost:3001';
const YJS_WEBSOCKET = 'ws://localhost:3001/yjs';

let dbPromise = null;
if (typeof window !== 'undefined') {
  dbPromise = openDB('yjs-editor', 1, {
    upgrade(db) {
      if (!db.objectStoreNames.contains('docs')) {
        db.createObjectStore('docs');
      }
      if (!db.objectStoreNames.contains('comments')) {
        db.createObjectStore('comments');
      }
      if (!db.objectStoreNames.contains('versions')) {
        db.createObjectStore('versions');
      }
    },
  });
}

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userName, setUserName] = useState('');
  const [docId, setDocId] = useState('demo-doc');
  const [userId] = useState(uuidv4());
  const [activeUsers, setActiveUsers] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [versions, setVersions] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('connected');
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [comments, setComments] = useState([]);
  const [showCommentPanel, setShowCommentPanel] = useState(false);
  const [newCommentText, setNewCommentText] = useState('');
  const [selectedTextRange, setSelectedTextRange] = useState(null);
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareLink, setShareLink] = useState('');
  const [activeSidebarTab, setActiveSidebarTab] = useState('users');
  const [mentionNotifications, setMentionNotifications] = useState([]);
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const [pendingChangesCount, setPendingChangesCount] = useState(0);
  
  const quillRef = useRef(null);
  const socketRef = useRef(null);
  const ydocRef = useRef(null);
  const providerRef = useRef(null);
  const bindingRef = useRef(null);
  const remoteCursorsRef = useRef({});
  const isInitializedRef = useRef(false);

  const addNotification = useCallback((message, type) => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  }, []);

  const saveDocToIDB = useCallback(async (docId, ydoc) => {
    if (!dbPromise) return;
    try {
      const db = await dbPromise;
      const state = Y.encodeStateAsUpdate(ydoc);
      await db.put('docs', state, docId);
    } catch (e) {
      console.error('Error saving to IndexedDB:', e);
    }
  }, []);

  const loadDocFromIDB = useCallback(async (docId, ydoc) => {
    if (!dbPromise) return false;
    try {
      const db = await dbPromise;
      const state = await db.get('docs', docId);
      if (state) {
        Y.applyUpdate(ydoc, state);
        console.log('Loaded document from IndexedDB');
        return true;
      }
    } catch (e) {
      console.error('Error loading from IndexedDB:', e);
    }
    return false;
  }, []);

  const setupSocketListeners = useCallback((socket) => {
    socket.on('connect', () => {
      console.log('Socket connected');
      setConnectionStatus('connected');
      setIsOfflineMode(false);
      if (isReconnecting) {
        setIsReconnecting(false);
        socket.emit('reconnect-document', { docId, userId, userName });
        addNotification('已重新连接！正在同步数据...', 'join');
      }
    });

    socket.on('disconnect', (reason) => {
      console.log('Socket disconnected:', reason);
      setConnectionStatus('disconnected');
      setIsOfflineMode(true);
      addNotification('连接已断开，进入离线编辑模式', 'leave');
    });

    socket.on('reconnect', (attemptNumber) => {
      console.log('Reconnected after', attemptNumber, 'attempts');
      setIsReconnecting(true);
    });

    socket.on('reconnect_attempt', (attemptNumber) => {
      console.log('Reconnect attempt:', attemptNumber);
      setConnectionStatus('reconnecting');
    });

    socket.on('reconnect_failed', () => {
      console.log('Reconnect failed');
      setConnectionStatus('failed');
      addNotification('重连失败，继续离线编辑', 'leave');
    });

    socket.on('active-users', (users) => {
      setActiveUsers(users);
    });

    socket.on('user-joined', ({ user }) => {
      addNotification(`${user.name} 加入了文档`, 'join');
    });

    socket.on('user-left', ({ user }) => {
      addNotification(`${user.name} 离开了文档`, 'leave');
    });

    socket.on('cursor-cleanup', ({ userId: cleanupUserId }) => {
      const cursors = quillRef.current?.getModule('cursors');
      if (cursors && remoteCursorsRef.current[cleanupUserId]) {
        cursors.removeCursor(cleanupUserId);
        delete remoteCursorsRef.current[cleanupUserId];
      }
    });

    socket.on('cursor-moved', ({ userId: remoteUserId, cursor, selection, userName: cursorUserName, color }) => {
      const cursors = quillRef.current?.getModule('cursors');
      if (cursors && remoteUserId !== userId) {
        if (!remoteCursorsRef.current[remoteUserId]) {
          cursors.createCursor(remoteUserId, cursorUserName, color);
          remoteCursorsRef.current[remoteUserId] = true;
        }
        cursors.moveCursor(remoteUserId, cursor);
      }
    });

    socket.on('document-ready', ({ comments: serverComments }) => {
      setComments(serverComments);
    });

    socket.on('comments-list', (commentsList) => {
      setComments(commentsList);
    });

    socket.on('comment-added', (newComment) => {
      setComments(prev => [...prev, newComment]);
      addNotification('收到新评论', 'comment');
    });

    socket.on('comment-resolved', ({ commentId, resolvedBy }) => {
      setComments(prev => prev.map(c => 
        c.id === commentId ? { ...c, resolved: true } : c
      ));
    });

    socket.on('reply-added', ({ commentId, reply }) => {
      setComments(prev => prev.map(c => 
        c.id === commentId ? { ...c, replies: [...c.replies, reply] } : c
      ));
    });

    socket.on('mention-notification', ({ from, text, timestamp }) => {
      const id = Date.now();
      setMentionNotifications(prev => [...prev, { id, from, text, timestamp }]);
      addNotification(`${from} 提到了你`, 'mention');
      setTimeout(() => {
        setMentionNotifications(prev => prev.filter(n => n.id !== id));
      }, 10000);
    });

    socket.on('versions-list', (versionsList) => {
      setVersions(versionsList);
    });

    socket.on('version-saved', (newVersion) => {
      setVersions(prev => {
        const exists = prev.some(v => v.version === newVersion.version);
        if (!exists) {
          return [...prev, newVersion];
        }
        return prev;
      });
      addNotification(`版本 ${newVersion.version} 已保存`, 'join');
    });

    socket.on('notification', ({ message, type }) => {
      addNotification(message, type);
    });

    socket.on('error', ({ message }) => {
      addNotification(`错误: ${message}`, 'leave');
    });
  }, [docId, userId, userName, isReconnecting, addNotification]);

  const handleTextSelection = useCallback(() => {
    const quill = quillRef.current;
    if (!quill) return;
    
    const range = quill.getSelection();
    if (range && range.length > 0) {
      setSelectedTextRange(range);
      const selectedText = quill.getText(range.index, range.length);
      setNewCommentText(`"${selectedText.trim()}" - `);
    }
  }, []);

  const initializeEditor = useCallback(async () => {
    if (isInitializedRef.current) {
      return;
    }
    isInitializedRef.current = true;

    try {
      const socket = io(SOCKET_SERVER, {
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 20000,
        transports: ['websocket', 'polling']
      });
      socketRef.current = socket;

      setupSocketListeners(socket);

      const ydoc = new Y.Doc({ guid: docId });
      ydocRef.current = ydoc;

      const loadedFromIDB = await loadDocFromIDB(docId, ydoc);
      if (loadedFromIDB) {
        addNotification('已加载本地缓存文档', 'join');
      }

      ydoc.on('update', (update, origin) => {
        if (origin !== 'server') {
          saveDocToIDB(docId, ydoc);
          setPendingChangesCount(prev => prev + 1);
        }
      });

      const provider = new WebsocketProvider(
        YJS_WEBSOCKET,
        docId,
        ydoc,
        {
          connect: true,
          maxConns: 3,
          resyncInterval: 5000
        }
      );
      providerRef.current = provider;

      provider.on('status', (event) => {
        console.log('Yjs provider status:', event.status);
        if (event.status === 'connected') {
          setPendingChangesCount(0);
        }
      });

      provider.on('synced', (isSynced) => {
        console.log('Yjs synced:', isSynced);
        if (isSynced) {
          addNotification('文档同步完成', 'join');
          setPendingChangesCount(0);
        }
      });

      provider.on('connection-close', () => {
        console.log('Yjs connection closed');
      });

      const quill = new Quill('#editor', {
        theme: 'snow',
        modules: {
          toolbar: [
            [{ 'header': [1, 2, 3, false] }],
            ['bold', 'italic', 'underline', 'strike'],
            [{ 'color': [] }, { 'background': [] }],
            [{ 'list': 'ordered'}, { 'list': 'bullet' }],
            [{ 'align': [] }],
            ['link', 'image'],
            ['clean']
          ],
          cursors: {
            timeout: 5000
          }
        }
      });
      quillRef.current = quill;

      const ytext = ydoc.getText('quill');
      const binding = new QuillBinding(ytext, quill, provider.awareness);
      bindingRef.current = binding;

      provider.awareness.setLocalStateField('user', {
        name: userName,
        color: getRandomColor()
      });

      provider.awareness.on('update', () => {
        const states = Array.from(provider.awareness.getStates().values());
        const users = states
          .filter(state => state.user)
          .map(state => ({
            name: state.user.name,
            color: state.user.color,
            cursor: state.cursor
          }));
      });

      quill.on('selection-change', (range, oldRange, source) => {
        if (range && source === 'user' && socket.connected) {
          socket.emit('cursor-update', {
            docId,
            userId,
            cursor: range,
            selection: range.length > 0 ? {
              text: quill.getText(range.index, range.length),
              range: range
            } : null
          });
          
          if (range.length > 0) {
            handleTextSelection();
          }
        }
      });

      socket.emit('join-document', { docId, userId, userName });
      socket.emit('get-versions', { docId });

      window.addEventListener('online', () => {
        addNotification('网络已恢复，正在同步...', 'join');
        setIsOfflineMode(false);
        provider.connect();
      });

      window.addEventListener('offline', () => {
        addNotification('网络已断开，进入离线编辑模式', 'leave');
        setIsOfflineMode(true);
        provider.disconnect();
      });

    } catch (error) {
      console.error('Error initializing editor:', error);
      isInitializedRef.current = false;
    }
  }, [docId, userId, userName, setupSocketListeners, handleTextSelection, loadDocFromIDB, saveDocToIDB, addNotification]);

  useEffect(() => {
    if (isLoggedIn) {
      initializeEditor();
    }
    
    return () => {
      if (bindingRef.current) {
        bindingRef.current.destroy();
      }
      if (providerRef.current) {
        providerRef.current.destroy();
      }
      if (ydocRef.current) {
        ydocRef.current.destroy();
      }
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      window.removeEventListener('online', () => {});
      window.removeEventListener('offline', () => {});
      isInitializedRef.current = false;
    };
  }, [isLoggedIn, initializeEditor]);

  const submitComment = () => {
    if (!newCommentText.trim() || !socketRef.current) return;
    
    socketRef.current.emit('add-comment', {
      docId,
      comment: {
        text: newCommentText,
        range: selectedTextRange,
        selectedText: selectedTextRange ? 
          quillRef.current?.getText(selectedTextRange.index, selectedTextRange.length) : null
      }
    });
    
    setNewCommentText('');
    setSelectedTextRange(null);
    setShowCommentPanel(false);
  };

  const resolveComment = (commentId) => {
    if (!socketRef.current) return;
    socketRef.current.emit('resolve-comment', { docId, commentId });
  };

  const submitReply = (commentId, replyText) => {
    if (!replyText.trim() || !socketRef.current) return;
    
    socketRef.current.emit('add-reply', {
      docId,
      commentId,
      reply: { text: replyText }
    });
  };

  const generateShareLink = () => {
    setShareLink(`${window.location.origin}/share/${docId}`);
  };

  const copyShareLink = () => {
    navigator.clipboard.writeText(shareLink);
    addNotification('链接已复制到剪贴板', 'join');
  };

  const saveVersion = async () => {
    if (!ydocRef.current) return;
    
    const snapshot = Y.encodeStateAsUpdate(ydocRef.current);
    const base64Snapshot = btoa(String.fromCharCode(...new Uint8Array(snapshot)));
    
    if (socketRef.current?.connected) {
      socketRef.current.emit('save-version', {
        docId,
        userId,
        snapshot: base64Snapshot
      });
    } else {
      if (dbPromise) {
        const db = await dbPromise;
        const versions = await db.get('versions', docId) || [];
        const newVersion = {
          id: uuidv4(),
          version: versions.length + 1,
          timestamp: new Date().toISOString(),
          snapshot: base64Snapshot,
          savedBy: userId
        };
        versions.push(newVersion);
        await db.put('versions', versions, docId);
        setVersions(versions);
        addNotification(`版本 ${newVersion.version} 已保存到本地`, 'join');
      }
    }
  };

  const loadVersion = async (version) => {
    if (!ydocRef.current || !quillRef.current) return;
    
    try {
      const snapshot = Uint8Array.from(atob(version.snapshot), c => c.charCodeAt(0));
      Y.applyUpdate(ydocRef.current, snapshot);
      addNotification(`已恢复到版本 ${version.version}`, 'join');
    } catch (e) {
      console.error('Error loading version:', e);
    }
  };

  const handleJoin = (e) => {
    e.preventDefault();
    if (userName.trim()) {
      setIsLoggedIn(true);
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="login-screen">
        <div className="login-card">
          <h2>📝 实时协作文档编辑器</h2>
          <p style={{ color: '#666', marginBottom: '1.5rem', textAlign: 'center' }}>
            基于 Yjs CRDT 的多人实时协作编辑器<br/>
            支持离线编辑、自动同步
          </p>
          <form onSubmit={handleJoin}>
            <div className="form-group">
              <label>您的名字</label>
              <input
                type="text"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                placeholder="请输入您的名字"
                required
              />
            </div>
            <div className="form-group">
              <label>文档ID</label>
              <input
                type="text"
                value={docId}
                onChange={(e) => setDocId(e.target.value)}
                placeholder="输入文档ID"
              />
            </div>
            <button type="submit" className="join-btn">
              加入文档
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <h1>📝 实时协作文档编辑器</h1>
          <span className="doc-id-badge">文档: {docId}</span>
          {isOfflineMode && (
            <span className="offline-badge">📴 离线模式</span>
          )}
          {pendingChangesCount > 0 && (
            <span className="pending-badge">
              ⏳ {pendingChangesCount} 待同步
            </span>
          )}
        </div>
        <div className="header-right">
          <div className={`connection-status ${connectionStatus}`}>
            {connectionStatus === 'connected' ? '🟢 已连接' : 
             connectionStatus === 'reconnecting' ? '🟡 重连中...' : 
             connectionStatus === 'failed' ? '🔴 连接失败' : '⚪ 断开'}
          </div>
          <button 
            className="share-btn"
            onClick={() => {
              setShowShareModal(true);
              generateShareLink();
            }}
          >
            🔗 分享
          </button>
          <div className="user-avatar">
            {userName.charAt(0).toUpperCase()}
          </div>
          <span>{userName}</span>
        </div>
      </header>
      
      <div className="main-content">
        <div className="editor-wrapper">
          <div className="editor-toolbar">
            <button 
              className={`toolbar-btn ${showCommentPanel ? 'active' : ''}`}
              onClick={() => setShowCommentPanel(!showCommentPanel)}
            >
              💬 添加评论
            </button>
            <span className="online-count">
              👥 {activeUsers.filter(u => u.isOnline).length} 人在线
            </span>
          </div>
          
          {showCommentPanel && (
            <div className="comment-input-panel">
              <div className="comment-input-header">
                <span>添加评论</span>
                <button 
                  className="close-btn"
                  onClick={() => setShowCommentPanel(false)}
                >
                  ✕
                </button>
              </div>
              <textarea
                className="comment-textarea"
                value={newCommentText}
                onChange={(e) => setNewCommentText(e.target.value)}
                placeholder="输入评论内容，使用 @用户名 提及其他用户..."
                rows={3}
              />
              <div className="comment-actions">
                <span className="mention-hint">
                  💡 输入 @ 可以提及其他用户
                </span>
                <button 
                  className="submit-comment-btn"
                  onClick={submitComment}
                >
                  提交评论
                </button>
              </div>
            </div>
          )}
          
          <div id="editor" ref={quillRef}></div>
        </div>
        
        <div className="sidebar">
          <div className="sidebar-tabs">
            <button 
              className={`tab-btn ${activeSidebarTab === 'users' ? 'active' : ''}`}
              onClick={() => setActiveSidebarTab('users')}
            >
              👥 用户 ({activeUsers.filter(u => u.isOnline).length})
            </button>
            <button 
              className={`tab-btn ${activeSidebarTab === 'comments' ? 'active' : ''}`}
              onClick={() => setActiveSidebarTab('comments')}
            >
              💬 评论 ({comments.filter(c => !c.resolved).length})
            </button>
            <button 
              className={`tab-btn ${activeSidebarTab === 'versions' ? 'active' : ''}`}
              onClick={() => setActiveSidebarTab('versions')}
            >
              📚 版本 ({versions.length})
            </button>
          </div>

          {activeSidebarTab === 'users' && (
            <div className="panel-content">
              <div className="active-users">
                {activeUsers.map(user => (
                  <div key={user.id} className="user-item">
                    <div className="user-avatar-small" style={{ backgroundColor: user.color }}>
                      {user.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="user-info">
                      <span className="user-name">{user.name}</span>
                      <span className={`user-status ${user.isOnline ? 'online' : 'offline'}`}>
                        {user.isOnline ? '在线' : '离线'}
                      </span>
                    </div>
                    {user.selection && (
                      <span className="user-selection">
                        正在选择文本
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSidebarTab === 'comments' && (
            <div className="panel-content">
              <div className="comments-list">
                {comments.length === 0 ? (
                  <div className="empty-state">
                    <span className="empty-icon">💬</span>
                    <p>暂无评论</p>
                    <p className="empty-hint">在编辑器中选择文本后点击"添加评论"</p>
                  </div>
                ) : (
                  comments.map(comment => (
                    <div 
                      key={comment.id} 
                      className={`comment-card ${comment.resolved ? 'resolved' : ''}`}
                    >
                      <div className="comment-header">
                        <div 
                          className="comment-avatar"
                          style={{ backgroundColor: comment.userColor }}
                        >
                          {comment.userName.charAt(0).toUpperCase()}
                        </div>
                        <div className="comment-meta">
                          <span className="comment-author">{comment.userName}</span>
                          <span className="comment-time">
                            {new Date(comment.timestamp).toLocaleString('zh-CN')}
                          </span>
                        </div>
                        {!comment.resolved && (
                          <button 
                            className="resolve-btn"
                            onClick={() => resolveComment(comment.id)}
                          >
                            ✓ 解决
                          </button>
                        )}
                      </div>
                      <div className="comment-text">{comment.text}</div>
                      {comment.selectedText && (
                        <div className="comment-quote">
                          "{comment.selectedText}"
                        </div>
                      )}
                      
                      {comment.replies && comment.replies.length > 0 && (
                        <div className="replies-list">
                          {comment.replies.map(reply => (
                            <div key={reply.id} className="reply-item">
                              <div 
                                className="reply-avatar"
                                style={{ backgroundColor: reply.userColor }}
                              >
                                {reply.userName.charAt(0).toUpperCase()}
                              </div>
                              <div className="reply-content">
                                <span className="reply-author">{reply.userName}</span>
                                <span className="reply-text">{reply.text}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      
                      <div className="reply-input-container">
                        <input
                          type="text"
                          className="reply-input"
                          placeholder="回复此评论..."
                          onKeyPress={(e) => {
                            if (e.key === 'Enter') {
                              submitReply(comment.id, e.target.value);
                              e.target.value = '';
                            }
                          }}
                        />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {activeSidebarTab === 'versions' && (
            <div className="panel-content">
              <button 
                className="save-version-btn" 
                onClick={saveVersion}
              >
                💾 {isOfflineMode ? '保存版本到本地' : '保存当前版本'}
              </button>
              <div className="versions-list">
                {versions.length === 0 ? (
                  <div className="empty-state">
                    <span className="empty-icon">📚</span>
                    <p>暂无保存的版本</p>
                  </div>
                ) : (
                  versions.slice().reverse().map((version, index) => (
                    <div 
                      key={version.id || index} 
                      className="version-item"
                      onClick={() => loadVersion(version)}
                    >
                      <div className="version-number">版本 {version.version}</div>
                      <div className="version-time">
                        {new Date(version.timestamp).toLocaleString('zh-CN')}
                      </div>
                      <div className="version-restore-hint">
                        点击恢复此版本
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          <div className="panel">
            <h3>📢 通知</h3>
            <div className="notifications">
              {notifications.slice(-5).map(notif => (
                <div key={notif.id} className={`notification ${notif.type}`}>
                  {notif.message}
                </div>
              ))}
              {notifications.length === 0 && (
                <div className="empty-state-small">暂无通知</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {showShareModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>🔗 分享文档</h3>
              <button 
                className="close-btn"
                onClick={() => setShowShareModal(false)}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: '1rem', color: '#666' }}>
                复制链接给其他用户即可开始协作编辑
              </p>
              
              {shareLink && (
                <div className="share-link-container">
                  <input 
                    type="text" 
                    className="share-link-input"
                    value={shareLink}
                    readOnly
                  />
                  <button 
                    className="copy-link-btn"
                    onClick={copyShareLink}
                  >
                    复制
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {mentionNotifications.length > 0 && (
        <div className="mention-notifications">
          {mentionNotifications.map(notif => (
            <div key={notif.id} className="mention-bubble">
              <div className="mention-header">
                <span className="mention-from">@{notif.from}</span>
                <span className="mention-time">
                  {new Date(notif.timestamp).toLocaleTimeString('zh-CN')}
                </span>
              </div>
              <div className="mention-text">{notif.text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function getRandomColor() {
  const colors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
    '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
    '#FF8C42', '#6C5CE7', '#00B894', '#E17055'
  ];
  return colors[Math.floor(Math.random() * colors.length)];
}

export default App;
