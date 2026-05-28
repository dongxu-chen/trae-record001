import React, { useState, useEffect } from 'react';
import {
  Paper, Typography, Grid, Card, CardContent, Box, Button,
  Table, TableBody, TableCell, TableHead, TableRow, Chip,
  Switch, FormControlLabel, Alert, TextField,
} from '@mui/material';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import api from '../services/api';

function AutoTuningPanel({ poolConfig, workload }) {
  const [tuningHistory, setTuningHistory] = useState([]);
  const [policy, setPolicy] = useState(null);
  const [autoEnabled, setAutoEnabled] = useState(false);
  const [latestDecision, setLatestDecision] = useState(null);

  useEffect(() => {
    loadPolicy();
    loadHistory();
  }, []);

  const loadPolicy = async () => {
    try {
      const res = await api.getTuningPolicy();
      setPolicy(res.data);
      setAutoEnabled(res.data.enabled);
    } catch (e) {}
  };

  const loadHistory = async () => {
    try {
      const res = await api.getTuningHistory();
      setTuningHistory(res.data || []);
    } catch (e) {}
  };

  const handleManualEvaluate = async () => {
    try {
      const res = await api.evaluateTuning();
      if (res.status === 204 || !res.data) {
        setLatestDecision(null);
        return;
      }
      setLatestDecision(res.data);
    } catch (e) {}
  };

  const handleApply = async (decision) => {
    try {
      await api.applyTuning(decision);
      setLatestDecision({ ...decision, applied: true });
      loadHistory();
    } catch (e) {}
  };

  const handleAutoStep = async () => {
    try {
      const res = await api.autoTuneStep();
      if (res.data) {
        setLatestDecision(res.data);
        loadHistory();
      }
    } catch (e) {}
  };

  const toggleAuto = async () => {
    const newEnabled = !autoEnabled;
    setAutoEnabled(newEnabled);
    if (policy) {
      policy.enabled = newEnabled;
      try {
        await api.updateTuningPolicy(policy);
      } catch (e) {}
    }
  };

  const getActionColor = (action) => {
    switch (action) {
      case 'SCALE_UP': return 'error';
      case 'SCALE_DOWN': return 'success';
      case 'ADJUST_MIN_IDLE': return 'warning';
      default: return 'default';
    }
  };

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <AutoFixHighIcon color="secondary" sx={{ mr: 1 }} />
          <Typography variant="h6">自动参数调整</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <FormControlLabel
            control={<Switch checked={autoEnabled} onChange={toggleAuto} />}
            label="自动模式"
          />
          <Button variant="outlined" onClick={handleManualEvaluate}>
            评估调整
          </Button>
          <Button variant="contained" color="secondary" onClick={handleAutoStep}>
            执行一步
          </Button>
        </Box>
      </Box>

      {latestDecision && (
        <Alert
          severity={latestDecision.applied ? 'success' : 'info'}
          sx={{ mb: 3 }}
          action={
            !latestDecision.applied && (
              <Button color="inherit" size="small" onClick={() => handleApply(latestDecision)}>
                应用
              </Button>
            )
          }
        >
          <Typography variant="subtitle2">
            {latestDecision.action === 'SCALE_UP' ? '⬆️ 扩容' :
             latestDecision.action === 'SCALE_DOWN' ? '⬇️ 缩容' : '🔧 调整'}
          </Typography>
          <Typography variant="body2">
            {latestDecision.parameter}: {latestDecision.oldValue} → {latestDecision.newValue}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {latestDecision.reason} (置信度: {(latestDecision.confidence * 100).toFixed(0)}%)
          </Typography>
        </Alert>
      )}

      {policy && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth size="small" type="number"
              label="扩容利用率阈值"
              value={policy.scaleUpUtilizationThreshold}
              onChange={(e) => setPolicy({...policy, scaleUpUtilizationThreshold: parseFloat(e.target.value)})}
              InputProps={{ inputProps: { min: 0.5, max: 1, step: 0.05 } }}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth size="small" type="number"
              label="缩容利用率阈值"
              value={policy.scaleDownUtilizationThreshold}
              onChange={(e) => setPolicy({...policy, scaleDownUtilizationThreshold: parseFloat(e.target.value)})}
              InputProps={{ inputProps: { min: 0.1, max: 0.6, step: 0.05 } }}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth size="small" type="number"
              label="调整步长"
              value={policy.scaleStepSize}
              onChange={(e) => setPolicy({...policy, scaleStepSize: parseInt(e.target.value)})}
              InputProps={{ inputProps: { min: 1, max: 10 } }}
            />
          </Grid>
        </Grid>
      )}

      <Typography variant="subtitle1" gutterBottom>调整历史</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>时间</TableCell>
            <TableCell>操作</TableCell>
            <TableCell>参数</TableCell>
            <TableCell>变更</TableCell>
            <TableCell>原因</TableCell>
            <TableCell>置信度</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {tuningHistory.slice(-20).reverse().map((d, i) => (
            <TableRow key={i}>
              <TableCell>{new Date(d.timestamp).toLocaleTimeString()}</TableCell>
              <TableCell>
                <Chip
                  label={d.action}
                  color={getActionColor(d.action)}
                  size="small"
                />
              </TableCell>
              <TableCell>{d.parameter}</TableCell>
              <TableCell>{d.oldValue} → {d.newValue}</TableCell>
              <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {d.reason}
              </TableCell>
              <TableCell>{(d.confidence * 100).toFixed(0)}%</TableCell>
            </TableRow>
          ))}
          {tuningHistory.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                暂无调整记录，启动监控后自动评估
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Paper>
  );
}

export default AutoTuningPanel;
