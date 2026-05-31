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
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import { CheckCircle, Error, Warning, CompareArrows } from '@mui/icons-material';
import schemaApi from '../services/api';

function CompatibilityChecker() {
  const [formData, setFormData] = useState({
    type: 'AVRO',
    level: 'BACKWARD',
    oldSchema: '',
    newSchema: '',
  });
  const [result, setResult] = useState(null);

  const handleCheck = async () => {
    try {
      const response = await schemaApi.checkCompatibility(formData);
      setResult(response.data);
    } catch (error) {
      console.error('Error checking compatibility:', error);
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
          ],
        }, null, 2),
        newSchema: JSON.stringify({
          type: 'record',
          name: 'User',
          fields: [
            { name: 'id', type: 'string' },
            { name: 'name', type: 'string' },
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
          },
          required: ['id', 'name'],
        }, null, 2),
        newSchema: JSON.stringify({
          type: 'object',
          properties: {
            id: { type: 'string' },
            name: { type: 'string' },
            email: { type: 'string' },
          },
          required: ['id', 'name'],
        }, null, 2),
      });
    } else {
      setFormData({
        ...formData,
        oldSchema: `syntax = "proto3";
message User {
  string id = 1;
  string name = 2;
}`,
        newSchema: `syntax = "proto3";
message User {
  string id = 1;
  string name = 2;
  string email = 3;
}`,
      });
    }
  };

  return (
    <div>
      <Typography variant="h4" gutterBottom>
        Compatibility Checker
      </Typography>

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
              <InputLabel>Compatibility Level</InputLabel>
              <Select
                value={formData.level}
                label="Compatibility Level"
                onChange={(e) => setFormData({ ...formData, level: e.target.value })}
              >
                <MenuItem value="NONE">NONE</MenuItem>
                <MenuItem value="FORWARD">FORWARD</MenuItem>
                <MenuItem value="BACKWARD">BACKWARD</MenuItem>
                <MenuItem value="FULL">FULL</MenuItem>
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
              label="Old Schema (Reader)"
              multiline
              rows={15}
              value={formData.oldSchema}
              onChange={(e) => setFormData({ ...formData, oldSchema: e.target.value })}
              variant="outlined"
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="New Schema (Writer)"
              multiline
              rows={15}
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
            onClick={handleCheck}
          >
            Check Compatibility
          </Button>
        </Box>
      </Paper>

      {result && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Chip
              label={result.compatible ? 'COMPATIBLE' : 'INCOMPATIBLE'}
              color={result.compatible ? 'success' : 'error'}
              sx={{ mr: 2 }}
            />
            <Typography variant="h6">
              {result.level} Compatibility Check Result
            </Typography>
          </Box>

          {result.errors?.length > 0 && (
            <Alert severity="error" sx={{ mb: 2 }}>
              <List dense>
                {result.errors.map((error, idx) => (
                  <ListItem key={idx}>
                    <ListItemIcon>
                      <Error color="error" fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={error} />
                  </ListItem>
                ))}
              </List>
            </Alert>
          )}

          {result.warnings?.length > 0 && (
            <Alert severity="warning">
              <List dense>
                {result.warnings.map((warning, idx) => (
                  <ListItem key={idx}>
                    <ListItemIcon>
                      <Warning color="warning" fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={warning} />
                  </ListItem>
                ))}
              </List>
            </Alert>
          )}

          {result.compatible && result.errors?.length === 0 && (
            <Alert severity="success">
              <ListItem>
                <ListItemIcon>
                  <CheckCircle color="success" />
                </ListItemIcon>
                <ListItemText primary="Schemas are compatible!" />
              </ListItem>
            </Alert>
          )}
        </Paper>
      )}
    </div>
  );
}

export default CompatibilityChecker;
