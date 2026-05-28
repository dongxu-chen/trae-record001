import React from 'react';
import {
  Paper,
  Typography,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Grid,
  FormControlLabel,
  Switch,
} from '@mui/material';

const POOL_TYPES = [
  { value: 'HIKARICP', label: 'HikariCP (推荐)' },
  { value: 'DRUID', label: 'Druid (监控丰富)' },
  { value: 'TOMCAT_JDBC', label: 'Tomcat JDBC' },
];

function PoolConfigForm({ config, onChange, selectedPoolType, onPoolTypeChange }) {
  const handleChange = (field, value) => {
    onChange({ ...config, [field]: value });
  };

  if (!config) return null;

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        连接池配置
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <FormControl fullWidth>
            <InputLabel>连接池类型</InputLabel>
            <Select
              value={selectedPoolType}
              label="连接池类型"
              onChange={(e) => onPoolTypeChange(e.target.value)}
            >
              {POOL_TYPES.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  {type.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="最大连接数 (maxPoolSize)"
            type="number"
            value={config.maxPoolSize || ''}
            onChange={(e) => handleChange('maxPoolSize', parseInt(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 1, max: 200 } }}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="最小空闲连接数 (minIdle)"
            type="number"
            value={config.minIdle || ''}
            onChange={(e) => handleChange('minIdle', parseInt(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 0, max: 100 } }}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="连接超时 (ms)"
            type="number"
            value={config.connectionTimeoutMs || ''}
            onChange={(e) => handleChange('connectionTimeoutMs', parseInt(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 1000 } }}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="空闲超时 (ms)"
            type="number"
            value={config.idleTimeoutMs || ''}
            onChange={(e) => handleChange('idleTimeoutMs', parseInt(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 0 } }}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="最大生命周期 (ms)"
            type="number"
            value={config.maxLifetimeMs || ''}
            onChange={(e) => handleChange('maxLifetimeMs', parseInt(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 0 } }}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="泄漏检测阈值 (ms)"
            type="number"
            value={config.leakDetectionThresholdMs || ''}
            onChange={(e) => handleChange('leakDetectionThresholdMs', parseInt(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 0 } }}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="验证查询"
            value={config.validationQuery || ''}
            onChange={(e) => handleChange('validationQuery', e.target.value)}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="空闲检测间隔 (ms)"
            type="number"
            value={config.timeBetweenEvictionRunsMs || ''}
            onChange={(e) => handleChange('timeBetweenEvictionRunsMs', parseInt(e.target.value) || 0)}
            InputProps={{ inputProps: { min: 0 } }}
          />
        </Grid>

        <Grid item xs={12}>
          <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
            <FormControlLabel
              control={
                <Switch
                  checked={config.testOnBorrow || false}
                  onChange={(e) => handleChange('testOnBorrow', e.target.checked)}
                />
              }
              label="获取连接时验证"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={config.testOnReturn || false}
                  onChange={(e) => handleChange('testOnReturn', e.target.checked)}
                />
              }
              label="归还连接时验证"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={config.testWhileIdle || false}
                  onChange={(e) => handleChange('testWhileIdle', e.target.checked)}
                />
              }
              label="空闲时验证"
            />
          </Box>
        </Grid>
      </Grid>
    </Paper>
  );
}

export default PoolConfigForm;
