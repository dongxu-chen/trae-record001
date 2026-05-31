import React, { useState, useEffect } from 'react';
import {
  Paper, Box, Typography, Chip, Button, CircularProgress,
  FormControl, InputLabel, Select, MenuItem, OutlinedInput,
  ListItemText, Checkbox, Grid, Card, CardContent,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  BarChart as BarChartIcon,
  Timeline as TimelineIcon,
  TrendingUp as TrendingUpIcon,
  ShowChart as ShowChartIcon
} from '@mui/icons-material';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  Legend, ResponsiveContainer, AreaChart, Area, BarChart, Bar
} from 'recharts';
import { comparisonApi } from '../services/api';

const lifecycleColors = {
  emerging: '#4caf50',
  growing: '#2196f3',
  bursting: '#f44336',
  declining: '#ff9800',
  stable: '#9e9e9e'
};

const chartColors = ['#1976d2', '#388e3c', '#f57c00', '#7b1fa2', '#d32f2f', '#0288d1'];

function TopicComparison() {
  const [availableTopics, setAvailableTopics] = useState([]);
  const [selectedTopics, setSelectedTopics] = useState([]);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState(null);

  const fetchAvailableTopics = async () => {
    try {
      const response = await comparisonApi.getAvailableTopics();
      setAvailableTopics(response.data.topics || []);
    } catch (error) {
      console.error('Failed to fetch available topics:', error);
    }
  };

  const handleCompare = async () => {
    if (selectedTopics.length < 2) {
      alert('请至少选择2个话题进行对比');
      return;
    }

    try {
      setLoading(true);
      const response = await comparisonApi.compareTopics(selectedTopics, timeRange);
      setComparisonResult(response.data);
    } catch (error) {
      console.error('Failed to compare topics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAvailableTopics();
  }, []);

  const getTopicName = (topicId) => {
    const topic = availableTopics.find(t => t.topic_id === topicId);
    return topic?.name || topicId.slice(0, 8);
  };

  const prepareSizeChartData = () => {
    if (!comparisonResult?.topics) return [];

    const allTimestamps = new Set();
    comparisonResult.topics.forEach(topic => {
      topic.size_history?.forEach(point => {
        allTimestamps.add(new Date(point.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }));
      });
    });

    const timestamps = Array.from(allTimestamps).sort();

    return timestamps.map(time => {
      const dataPoint = { time };
      comparisonResult.topics.forEach((topic, index) => {
        const point = topic.size_history?.find(p => 
          new Date(p.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) === time
        );
        dataPoint[`topic_${index}`] = point?.value || 0;
      });
      return dataPoint;
    });
  };

  const prepareInfluenceChartData = () => {
    if (!comparisonResult?.topics) return [];

    const allTimestamps = new Set();
    comparisonResult.topics.forEach(topic => {
      topic.influence_history?.forEach(point => {
        allTimestamps.add(new Date(point.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }));
      });
    });

    const timestamps = Array.from(allTimestamps).sort();

    return timestamps.map(time => {
      const dataPoint = { time };
      comparisonResult.topics.forEach((topic, index) => {
        const point = topic.influence_history?.find(p => 
          new Date(p.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) === time
        );
        dataPoint[`topic_${index}`] = point?.value ? point.value * 100 : 0;
      });
      return dataPoint;
    });
  };

  const prepareSocialChartData = () => {
    if (!comparisonResult?.topics) return [];

    return comparisonResult.topics.map((topic, index) => {
      const lastSocial = topic.social_history?.[topic.social_history.length - 1];
      return {
        name: getTopicName(topic.topic_id),
        shares: lastSocial?.shares || 0,
        likes: lastSocial?.likes || 0,
        comments: lastSocial?.comments || 0,
        color: chartColors[index % chartColors.length]
      };
    });
  };

  const getRankingData = () => {
    if (!comparisonResult?.metrics) return [];

    const rankings = [];
    
    if (comparisonResult.metrics.peak_size_ranking) {
      rankings.push({
        title: '峰值规模排名',
        icon: <BarChartIcon />,
        items: comparisonResult.metrics.peak_size_ranking.map(([id, size], idx) => ({
          rank: idx + 1,
          name: getTopicName(id),
          value: `${size} 篇`
        }))
      });
    }

    if (comparisonResult.metrics.growth_rate_ranking) {
      rankings.push({
        title: '增长速度排名',
        icon: <TrendingUpIcon />,
        items: comparisonResult.metrics.growth_rate_ranking.map(([id, rate], idx) => ({
          rank: idx + 1,
          name: getTopicName(id),
          value: `${rate.toFixed(2)} 篇/小时`
        }))
      });
    }

    if (comparisonResult.metrics.duration_ranking) {
      rankings.push({
        title: '持续时间排名',
        icon: <TimelineIcon />,
        items: comparisonResult.metrics.duration_ranking.map(([id, duration], idx) => ({
          rank: idx + 1,
          name: getTopicName(id),
          value: `${duration.toFixed(2)} 小时`
        }))
      });
    }

    if (comparisonResult.metrics.social_score_ranking) {
      rankings.push({
        title: '社交热度排名',
        icon: <ShowChartIcon />,
        items: comparisonResult.metrics.social_score_ranking.map(([id, score], idx) => ({
          rank: idx + 1,
          name: getTopicName(id),
          value: score.toFixed(2)
        }))
      });
    }

    return rankings;
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6">话题对比分析</Typography>
        <Button 
          size="small" 
          startIcon={<RefreshIcon />}
          onClick={fetchAvailableTopics}
        >
          刷新话题列表
        </Button>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>选择对比话题（至少2个）</InputLabel>
              <Select
                multiple
                value={selectedTopics}
                onChange={(e) => setSelectedTopics(e.target.value)}
                input={<OutlinedInput label="选择对比话题" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip 
                        key={value} 
                        label={getTopicName(value)} 
                        size="small" 
                      />
                    ))}
                  </Box>
                )}
              >
                {availableTopics.map((topic) => (
                  <MenuItem key={topic.topic_id} value={topic.topic_id}>
                    <Checkbox checked={selectedTopics.indexOf(topic.topic_id) > -1} />
                    <ListItemText 
                      primary={topic.name} 
                      secondary={`${topic.size}篇 - ${topic.lifecycle}`} 
                    />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>时间范围</InputLabel>
              <Select
                value={timeRange || ''}
                onChange={(e) => setTimeRange(e.target.value || null)}
                label="时间范围"
              >
                <MenuItem value="">全部历史</MenuItem>
                <MenuItem value={1}>最近1小时</MenuItem>
                <MenuItem value={6}>最近6小时</MenuItem>
                <MenuItem value={24}>最近24小时</MenuItem>
                <MenuItem value={72}>最近3天</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={2}>
            <Button
              fullWidth
              variant="contained"
              onClick={handleCompare}
              disabled={selectedTopics.length < 2 || loading}
            >
              {loading ? <CircularProgress size={20} /> : '开始对比'}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {!comparisonResult ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="textSecondary">
            请选择至少2个话题开始对比分析
          </Typography>
        </Paper>
      ) : (
        <>
          <Grid container spacing={2} mb={3}>
            {comparisonResult.topics.map((topic, index) => (
              <Grid item xs={12} md={6} lg={4} key={topic.topic_id}>
                <Card variant="outlined" sx={{ borderLeft: `4px solid ${chartColors[index % chartColors.length]}` }}>
                  <CardContent>
                    <Box display="flex" alignItems="center" gap={1} mb={1}>
                      <Box 
                        sx={{ 
                          width: 12, 
                          height: 12, 
                          borderRadius: '50%', 
                          backgroundColor: chartColors[index % chartColors.length] 
                        }} 
                      />
                      <Typography variant="subtitle1" fontWeight="bold">
                        {getTopicName(topic.topic_id)}
                      </Typography>
                    </Box>
                    <Grid container spacing={1}>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="textSecondary">峰值规模</Typography>
                        <Typography variant="h6">{topic.peak_size} 篇</Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="textSecondary">持续时间</Typography>
                        <Typography variant="h6">{topic.total_duration_hours.toFixed(1)}h</Typography>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          <Grid container spacing={2} mb={3}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  📈 规模增长趋势对比
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={prepareSizeChartData()}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    {comparisonResult.topics.map((topic, index) => (
                      <Line
                        key={topic.topic_id}
                        type="monotone"
                        dataKey={`topic_${index}`}
                        name={getTopicName(topic.topic_id)}
                        stroke={chartColors[index % chartColors.length]}
                        strokeWidth={2}
                        dot={{ r: 4 }}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  💪 影响力变化对比
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={prepareInfluenceChartData()}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis label={{ value: '%', angle: -90, position: 'insideLeft' }} />
                    <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
                    <Legend />
                    {comparisonResult.topics.map((topic, index) => (
                      <Area
                        key={topic.topic_id}
                        type="monotone"
                        dataKey={`topic_${index}`}
                        name={getTopicName(topic.topic_id)}
                        stroke={chartColors[index % chartColors.length]}
                        fill={chartColors[index % chartColors.length]}
                        fillOpacity={0.2}
                      />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
          </Grid>

          <Grid container spacing={2} mb={3}>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  🔄 生命周期对比
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>话题</TableCell>
                        <TableCell>生命周期事件</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {comparisonResult.topics.map((topic, index) => (
                        <TableRow key={topic.topic_id}>
                          <TableCell>
                            <Box display="flex" alignItems="center" gap={1}>
                              <Box 
                                sx={{ 
                                  width: 8, 
                                  height: 8, 
                                  borderRadius: '50%', 
                                  backgroundColor: chartColors[index % chartColors.length] 
                                }} 
                              />
                              {getTopicName(topic.topic_id)}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Box display="flex" gap={0.5} flexWrap="wrap">
                              {topic.lifecycle_timeline?.map((event, i) => (
                                <Chip
                                  key={i}
                                  size="small"
                                  label={event.lifecycle}
                                  sx={{ 
                                    backgroundColor: lifecycleColors[event.lifecycle] || '#e0e0e0',
                                    color: 'white',
                                    fontSize: 10
                                  }}
                                />
                              ))}
                            </Box>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  💬 社交指标对比
                </Typography>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={prepareSocialChartData()}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="shares" name="转发" fill="#1976d2" />
                    <Bar dataKey="likes" name="点赞" fill="#388e3c" />
                    <Bar dataKey="comments" name="评论" fill="#f57c00" />
                  </BarChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  🏆 综合排名
                </Typography>
                <Box>
                  {getRankingData().map((ranking, idx) => (
                    <Box key={idx} mb={2}>
                      <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                        {ranking.icon}
                        <Typography variant="body2" fontWeight="bold">
                          {ranking.title}
                        </Typography>
                      </Box>
                      {ranking.items.slice(0, 3).map((item) => (
                        <Box 
                          key={item.name} 
                          display="flex" 
                          justifyContent="space-between"
                          sx={{ py: 0.3 }}
                        >
                          <Typography variant="caption">
                            #{item.rank} {item.name}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {item.value}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  ))}
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  );
}

export default TopicComparison;
