import React, { useState, useEffect } from 'react';
import {
  Paper, Typography, Grid, Card, CardContent, Box, Button,
  Table, TableBody, TableCell, TableHead, TableRow, Chip,
  Alert, List, ListItem, ListItemIcon, ListItemText,
  LinearProgress,
} from '@mui/material';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import StorageIcon from '@mui/icons-material/Storage';
import api from '../services/api';

function SlowSqlPanel() {
  const [analysis, setAnalysis] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [slowRecords, setSlowRecords] = useState([]);

  const loadData = async () => {
    try {
      const [analysisRes, alertsRes, slowRes] = await Promise.all([
        api.analyzeSlowSql(),
        api.getAlerts(),
        api.getSlowSqlRecords(30),
      ]);
      setAnalysis(analysisRes.data);
      setAlerts(alertsRes.data || []);
      setSlowRecords(slowRes.data || []);
    } catch (e) {
      console.error('Failed to load slow SQL data:', e);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleAcknowledge = async (alertId) => {
    try {
      await api.acknowledgeAlert(alertId);
      loadData();
    } catch (e) {}
  };

  const getRiskColor = (level) => {
    switch (level) {
      case 'HIGH': return 'error';
      case 'MEDIUM': return 'warning';
      default: return 'success';
    }
  };

  const getSeverityIcon = (severity) => {
    if (severity === 'CRITICAL') return <ErrorIcon color="error" />;
    return <WarningIcon color="warning" />;
  };

  return (
    <Box>
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <StorageIcon color="primary" sx={{ mr: 1 }} />
            <Typography variant="h6">慢SQL与连接池关联分析</Typography>
          </Box>
          <Button variant="outlined" onClick={loadData}>刷新</Button>
        </Box>

        {analysis && (
          <>
            <Grid container spacing={3} sx={{ mb: 3 }}>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="subtitle2" color="text.secondary">慢SQL总数</Typography>
                    <Typography variant="h4">{analysis.totalSlowQueries}</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="subtitle2" color="text.secondary">平均执行时间</Typography>
                    <Typography variant="h4">{analysis.avgSlowQueryTimeMs?.toFixed(0)} ms</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="subtitle2" color="text.secondary">池压力相关性</Typography>
                    <Typography variant="h4">{analysis.correlationWithPoolPressure?.toFixed(2)}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {analysis.correlationWithPoolPressure > 0.6 ? '强相关' : '弱相关'}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography variant="subtitle2" color="text.secondary">泄漏风险</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="h4" color={getRiskColor(analysis.leakRiskLevel)}>
                        {analysis.leakRiskScore?.toFixed(0)}
                      </Typography>
                      <Chip label={analysis.leakRiskLevel} color={getRiskColor(analysis.leakRiskLevel)} size="small" />
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(100, analysis.leakRiskScore || 0)}
                      color={getRiskColor(analysis.leakRiskLevel)}
                      sx={{ mt: 1 }}
                    />
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {analysis.analysisSummary && analysis.analysisSummary.length > 0 && (
              <Alert severity={analysis.leakRiskLevel === 'HIGH' ? 'error' : 'info'} sx={{ mb: 3 }}>
                {analysis.analysisSummary.map((s, i) => (
                  <Typography key={i} variant="body2">{s}</Typography>
                ))}
              </Alert>
            )}
          </>
        )}
      </Paper>

      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>连接泄漏告警</Typography>
        {alerts.filter(a => !a.acknowledged).length === 0 ? (
          <Alert severity="success">
            <CheckCircleIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            无活跃告警
          </Alert>
        ) : (
          <List>
            {alerts.filter(a => !a.acknowledged).map((alert, i) => (
              <ListItem
                key={i}
                sx={{
                  bgcolor: alert.severity === 'CRITICAL' ? '#ffebee' : '#fff8e1',
                  borderRadius: 1,
                  mb: 1,
                }}
                secondaryAction={
                  <Button size="small" onClick={() => handleAcknowledge(alert.alertId)}>
                    确认
                  </Button>
                }
              >
                <ListItemIcon>{getSeverityIcon(alert.severity)}</ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip label={alert.severity} color={alert.severity === 'CRITICAL' ? 'error' : 'warning'} size="small" />
                      <Typography variant="body2">连接 #{alert.connectionId}</Typography>
                    </Box>
                  }
                  secondary={
                    <>
                      <Typography variant="body2">{alert.message}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        持有时间: {alert.holdDurationMs?.toFixed(0)}ms | 
                        池利用率: {(alert.poolUtilizationAtAlert * 100).toFixed(1)}% |
                        活跃连接: {alert.activeConnectionsAtAlert}
                      </Typography>
                      {alert.recommendations && alert.recommendations.length > 0 && (
                        <Box sx={{ mt: 1 }}>
                          {alert.recommendations.map((r, j) => (
                            <Typography key={j} variant="caption" display="block" color="text.secondary">
                              • {r}
                            </Typography>
                          ))}
                        </Box>
                      )}
                    </>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </Paper>

      <Paper elevation={2} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>慢SQL记录 (最近 {slowRecords.length} 条)</Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>时间</TableCell>
              <TableCell>类型</TableCell>
              <TableCell>SQL预览</TableCell>
              <TableCell align="right">执行时间</TableCell>
              <TableCell align="right">持有时间</TableCell>
              <TableCell align="right">借出时间</TableCell>
              <TableCell>连接</TableCell>
              <TableCell>标记</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {slowRecords.slice().reverse().slice(0, 30).map((r, i) => (
              <TableRow key={i} sx={{
                bgcolor: r.isPotentialLeak ? '#ffebee' : r.isLongTransaction ? '#fff8e1' : 'inherit',
              }}>
                <TableCell>{new Date(r.timestamp).toLocaleTimeString()}</TableCell>
                <TableCell>
                  <Chip label={r.sqlType} size="small" variant="outlined" />
                </TableCell>
                <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                  {r.sqlPreview}
                </TableCell>
                <TableCell align="right">{r.executionTimeMs?.toFixed(0)}ms</TableCell>
                <TableCell align="right">{r.holdTimeMs?.toFixed(0)}ms</TableCell>
                <TableCell align="right">{r.borrowTimeMs?.toFixed(1)}ms</TableCell>
                <TableCell>#{r.connectionId}</TableCell>
                <TableCell>
                  {r.isPotentialLeak && <Chip label="泄漏" color="error" size="small" />}
                  {r.isLongTransaction && !r.isPotentialLeak && <Chip label="长事务" color="warning" size="small" />}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}

export default SlowSqlPanel;
