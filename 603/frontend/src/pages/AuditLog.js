import React, { useState, useEffect } from 'react';
import {
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Box,
  TextField,
  InputAdornment,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import { getAuditLogs } from '../services/api';

function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [filterAction, setFilterAction] = useState('');
  const [searchText, setSearchText] = useState('');

  const fetchLogs = async () => {
    try {
      const res = await getAuditLogs();
      setLogs(res.data.logs || []);
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 10000);
    return () => clearInterval(interval);
  }, []);

  const getActionColor = (action) => {
    if (action.includes('scale') || action.includes('Scale')) return 'primary';
    if (action.includes('partition') || action.includes('Partition')) return 'secondary';
    if (action.includes('rate') || action.includes('Rate')) return 'warning';
    if (action.includes('strategy') || action.includes('Strategy')) return 'info';
    if (action.includes('alert') || action.includes('Alert')) return 'error';
    if (action.includes('dlq') || action.includes('DLQ')) return 'secondary';
    if (action.includes('replay') || action.includes('Replay')) return 'primary';
    if (action.includes('delay') || action.includes('Delay')) return 'warning';
    return 'default';
  };

  const formatAction = (action) => {
    const actionMap = {
      add_topic: '添加Topic',
      remove_topic: '移除Topic',
      scale_up: '消费者扩容',
      scale_down: '消费者缩容',
      manual_scale: '手动调整消费者',
      partition_up: '分区增加',
      partition_down: '分区减少',
      manual_partition: '手动调整分区',
      rate_limit_adjust: '限流调整',
      manual_rate_limit: '手动设置限流',
      update_strategy: '更新策略',
      delete_strategy: '删除策略',
      prediction_alert: '预测告警',
      dlq_config: '死信配置',
      dlq_send: '入死信队列',
      dlq_retry: '死信重试',
      replay: '消息重放',
      replay_cancel: '取消重放',
      delay_config: '延迟处理配置',
      delay_pause: '暂停订阅',
      delay_resume: '恢复订阅',
    };
    return actionMap[action] || action;
  };

  const filteredLogs = logs.filter((log) => {
    const matchesAction = !filterAction || log.Action === filterAction;
    const matchesSearch =
      !searchText ||
      log.Topic?.toLowerCase().includes(searchText.toLowerCase()) ||
      log.Message?.toLowerCase().includes(searchText.toLowerCase());
    return matchesAction && matchesSearch;
  });

  const actionTypes = [...new Set(logs.map((log) => log.Action))];

  return (
    <div>
      <Typography variant="h4" gutterBottom>
        执行审计
      </Typography>
      <Typography variant="body2" color="textSecondary" paragraph>
        记录所有自动和手动操作的审计日志
      </Typography>

      <Box display="flex" gap={2} mb={3}>
        <TextField
          label="搜索"
          variant="outlined"
          size="small"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ width: 300 }}
        />
        <FormControl size="small" sx={{ width: 200 }}>
          <InputLabel>操作类型</InputLabel>
          <Select
            value={filterAction}
            label="操作类型"
            onChange={(e) => setFilterAction(e.target.value)}
          >
            <MenuItem value="">全部</MenuItem>
            {actionTypes.map((action) => (
              <MenuItem key={action} value={action}>
                {formatAction(action)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell width={180}>时间</TableCell>
              <TableCell width={150}>操作类型</TableCell>
              <TableCell width={250}>Topic</TableCell>
              <TableCell>详情</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredLogs.map((log) => (
              <TableRow key={log.ID} hover>
                <TableCell>
                  {new Date(log.Timestamp).toLocaleString()}
                </TableCell>
                <TableCell>
                  <Chip
                    label={formatAction(log.Action)}
                    color={getActionColor(log.Action)}
                    size="small"
                  />
                </TableCell>
                <TableCell>{log.Topic || '-'}</TableCell>
                <TableCell>{log.Message}</TableCell>
              </TableRow>
            ))}
            {filteredLogs.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  <Typography color="textSecondary" py={3}>
                    暂无审计日志
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Box mt={4} p={3} component={Paper}>
        <Typography variant="h6" gutterBottom>
          操作类型说明
        </Typography>
        <Box display="grid" gridTemplateColumns="repeat(2, 1fr)" gap={2}>
          <Box>
            <Chip label="添加Topic" size="small" sx={{ mr: 1 }} />
            <Typography variant="body2" display="inline">
              添加新的Topic到监控列表
            </Typography>
          </Box>
          <Box>
            <Chip label="移除Topic" size="small" color="default" sx={{ mr: 1 }} />
            <Typography variant="body2" display="inline">
              从监控列表中移除Topic
            </Typography>
          </Box>
          <Box>
            <Chip label="消费者扩容" size="small" color="primary" sx={{ mr: 1 }} />
            <Typography variant="body2" display="inline">
              自动增加消费者数量
            </Typography>
          </Box>
          <Box>
            <Chip label="消费者缩容" size="small" color="primary" sx={{ mr: 1 }} />
            <Typography variant="body2" display="inline">
              自动减少消费者数量
            </Typography>
          </Box>
          <Box>
            <Chip label="分区调整" size="small" color="secondary" sx={{ mr: 1 }} />
            <Typography variant="body2" display="inline">
              自动调整Topic分区数量
            </Typography>
          </Box>
          <Box>
            <Chip label="限流调整" size="small" color="warning" sx={{ mr: 1 }} />
            <Typography variant="body2" display="inline">
              自动调整生产者发送速率
            </Typography>
          </Box>
          <Box>
            <Chip label="策略变更" size="small" color="info" sx={{ mr: 1 }} />
            <Typography variant="body2" display="inline">
              处理策略配置变更
            </Typography>
          </Box>
          <Box>
            <Chip label="预测告警" size="small" color="error" sx={{ mr: 1 }} />
            <Typography variant="body2" display="inline">
              积压预测触发告警阈值
            </Typography>
          </Box>
        </Box>
      </Box>
    </div>
  );
}

export default AuditLog;
