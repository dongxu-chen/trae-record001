import React from 'react';
import {
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Box,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Chip,
  Alert,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import SavingsIcon from '@mui/icons-material/Savings';
import SpeedIcon from '@mui/icons-material/Speed';
import InfoIcon from '@mui/icons-material/Info';

function OptimizationResults({ result }) {
  const getRiskColor = (level) => {
    switch (level) {
      case 'LOW':
        return 'success';
      case 'MEDIUM':
        return 'warning';
      case 'HIGH':
        return 'error';
      default:
        return 'default';
    }
  };

  const getImprovementColor = (value) => {
    if (value > 0) return 'success.main';
    if (value < 0) return 'error.main';
    return 'text.primary';
  };

  const formatImprovement = (value) => {
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%`;
  };

  if (result.originalConfig) {
    return (
      <Box>
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            优化前后对比
          </Typography>

          {result.summary && (
            <Alert severity="info" sx={{ mb: 3 }}>
              {result.summary}
            </Alert>
          )}

          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom color="text.secondary">
                    原始配置
                  </Typography>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell>最大连接数</TableCell>
                        <TableCell align="right">{result.originalConfig.maxPoolSize}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>最小空闲连接</TableCell>
                        <TableCell align="right">{result.originalConfig.minIdle}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>连接超时</TableCell>
                        <TableCell align="right">{result.originalConfig.connectionTimeoutMs}ms</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card variant="outlined" sx={{ borderColor: 'primary.main', bgcolor: 'primary.light' }}>
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom color="primary">
                    优化后配置
                  </Typography>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell>最大连接数</TableCell>
                        <TableCell align="right">
                          <strong>{result.optimizedConfig.maxPoolSize}</strong>
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>最小空闲连接</TableCell>
                        <TableCell align="right">
                          <strong>{result.optimizedConfig.minIdle}</strong>
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>连接超时</TableCell>
                        <TableCell align="right">
                          <strong>{result.optimizedConfig.connectionTimeoutMs}ms</strong>
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {result.improvements && (
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <TrendingDownIcon color="success" sx={{ mr: 1 }} />
                      <Typography variant="subtitle2" color="text.secondary">
                        等待时间降低
                      </Typography>
                    </Box>
                    <Typography
                      variant="h4"
                      color={getImprovementColor(result.improvements.waitTimeReductionPercent)}
                    >
                      {formatImprovement(result.improvements.waitTimeReductionPercent || 0)}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <SavingsIcon color="success" sx={{ mr: 1 }} />
                      <Typography variant="subtitle2" color="text.secondary">
                        资源节省
                      </Typography>
                    </Box>
                    <Typography
                      variant="h4"
                      color={getImprovementColor(result.improvements.resourceSavingPercent)}
                    >
                      {formatImprovement(result.improvements.resourceSavingPercent || 0)}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <SpeedIcon color="success" sx={{ mr: 1 }} />
                      <Typography variant="subtitle2" color="text.secondary">
                        吞吐量提升
                      </Typography>
                    </Box>
                    <Typography
                      variant="h4"
                      color={getImprovementColor(result.improvements.throughputImprovementPercent)}
                    >
                      {formatImprovement(result.improvements.throughputImprovementPercent || 0)}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <InfoIcon color="primary" sx={{ mr: 1 }} />
                      <Typography variant="subtitle2" color="text.secondary">
                        利用率变化
                      </Typography>
                    </Box>
                    <Typography
                      variant="h4"
                      color={getImprovementColor(result.improvements.utilizationChangePercent)}
                    >
                      {formatImprovement(result.improvements.utilizationChangePercent || 0)}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </Paper>
      </Box>
    );
  }

  return (
    <Box>
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6">优化建议</Typography>
          <Chip
            label={`风险等级: ${result.riskLevel}`}
            color={getRiskColor(result.riskLevel)}
          />
        </Box>

        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  推荐最大连接数
                </Typography>
                <Typography variant="h4">{result.recommendedMaxPoolSize}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  推荐最小空闲连接
                </Typography>
                <Typography variant="h4">{result.recommendedMinIdle}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  预期平均等待时间
                </Typography>
                <Typography variant="h4">{result.expectedAvgWaitTimeMs?.toFixed(2)}ms</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  预期资源节省
                </Typography>
                <Typography variant="h4">{result.resourceSavingPercent?.toFixed(1)}%</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Alert severity="info" sx={{ mb: 3 }}>
          {result.justification}
        </Alert>
      </Paper>

      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>配置变更详情</Typography>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>配置项</TableCell>
              <TableCell align="right">变更</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {result.configurationChanges &&
              Object.entries(result.configurationChanges).map(([key, value]) => (
                <TableRow key={key}>
                  <TableCell>{key}</TableCell>
                  <TableCell align="right">
                    <code>{value}</code>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Paper>

      <Paper elevation={2} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>优化建议清单</Typography>
        <List>
          {result.recommendations &&
            result.recommendations.map((rec, index) => (
              <ListItem key={index}>
                <ListItemIcon>
                  {rec.includes('警告') ? (
                    <WarningIcon color="warning" />
                  ) : (
                    <CheckCircleIcon color="success" />
                  )}
                </ListItemIcon>
                <ListItemText primary={rec} />
              </ListItem>
            ))}
        </List>
      </Paper>
    </Box>
  );
}

export default OptimizationResults;
