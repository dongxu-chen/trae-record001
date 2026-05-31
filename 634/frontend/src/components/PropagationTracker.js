import React, { useState, useEffect } from 'react';
import {
  Paper, Box, Typography, Chip, Button, CircularProgress,
  List, ListItem, ListItemText, Divider, Avatar,
  Card, CardContent, Grid, LinearProgress
} from '@mui/material';
import {
  Share as ShareIcon,
  Favorite as LikeIcon,
  Comment as CommentIcon,
  Whatshot as IgnitionIcon,
  Star as StarIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { topicApi } from '../services/api';
import { Tree, TreeNode } from 'react-organizational-chart';

function PropagationTracker({ topicId, topicName }) {
  const [propagation, setPropagation] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchPropagation = async () => {
    if (!topicId) return;
    
    try {
      setLoading(true);
      const response = await topicApi.getPropagation(topicId);
      setPropagation(response.data);
    } catch (error) {
      console.error('Failed to fetch propagation data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPropagation();
  }, [topicId]);

  const formatTime = (timeStr) => {
    if (!timeStr) return '未知';
    return new Date(timeStr).toLocaleString('zh-CN');
  };

  const calculateSocialScore = (shares, likes, comments) => {
    return Math.round(shares * 0.5 + likes * 0.3 + comments * 0.2);
  };

  const renderTreeNode = (node) => {
    const socialScore = calculateSocialScore(
      node.share_count, 
      node.like_count, 
      node.comment_count
    );
    
    return (
      <TreeNode
        label={
          <Card 
            sx={{ 
              minWidth: 200, 
              backgroundColor: node.is_ignition ? '#fff3e0' : '#fff',
              border: node.is_ignition ? '2px solid #ff9800' : '1px solid #e0e0e0'
            }}
          >
            <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
              <Typography variant="body2" noWrap sx={{ fontWeight: node.is_ignition ? 'bold' : 'normal' }}>
                {node.is_ignition && <IgnitionIcon sx={{ fontSize: 16, color: '#ff9800', mr: 0.5 }} />}
                {node.title}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                {node.source}
              </Typography>
              <Box display="flex" gap={1} mt={0.5}>
                <Chip 
                  size="small" 
                  icon={<ShareIcon sx={{ fontSize: 14 }} />} 
                  label={node.share_count}
                  sx={{ height: 20, fontSize: 10 }}
                />
                <Chip 
                  size="small" 
                  icon={<LikeIcon sx={{ fontSize: 14 }} />} 
                  label={node.like_count}
                  sx={{ height: 20, fontSize: 10 }}
                />
                <Chip 
                  size="small" 
                  icon={<CommentIcon sx={{ fontSize: 14 }} />} 
                  label={node.comment_count}
                  sx={{ height: 20, fontSize: 10 }}
                />
              </Box>
            </CardContent>
          </Card>
        }
        key={node.article_id}
      >
        {node.children && node.children.map(childId => {
          const childNode = propagation?.propagation_tree?.find(n => n.article_id === childId);
          return childNode ? renderTreeNode(childNode) : null;
        })}
      </TreeNode>
    );
  };

  if (!topicId) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="textSecondary">
          请选择一个话题查看传播路径
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">
          传播路径溯源 - {topicName || topicId.slice(0, 8)}
        </Typography>
        <Button 
          size="small" 
          startIcon={<RefreshIcon />}
          onClick={fetchPropagation}
          disabled={loading}
        >
          刷新
        </Button>
      </Box>

      {loading ? (
        <Box display="flex" justifyContent="center" p={4}>
          <CircularProgress />
        </Box>
      ) : !propagation ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="textSecondary">
            暂无传播数据，请等待更多文章加入话题后再试
          </Typography>
        </Paper>
      ) : (
        <>
          <Grid container spacing={2} mb={3}>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2 }}>
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <IgnitionIcon color="warning" />
                  <Typography variant="subtitle1">引爆点数量</Typography>
                </Box>
                <Typography variant="h3">
                  {propagation.ignition_points?.length || 0}
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2 }}>
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <ShareIcon color="primary" />
                  <Typography variant="subtitle1">传播深度</Typography>
                </Box>
                <Typography variant="h3">
                  {propagation.total_propagation_depth || 0} 层
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2 }}>
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <StarIcon color="secondary" />
                  <Typography variant="subtitle1">关键影响者</Typography>
                </Box>
                <Typography variant="h3">
                  {propagation.key_influencers?.length || 0} 位
                </Typography>
              </Paper>
            </Grid>
          </Grid>

          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              🔥 引爆点文章
            </Typography>
            <List>
              {propagation.ignition_points?.map((point, index) => (
                <React.Fragment key={point.article_id}>
                  <ListItem>
                    <Avatar sx={{ bgcolor: '#ff9800', mr: 2 }}>
                      {index + 1}
                    </Avatar>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body1" fontWeight="bold">
                            {point.title}
                          </Typography>
                          <Chip 
                            size="small" 
                            label={`影响力 ${(point.influence_score * 100).toFixed(0)}%`}
                            color="warning"
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="textSecondary">
                            {point.source} - {formatTime(point.publish_time)}
                          </Typography>
                          <Box display="flex" gap={2} mt={0.5}>
                            <Typography variant="caption" color="textSecondary">
                              <ShareIcon fontSize="small" sx={{ verticalAlign: 'middle' }} /> 
                              {point.share_count} 转发
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              <LikeIcon fontSize="small" sx={{ verticalAlign: 'middle' }} /> 
                              {point.like_count} 点赞
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              <CommentIcon fontSize="small" sx={{ verticalAlign: 'middle' }} /> 
                              {point.comment_count} 评论
                            </Typography>
                          </Box>
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < propagation.ignition_points.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </Paper>

          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              ⭐ 关键影响者
            </Typography>
            <Grid container spacing={2}>
              {propagation.key_influencers?.map((inf, index) => (
                <Grid item xs={12} md={6} key={inf.article_id}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box display="flex" alignItems="center" gap={1} mb={1}>
                        <Chip 
                          size="small" 
                          label={`#${index + 1}`}
                          color={index < 3 ? 'primary' : 'default'}
                        />
                        <Typography variant="body2" noWrap sx={{ flex: 1 }}>
                          {inf.title}
                        </Typography>
                      </Box>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="caption" color="textSecondary">
                          {inf.source}
                        </Typography>
                        <Box>
                          <Typography variant="caption" color="textSecondary">
                            影响力: 
                          </Typography>
                          <Typography variant="subtitle2" color="primary" component="span">
                            {(inf.final_score * 100).toFixed(0)}%
                          </Typography>
                        </Box>
                      </Box>
                      <LinearProgress 
                        variant="determinate" 
                        value={inf.final_score * 100}
                        sx={{ mt: 1 }}
                      />
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>

          {propagation.propagation_tree && propagation.propagation_tree.length > 0 && (
            <Paper sx={{ p: 2, overflow: 'auto' }}>
              <Typography variant="subtitle1" gutterBottom>
                🌳 传播树结构
              </Typography>
              <Box sx={{ minWidth: '800px' }}>
                <Tree
                  lineWidth={'2px'}
                  lineColor={'#bbb'}
                  lineBorderRadius={'10px'}
                  label={
                    <Typography variant="caption" color="textSecondary">
                      传播起点
                    </Typography>
                  }
                >
                  {propagation.propagation_tree
                    .filter(node => node.is_ignition)
                    .map(renderTreeNode)}
                </Tree>
              </Box>
            </Paper>
          )}
        </>
      )}
    </Box>
  );
}

export default PropagationTracker;
