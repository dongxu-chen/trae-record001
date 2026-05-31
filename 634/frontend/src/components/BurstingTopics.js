import React, { useState, useEffect } from 'react';
import { 
  Paper, Box, Typography, CircularProgress, Grid, Card,
  CardContent, Chip, Button, LinearProgress
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import { topicApi } from '../services/api';
import { wsService } from '../services/websocketService';

const lifecycleColors = {
  emerging: '#4caf50',
  growing: '#2196f3',
  bursting: '#f44336',
  declining: '#ff9800',
  stable: '#9e9e9e'
};

function BurstingTopics({ onTopicSelect }) {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchBurstingTopics = async () => {
    try {
      setLoading(true);
      const response = await topicApi.getBurstingTopics();
      setTopics(response.data.topics || []);
    } catch (error) {
      console.error('Failed to fetch bursting topics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBurstingTopics();

    const handleTopicUpdate = () => {
      fetchBurstingTopics();
    };

    wsService.addListener('topic_update', handleTopicUpdate);
    return () => wsService.removeListener('topic_update', handleTopicUpdate);
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={1}>
          <TrendingUpIcon color="error" sx={{ fontSize: 30 }} />
          <Typography variant="h6">爆发话题检测</Typography>
          <Chip label={`${topics.length} 个`} color="error" size="small" />
        </Box>
        <Button variant="contained" size="small" onClick={fetchBurstingTopics}>
          刷新
        </Button>
      </Box>

      {topics.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="textSecondary">
            暂无爆发中的话题
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            爆发话题是指增长速度超过阈值的话题
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {topics.map((topic) => (
            <Grid item xs={12} md={6} lg={4} key={topic.topic_id}>
              <Card 
                sx={{ 
                  height: '100%',
                  borderLeft: 4,
                  borderColor: 'error.main',
                  '&:hover': {
                    boxShadow: 6,
                    cursor: 'pointer'
                  }
                }}
                onClick={() => onTopicSelect(topic)}
              >
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                    <Typography variant="h6" component="div" sx={{ fontWeight: 'bold' }}>
                      {topic.name}
                    </Typography>
                    <Chip
                      label="爆发中"
                      size="small"
                      sx={{
                        backgroundColor: lifecycleColors.bursting,
                        color: 'white'
                      }}
                    />
                  </Box>

                  <Box display="flex" flexWrap="wrap" gap={0.5} mb={2}>
                    {topic.keywords?.slice(0, 5).map((kw, i) => (
                      <Chip key={i} label={kw} size="small" variant="outlined" />
                    ))}
                  </Box>

                  <Grid container spacing={2} mb={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="textSecondary">文章数量</Typography>
                      <Typography variant="h5">{topic.size}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="textSecondary">影响力</Typography>
                      <Typography variant="h5">{(topic.influence_score * 100).toFixed(0)}%</Typography>
                    </Grid>
                  </Grid>

                  <Box mb={1}>
                    <Typography variant="body2" color="textSecondary">增长趋势</Typography>
                    <LinearProgress 
                      variant="determinate" 
                      value={Math.min(topic.trend_score * 20, 100)}
                      color="error"
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>

                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="caption" color="textSecondary">
                      趋势分数: {topic.trend_score?.toFixed(2)}
                    </Typography>
                    <Button size="small">查看详情</Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}

export default BurstingTopics;
