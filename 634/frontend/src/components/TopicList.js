import React, { useState, useEffect } from 'react';
import { 
  Paper, Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, Chip, Button, TextField,
  InputAdornment, Box, Typography, CircularProgress
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { topicApi } from '../services/api';
import { wsService } from '../services/websocketService';

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

function TopicList({ onTopicSelect }) {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [lifecycleFilter, setLifecycleFilter] = useState('');

  const fetchTopics = async () => {
    try {
      setLoading(true);
      const response = await topicApi.getAllTopics();
      setTopics(response.data.topics || []);
    } catch (error) {
      console.error('Failed to fetch topics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopics();

    const handleTopicUpdate = (data) => {
      setTopics(prev => {
        const existing = prev.findIndex(t => t.topic_id === data.topic_id);
        if (existing >= 0) {
          const updated = [...prev];
          updated[existing] = { ...updated[existing], ...data };
          return updated;
        }
        return [data, ...prev];
      });
    };

    wsService.addListener('topic_update', handleTopicUpdate);
    return () => wsService.removeListener('topic_update', handleTopicUpdate);
  }, []);

  const filteredTopics = topics.filter(topic => {
    const matchesFilter = topic.name?.toLowerCase().includes(filter.toLowerCase()) ||
      topic.keywords?.some(k => k.toLowerCase().includes(filter.toLowerCase()));
    const matchesLifecycle = !lifecycleFilter || topic.lifecycle === lifecycleFilter;
    return matchesFilter && matchesLifecycle;
  });

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" gap={2} mb={3}>
        <TextField
          placeholder="搜索话题..."
          variant="outlined"
          size="small"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ flexGrow: 1 }}
        />
        <TextField
          select
          label="生命周期"
          variant="outlined"
          size="small"
          value={lifecycleFilter}
          onChange={(e) => setLifecycleFilter(e.target.value)}
          SelectProps={{ native: true }}
        >
          <option value="">全部</option>
          {Object.entries(lifecycleLabels).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </TextField>
        <Button variant="contained" onClick={fetchTopics}>刷新</Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>话题名称</TableCell>
              <TableCell>关键词</TableCell>
              <TableCell>文章数</TableCell>
              <TableCell>生命周期</TableCell>
              <TableCell>影响力</TableCell>
              <TableCell>趋势</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredTopics.map((topic) => (
              <TableRow key={topic.topic_id} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight="medium">
                    {topic.name}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Box display="flex" flexWrap="wrap" gap={0.5}>
                    {topic.keywords?.slice(0, 5).map((kw, i) => (
                      <Chip key={i} label={kw} size="small" variant="outlined" />
                    ))}
                  </Box>
                </TableCell>
                <TableCell>{topic.size}</TableCell>
                <TableCell>
                  <Chip
                    label={lifecycleLabels[topic.lifecycle] || topic.lifecycle}
                    size="small"
                    sx={{
                      backgroundColor: lifecycleColors[topic.lifecycle] || '#e0e0e0',
                      color: 'white'
                    }}
                  />
                </TableCell>
                <TableCell>
                  {(topic.influence_score * 100).toFixed(1)}%
                </TableCell>
                <TableCell>
                  {topic.trend_score?.toFixed(2)}
                </TableCell>
                <TableCell>
                  <Button 
                    size="small" 
                    variant="outlined"
                    onClick={() => onTopicSelect(topic)}
                  >
                    详情
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {filteredTopics.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography color="textSecondary" p={3}>
                    暂无话题数据
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

export default TopicList;
