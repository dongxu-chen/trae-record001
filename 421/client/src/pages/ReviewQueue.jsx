import React, { useState, useEffect } from 'react';
import { 
  Container, Typography, Paper, Grid, Card, CardContent, 
  CardActions, Button, Chip, Box, List, ListItem, 
  ListItemText, Divider, Avatar, TextField, Dialog,
  DialogTitle, DialogContent, DialogActions
} from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import useStore from '../store/useStore';

const ReviewQueue = () => {
  const navigate = useNavigate();
  const { documents, revisions, setDocuments, setRevisions } = useStore();
  const [loading, setLoading] = useState(true);
  const [openDocument, setOpenDocument] = useState(null);
  const [reviewComment, setReviewComment] = useState('');
  const [openFinalReview, setOpenFinalReview] = useState(null);

  useEffect(() => {
    loadPendingReviews();
  }, []);

  const loadPendingReviews = async () => {
    try {
      const res = await api.get('/api/reviews/pending');
      setDocuments(res.data.documents);
      setRevisions(res.data.revisions);
      setLoading(false);
    } catch (err) {
      console.error('Load pending reviews error:', err);
      setLoading(false);
    }
  };

  const handleApproveRevision = async (revisionId) => {
    try {
      await api.post(`/api/reviews/${revisionId}/approve`, { comment: reviewComment });
      setReviewComment('');
      loadPendingReviews();
    } catch (err) {
      console.error('Approve error:', err);
    }
  };

  const handleRejectRevision = async (revisionId) => {
    try {
      await api.post(`/api/reviews/${revisionId}/reject`, { comment: reviewComment });
      setReviewComment('');
      loadPendingReviews();
    } catch (err) {
      console.error('Reject error:', err);
    }
  };

  const handleFinalApprove = async (docId) => {
    try {
      await api.post(`/api/reviews/document/${docId}/final-approve`, { comment: reviewComment });
      setOpenFinalReview(null);
      setReviewComment('');
      loadPendingReviews();
    } catch (err) {
      console.error('Final approve error:', err);
    }
  };

  const handleFinalReject = async (docId) => {
    try {
      await api.post(`/api/reviews/document/${docId}/final-reject`, { comment: reviewComment });
      setOpenFinalReview(null);
      setReviewComment('');
      loadPendingReviews();
    } catch (err) {
      console.error('Final reject error:', err);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      draft: 'default',
      in_review: 'warning',
      approved: 'success',
      rejected: 'error',
      pending: 'warning'
    };
    return colors[status] || 'default';
  };

  const renderDiff = (diffString) => {
    try {
      const changes = JSON.parse(diffString);
      return (
        <Box sx={{ fontFamily: 'monospace', fontSize: '12px', lineHeight: 1.6 }}>
          {changes.slice(0, 20).map((part, idx) => (
            <span
              key={idx}
              style={{
                backgroundColor: part.added ? '#e6ffed' : part.removed ? '#ffeef0' : 'transparent',
                color: part.added ? '#22863a' : part.removed ? '#b31d28' : 'inherit'
              }}
            >
              {part.value}
            </span>
          ))}
          {changes.length > 20 && <span>...</span>}
        </Box>
      );
    } catch (e) {
      return <Typography variant="body2">无法显示差异</Typography>;
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        待审核文档
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              文档列表 ({documents.length})
            </Typography>
            <List>
              {documents.length === 0 ? (
                <ListItem>
                  <ListItemText primary="暂无待审核文档" />
                </ListItem>
              ) : (
                documents.map((doc) => (
                  <React.Fragment key={doc.docId}>
                    <ListItem
                      sx={{
                        flexDirection: 'column',
                        alignItems: 'stretch',
                        cursor: 'pointer',
                        '&:hover': { bgcolor: 'grey.50' }
                      }}
                      onClick={() => navigate(`/document/${doc.docId}`)}
                    >
                      <Box display="flex" justifyContent="space-between" alignItems="center" width="100%">
                        <Box>
                          <Typography variant="h6">{doc.title}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            创建者: {doc.author?.username} | 更新于: {new Date(doc.updatedAt).toLocaleString()}
                          </Typography>
                        </Box>
                        <Box display="flex" gap={1} alignItems="center">
                          <Chip 
                            label="审核中" 
                            color="warning"
                            size="small"
                          />
                          <Button
                            size="small"
                            startIcon={<VisibilityIcon />}
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/document/${doc.docId}`);
                            }}
                          >
                            查看
                          </Button>
                          <Button
                            size="small"
                            color="success"
                            onClick={(e) => {
                              e.stopPropagation();
                              setOpenFinalReview(doc);
                            }}
                          >
                            最终审核
                          </Button>
                        </Box>
                      </Box>
                    </ListItem>
                    <Divider />
                  </React.Fragment>
                ))
              )}
            </List>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              待处理修订 ({revisions.length})
            </Typography>
            <List>
              {revisions.length === 0 ? (
                <ListItem>
                  <ListItemText primary="暂无待处理修订" />
                </ListItem>
              ) : (
                revisions.map((revision) => (
                  <React.Fragment key={revision._id}>
                    <ListItem sx={{ flexDirection: 'column', alignItems: 'stretch' }}>
                      <Box mb={2}>
                        <Box display="flex" alignItems="center" gap={1} mb={1}>
                          <Avatar sx={{ width: 24, height: 24, fontSize: 12 }}>
                            {revision.author?.username?.charAt(0).toUpperCase()}
                          </Avatar>
                          <Typography variant="subtitle2">
                            {revision.author?.username}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            版本 {revision.version}
                          </Typography>
                        </Box>
                        {renderDiff(revision.diff)}
                        <Typography variant="caption" color="text.secondary" display="block" mt={1}>
                          {new Date(revision.createdAt).toLocaleString()}
                        </Typography>
                      </Box>
                      <Box display="flex" gap={1}>
                        <Button
                          size="small"
                          variant="contained"
                          color="success"
                          startIcon={<CheckIcon />}
                          onClick={() => handleApproveRevision(revision._id)}
                          fullWidth
                        >
                          通过
                        </Button>
                        <Button
                          size="small"
                          variant="contained"
                          color="error"
                          startIcon={<CloseIcon />}
                          onClick={() => handleRejectRevision(revision._id)}
                          fullWidth
                        >
                          拒绝
                        </Button>
                      </Box>
                    </ListItem>
                    <Divider sx={{ my: 1 }} />
                  </React.Fragment>
                ))
              )}
            </List>
          </Paper>
        </Grid>
      </Grid>

      <Dialog
        open={!!openFinalReview}
        onClose={() => setOpenFinalReview(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>最终审核 - {openFinalReview?.title}</DialogTitle>
        <DialogContent>
          <TextField
            margin="dense"
            label="审核意见"
            fullWidth
            multiline
            rows={3}
            value={reviewComment}
            onChange={(e) => setReviewComment(e.target.value)}
            placeholder="请输入审核意见（可选）"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenFinalReview(null)}>取消</Button>
          <Button 
            color="error" 
            onClick={() => handleFinalReject(openFinalReview?.docId)}
          >
            拒绝文档
          </Button>
          <Button 
            color="success" 
            variant="contained"
            onClick={() => handleFinalApprove(openFinalReview?.docId)}
          >
            通过文档
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ReviewQueue;
