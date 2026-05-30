import React, { useState } from 'react';
import { useQuery } from 'react-query';
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
  TextField,
  Grid,
} from '@mui/material';
import { format } from 'date-fns';
import { auditApi } from '../services/api';

const AuditLogs: React.FC = () => {
  const [filterUser, setFilterUser] = useState('');
  const [filterSecretId, setFilterSecretId] = useState('');

  const { data, isLoading } = useQuery(
    ['auditLogs', filterUser, filterSecretId],
    () => auditApi.list(100, 0, filterSecretId || undefined, filterUser || undefined)
  );

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'CREATE':
        return 'success';
      case 'READ':
        return 'primary';
      case 'UPDATE':
        return 'warning';
      case 'DELETE':
        return 'error';
      case 'ROTATE':
        return 'secondary';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Audit Logs
      </Typography>

      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} sm={6} md={4}>
          <TextField
            fullWidth
            label="Filter by User"
            value={filterUser}
            onChange={(e) => setFilterUser(e.target.value)}
            size="small"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <TextField
            fullWidth
            label="Filter by Secret ID"
            value={filterSecretId}
            onChange={(e) => setFilterSecretId(e.target.value)}
            size="small"
          />
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Time</TableCell>
              <TableCell>Action</TableCell>
              <TableCell>User</TableCell>
              <TableCell>Secret ID</TableCell>
              <TableCell>IP Address</TableCell>
              <TableCell>Success</TableCell>
              <TableCell>Message</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data?.data.logs.map((log) => (
              <TableRow key={log.id}>
                <TableCell>
                  {format(new Date(log.created_at), 'yyyy-MM-dd HH:mm:ss')}
                </TableCell>
                <TableCell>
                  <Chip
                    label={log.action}
                    color={getActionColor(log.action) as any}
                    size="small"
                  />
                </TableCell>
                <TableCell>{log.user}</TableCell>
                <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                  {log.secret_id?.substring(0, 8)}...
                </TableCell>
                <TableCell>{log.ip_address || '-'}</TableCell>
                <TableCell>
                  <Chip
                    label={log.success ? 'Yes' : 'No'}
                    color={log.success ? 'success' : 'error'}
                    size="small"
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>{log.message}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="body2" color="textSecondary" mt={2}>
        Total logs: {data?.data.total || 0}
      </Typography>
    </Box>
  );
};

export default AuditLogs;
