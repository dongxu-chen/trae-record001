import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
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
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  AddCircle,
  RemoveCircle,
  Edit,
  CompareArrows,
  SwapHoriz,
  CheckCircle,
  Error,
} from '@mui/icons-material';
import schemaApi from '../services/api';

function SchemaDiffViewer() {
  const [searchParams] = useSearchParams();
  const subjectParam = searchParams.get('subject');
  const oldVersionParam = searchParams.get('old');
  const newVersionParam = searchParams.get('new');

  const [formData, setFormData] = useState({
    type: 'AVRO',
    oldSchema: '',
    newSchema: '',
  });
  const [diffResult, setDiffResult] = useState(null);
  const [viewMode, setViewMode] = useState('structured');

  useEffect(() => {
    if (subjectParam && oldVersionParam && newVersionParam) {
      loadVersionDiff();
    }
  }, [subjectParam, oldVersionParam, newVersionParam]);

  const loadVersionDiff = async () => {
    try {
      const response = await schemaApi.compareVersions(
        subjectParam,
        parseInt(oldVersionParam),
        parseInt(newVersionParam)
      );
      setDiffResult(response.data);
    } catch (error) {
      console.error('Error loading version diff:', error);
    }
  };

  const handleCompare = async () => {
    try {
      const response = await schemaApi.compareSchemasDirect(
        formData.type,
        formData.oldSchema,
        formData.newSchema
      );
      setDiffResult(response.data);
    } catch (error) {
      console.error('Error comparing schemas:', error);
    }
  };

  const loadSampleSchema = () => {
    if (formData.type === 'AVRO') {
      setFormData({
        ...formData,
        oldSchema: JSON.stringify({
          type: 'record',
          name: 'User',
          fields: [
            { name: 'id', type: 'string' },
            { name: 'name', type: 'string' },
            { name: 'age', type: 'int' },
          ],
        }, null, 2),
        newSchema: JSON.stringify({
          type: 'record',
          name: 'User',
          fields: [
            { name: 'id', type: 'string' },
            { name: 'fullName', type: 'string' },
            { name: 'email', type: ['null', 'string'], default: null },
          ],
        }, null, 2),
      });
    } else if (formData.type === 'JSON_SCHEMA') {
      setFormData({
        ...formData,
        oldSchema: JSON.stringify({
          type: 'object',
          properties: {
            id: { type: 'string' },
            name: { type: 'string' },
            age: { type: 'integer' },
          },
          required: ['id', 'name'],
        }, null, 2),
        newSchema: JSON.stringify({
          type: 'object',
          properties: {
            id: { type: 'string' },
            fullName: { type: 'string' },
            email: { type: 'string', default: '' },
          },
          required: ['id'],
        }, null, 2),
      });
    } else {
      setFormData({
        ...formData,
        oldSchema: `syntax = "proto3";
message User {
  string id = 1;
  string name = 2;
  int32 age = 3;
}`,
        newSchema: `syntax = "proto3";
message User {
  string id = 1;
  string full_name = 2;
  string email = 4;
}`,
      });
    }
  };

  const getChangeTypeColor = (changeType) => {
    switch (changeType) {
      case 'ADDED': return 'success.light';
      case 'REMOVED': return 'error.light';
      case 'MODIFIED': return 'warning.light';
      case 'RENAMED': return 'info.light';
      default: return 'background.paper';
    }
  };

  const getChangeTypeIcon = (changeType) => {
    switch (changeType) {
      case 'ADDED': return <AddCircle color="success" fontSize="small" />;
      case 'REMOVED': return <RemoveCircle color="error" fontSize="small" />;
      case 'MODIFIED': return <Edit color="warning" fontSize="small" />;
      case 'RENAMED': return <SwapHoriz color="info" fontSize="small" />;
      default: return <CheckCircle color="disabled" fontSize="small" />;
    }
  };

  const getChangeTypeLabel = (changeType) => {
    switch (changeType) {
      case 'ADDED': return 'Added';
      case 'REMOVED': return 'Removed';
      case 'MODIFIED': return 'Modified';
      case 'RENAMED': return 'Renamed';
      case 'UNCHANGED': return 'Unchanged';
      default: return changeType;
    }
  };

  return (
    <div>
      <Typography variant="h4" gutterBottom>
        Schema Diff Viewer
      </Typography>

      {subjectParam && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="subtitle1">
            Comparing {subjectParam}: v{oldVersionParam} vs v{newVersionParam}
          </Typography>
        </Paper>
      )}

      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Schema Type</InputLabel>
              <Select
                value={formData.type}
                label="Schema Type"
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              >
                <MenuItem value="AVRO">Avro</MenuItem>
                <MenuItem value="PROTOBUF">Protobuf</MenuItem>
                <MenuItem value="JSON_SCHEMA">JSON Schema</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>View Mode</InputLabel>
              <Select
                value={viewMode}
                label="View Mode"
                onChange={(e) => setViewMode(e.target.value)}
              >
                <MenuItem value="structured">Structured Comparison</MenuItem>
                <MenuItem value="summary">Summary View</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <Button
              variant="outlined"
              onClick={loadSampleSchema}
              fullWidth
              sx={{ height: '100%' }}
            >
              Load Sample
            </Button>
          </Grid>
        </Grid>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Old Schema"
              multiline
              rows={12}
              value={formData.oldSchema}
              onChange={(e) => setFormData({ ...formData, oldSchema: e.target.value })}
              variant="outlined"
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="New Schema"
              multiline
              rows={12}
              value={formData.newSchema}
              onChange={(e) => setFormData({ ...formData, newSchema: e.target.value })}
              variant="outlined"
            />
          </Grid>
        </Grid>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
          <Button
            variant="contained"
            size="large"
            startIcon={<CompareArrows />}
            onClick={handleCompare}
          >
            Compare Schemas
          </Button>
        </Box>
      </Paper>

      {diffResult && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Diff Result: {diffResult.oldVersion} vs {diffResult.newVersion}
            </Typography>
          </Box>

          {diffResult.renames?.length > 0 && (
            <Paper sx={{ p: 2, mb: 3, bgcolor: 'info.light' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <SwapHoriz color="info" sx={{ mr: 1 }} />
                <Typography variant="subtitle1">
                  Suspected Renames ({diffResult.renames.length})
                </Typography>
              </Box>
              <Divider sx={{ mb: 1 }} />
              <List dense>
                {diffResult.renames.map((item, idx) => (
                  <ListItem key={idx}>
                    <ListItemIcon>
                      <SwapHoriz color="info" fontSize="small" />
                    </ListItemIcon>
                    <ListItemText
                      primary={item.field}
                      secondary={item.description}
                    />
                  </ListItem>
                ))}
              </List>
            </Paper>
          )}

          {viewMode === 'structured' && diffResult.structuredDiff?.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>Structured Comparison</Typography>
              <TableContainer component={Paper}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell width="20%">Field</TableCell>
                      <TableCell width="10%">Status</TableCell>
                      <TableCell width="25%">Old Type</TableCell>
                      <TableCell width="25%">New Type</TableCell>
                      <TableCell width="10%">Old Required</TableCell>
                      <TableCell width="10%">New Required</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {diffResult.structuredDiff.map((node, idx) => (
                      <TableRow
                        key={idx}
                        sx={{
                          bgcolor: getChangeTypeColor(node.changeType),
                          pl: node.level ? node.level * 2 : 0,
                        }}
                      >
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Box sx={{ mr: 1 }}>
                              {getChangeTypeIcon(node.changeType)}
                            </Box>
                            {node.renameFrom ? (
                              <span>
                                <span style={{ textDecoration: 'line-through', color: 'error.main' }}>
                                  {node.renameFrom}
                                </span>
                                {' → '}
                                <span style={{ color: 'success.main' }}>
                                  {node.renameTo}
                                </span>
                                <Chip
                                  label={`${(node.renameConfidence * 100).toFixed(0)}%`}
                                  size="small"
                                  color="info"
                                  sx={{ ml: 1 }}
                                />
                              </span>
                            ) : (
                              node.fieldName
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={getChangeTypeLabel(node.changeType)}
                            size="small"
                            color={
                              node.changeType === 'ADDED' ? 'success' :
                              node.changeType === 'REMOVED' ? 'error' :
                              node.changeType === 'MODIFIED' ? 'warning' :
                              node.changeType === 'RENAMED' ? 'info' : 'default'
                            }
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          {node.oldType || '-'}
                          {node.oldDefault && (
                            <Typography variant="caption" display="block" color="textSecondary">
                              default: {node.oldDefault}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          {node.newType || '-'}
                          {node.newDefault && (
                            <Typography variant="caption" display="block" color="textSecondary">
                              default: {node.newDefault}
                              {node.hasDefault && (
                                <Chip
                                  label="compatible"
                                  size="small"
                                  color="success"
                                  variant="outlined"
                                  sx={{ ml: 1 }}
                                />
                              )}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell align="center">
                          {node.oldRequired !== undefined && (
                            node.oldRequired ?
                              <Error color="error" fontSize="small" /> :
                              <CheckCircle color="success" fontSize="small" />
                          )}
                        </TableCell>
                        <TableCell align="center">
                          {node.newRequired !== undefined && (
                            node.newRequired ?
                              <Error color="error" fontSize="small" /> :
                              <CheckCircle color="success" fontSize="small" />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}

          {viewMode === 'summary' && (
            <Grid container spacing={3}>
              {diffResult.additions?.length > 0 && (
                <Grid item xs={12} md={4}>
                  <Paper sx={{ p: 2, bgcolor: 'success.light' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <AddCircle color="success" sx={{ mr: 1 }} />
                      <Typography variant="subtitle1">Additions ({diffResult.additions.length})</Typography>
                    </Box>
                    <Divider sx={{ mb: 1 }} />
                    <List dense>
                      {diffResult.additions.map((item, idx) => (
                        <ListItem key={idx}>
                          <ListItemIcon>
                            <AddCircle color="success" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText
                            primary={item.field}
                            secondary={
                              item.hasDefault ?
                                `${item.path} (with default, compatible)` :
                                item.path
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Paper>
                </Grid>
              )}

              {diffResult.deletions?.length > 0 && (
                <Grid item xs={12} md={4}>
                  <Paper sx={{ p: 2, bgcolor: 'error.light' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <RemoveCircle color="error" sx={{ mr: 1 }} />
                      <Typography variant="subtitle1">Deletions ({diffResult.deletions.length})</Typography>
                    </Box>
                    <Divider sx={{ mb: 1 }} />
                    <List dense>
                      {diffResult.deletions.map((item, idx) => (
                        <ListItem key={idx}>
                          <ListItemIcon>
                            <RemoveCircle color="error" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText
                            primary={item.field}
                            secondary={item.path}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Paper>
                </Grid>
              )}

              {diffResult.modifications?.length > 0 && (
                <Grid item xs={12} md={4}>
                  <Paper sx={{ p: 2, bgcolor: 'warning.light' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Edit color="warning" sx={{ mr: 1 }} />
                      <Typography variant="subtitle1">Modifications ({diffResult.modifications.length})</Typography>
                    </Box>
                    <Divider sx={{ mb: 1 }} />
                    <List dense>
                      {diffResult.modifications.map((item, idx) => (
                        <ListItem key={idx}>
                          <ListItemIcon>
                            <Edit color="warning" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText
                            primary={item.field}
                            secondary={`${item.oldValue?.substring(0, 30)}... → ${item.newValue?.substring(0, 30)}...`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Paper>
                </Grid>
              )}
            </Grid>
          )}

          {diffResult.additions?.length === 0 &&
           diffResult.deletions?.length === 0 &&
           diffResult.modifications?.length === 0 &&
           diffResult.renames?.length === 0 && (
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <Chip label="No differences found" color="success" />
            </Paper>
          )}
        </Paper>
      )}
    </div>
  );
}

export default SchemaDiffViewer;
