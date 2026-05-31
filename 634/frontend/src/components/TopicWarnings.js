import React, { useState, useEffect } from 'react';
import {
  Paper, Box, Typography, List, ListItem, ListItemText, 
  ListItemSecondaryAction, IconButton, Chip, Button,
  Alert, AlertTitle, LinearProgress, Divider, Badge,
  Tooltip, Accordion, AccordionSummary, AccordionDetails
} from '@mui/material';
import {
  Warning as WarningIcon,
  Check as CheckIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  Timeline as TimelineIcon,
  TrendingUp as TrendingUpIcon
} from '@mui/icons-material';
import { warningApi } from '../services/api';
import { wsService } from '../services/websocketService';

const warningLevelConfig = {
  critical: { color: '#d32f2f', bgColor: '#ffebee', label: '严重', icon: '🔴' },
  high: { color: '#f57c00', bgColor: '#fff3e0', label: '高', icon: '🟠' },
  medium: { color: '#fbc02d', bgColor: '#fffde7', label: '中', icon: '🟡' },
  low: { color: '#388e3c', bgColor: '#e8f5e9', label: '低', icon: '🟢' }
};

function TopicWarnings({ onTopicSelect }) {
  const [warnings, setWarnings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showHistory, setShowHistory] = useState(false);

  const fetchWarnings = async () => {
    try {
      setLoading(true);
      const response = showHistory 
        ? await warningApi.getWarningHistory(20)
        : await warningApi.getActiveWarnings();
      setWarnings(response.data.warnings || []);
    } catch (error) {
      console.error('Failed to fetch warnings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (topicId) => {
    try {
      await warningApi.acknowledgeWarning(topicId);
      fetchWarnings();
    } catch (error) {
      console.error('Failed to acknowledge warning:', error);
    }
  };

  useEffect(() => {
    fetchWarnings();

    const handleNewWarning = () => {
      if (!showHistory) {
        fetchWarnings();
      }
    };

    wsService.addListener('topic_warning', handleNewWarning);
    return () => wsService.removeListener('topic_warning', handleNewWarning);
  }, [showHistory]);

  const formatTime = (timeStr) => {
    if (!timeStr) return '未知';
    return new Date(timeStr).toLocaleString('zh-CN');
  };

  const getUnacknowledgedCount = () => {
    if (showHistory) return 0;
    return warnings.length;
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="h6">话题预警中心</Typography>
          <Badge badgeContent={getUnacknowledgedCount()} color="error">
            <WarningIcon color="action" />
          </Badge>
        </Box>
        <Box display="flex" gap={1}>
          <Button 
            size="small" 
            variant={showHistory ? 'contained' : 'outlined'}
            onClick={() => setShowHistory(!showHistory)}
          >
            {showHistory ? '查看活跃预警' : '查看历史记录'}
          </Button>
          <Button 
            size="small" 
            startIcon={<RefreshIcon />}
            onClick={fetchWarnings}
            disabled={loading}
          >
            刷新
          </Button>
        </Box>
      </Box>

      <Paper sx={{ maxHeight: '600px', overflow: 'auto' }}>
        {loading ? (
          <Box p={3}>
            <LinearProgress />
          </Box>
        ) : warnings.length === 0 ? (
          <Box p={4} textAlign="center">
            <Typography color="textSecondary">
              {showHistory ? '暂无历史预警记录' : '暂无活跃预警，系统运行正常 🎉'}
            </Typography>
          </Box>
        ) : (
          <List>
            {warnings.map((warning, index) => {
              const config = warningLevelConfig[warning.warning_level] || warningLevelConfig.low;
              return (
                <React.Fragment key={warning.warning_id}>
                  <ListItem 
                    sx={{ 
                      backgroundColor: config.bgColor,
                      '&:hover': { backgroundColor: config.bgColor, opacity: 0.9 }
                    }}
                  >
                    <Box mr={2}>
                      <Typography variant="h4">{config.icon}</Typography>
                    </Box>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                          <Typography variant="subtitle1" fontWeight="bold">
                            {warning.topic_name}
                          </Typography>
                          <Chip 
                            size="small" 
                            label={config.label} 
                            sx={{ backgroundColor: config.color, color: 'white' }}
                          />
                          <Chip 
                            size="small" 
                            label={`置信度 ${(warning.confidence * 100).toFixed(0)}%`}
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="textSecondary" paragraph>
                            {warning.message}
                          </Typography>
                          <Box display="flex" gap={2} flexWrap="wrap">
                            <Typography variant="caption" color="textSecondary">
                              <TimelineIcon fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
                              预测爆发: {formatTime(warning.predicted_burst_time)}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              创建时间: {formatTime(warning.created_at)}
                            </Typography>
                          </Box>
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Box display="flex" gap={1}>
                        {!showHistory && (
                          <Tooltip title="标记为已处理">
                            <IconButton 
                              size="small" 
                              onClick={() => handleAcknowledge(warning.topic_id)}
                              color="success"
                            >
                              <CheckIcon />
                            </IconButton>
                          </Tooltip>
                        )}
                        {onTopicSelect && (
                          <Tooltip title="查看话题详情">
                            <IconButton 
                              size="small"
                              onClick={() => onTopicSelect(warning.topic_id)}
                            >
                              <TrendingUpIcon />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    </ListItemSecondaryAction>
                  </ListItem>
                  
                  <Accordion sx={{ margin: 0 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="caption" color="textSecondary">
                        查看详细指标和历史趋势
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      {warning.current_metrics && (
                        <Box mb={2}>
                          <Typography variant="subtitle2" gutterBottom>当前指标</Typography>
                          <Box display="flex" gap={3} flexWrap="wrap">
                            <Box>
                              <Typography variant="caption" color="textSecondary">话题规模</Typography>
                              <Typography variant="h6">{warning.current_metrics.size}</Typography>
                            </Box>
                            <Box>
                              <Typography variant="caption" color="textSecondary">增长速度</Typography>
                              <Typography variant="h6">{warning.current_metrics.velocity?.toFixed(2)}</Typography>
                            </Box>
                            <Box>
                              <Typography variant="caption" color="textSecondary">增长动量</Typography>
                              <Typography variant="h6">{warning.current_metrics.momentum?.toFixed(2)}</Typography>
                            </Box>
                            <Box>
                              <Typography variant="caption" color="textSecondary">社交热度</Typography>
                              <Typography variant="h6">{(warning.current_metrics.share_score * 100).toFixed(0)}%</Typography>
                            </Box>
                          </Box>
                        </Box>
                      )}
                      
                      {warning.historical_trend && warning.historical_trend.length > 0 && (
                        <Box>
                          <Typography variant="subtitle2" gutterBottom>历史趋势</Typography>
                          <Box display="flex" gap={1} flexWrap="wrap">
                            {warning.historical_trend.slice(-5).map((point, i) => (
                              <Chip 
                                key={i}
                                size="small"
                                label={`${point.size}篇`}
                                variant="outlined"
                              />
                            ))}
                          </Box>
                        </Box>
                      )}
                    </AccordionDetails>
                  </Accordion>
                  
                  {index < warnings.length - 1 && <Divider />}
                </React.Fragment>
              );
            })}
          </List>
        )}
      </Paper>
      
      <Box mt={2} p={2} bgcolor="#f5f5f5" borderRadius={1}>
        <Typography variant="caption" color="textSecondary">
          💡 预警说明：系统通过监测话题规模增长率、传播速度、动量变化、社交热度等6项指标，
          在话题进入爆发期前发出预警，帮助您提前把握热点趋势。
        </Typography>
      </Box>
    </Box>
  );
}

export default TopicWarnings;
