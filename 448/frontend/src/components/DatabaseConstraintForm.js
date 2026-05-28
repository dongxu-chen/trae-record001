import React from 'react';
import {
  Paper,
  Typography,
  Grid,
  TextField,
  Box,
  Alert,
} from '@mui/material';
import StorageIcon from '@mui/icons-material/Storage';

function DatabaseConstraintForm({ constraint, onChange }) {
  const handleChange = (field, value) => {
    onChange({ ...constraint, [field]: value });
  };

  if (!constraint) return null;

  const available = constraint.maxDatabaseConnections > 0
    ? Math.max(1, Math.floor((constraint.maxDatabaseConnections - (constraint.reservedConnections || 0)) / Math.max(1, constraint.sharedByApplications || 1)))
    : 0;

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <StorageIcon color="primary" sx={{ mr: 1 }} />
        <Typography variant="h6">
          数据库连接上限约束
        </Typography>
      </Box>

      <Alert severity="info" sx={{ mb: 2 }}>
        设置数据库最大连接数约束，确保优化建议不会超过数据库承载上限
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <TextField
            fullWidth
            label="数据库最大连接数"
            type="number"
            value={constraint.maxDatabaseConnections || ''}
            onChange={(e) => handleChange('maxDatabaseConnections', parseInt(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 1, max: 10000 } }}
            helperText="如 MySQL max_connections"
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <TextField
            fullWidth
            label="共享应用数"
            type="number"
            value={constraint.sharedByApplications || ''}
            onChange={(e) => handleChange('sharedByApplications', parseInt(e.target.value) || 1)}
            InputProps={{ inputProps: { min: 1, max: 50 } }}
            helperText="共用此数据库的应用数量"
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <TextField
            fullWidth
            label="预留连接数"
            type="number"
            value={constraint.reservedConnections || ''}
            onChange={(e) => handleChange('reservedConnections', parseInt(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 0, max: 100 } }}
            helperText="为管理/监控预留的连接"
          />
        </Grid>

        <Grid item xs={12} md={3}>
          <TextField
            fullWidth
            label="数据库类型"
            value={constraint.databaseType || ''}
            onChange={(e) => handleChange('databaseType', e.target.value)}
            helperText="MySQL, PostgreSQL, Oracle 等"
          />
        </Grid>

        <Grid item xs={12}>
          <Alert severity={available > 0 ? 'success' : 'warning'} variant="outlined">
            当前应用可用连接数上限：<strong>{available}</strong> 个
            （计算方式：({constraint.maxDatabaseConnections} - {constraint.reservedConnections || 0}) / {constraint.sharedByApplications || 1} = {available}）
          </Alert>
        </Grid>
      </Grid>
    </Paper>
  );
}

export default DatabaseConstraintForm;
