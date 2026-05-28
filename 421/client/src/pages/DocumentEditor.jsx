import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Container, Paper, Typography, Box, Chip, Button, Grid,
  IconButton, Divider, List, ListItem, ListItemText,
  Avatar, TextField, Dialog, DialogTitle, DialogContent,
  DialogActions, MenuItem, CircularProgress, Snackbar, Alert,
  Tooltip, Drawer
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import SaveIcon from '@mui/icons-material/Save';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import api from '../services/api';
import socketService from '../services/socket';
import useStore from '../store/useStore';
import { useAuth } from '../context/AuthContext';
import FormatToolbar from '../components/FormatToolbar';
import SideBySideDiff from '../components/SideBySideDiff';
import AISuggestionPanel from '../components/AISuggestionPanel';

const DocumentEditor = () => {
  const { docId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { 
    currentDocument, setCurrentDocument, 
    revisions, setRevisions, 
    comments, setComments, addComment, updateComment,
    activeUsers, setActiveUsers, cursors, setCursor, clearCursors,
    updateDocument
  } = useStore();
  
  const [content, setContent] = useState('');
  const [richContent, setRichContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [viewMode, setViewMode] = useState('edit');
  const [openRevisions, setOpenRevisions] = useState(false);
  const [openComments, setOpenComments] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [selectedText, setSelectedText] = useState('');
  const [users, setUsers] = useState([]);
  const [version, setVersion] = useState(0);
  const [notification, setNotification] = useState({ open: false, message: '', type: 'info' });
  const [selectionStart, setSelectionStart] = useState({ start: 0, end: 0 });
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState([]);
  const [aiSummary, setAiSummary] = useState(null);
  const [aiAnalyzing, setAiAnalyzing] = useState(false);
  const editorRef = useRef(null);
  const contentBeforeRef = useRef('');
  const richContentBeforeRef = useRef(null);
  const socketListenersRef = useRef(false);

  useEffect(() => {
    loadDocument();
    loadUsers();
    
    return () => {
      socketService.leaveDocument(docId);
      clearCursors();
    };
  }, [docId]);

  useEffect(() => {
    if (currentDocument && !socketListenersRef.current) {
      socketListenersRef.current = true;
      setupSocketListeners();
    }
  }, [currentDocument]);

  const showNotification = (message, type = 'info') => {
    setNotification({ open: true, message, type });
  };

  const loadDocument = async () => {
    try {
      const res = await api.get(`/api/documents/${docId}`);
      setCurrentDocument(res.data);
      setContent(res.data.content);
      setRichContent(res.data.richContent || parseToRichContent(res.data.content));
      contentBeforeRef.current = res.data.content;
      richContentBeforeRef.current = res.data.richContent || parseToRichContent(res.data.content);
      setVersion(res.data.version);
      
      socketService.connect();
      socketService.emit('register-user', { userId: user.id });
      socketService.joinDocument(docId, user.id, user.username);
      
      await loadRevisions();
      await loadComments();
      setLoading(false);
    } catch (err) {
      console.error('Load document error:', err);
      setLoading(false);
    }
  };

  const parseToRichContent = (text) => {
    return {
      type: 'doc',
      content: text.split('\n').map(line => ({
        type: 'paragraph',
        content: [{
          type: 'text',
          text: line,
          marks: []
        }]
      }))
    };
  };

  const loadUsers = async () => {
    try {
      const res = await api.get('/api/auth/users');
      setUsers(res.data.filter(u => u.role === 'reviewer' || u.role === 'admin'));
    } catch (err) {
      console.error('Load users error:', err);
    }
  };

  const setupSocketListeners = useCallback(() => {
    socketService.on('document-sync', (data) => {
      setContent(data.content);
      if (data.richContent) {
        setRichContent(data.richContent);
      }
      setVersion(data.version);
    });

    socketService.on('operation', (data) => {
      if (data.userId !== user.id) {
        const newContent = applyRemoteOp(content, data.op);
        setContent(newContent);
        if (data.richContent) {
          setRichContent(data.richContent);
        }
        setVersion(data.version);
      }
    });

    socketService.on('format-operation', (data) => {
      if (data.userId !== user.id) {
        if (data.richContent) {
          setRichContent(data.richContent);
          contentBeforeRef.current = richContentToText(data.richContent);
          setContent(richContentToText(data.richContent));
        }
        setVersion(data.version);
      }
    });

    socketService.on('table-operation', (data) => {
      if (data.userId !== user.id) {
        const newContent = applyRemoteOp(content, data.op);
        setContent(newContent);
        setVersion(data.version);
      }
    });

    socketService.on('active-users', (users) => {
      setActiveUsers(users);
    });

    socketService.on('cursor-update', (data) => {
      if (data.socketId !== socketService.socket?.id) {
        setCursor(data.socketId, data);
      }
    });

    socketService.on('revision-created', (revision) => {
      setRevisions(prev => [revision, ...prev]);
      showNotification('有新的修订已提交', 'info');
    });

    socketService.on('workflow-update', (data) => {
      const messages = {
        document_submitted: '文档已提交审核',
        revision_approved: '修订已通过',
        revision_rejected: '修订被拒绝',
        document_approved: '文档已审核通过',
        document_rejected: '文档审核未通过'
      };
      if (messages[data.action]) {
        showNotification(messages[data.action], data.action.includes('approved') ? 'success' : 
          data.action.includes('rejected') ? 'error' : 'info');
      }
      if (data.action === 'document_approved' || data.action === 'document_rejected') {
        updateDocument(docId, { 
          status: data.action === 'document_approved' ? 'approved' : 'rejected' });
      }
    });

    socketService.on('notification', (notification) => {
      showNotification(notification.message, 'info');
    });
  }, [content, user.id, docId, updateDocument]);

  const richContentToText = (richContent) => {
    if (!richContent || !richContent.content) return '';
    return richContent.content
      .map(block => block.content.map(t => t.text).join(''))
      .join('\n');
  };

  const applyRemoteOp = (currentContent, op) => {
    try {
      if (op.op && op.op[0]) {
        const operation = op.op[0];
        if (operation.si !== undefined) {
          const pos = operation.p[1];
          return currentContent.slice(0, pos) + operation.si + currentContent.slice(pos);
        } else if (operation.sd !== undefined) {
          const pos = operation.p[1];
          const length = operation.sd.length;
          return currentContent.slice(0, pos) + currentContent.slice(pos + length);
        }
      }
    } catch (e) {
      console.error('Apply op error:', e);
    }
    return currentContent;
  };

  const handleContentChange = (e) => {
    const newContent = e.target.value;
    setContent(newContent);
    
    const oldContent = contentBeforeRef.current;
    const op = createOperation(oldContent, newContent, version);
    
    if (op) {
      socketService.sendOperation(docId, op, user.id);
      setVersion(version + 1);
    }
    
    contentBeforeRef.current = newContent;
  };

  const createOperation = (oldText, newText, currentVersion) => {
    let start = 0;
    const minLen = Math.min(oldText.length, newText.length);
    
    while (start < minLen && oldText[start] === newText[start]) {
      start++;
    }
    
    let oldEnd = oldText.length;
    let newEnd = newText.length;
    
    while (oldEnd > start && newEnd > start && oldText[oldEnd - 1] === newText[newEnd - 1]) {
      oldEnd--;
      newEnd--;
    }
    
    const deleted = oldText.slice(start, oldEnd);
    const inserted = newText.slice(start, newEnd);
    
    const ops = [];
    if (deleted) {
      ops.push({ p: ['', start], sd: deleted });
    }
    if (inserted) {
      ops.push({ p: ['', start], si: inserted });
    }
    
    return ops.length > 0 ? { v: currentVersion, op: ops } : null;
  };

  const handleFormat = (formatType, value = null) => {
    if (!richContent) return;

    const start = Math.min(selectionStart.start, selectionStart.end);
    const end = Math.max(selectionStart.start, selectionStart.end);
    
    if (start === end) {
      showNotification('请先选择要格式化的文本', 'warning');
      return;
    }

    const newRichContent = JSON.parse(JSON.stringify(richContent));
    
    let charCount = 0;
    for (let blockIdx = 0; blockIdx < newRichContent.content.length; blockIdx++) {
      const block = newRichContent.content[blockIdx];
      for (let textIdx = 0; textIdx < block.content.length; textIdx++) {
        const textNode = block.content[textIdx];
        const nodeStart = charCount;
        const nodeEnd = charCount + textNode.text.length;
        
        if (start >= nodeStart && end <= nodeEnd) {
          if (!textNode.marks) textNode.marks = [];
          
          const existingMark = textNode.marks.find(m => m.type === formatType);
          
          if (value !== null) {
            if (existingMark) {
              existingMark.color = value;
            } else {
              textNode.marks.push({ type: formatType, color: value });
          } else {
            if (existingMark) {
              textNode.marks = textNode.marks.filter(m => m.type !== formatType);
            } else {
              textNode.marks.push({ type: formatType });
            }
          }
          break;
        }
        charCount = nodeEnd;
      }
      charCount += 1;
    }

    setRichContent(newRichContent);
    setContent(richContentToText(newRichContent));
    
    const formatOp = {
      v: version,
      type: 'format-operation',
      blockIndex: 0,
      textIndex: 0,
      start,
      end,
      mark: formatType,
      value: value !== null ? true : !existingMark,
      markData: value ? { color: value } : {}
    };
    
    socketService.emit('format-operation', { docId, op: formatOp, userId: user.id });
    setVersion(version + 1);
    
    richContentBeforeRef.current = newRichContent;
    contentBeforeRef.current = richContentToText(newRichContent);
  };

  const handleTableOperation = (action) => {
    const tables = parseTableStructure(content);
    const cursorPos = editorRef.current?.selectionStart || 0;
    
    const tableAtPos = tables.find(t => cursorPos >= t.startPos && cursorPos <= t.endPos);
    
    if (!tableAtPos && tables.length === 0) {
      showNotification('请将光标放在表格中以进行表格操作', 'warning');
      return;
    }

    let tableOp = {
      v: version,
      type: 'table-operation',
      action: action.replace('-')[1],
      tableIndex: tables.indexOf(tableAtPos || 0),
      position: action.includes('above') || action.includes('left') ? 'before' : 'after'
    };

    if (action.includes('column')) {
      tableOp.columnIndex = tableAtPos ? getCellIndexAtPosition(cursorPos - tableAtPos.startPos, tableAtPos) : 0;
    }

    socketService.emit('table-operation', { docId, op: tableOp, userId: user.id });
    setVersion(version + 1);
  };

  const parseTableStructure = (text) => {
    const tableRegex = /\|(.+)\|/g;
    const tables = [];
    let match;
    
    while ((match = tableRegex.exec(text)) !== null) {
      const rowText = match[1];
      const cells = rowText.split('|').map(c => c.trim());
      
      tables.push({
        startPos: match.index,
        endPos: match.index + match[0].length,
        cells: cells,
        rowIndex: tables.length
      });
    }
    
    return tables;
  };

  const getCellIndexAtPosition = (relativePos, table) => {
    let currentPos = 1;
    for (let i = 0; i < table.cells.length; i++) {
      const cellLength = table.cells[i].length + 1;
      if (relativePos >= currentPos && relativePos < currentPos + cellLength) {
        return i;
      }
      currentPos += cellLength;
    }
    return -1;
  };

  const handleSelectionChange = () => {
    if (editorRef.current) {
      setSelectionStart({
        start: editorRef.current.selectionStart,
        end: editorRef.current.selectionEnd
      });
    }
  };

  const handleSaveRevision = async () => {
    setSaving(true);
    try {
      const Diff = (await import('diff')).default;
      const diff = Diff.diffChars(contentBeforeRef.current, content);
      
      await api.post(`/api/documents/${docId}/submit-review`);
      
      socketService.saveRevision({
        documentId: docId,
        userId: user.id,
        operations: [],
        contentBefore: contentBeforeRef.current,
        contentAfter: content,
        richContentBefore: richContentBeforeRef.current,
        richContentAfter: richContent,
        diff: JSON.stringify(diff)
      });
      
      updateDocument(docId, { status: 'in_review' });
      loadRevisions();
      showNotification('修订已提交审核', 'success');
    } catch (err) {
      console.error('Save revision error:', err);
      showNotification('提交失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  const loadRevisions = async () => {
    try {
      const res = await api.get(`/api/documents/${docId}/revisions`);
      setRevisions(res.data);
    } catch (err) {
      console.error('Load revisions error:', err);
    }
  };

  const loadComments = async () => {
    try {
      const res = await api.get(`/api/comments/document/${docId}`);
      setComments(res.data);
    } catch (err) {
      console.error('Load comments error:', err);
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;
    
    try {
      const res = await api.post('/api/comments', {
        documentId: docId,
        content: newComment,
        selectedText
      });
      addComment(res.data);
      setNewComment('');
      setSelectedText('');
      
      socketService.emit('notify-workflow', {
        docId,
        action: 'new_comment',
        data: { commentId: res.data._id, authorId: user.id }
      });
    } catch (err) {
      console.error('Add comment error:', err);
    }
  };

  const handleResolveComment = async (commentId) => {
    try {
      const res = await api.post(`/api/comments/${commentId}/resolve`);
      updateComment(commentId, res.data);
    } catch (err) {
      console.error('Resolve comment error:', err);
    }
  };

  const handleTextSelect = () => {
    const selection = window.getSelection().toString();
    if (selection) {
      setSelectedText(selection);
    }
  };

  const handleAIAnalyze = async () => {
    setAiAnalyzing(true);
    try {
      const res = await api.post('/api/ai/analyze', {
        documentId: currentDocument?._id,
        content: content,
        options: {
          checkTypos: true,
          checkGrammar: true,
          checkStyle: true,
          checkPunctuation: true,
          checkConsistency: true
        }
      });
      
      setAiSuggestions(res.data.suggestions);
      setAiSummary(res.data.summary);
      setAiPanelOpen(true);
      showNotification(`AI 分析完成，发现 ${res.data.summary.total} 个建议`, 'success');
    } catch (err) {
      console.error('AI analyze error:', err);
      showNotification('AI 分析失败', 'error');
    } finally {
      setAiAnalyzing(false);
    }
  };

  const handleAcceptSuggestion = async (suggestionId) => {
    try {
      await api.post(`/api/ai/${suggestionId}/accept`);
      setAiSuggestions(prev => prev.map(s => 
        s._id === suggestionId ? { ...s, status: 'accepted' } : s
      ));
      loadAISuggestions();
    } catch (err) {
      console.error('Accept suggestion error:', err);
    }
  };

  const handleRejectSuggestion = async (suggestionId) => {
    try {
      await api.post(`/api/ai/${suggestionId}/reject`);
      setAiSuggestions(prev => prev.map(s => 
        s._id === suggestionId ? { ...s, status: 'rejected' } : s
      ));
    } catch (err) {
      console.error('Reject suggestion error:', err);
    }
  };

  const handleIgnoreSuggestion = async (suggestionId) => {
    try {
      await api.post(`/api/ai/${suggestionId}/ignore`);
      setAiSuggestions(prev => prev.map(s => 
        s._id === suggestionId ? { ...s, status: 'ignored' } : s
      ));
    } catch (err) {
      console.error('Ignore suggestion error:', err);
    }
  };

  const handleBatchAccept = async (suggestionIds) => {
    try {
      await api.post('/api/ai/batch-accept', { suggestionIds });
      setAiSuggestions(prev => prev.map(s => 
        suggestionIds.includes(s._id) ? { ...s, status: 'accepted' } : s
      ));
      showNotification(`已接受 ${suggestionIds.length} 个建议`, 'success');
    } catch (err) {
      console.error('Batch accept error:', err);
    }
  };

  const handleBatchIgnore = async (suggestionIds) => {
    try {
      await api.post('/api/ai/batch-ignore', { suggestionIds });
      setAiSuggestions(prev => prev.map(s => 
        suggestionIds.includes(s._id) ? { ...s, status: 'ignored' } : s
      ));
      showNotification(`已忽略 ${suggestionIds.length} 个建议`, 'info');
    } catch (err) {
      console.error('Batch ignore error:', err);
    }
  };

  const loadAISuggestions = async () => {
    try {
      const res = await api.get(`/api/ai/document/${currentDocument?.docId}`);
      setAiSuggestions(res.data.suggestions);
      setAiSummary(res.data.summary);
    } catch (err) {
      console.error('Load AI suggestions error:', err);
    }
  };

  const isReviewer = currentDocument?.reviewers?.some(r => r._id === user.id);
  const isAuthor = currentDocument?.author?._id === user?.id;

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <CircularProgress />
      </Box>
    );
  }

  const renderEditorContent = () => {
    if (viewMode === 'compare') {
      return (
        <SideBySideDiff 
          revisions={revisions}
          currentContent={content}
          currentRichContent={richContent}
        />
      );
    }

    return (
      <Box>
        <FormatToolbar 
          onFormat={handleFormat}
          onTableOperation={handleTableOperation}
          disabled={currentDocument?.status === 'approved'}
        />
        <TextField
          inputRef={editorRef}
          fullWidth
          multiline
          rows={20}
          value={content}
          onChange={handleContentChange}
          onSelect={handleTextSelect}
          onMouseUp={handleSelectionChange}
          onKeyUp={handleSelectionChange}
          placeholder="开始编辑文档..."
          variant="standard"
          disabled={currentDocument?.status === 'approved'}
          InputProps={{
            disableUnderline: true,
            sx: {
              fontFamily: 'monospace',
              fontSize: '16px',
              lineHeight: 1.8,
              p: 2,
              '&.Mui-disabled': {
                backgroundColor: '#f5f5f5'
              }
            }
          }}
        />
      </Box>
    );
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" gutterBottom>
            {currentDocument?.title}
          </Typography>
          <Box display="flex" gap={2} alignItems="center">
            <Chip 
              label={
                currentDocument?.status === 'draft' ? '草稿' :
                currentDocument?.status === 'in_review' ? '审核中' :
                currentDocument?.status === 'approved' ? '已通过' : '已拒绝'
              } 
              color={
                currentDocument?.status === 'draft' ? 'default' :
                currentDocument?.status === 'in_review' ? 'warning' :
                currentDocument?.status === 'approved' ? 'success' : 'error'
              }
            />
            <Typography variant="body2" color="text.secondary">
              版本: {version}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              创建者: {currentDocument?.author?.username}
            </Typography>
          </Box>
        </Box>
        <Box display="flex" gap={2}>
          <Button
            variant={viewMode === 'edit' ? 'contained' : 'outlined'}
            startIcon={<EditIcon />}
            onClick={() => setViewMode('edit')}
          >
            编辑
          </Button>
          <Button
            variant={viewMode === 'compare' ? 'contained' : 'outlined'}
            startIcon={<VisibilityIcon />}
            onClick={() => setViewMode('compare')}
          >
            版本对比
          </Button>
          <Button
            variant="outlined"
            onClick={() => setOpenRevisions(true)}
          >
            修订历史 ({revisions.length})
          </Button>
          <Button
            variant="outlined"
            onClick={() => setOpenComments(true)}
          >
            批注 ({comments.filter(c => !c.resolved).length})
          </Button>
          <Button
            variant={aiPanelOpen ? 'contained' : 'outlined'}
            color="secondary"
            startIcon={<AutoAwesomeIcon />}
            onClick={handleAIAnalyze}
            disabled={aiAnalyzing}
          >
            {aiAnalyzing ? '分析中...' : `AI 审阅 ${aiSummary?.total ? `(${aiSummary.total})` : ''}`}
          </Button>
          {isAuthor && currentDocument?.status === 'draft' && (
            <Button
              variant="contained"
              color="primary"
              startIcon={<SaveIcon />}
              onClick={handleSaveRevision}
              disabled={saving}
            >
              {saving ? '提交中...' : '提交审核'}
            </Button>
          )}
        </Box>
      </Box>

      {activeUsers.length > 1 && (
        <Box mb={2} display="flex" gap={1} alignItems="center">
          <Typography variant="body2" color="text.secondary">
            在线用户:
          </Typography>
          {activeUsers.map((u, idx) => (
            <Chip 
              key={idx} 
              label={u.username} 
              size="small"
              avatar={<Avatar sx={{ width: 24, height: 24, fontSize: 12 }}>
                {u.username?.charAt(0).toUpperCase()}
              </Avatar>}
            />
          ))}
        </Box>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 0, overflow: 'hidden' }}>
            {renderEditorContent()}
          </Paper>
        </Grid>
      </Grid>

      <Dialog 
        open={openRevisions} 
        onClose={() => setOpenRevisions(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>修订历史</DialogTitle>
        <DialogContent dividers>
          <List>
            {revisions.length === 0 ? (
            <ListItem>
              <ListItemText primary="暂无修订记录" />
            </ListItem>
          ) : (
              revisions.map((revision) => (
                <RevisionItem 
                  key={revision._id} 
                revision={revision} 
                  isReviewer={isReviewer}
                  onLoad={loadRevisions}
                />
              ))
            )}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenRevisions(false)}>关闭</Button>
        </DialogActions>
      </Dialog>

      <Dialog 
        open={openComments} 
        onClose={() => setOpenComments(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>批注讨论</DialogTitle>
        <DialogContent dividers>
          {selectedText && (
            <Box mb={2} p={2} bgcolor="grey.100" borderRadius={1}>
              <Typography variant="body2" color="text.secondary">选中文本:</Typography>
              <Typography variant="body2">{selectedText}</Typography>
            </Box>
          )}
          <Box display="flex" gap={1} mb={2}>
            <TextField
              fullWidth
              placeholder="添加批注..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              size="small"
            />
            <Button 
              variant="contained" 
              onClick={handleAddComment}
              disabled={!newComment.trim()}
            >
              发送
            </Button>
          </Box>
          <Divider />
          <List>
            {comments.length === 0 ? (
              <ListItem>
                <ListItemText primary="暂无批注" />
              </ListItem>
            ) : (
                comments.map((comment) => (
                  <CommentItem 
                    key={comment._id} 
                    comment={comment}
                    onResolve={handleResolveComment}
                  />
                ))
              )}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenComments(false)}>关闭</Button>
        </DialogActions>
      </Dialog>

      <Drawer
        anchor="right"
        open={aiPanelOpen}
        onClose={() => setAiPanelOpen(false)}
        PaperProps={{ sx: { width: 450, maxWidth: '90vw' } }}
      >
        <Box sx={{ p: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">AI 智能审阅</Typography>
            <Button onClick={() => setAiPanelOpen(false)}>关闭</Button>
          </Box>
          <AISuggestionPanel
            suggestions={aiSuggestions}
            summary={aiSummary}
            onAccept={handleAcceptSuggestion}
            onReject={handleRejectSuggestion}
            onIgnore={handleIgnoreSuggestion}
            onBatchAccept={handleBatchAccept}
            onBatchIgnore={handleBatchIgnore}
          />
        </Box>
      </Drawer>

      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={() => setNotification({ ...notification, open: false })}
      >
        <Alert 
          onClose={() => setNotification({ ...notification, open: false })} 
          severity={notification.type}
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

const RevisionItem = ({ revision, isReviewer, onLoad }) => {
  const [diffView, setDiffView] = useState(false);

  const handleApprove = async () => {
    try {
      await api.post(`/api/reviews/${revision._id}/approve`);
      onLoad();
    } catch (err) {
      console.error('Approve error:', err);
    }
  };

  const handleReject = async () => {
    try {
      await api.post(`/api/reviews/${revision._id}/reject`);
      onLoad();
    } catch (err) {
      console.error('Reject error:', err);
    }
  };

  const renderDiff = () => {
    try {
      const changes = JSON.parse(revision.richDiff || revision.diff);
      return (
        <Box sx={{ fontFamily: 'monospace', fontSize: '14px', lineHeight: 1.6 }}>
          {changes.map((part, idx) => (
            <span
              key={idx}
              style={{
                backgroundColor: part.added ? '#e6ffed' : part.removed ? '#ffeef0' : 'transparent',
                color: part.added ? '#22863a' : part.removed ? '#b31d28' : 'inherit',
                textDecoration: part.removed ? 'line-through' : 'none'
              }}
            >
              {part.value}
            </span>
          ))}
        </Box>
      );
    } catch (e) {
      return <Typography variant="body2">无法显示差异</Typography>;
    }
  };

  return (
    <React.Fragment>
      <ListItem 
        sx={{ flexDirection: 'column', alignItems: 'stretch' }}
        divider
      >
        <Box display="flex" justifyContent="space-between" alignItems="center" width="100%">
          <ListItemText
            primary={`版本 ${revision.version}`}
            secondary={
              <>
                <Typography component="span" variant="body2">
                  提交者: {revision.author?.username}
                </Typography>
                <Typography component="span" variant="body2" sx={{ ml: 2 }}>
                  {new Date(revision.createdAt).toLocaleString()}
                </Typography>
              </>
            }
          />
          <Box>
            <Chip 
              label={
                revision.status === 'pending' ? '待审核' :
                revision.status === 'approved' ? '已通过' :
                revision.status === 'rejected' ? '已拒绝' : '已应用'
              }
              color={
                revision.status === 'pending' ? 'warning' :
                revision.status === 'approved' ? 'success' :
                revision.status === 'rejected' ? 'error' : 'default'
              }
              size="small"
              sx={{ mr: 1 }}
            />
            <Button size="small" onClick={() => setDiffView(!diffView)}>
              {diffView ? '收起' : '查看差异'}
            </Button>
            {isReviewer && revision.status === 'pending' && (
              <>
                <Button size="small" color="success" onClick={handleApprove}>
                  通过
                </Button>
                <Button size="small" color="error" onClick={handleReject}>
                  拒绝
                </Button>
              </>
            )}
          </Box>
        </Box>
        {diffView && (
          <Box mt={2} p={2} bgcolor="grey.50" borderRadius={1}>
            {renderDiff()}
            {revision.reviewComment && (
              <Box mt={2} pt={2} borderTop="1px solid #ddd">
                <Typography variant="body2" color="text.secondary">
                  审核意见: {revision.reviewComment}
                </Typography>
              </Box>
            )}
          </Box>
        )}
      </ListItem>
    </React.Fragment>
  );
};

const CommentItem = ({ comment, onResolve }) => {
  const [reply, setReply] = useState('');
  const [showReply, setShowReply] = useState(false);

  const handleReply = async () => {
    if (!reply.trim()) return;
    try {
      await api.post(`/api/comments/${comment._id}/reply`, { content: reply });
      setReply('');
      setShowReply(false);
    } catch (err) {
      console.error('Reply error:', err);
    }
  };

  return (
    <ListItem 
      sx={{ 
        flexDirection: 'column', 
        alignItems: 'stretch',
        bgcolor: comment.resolved ? 'grey.50' : 'transparent',
        opacity: comment.resolved ? 0.7 : 1
      }}
      divider
    >
      <Box width="100%">
        <Box display="flex" justifyContent="space-between" alignItems="flex-start">
          <Box display="flex" gap={1} alignItems="center">
            <Avatar sx={{ width: 32, height: 32, fontSize: 14 }}>
              {comment.author?.username?.charAt(0).toUpperCase()}
            </Avatar>
            <Box>
              <Typography variant="subtitle2">
                {comment.author?.username}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {new Date(comment.createdAt).toLocaleString()}
              </Typography>
            </Box>
          </Box>
          {!comment.resolved && (
            <Button 
              size="small" 
              onClick={() => onResolve(comment._id)}
            >
              标记已解决
            </Button>
          )}
          {comment.resolved && (
            <Chip label="已解决" size="small" color="success" />
          )}
        </Box>
        {comment.selectedText && (
          <Box mt={1} p={1} bgcolor="yellow.50" borderRadius={1}>
            <Typography variant="body2" color="text.secondary">
              "{comment.selectedText}"
            </Typography>
          </Box>
        )}
        <Typography variant="body1" sx={{ mt: 1 }}>
          {comment.content}
        </Typography>
        
        {comment.replies && comment.replies.length > 0 && (
          <Box mt={2} ml={4}>
            {comment.replies.map((r, idx) => (
              <Box key={idx} mb={1}>
                <Box display="flex" gap={1} alignItems="center">
                  <Avatar sx={{ width: 24, height: 24, fontSize: 12 }}>
                    {r.author?.username?.charAt(0).toUpperCase()}
                  </Avatar>
                  <Typography variant="caption">
                    {r.author?.username} - {new Date(r.createdAt).toLocaleString()}
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ ml: 4, mt: 0.5 }}>
                  {r.content}
                </Typography>
              </Box>
            ))}
          </Box>
        )}
        
        <Box mt={1}>
          {!showReply ? (
            <Button size="small" onClick={() => setShowReply(true)}>
              回复
            </Button>
          ) : (
            <Box display="flex" gap={1}>
              <TextField
                size="small"
                fullWidth
                placeholder="回复..."
                value={reply}
                onChange={(e) => setReply(e.target.value)}
              />
              <Button size="small" onClick={handleReply}>发送</Button>
              <Button size="small" onClick={() => setShowReply(false)}>取消</Button>
            </Box>
          )}
        </Box>
      </Box>
    </ListItem>
  );
};

export default DocumentEditor;
