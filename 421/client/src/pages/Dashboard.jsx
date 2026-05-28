import React, { useState, useEffect } from 'react';
import { 
  Container, Typography, Button, Grid, Card, CardContent, 
  CardActions, Box, Chip, IconButton, Dialog, DialogTitle,
  DialogContent, TextField, DialogActions, MenuItem
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import useStore from '../store/useStore';
import { useAuth } from '../context/AuthContext';

const Dashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { documents, setDocuments, addDocument, updateDocument } = useStore();
  const [openDialog, setOpenDialog] = useState(false);
  const [newDoc, setNewDoc] = useState({ title: '', content: '', reviewers: [] });
  const [users, setUsers] = useState([]);

  useEffect(() => {
    loadDocuments();
    loadUsers();
  }, []);

  const loadDocuments = async () => {
    try {
      const res = await api.get('/api/documents');
      setDocuments(res.data);
    } catch (err) {
      console.error('Load documents error:', err);
    }
  };

  const loadUsers = async () => {
    try {
      const res = await api.get('/api/auth/users');
      setUsers(res.data.filter(u => u.role === 'reviewer' || u.role === 'admin'));
    } catch (err) {
      console.error('Load users error:', err);
    }
  };

  const handleCreateDocument = async () => {
    try {
      const res = await api.post('/api/documents', newDoc);
      addDocument(res.data);
      setOpenDialog(false);
      setNewDoc({ title: '', content: '', reviewers: [] });
      navigate(`/document/${res.data.docId}`);
    } catch (err) {
      console.error('Create document error:', err);
    }
  };

  const handleDeleteDocument = async (docId, e) => {
    e.stopPropagation();
    if (window.confirm('确定要删除这个文档吗？')) {
      try {
        await api.delete(`/api/documents/${docId}`);
        setDocuments(documents.filter(d => d.docId !== docId));
      } catch (err) {
        console.error('Delete document error:', err);
      }
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      draft: 'default',
      in_review: 'warning',
      approved: 'success',
      rejected: 'error'
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status) => {
    const texts = {
      draft: '草稿',
      in_review: '审核中',
      approved: '已通过',
      rejected: '已拒绝'
    };
    return texts[status] || status;
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4">我的文档</Typography>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />}
          onClick={() => setOpenDialog(true)}
        >
          新建文档
        </Button>
      </Box>

      <Grid container spacing={3}>
        {documents.map((doc) => (
          <Grid item xs={12} sm={6} md={4} key={doc.docId}>
            <Card 
              sx={{ cursor: 'pointer', '&:hover': { boxShadow: 6 } }}
              onClick={() => navigate(`/document/${doc.docId}`)}
            >
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                  <Typography variant="h6" gutterBottom noWrap>
                    {doc.title}
                  </Typography>
                  <Chip 
                    label={getStatusText(doc.status)} 
                    color={getStatusColor(doc.status)}
                    size="small"
                  />
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ 
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical',
                  minHeight: 60
                }}>
                  {doc.content || '暂无内容'}
                </Typography>
                <Box mt={2}>
                  <Typography variant="caption" color="text.secondary">
                    创建者: {doc.author?.username}
                  </Typography>
                </Box>
                <Box mt={1}>
                  <Typography variant="caption" color="text.secondary">
                    更新于: {new Date(doc.updatedAt).toLocaleString()}
                  </Typography>
                </Box>
              </CardContent>
              <CardActions>
                {doc.author?._id === user?.id && (
                  <IconButton 
                    size="small" 
                    color="error"
                    onClick={(e) => handleDeleteDocument(doc.docId, e)}
                  >
                    <DeleteIcon />
                  </IconButton>
                )}
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
        <DialogTitle>新建文档</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="文档标题"
            fullWidth
            value={newDoc.title}
            onChange={(e) => setNewDoc({ ...newDoc, title: e.target.value })}
          />
          <TextField
            margin="dense"
            label="初始内容"
            fullWidth
            multiline
            rows={4}
            value={newDoc.content}
            onChange={(e) => setNewDoc({ ...newDoc, content: e.target.value })}
          />
          <TextField
            margin="dense"
            select
            label="指定审核人"
            fullWidth
            SelectProps={{ multiple: true }}
            value={newDoc.reviewers}
            onChange={(e) => setNewDoc({ ...newDoc, reviewers: e.target.value })}
          >
            {users.map((u) => (
              <MenuItem key={u._id} value={u._id}>
                {u.username}
              </MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>取消</Button>
          <Button onClick={handleCreateDocument} variant="contained">创建</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Dashboard;
