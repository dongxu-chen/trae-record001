import React from 'react';
import { useQuery } from 'react-query';
import { Grid, Card, CardContent, Typography, CircularProgress, Box, Chip } from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';
import HistoryIcon from '@mui/icons-material/History';
import SecurityIcon from '@mui/icons-material/Security';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { secretApi, auditApi, healthApi } from '../services/api';

const Dashboard: React.FC = () => {
  const { data: secretsData, isLoading: secretsLoading } = useQuery('secrets', () => secretApi.list(100));
  const { data: auditStats, isLoading: auditLoading } = useQuery('auditStats', () => auditApi.stats());
  const { data: healthData, isLoading: healthLoading } = useQuery('health', () => healthApi.check());

  if (secretsLoading || auditLoading || healthLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const totalSecrets = secretsData?.data.total || 0;
  const rotatedSecrets = secretsData?.data.secrets.filter(s => s.is_rotated).length || 0;
  const totalActions = Object.values(auditStats?.data.stats || {}).reduce((a, b) => a + b, 0);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <LockIcon color="primary" sx={{ mr: 1 }} />
                <Typography color="textSecondary">Total Secrets</Typography>
              </Box>
              <Typography variant="h3">{totalSecrets}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <HistoryIcon color="secondary" sx={{ mr: 1 }} />
                <Typography color="textSecondary">Rotated Secrets</Typography>
              </Box>
              <Typography variant="h3">{rotatedSecrets}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <SecurityIcon color="action" sx={{ mr: 1 }} />
                <Typography color="textSecondary">Audit Actions</Typography>
              </Box>
              <Typography variant="h3">{totalActions}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <CheckCircleIcon color={healthData?.data.status === 'healthy' ? 'success' : 'error'} sx={{ mr: 1 }} />
                <Typography color="textSecondary">System Status</Typography>
              </Box>
              <Typography variant="h5" sx={{ textTransform: 'capitalize' }}>
                {healthData?.data.status || 'Unknown'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Service Health
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={2}>
            {Object.entries(healthData?.data.services || {}).map(([service, status]) => (
              <Chip
                key={service}
                label={`${service}: ${status}`}
                color={status === 'healthy' || status === 'not_configured' ? 'success' : 'error'}
                variant="outlined"
              />
            ))}
          </Box>
        </CardContent>
      </Card>

      {auditStats?.data.stats && Object.keys(auditStats.data.stats).length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Audit Action Breakdown
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={2}>
              {Object.entries(auditStats.data.stats).map(([action, count]) => (
                <Chip
                  key={action}
                  label={`${action}: ${count}`}
                  color="primary"
                  variant="outlined"
                />
              ))}
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default Dashboard;
