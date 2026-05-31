import React, { useState } from 'react';
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
  Alert,
  Divider,
} from '@mui/material';
import {
  AutoAwesome,
  CheckCircle,
  Error,
  Warning,
  Visibility,
  PlayArrow,
} from '@mui/icons-material';
import schemaApi from '../services/api';

function AutoEvolve() {
  const [formData, setFormData] = useState({
    subject: '',
    schema: '',
    username: 'system',
  });
  const [previewResult, setPreviewResult] = useState(null);
  const [evolveResult, setEvolveResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadSampleSchema = () => {
    setFormData({
      ...formData,
      subject: 'user-events',
      schema: JSON.stringify({
        type: 'record',
        name: 'User',
        fields: [
          { name: 'id', type: 'string' },
          { name: 'name', type: 'string' },
          { name: 'email', type: 'string' },
          { name: 'phone', type: 'string' },
        ],
      }, null, 2),
    });
  };

  const handlePreview = async () => {
    setLoading(true);
    setPreviewResult(null);
    setEvolveResult(null);
    try {
      const response = await schemaApi.previewEvolution(formData.subject, formData.schema);
      setPreviewResult(response.data);
    } catch (error) {
      console.error('Preview failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEvolve = async () => {
    setLoading(true);
    try {
      const response = await schemaApi.autoEvolveSchema(
        formData.subject,
        formData.schema,
        formData.username
      );
      setEvolveResult(response.data);
    } catch (error) {
      console.error('Evolve failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
        <AutoAwesome sx={{ mr: 2 }} /> Schema Auto Evolution
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Schema Subject"
              value={formData.subject}
              onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
              helperText="Enter the subject of the schema to evolve"
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField
              fullWidth
              label="Username"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            />
          </Grid>
          <Grid item xs={12} md={3}>
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

        <TextField
          fullWidth
          label="Proposed Schema"
          multiline
          rows={12}
          value={formData.schema}
          onChange={(e) => setFormData({ ...formData, schema: e.target.value })}
          helperText="Enter the new schema definition. The system will automatically adjust it to maintain compatibility."
          sx={{ mb: 3 }}
        />

        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button
            variant="outlined"
            size="large"
            startIcon={<Visibility />}
            onClick={handlePreview}
            disabled={loading || !formData.subject || !formData.schema}
          >
            Preview Changes
          </Button>
          <Button
            variant="contained"
            size="large"
            startIcon={<PlayArrow />}
            onClick={handleEvolve}
            disabled={loading || !formData.subject || !formData.schema}
          >
            Evolve Schema
          </Button>
        </Box>
      </Paper>

      {previewResult && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Preview Result
          </Typography>

          <Alert
            severity={previewResult.compatible ? 'success' : 'error'}
            sx={{ mb: 2 }}
          >
            {previewResult.message}
          </Alert>

          {previewResult.appliedChanges?.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                Changes to be applied ({previewResult.appliedChanges.length}):
              </Typography>
              <List dense>
                {previewResult.appliedChanges.map((change, idx) => (
                  <ListItem key={idx}>
                    <ListItemIcon>
                      <AutoAwesome color="success" fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={change} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {previewResult.warnings?.length > 0 && (
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                Warnings:
              </Typography>
              <List dense>
                {previewResult.warnings.map((warning, idx) => (
                  <ListItem key={idx}>
                    <ListItemIcon>
                      <Warning color="warning" fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={warning} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {previewResult.newSchema && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                Evolved Schema:
              </Typography>
              <Paper sx={{ p: 2, bgcolor: 'grey.100' }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                  {previewResult.newSchema}
                </pre>
              </Paper>
            </Box>
          )}
        </Paper>
      )}

      {evolveResult && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
            {evolveResult.success ? (
              <CheckCircle color="success" sx={{ mr: 1 }} />
            ) : (
              <Error color="error" sx={{ mr: 1 }} />
            )}
            Evolution Result
          </Typography>

          <Alert
            severity={evolveResult.success ? 'success' : 'error'}
            sx={{ mb: 2 }}
          >
            {evolveResult.message}
          </Alert>

          {evolveResult.success && (
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item>
                <Chip
                  label={`Version: ${evolveResult.oldVersion} → ${evolveResult.newVersion}`}
                  color="primary"
                />
              </Grid>
              <Grid item>
                <Chip
                  label={evolveResult.compatible ? 'Compatible' : 'Incompatible'}
                  color={evolveResult.compatible ? 'success' : 'error'}
                />
              </Grid>
              <Grid item>
                <Chip label={`Subject: ${evolveResult.subject}`} variant="outlined" />
              </Grid>
            </Grid>
          )}

          {evolveResult.appliedChanges?.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                Applied Changes ({evolveResult.appliedChanges.length}):
              </Typography>
              <List dense>
                {evolveResult.appliedChanges.map((change, idx) => (
                  <ListItem key={idx}>
                    <ListItemIcon>
                      <CheckCircle color="success" fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={change} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {evolveResult.newSchema && evolveResult.success && (
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                Final Schema (Version {evolveResult.newVersion}):
              </Typography>
              <Paper sx={{ p: 2, bgcolor: 'grey.100' }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                  {evolveResult.newSchema}
                </pre>
              </Paper>
            </Box>
          )}
        </Paper>
      )}
    </div>
  );
}

export default AutoEvolve;
