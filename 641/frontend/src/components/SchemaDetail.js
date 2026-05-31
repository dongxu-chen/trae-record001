import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography,
  Button,
  Paper,
  Chip,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Box,
} from '@mui/material';
import { ArrowBack, Add, CompareArrows } from '@mui/icons-material';
import schemaApi from '../services/api';

function SchemaDetail() {
  const { subject } = useParams();
  const navigate = useNavigate();
  const [schema, setSchema] = useState(null);
  const [versions, setVersions] = useState([]);
  const [openVersionDialog, setOpenVersionDialog] = useState(false);
  const [newVersion, setNewVersion] = useState({ schema: '', description: '' });
  const [selectedVersions, setSelectedVersions] = useState({ old: '', new: '' });

  useEffect(() => {
    loadSchema();
    loadVersions();
  }, [subject]);

  const loadSchema = async () => {
    try {
      const response = await schemaApi.getSchema(subject);
      setSchema(response.data);
    } catch (error) {
      console.error('Error loading schema:', error);
    }
  };

  const loadVersions = async () => {
    try {
      const response = await schemaApi.getVersions(subject);
      setVersions(response.data);
    } catch (error) {
      console.error('Error loading versions:', error);
    }
  };

  const handleAddVersion = async () => {
    try {
      await schemaApi.addVersion(subject, newVersion);
      setOpenVersionDialog(false);
      setNewVersion({ schema: '', description: '' });
      loadVersions();
    } catch (error) {
      console.error('Error adding version:', error);
    }
  };

  const handleCompareVersions = () => {
    if (selectedVersions.old && selectedVersions.new) {
      navigate(`/diff?subject=${subject}&old=${selectedVersions.old}&new=${selectedVersions.new}`);
    }
  };

  const handleCompatibilityChange = async (level) => {
    try {
      await schemaApi.updateCompatibility(subject, level);
      loadSchema();
    } catch (error) {
      console.error('Error updating compatibility:', error);
    }
  };

  const getTypeColor = (type) => {
    switch (type) {
      case 'AVRO': return 'primary';
      case 'PROTOBUF': return 'secondary';
      case 'JSON_SCHEMA': return 'success';
      default: return 'default';
    }
  };

  if (!schema) return <Typography>Loading...</Typography>;

  return (
    <div>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton onClick={() => navigate('/')} sx={{ mr: 2 }}>
          <ArrowBack />
        </IconButton>
        <Typography variant="h4">Schema: {subject}</Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>Schema Information</Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="textSecondary">Type</Typography>
              <Chip label={schema.type} color={getTypeColor(schema.type)} />
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="textSecondary">Compatibility Level</Typography>
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <Select
                  value={schema.compatibilityLevel}
                  onChange={(e) => handleCompatibilityChange(e.target.value)}
                >
                  <MenuItem value="NONE">NONE</MenuItem>
                  <MenuItem value="FORWARD">FORWARD</MenuItem>
                  <MenuItem value="BACKWARD">BACKWARD</MenuItem>
                  <MenuItem value="FULL">FULL</MenuItem>
                  <MenuItem value="FORWARD_TRANSITIVE">FORWARD_TRANSITIVE</MenuItem>
                  <MenuItem value="BACKWARD_TRANSITIVE">BACKWARD_TRANSITIVE</MenuItem>
                  <MenuItem value="FULL_TRANSITIVE">FULL_TRANSITIVE</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <Box>
              <Typography variant="body2" color="textSecondary">Created At</Typography>
              <Typography>{new Date(schema.createdAt).toLocaleString()}</Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>Compare Versions</Typography>
            <Grid container spacing={2}>
              <Grid item xs={5}>
                <FormControl fullWidth size="small">
                  <InputLabel>Old Version</InputLabel>
                  <Select
                    value={selectedVersions.old}
                    label="Old Version"
                    onChange={(e) => setSelectedVersions({ ...selectedVersions, old: e.target.value })}
                  >
                    {versions.map((v) => (
                      <MenuItem key={v.version} value={v.version}>v{v.version}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={2} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <CompareArrows />
              </Grid>
              <Grid item xs={5}>
                <FormControl fullWidth size="small">
                  <InputLabel>New Version</InputLabel>
                  <Select
                    value={selectedVersions.new}
                    label="New Version"
                    onChange={(e) => setSelectedVersions({ ...selectedVersions, new: e.target.value })}
                  >
                    {versions.map((v) => (
                      <MenuItem key={v.version} value={v.version}>v{v.version}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
            <Button
              variant="contained"
              onClick={handleCompareVersions}
              disabled={!selectedVersions.old || !selectedVersions.new}
              sx={{ mt: 2 }}
              fullWidth
            >
              Compare
            </Button>
          </Paper>
        </Grid>
      </Grid>

      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Versions ({versions.length})</Typography>
          <Button startIcon={<Add />} variant="contained" onClick={() => setOpenVersionDialog(true)}>
            Add New Version
          </Button>
        </Box>
        <List>
          {versions.map((version) => (
            <ListItem key={version.id} divider>
              <ListItemText
                primary={`Version ${version.version}`}
                secondary={version.description || 'No description'}
              />
              <ListItemSecondaryAction>
                <Typography variant="body2" color="textSecondary">
                  {new Date(version.createdAt).toLocaleString()}
                </Typography>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </Paper>

      <Dialog open={openVersionDialog} onClose={() => setOpenVersionDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add New Version</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Schema Definition"
            multiline
            rows={15}
            value={newVersion.schema}
            onChange={(e) => setNewVersion({ ...newVersion, schema: e.target.value })}
            sx={{ mt: 2, mb: 2 }}
          />
          <TextField
            fullWidth
            label="Description"
            value={newVersion.description}
            onChange={(e) => setNewVersion({ ...newVersion, description: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenVersionDialog(false)}>Cancel</Button>
          <Button onClick={handleAddVersion} variant="contained">Add Version</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}

export default SchemaDetail;
