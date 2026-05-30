import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Divider,
  LinearProgress,
  Alert as MuiAlert,
  Grid,
} from '@mui/material';
import {
  Check as CheckIcon,
  Done as DoneIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import dayjs from 'dayjs';
import { alertApi } from '../services/api';

function AlertPanel() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchAlerts = async () => {
    try {
      const response = await alertApi.getAll({ active: true });
      setAlerts(response.data);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (id) => {
    try {
      await alertApi.acknowledge(id);
      fetchAlerts();
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  const handleResolve = async (id) => {
    try {
      await alertApi.resolve(id);
      fetchAlerts();
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return 'error';
      case 'HIGH':
        return 'error';
      case 'MEDIUM':
        return 'warning';
      case 'LOW':
        return 'info';
      default:
        return 'default';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return <ErrorIcon color="error" />;
      case 'HIGH':
        return <ErrorIcon color="error" />;
      case 'MEDIUM':
        return <WarningIcon color="warning" />;
      case 'LOW':
        return <InfoIcon color="info" />;
      default:
        return <InfoIcon />;
    }
  };

  const getAlertTypeText = (type) => {
    switch (type) {
      case 'AVAILABILITY_VIOLATION':
        return '可用性违规';
      case 'LATENCY_VIOLATION':
        return '延迟违规';
      case 'ERROR_RATE_VIOLATION':
        return '错误率违规';
      case 'SLA_PREDICTED_VIOLATION':
        return '预测违规';
      default:
        return type;
    }
  };

  if (loading) {
    return <LinearProgress />;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        告警中心
      </Typography>

      {alerts.length === 0 ? (
        <MuiAlert severity="success">当前没有活跃告警</MuiAlert>
      ) : (
        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  严重告警
                </Typography>
                <Typography variant="h3" color="error">
                  {alerts.filter((a) => a.severity === 'CRITICAL' || a.severity === 'HIGH').length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  中等告警
                </Typography>
                <Typography variant="h3" color="warning.main">
                  {alerts.filter((a) => a.severity === 'MEDIUM').length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  低级告警
                </Typography>
                <Typography variant="h3" color="info.main">
                  {alerts.filter((a) => a.severity === 'LOW').length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  已确认
                </Typography>
                <Typography variant="h3">
                  {alerts.filter((a) => a.acknowledged).length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  告警列表
                </Typography>
                <List>
                  {alerts.map((alert, index) => (
                    <React.Fragment key={alert.id}>
                      {index > 0 && <Divider />}
                      <ListItem>
                        <Box mr={2}>{getSeverityIcon(alert.severity)}</Box>
                        <ListItemText
                          primary={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="subtitle1">
                                {alert.serviceName}
                              </Typography>
                              <Chip
                                label={getAlertTypeText(alert.alertType)}
                                size="small"
                                color={getSeverityColor(alert.severity)}
                              />
                              {alert.acknowledged && (
                                <Chip
                                  label="已确认"
                                  size="small"
                                  color="default"
                                  icon={<CheckIcon />}
                                />
                              )}
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="body2">{alert.message}</Typography>
                              <Typography variant="caption" color="textSecondary">
                                当前值: {alert.currentValue?.toFixed(2)} | 阈值:{' '}
                                {alert.thresholdValue?.toFixed(2)} | 时间:{' '}
                                {dayjs(alert.createdAt).format('YYYY-MM-DD HH:mm:ss')}
                              </Typography>
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          {!alert.acknowledged && (
                            <IconButton
                              edge="end"
                              aria-label="acknowledge"
                              onClick={() => handleAcknowledge(alert.id)}
                              sx={{ mr: 1 }}
                            >
                              <CheckIcon />
                            </IconButton>
                          )}
                          <IconButton
                            edge="end"
                            aria-label="resolve"
                            onClick={() => handleResolve(alert.id)}
                          >
                            <DoneIcon />
                          </IconButton>
                        </ListItemSecondaryAction>
                      </ListItem>
                    </React.Fragment>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}

export default AlertPanel;
