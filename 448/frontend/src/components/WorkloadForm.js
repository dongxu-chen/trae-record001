import React from 'react';
import {
  Paper,
  Typography,
  Grid,
  TextField,
  Button,
  Box,
  FormControlLabel,
  Switch,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import CompareIcon from '@mui/icons-material/Compare';
import BoltIcon from '@mui/icons-material/Bolt';

function WorkloadForm({ workload, onChange, onSimulate, onOptimize, onCompare, loading }) {
  const handleChange = (field, value) => {
    onChange({ ...workload, [field]: value });
  };

  const handleMapChange = (field, value) => {
    const mapConfig = { ...(workload.markovArrivalConfig || {}) };
    mapConfig[field] = value;
    onChange({ ...workload, markovArrivalConfig: mapConfig });
  };

  const handleMixedChange = (field, value) => {
    const mixedConfig = { ...(workload.mixedTransactionConfig || {}) };
    mixedConfig[field] = value;
    onChange({ ...workload, mixedTransactionConfig: mixedConfig });
  };

  if (!workload) return null;

  const mapConfig = workload.markovArrivalConfig || { enabled: false };
  const mixedConfig = workload.mixedTransactionConfig || { enabled: false };

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        业务负载配置
      </Typography>

      <Grid container spacing={3} sx={{ mb: 2 }}>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="基础到达率 (req/s)"
            type="number"
            value={workload.arrivalRate || ''}
            onChange={(e) => handleChange('arrivalRate', parseFloat(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 1, max: 1000, step: 1 } }}
            helperText="基础请求到达率"
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="平均服务时间 (ms)"
            type="number"
            value={workload.avgServiceTimeMs || ''}
            onChange={(e) => handleChange('avgServiceTimeMs', parseFloat(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 1, step: 1 } }}
            helperText="非混合模式下的平均执行时间"
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="服务时间标准差 (ms)"
            type="number"
            value={workload.serviceTimeStdDevMs || ''}
            onChange={(e) => handleChange('serviceTimeStdDevMs', parseFloat(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 0, step: 1 } }}
            helperText="服务时间的波动程度"
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="峰值并发用户数"
            type="number"
            value={workload.peakConcurrentUsers || ''}
            onChange={(e) => handleChange('peakConcurrentUsers', parseInt(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 1, max: 1000 } }}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="模拟时长 (ms)"
            type="number"
            value={workload.simulationDurationMs || ''}
            onChange={(e) => handleChange('simulationDurationMs', parseInt(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 1000, max: 60000 } }}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="方差因子"
            type="number"
            value={workload.varianceFactor || ''}
            onChange={(e) => handleChange('varianceFactor', parseFloat(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 0.1, max: 2, step: 0.1 } }}
          />
        </Grid>
      </Grid>

      <Accordion defaultExpanded={mapConfig.enabled} sx={{ mb: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
            <BoltIcon color="warning" sx={{ mr: 1 }} />
            <Typography variant="subtitle1">马尔可夫到达过程 (MAP) — 业务突发性建模</Typography>
            <Switch
              checked={mapConfig.enabled || false}
              onChange={(e) => handleMapChange('enabled', e.target.checked)}
              onClick={(e) => e.stopPropagation()}
              sx={{ ml: 'auto' }}
            />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Alert severity="info" sx={{ mb: 2 }}>
            MAP 模型通过马尔可夫链在「正常态」和「突发态」之间切换，更真实地捕捉业务流量的突发性。
            突发因子越大，流量波动越剧烈，对连接池的影响越大。
          </Alert>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="正常态到达率 (req/s)"
                type="number"
                value={mapConfig.arrivalRates?.[0] || ''}
                onChange={(e) => {
                  const rates = [...(mapConfig.arrivalRates || [30, 120])];
                  rates[0] = parseFloat(e.target.value) || 0;
                  handleMapChange('arrivalRates', rates);
                }}
                helperText="平稳时期的请求频率"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="突发态到达率 (req/s)"
                type="number"
                value={mapConfig.arrivalRates?.[1] || ''}
                onChange={(e) => {
                  const rates = [...(mapConfig.arrivalRates || [30, 120])];
                  rates[1] = parseFloat(e.target.value) || 0;
                  handleMapChange('arrivalRates', rates);
                }}
                helperText="突发时期的请求频率"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="突发因子"
                type="number"
                value={mapConfig.burstinessFactor || ''}
                onChange={(e) => handleMapChange('burstinessFactor', parseFloat(e.target.value) || 1)}
                InputProps={{ inputProps: { min: 1, max: 5, step: 0.1 } }}
                helperText="≥1.0，值越大突发性越强"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="正常态→突发态概率"
                type="number"
                value={mapConfig.transitionMatrix?.[0]?.[1] || ''}
                onChange={(e) => {
                  const val = parseFloat(e.target.value) || 0;
                  const matrix = (mapConfig.transitionMatrix || [[0.7, 0.3], [0.4, 0.6]]).map(r => [...r]);
                  matrix[0][1] = val;
                  matrix[0][0] = 1 - val;
                  handleMapChange('transitionMatrix', matrix);
                }}
                InputProps={{ inputProps: { min: 0, max: 1, step: 0.05 } }}
                helperText="正常态转突发态的概率"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="突发态→正常态概率"
                type="number"
                value={mapConfig.transitionMatrix?.[1]?.[0] || ''}
                onChange={(e) => {
                  const val = parseFloat(e.target.value) || 0;
                  const matrix = (mapConfig.transitionMatrix || [[0.7, 0.3], [0.4, 0.6]]).map(r => [...r]);
                  matrix[1][0] = val;
                  matrix[1][1] = 1 - val;
                  handleMapChange('transitionMatrix', matrix);
                }}
                InputProps={{ inputProps: { min: 0, max: 1, step: 0.05 } }}
                helperText="突发态转正常态的概率"
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Accordion defaultExpanded={mixedConfig.enabled} sx={{ mb: 3 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
            <Typography variant="subtitle1">🔀 混合事务模型 — 长短查询混合模拟</Typography>
            <Switch
              checked={mixedConfig.enabled || false}
              onChange={(e) => handleMixedChange('enabled', e.target.checked)}
              onClick={(e) => e.stopPropagation()}
              sx={{ ml: 'auto' }}
            />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Alert severity="info" sx={{ mb: 2 }}>
            混合事务模型模拟真实业务中短查询（如点查、简单写入）和长查询（如报表、聚合分析）的混合负载，
            更准确地反映不同类型查询对连接池的差异化影响。
          </Alert>
          <Grid container spacing={3}>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="短查询占比"
                type="number"
                value={mixedConfig.shortQueryRatio || ''}
                onChange={(e) => handleMixedChange('shortQueryRatio', parseFloat(e.target.value) || 0)}
                InputProps={{ inputProps: { min: 0, max: 1, step: 0.05 } }}
                helperText="0-1之间，如 0.8 表示 80%"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="短查询平均时间 (ms)"
                type="number"
                value={mixedConfig.shortQueryAvgTimeMs || ''}
                onChange={(e) => handleMixedChange('shortQueryAvgTimeMs', parseFloat(e.target.value) || 0)}
                InputProps={{ inputProps: { min: 1 } }}
                helperText="如点查、简单写入"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="短查询时间标准差 (ms)"
                type="number"
                value={mixedConfig.shortQueryStdDevMs || ''}
                onChange={(e) => handleMixedChange('shortQueryStdDevMs', parseFloat(e.target.value) || 0)}
                InputProps={{ inputProps: { min: 0 } }}
              />
            </Grid>
            <Grid item xs={12} md={3} />

            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="长查询平均时间 (ms)"
                type="number"
                value={mixedConfig.longQueryAvgTimeMs || ''}
                onChange={(e) => handleMixedChange('longQueryAvgTimeMs', parseFloat(e.target.value) || 0)}
                InputProps={{ inputProps: { min: 1 } }}
                helperText="如报表、聚合分析"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="长查询时间标准差 (ms)"
                type="number"
                value={mixedConfig.longQueryStdDevMs || ''}
                onChange={(e) => handleMixedChange('longQueryStdDevMs', parseFloat(e.target.value) || 0)}
                InputProps={{ inputProps: { min: 0 } }}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Button
          variant="contained"
          startIcon={<PlayArrowIcon />}
          onClick={onSimulate}
          disabled={loading}
          sx={{ minWidth: 150 }}
        >
          运行模拟
        </Button>
        <Button
          variant="contained"
          color="secondary"
          startIcon={<AutoFixHighIcon />}
          onClick={onOptimize}
          disabled={loading}
          sx={{ minWidth: 150 }}
        >
          智能优化
        </Button>
        <Button
          variant="outlined"
          startIcon={<CompareIcon />}
          onClick={onCompare}
          disabled={loading}
          sx={{ minWidth: 150 }}
        >
          对比分析
        </Button>
      </Box>
    </Paper>
  );
}

export default WorkloadForm;
