import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
} from '@mui/material';
import { executionApi, scenarioApi } from '../services/api';

const StatusLabels = {
  pending: '待执行',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
};

const StatusColors = {
  pending: 'default',
  running: 'warning',
  completed: 'success',
  failed: 'error',
};

function Executions() {
  const [executions, setExecutions] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadExecutions();
  }, [selectedScenario]);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await scenarioApi.list();
      setScenarios(data);
      await loadExecutions();
    } catch (err) {
      setError('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const loadExecutions = async () => {
    try {
      const data = await executionApi.list(selectedScenario || undefined);
      setExecutions(data);
    } catch (err) {
      setError('加载执行记录失败');
    }
  };

  const getScenarioName = (scenarioId) => {
    const scenario = scenarios.find((s) => s.id === scenarioId);
    return scenario ? scenario.name : scenarioId;
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        执行记录
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6}>
          <FormControl fullWidth>
            <InputLabel>筛选场景</InputLabel>
            <Select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              label="筛选场景"
            >
              <MenuItem value="">全部场景</MenuItem>
              {scenarios.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>场景名称</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>当前步骤</TableCell>
              <TableCell>总步骤</TableCell>
              <TableCell>开始时间</TableCell>
              <TableCell>结束时间</TableCell>
              <TableCell>创建时间</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {executions.map((exec) => (
              <TableRow key={exec.id}>
                <TableCell>
                  <Typography variant="body2" fontWeight="bold">
                    {getScenarioName(exec.scenario_id)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={StatusLabels[exec.status]}
                    color={StatusColors[exec.status]}
                    size="small"
                  />
                </TableCell>
                <TableCell>{exec.current_step}</TableCell>
                <TableCell>{exec.total_steps}</TableCell>
                <TableCell>
                  {exec.started_at
                    ? new Date(exec.started_at).toLocaleString()
                    : '-'}
                </TableCell>
                <TableCell>
                  {exec.ended_at
                    ? new Date(exec.ended_at).toLocaleString()
                    : '-'}
                </TableCell>
                <TableCell>
                  {new Date(exec.created_at).toLocaleString()}
                </TableCell>
              </TableRow>
            ))}
            {executions.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography color="text.secondary">暂无执行记录</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

export default Executions;
