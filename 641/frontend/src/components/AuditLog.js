import React, { useState, useEffect } from 'react';
import {
  Typography,
  Paper,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Grid,
  Box,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  History,
  Search,
  Visibility,
  ExpandMore,
  Person,
  CalendarToday,
  AutoAwesome,
  Code,
  Delete,
  Settings,
  CheckCircle,
  Error,
} from '@mui/icons-material';
import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import schemaApi from '../services/api';

function AuditLog() {
  const [filters, setFilters] = useState({
    subject: '',
    username: '',
    action: '',
    recentHours: 24,
  });
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  useEffect(() => {
    loadAuditLogs();
  }, []);

  const loadAuditLogs = async () => {
    setLoading(true);
    try {
      const response = await schemaApi.getAuditLogs(
        filters.username || undefined,
        filters.action || undefined,
        filters.recentHours
      );
      let logs = response.data;

      if (filters.subject) {
        logs = logs.filter(log =>
          log.subject.toLowerCase().includes(filters.subject.toLowerCase())
        );
      }

      setAuditLogs(logs);
    } catch (error) {
      console.error('Failed to load audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActionIcon = (action) => {
    switch (action) {
      case 'CREATED': return <AutoAwesome />;
      case 'VERSION_ADDED': return <History />;
      case 'VERSION_AUTO_GENERATED': return <AutoAwesome />;
      case 'COMPATIBILITY_UPDATED': return <Settings />;
      case 'DELETED': return <Delete />;
      case 'CODE_GENERATED': return <Code />;
      case 'SCHEMA_EVOLVED': return <AutoAwesome />;
      default: return <History />;
    }
  };

  const getActionColor = (action) => {
    switch (action) {
      case 'CREATED': return 'success';
      case 'VERSION_ADDED': return 'primary';
      case 'VERSION_AUTO_GENERATED': return 'info';
      case 'COMPATIBILITY_UPDATED': return 'warning';
      case 'DELETED': return 'error';
      case 'CODE_GENERATED': return 'secondary';
      case 'SCHEMA_EVOLVED': return 'info';
      default: return 'default';
    }
  };

  const formatDateTime = (dateStr) => {
    return new Date(dateStr).toLocaleString();
  };

  const openDetailDialog = (log) => {
    setSelectedLog(log);
    setDetailDialogOpen(true);
  };

  return (
    <div>
      <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
        <History sx={{ mr: 2 }} /> Schema Audit Log
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <TextField
              fullWidth
              label="Filter by Subject"
              value={filters.subject}
              onChange={(e) => setFilters({ ...filters, subject: e.target.value })}
              placeholder="e.g., user-events"
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField
              fullWidth
              label="Filter by Username"
              value={filters.username}
              onChange={(e) => setFilters({ ...filters, username: e.target.value })}
              placeholder="e.g., system"
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth>
              <InputLabel>Action Type</InputLabel>
              <Select
                value={filters.action}
                label="Action Type"
                onChange={(e) => setFilters({ ...filters, action: e.target.value })}
              >
                <MenuItem value="">All Actions</MenuItem>
                <MenuItem value="CREATED">Created</MenuItem>
                <MenuItem value="VERSION_ADDED">Version Added</MenuItem>
                <MenuItem value="VERSION_AUTO_GENERATED">Auto Generated</MenuItem>
                <MenuItem value="COMPATIBILITY_UPDATED">Compatibility Updated</MenuItem>
                <MenuItem value="DELETED">Deleted</MenuItem>
                <MenuItem value="CODE_GENERATED">Code Generated</MenuItem>
                <MenuItem value="SCHEMA_EVOLVED">Schema Evolved</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={3}>
            <Button
              variant="contained"
              startIcon={<Search />}
              onClick={loadAuditLogs}
              fullWidth
              sx={{ height: '100%' }}
            >
              Search
            </Button>
          </Grid>
        </Grid>

        <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
          <Chip
            label={`Last ${filters.recentHours} hours`}
            variant="outlined"
            onClick={() => setFilters({ ...filters, recentHours: filters.recentHours === 24 ? 168 : 24 })}
            clickable
          />
          <Chip
            label="All time"
            variant="outlined"
            onClick={() => setFilters({ ...filters, recentHours: null })}
            clickable
          />
        </Box>
      </Paper>

      <Paper>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Time</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Subject</TableCell>
                <TableCell>Version</TableCell>
                <TableCell>User</TableCell>
                <TableCell>Auto</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Details</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {auditLogs.map((log) => (
                <TableRow key={log.id} hover>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CalendarToday fontSize="small" color="action" />
                      {formatDateTime(log.createdAt)}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      icon={getActionIcon(log.action)}
                      label={log.action.replace(/_/g, ' ')}
                      color={getActionColor(log.action)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <code style={{ backgroundColor: 'grey.100', padding: '2px 6px', borderRadius: '4px' }}>
                      {log.subject}
                    </code>
                  </TableCell>
                  <TableCell align="center">
                    {log.version ? `v${log.version}` : '-'}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Person fontSize="small" color="action" />
                      {log.username}
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    {log.autoGenerated ? (
                      <AutoAwesome fontSize="small" color="info" />
                    ) : (
                      <span style={{ color: 'text.disabled' }}>-</span>
                    )}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 300 }}>
                    <Typography variant="body2" noWrap>
                      {log.changeDescription || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => openDetailDialog(log)}>
                      <Visibility fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        {auditLogs.length === 0 && !loading && (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography color="textSecondary">No audit logs found</Typography>
          </Box>
        )}
      </Paper>

      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Audit Log Details
          <Chip
            label={selectedLog?.action?.replace(/_/g, ' ')}
            color={selectedLog ? getActionColor(selectedLog.action) : 'default'}
            size="small"
            sx={{ ml: 2 }}
          />
        </DialogTitle>
        <DialogContent dividers>
          {selectedLog && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" gutterBottom color="textSecondary">
                    Basic Information
                  </Typography>
                  <List dense>
                    <ListItem>
                      <ListItemIcon><CalendarToday fontSize="small" /></ListItemIcon>
                      <ListItemText
                        primary="Timestamp"
                        secondary={formatDateTime(selectedLog.createdAt)}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Person fontSize="small" /></ListItemIcon>
                      <ListItemText
                        primary="User"
                        secondary={selectedLog.username}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><Code fontSize="small" /></ListItemIcon>
                      <ListItemText
                        primary="Subject"
                        secondary={selectedLog.subject}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon><History fontSize="small" /></ListItemIcon>
                      <ListItemText
                        primary="Version"
                        secondary={selectedLog.version ? `v${selectedLog.version}` : 'N/A'}
                      />
                    </ListItem>
                    {selectedLog.compatibilityCheckPassed !== null && (
                      <ListItem>
                        <ListItemIcon>
                          {selectedLog.compatibilityCheckPassed ? (
                            <CheckCircle color="success" fontSize="small" />
                          ) : (
                            <Error color="error" fontSize="small" />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary="Compatibility Check"
                          secondary={selectedLog.compatibilityCheckPassed ? 'Passed' : 'Failed'}
                        />
                      </ListItem>
                    )}
                    {selectedLog.autoGenerated && (
                      <ListItem>
                        <ListItemIcon><AutoAwesome color="info" fontSize="small" /></ListItemIcon>
                        <ListItemText
                          primary="Auto Generated"
                          secondary="Yes"
                        />
                      </ListItem>
                    )}
                  </List>
                </Paper>
              </Grid>

              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" gutterBottom color="textSecondary">
                    Change Description
                  </Typography>
                  <Typography variant="body1">
                    {selectedLog.changeDescription || 'No description available'}
                  </Typography>
                </Paper>
              </Grid>

              {selectedLog.oldSchemaText && (
                <Grid item xs={12} md={6}>
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography>Old Schema</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Paper sx={{ p: 2, bgcolor: 'grey.100', maxHeight: 300, overflow: 'auto' }}>
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '12px' }}>
                          {selectedLog.oldSchemaText}
                        </pre>
                      </Paper>
                    </AccordionDetails>
                  </Accordion>
                </Grid>
              )}

              {selectedLog.newSchemaText && (
                <Grid item xs={12} md={6}>
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography>New Schema</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Paper sx={{ p: 2, bgcolor: 'grey.100', maxHeight: 300, overflow: 'auto' }}>
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '12px' }}>
                          {selectedLog.newSchemaText}
                        </pre>
                      </Paper>
                    </AccordionDetails>
                  </Accordion>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default AuditLog;
