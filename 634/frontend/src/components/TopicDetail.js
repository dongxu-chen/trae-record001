import React, { useState, useEffect } from 'react';
import {
  Paper, Box, Typography, Chip, Grid, LinearProgress,
  List, ListItem, ListItemText, Divider, CircularProgress,
  Card, CardContent
} from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { topicApi, evolutionApi } from '../services/api';

const lifecycleColors = {
  emerging: '#4caf50',
  growing: '#2196f3',
  bursting: '#f44336',
  declining: '#ff9800',
  stable: '#9e9e9e'
};

const lifecycleLabels = {
  emerging: '萌芽',
  growing: '成长',
  bursting: '爆发',
  declining: '衰退',
  stable: '稳定'
};

function TopicDetail({ topicId }) {
  const [topic, setTopic] = useState(null);
  const [influence, setInfluence] = useState(null);
  const [articles, setArticles] = useState([]);
  const [evolutionChain, setEvolutionChain] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (topicId) {
      fetchTopicDetail();
    }
  }, [topicId]);

  const fetchTopicDetail = async () => {
    if (!topicId) return;

    try {
      setLoading(true);
      
      const [topicRes, articlesRes, evolutionRes] = await Promise.all([
        topicApi.getTopic(topicId),
        topicApi.getTopicArticles(topicId),
        evolutionApi.getChain(topicId).catch(() => ({ data: { chain: [] } }))
      ]);

      setTopic(topicRes.data.topic);
      setInfluence(topicRes.data.influence);
      setArticles(articlesRes.data.articles || []);
      setEvolutionChain(evolutionRes.data.chain || []);
    } catch (error) {
      console.error('Failed to fetch topic detail:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTrendData = () => {
    if (!topic) return [];
    return [
      { name: '创建', value: 1 },
      { name: '增长', value: Math.floor(topic.size * 0.3) },
      { name: '当前', value: topic.size }
    ];
  };

  const getInfluenceChartData = () => {
    if (!influence) return [];
    return [
      { name: '传播度', value: Math.min(influence.reach, 100) },
      { name: '参与度', value: influence.engagement * 100 },
      { name: '速度', value: Math.min(influence.velocity * 10, 100) },
      { name: '动量', value: influence.momentum * 100 },
      { name: '社交热度', value: influence.share_score * 100 }
    ];
  };

  if (!topicId) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" p={8}>
        <Typography color="textSecondary">请选择一个话题查看详情</Typography>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (!topic) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" p={8}>
        <Typography color="textSecondary">话题不存在或已被删除</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={3}>
          <Box>
            <Typography variant="h4" gutterBottom>
              {topic.name}
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap" mb={2}>
              {topic.keywords?.map((kw, i) => (
                <Chip key={i} label={kw} color="primary" variant="outlined" />
              ))}
            </Box>
          </Box>
          <Chip
            label={lifecycleLabels[topic.lifecycle] || topic.lifecycle}
            size="large"
            sx={{
              backgroundColor: lifecycleColors[topic.lifecycle] || '#e0e0e0',
              color: 'white',
              fontSize: '1rem'
            }}
          />
        </Box>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>话题信息</Typography>
            <List>
              <ListItem>
                <ListItemText 
                  primary="话题ID" 
                  secondary={topic.topic_id}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText 
                  primary="文章数量" 
                  secondary={topic.size}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText 
                  primary="影响力分数" 
                  secondary={`${(topic.influence_score * 100).toFixed(1)}%`}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText 
                  primary="趋势分数" 
                  secondary={topic.trend_score?.toFixed(2)}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText 
                  primary="创建时间" 
                  secondary={topic.created_at}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText 
                  primary="总转发量" 
                  secondary={topic.total_shares || 0}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText 
                  primary="总点赞量" 
                  secondary={topic.total_likes || 0}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText 
                  primary="总评论量" 
                  secondary={topic.total_comments || 0}
                />
              </ListItem>
            </List>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>影响力指标</Typography>
            {influence && (
              <Box>
                <Box mb={2}>
                  <Typography variant="body2" color="textSecondary">综合影响力</Typography>
                  <Typography variant="h5">{(influence.overall_score * 100).toFixed(1)}%</Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={influence.overall_score * 100}
                    sx={{ height: 10, borderRadius: 5 }}
                  />
                </Box>
                <Divider sx={{ my: 2 }} />
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="textSecondary">传播度 (Reach)</Typography>
                    <Typography variant="h6">{influence.reach}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="textSecondary">参与度 (Engagement)</Typography>
                    <Typography variant="h6">{(influence.engagement * 100).toFixed(1)}%</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="textSecondary">速度 (Velocity)</Typography>
                    <Typography variant="h6">{influence.velocity.toFixed(2)}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="textSecondary">动量 (Momentum)</Typography>
                    <Typography variant="h6">{(influence.momentum * 100).toFixed(1)}%</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="textSecondary">社交热度 (Share Score)</Typography>
                    <Typography variant="h6">{(influence.share_score * 100).toFixed(1)}%</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="textSecondary">平均转发/文章</Typography>
                    <Typography variant="h6">{topic.total_shares && topic.size > 0 ? Math.round(topic.total_shares / topic.size) : 0}</Typography>
                  </Grid>
                </Grid>
              </Box>
            )}
          </Grid>
        </Grid>
      </Paper>

      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>话题增长趋势</Typography>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={getTrendData()}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#1976d2" 
                  strokeWidth={2}
                  dot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>影响力构成</Typography>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={getInfluenceChartData()}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#4caf50" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {evolutionChain.length > 0 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>演化路径</Typography>
          <List>
            {evolutionChain.map((item, index) => (
              <React.Fragment key={index}>
                <ListItem>
                  <ListItemText
                    primary={`${item.type.toUpperCase()}: ${item.from_topic.slice(0, 8)} → ${item.to_topic.slice(0, 8)}`}
                    secondary={`相似度: ${(item.similarity * 100).toFixed(1)}% - ${item.timestamp}`}
                  />
                </ListItem>
                {index < evolutionChain.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        </Paper>
      )}

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>相关文章 ({articles.length})</Typography>
        <List>
          {articles.map((article, index) => (
            <React.Fragment key={article.id || index}>
              <ListItem>
                <ListItemText
                  primary={article.title}
                  secondary={`${article.source} - ${article.publish_time}`}
                />
              </ListItem>
              {index < articles.length - 1 && <Divider />}
            </React.Fragment>
          ))}
          {articles.length === 0 && (
            <ListItem>
              <ListItemText primary="暂无相关文章" />
            </ListItem>
          )}
        </List>
      </Paper>
    </Box>
  );
}

export default TopicDetail;
