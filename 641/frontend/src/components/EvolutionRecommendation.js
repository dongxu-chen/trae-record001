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
  Stepper,
  Step,
  StepLabel,
  Divider,
} from '@mui/material';
import {
  TrendingUp,
  Error,
  Warning,
  CheckCircle,
  Lightbulb,
  Flag,
  SwapHoriz,
  AddCircle,
  RemoveCircle,
} from '@mui/icons-material';
import schemaApi from '../services/api';

function EvolutionRecommendation() {
  const [formData, setFormData] = useState({
    type: 'AVRO',
    level: 'BACKWARD',
    oldSchema: '',
    newSchema: '',
  });
  const [recommendation, setRecommendation] = useState(null);

  const handleGetRecommendation = async () => {
    try {
      const response = await schemaApi.getEvolutionRecommendation(formData);
      setRecommendation(response.data);
    } catch (error) {
      console.error('Error getting recommendation:', error);
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
            { name: 'firstName', type: 'string' },
            { name: 'lastName', type: 'string' },
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
            email: { type: 'string' },
          },
          required: ['id', 'fullName'],
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

  const getImpactColor = (impact) => {
    switch (impact) {
      case 'CRITICAL': return 'error';
      case 'HIGH': return 'warning';
      case 'MEDIUM': return 'info';
      case 'LOW': return 'success';
      default: return 'default';
    }
  };

  return (
    <div>
      <Typography variant="h4" gutterBottom>
        Schema Evolution Recommendation
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
              label="Current Schema"
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
              label="Proposed Schema"
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
            startIcon={<Lightbulb />}
            onClick={handleGetRecommendation}
          >
            Get Evolution Recommendation
          </Button>
        </Box>
      </Paper>

      {recommendation && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <TrendingUp sx={{ mr: 2, fontSize: 32 }} />
            <Typography variant="h5">Evolution Analysis</Typography>
            <Chip
              label={`Impact: ${recommendation.impact}`}
              color={getImpactColor(recommendation.impact)}
              sx={{ ml: 2 }}
            />
          </Box>

          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="subtitle1">{recommendation.recommendation}</Typography>
          </Alert>

          {recommendation.detectedRenames?.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Paper sx={{ p: 2, bgcolor: 'info.light' }}>
                <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
                  <SwapHoriz color="info" sx={{ mr: 1 }} /> Suspected Field Renames ({recommendation.detectedRenames.length})
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <List dense>
                  {recommendation.detectedRenames.map((rename, idx) => (
                    <ListItem key={idx}>
                      <ListItemIcon>
                        <SwapHoriz color="info" fontSize="small" />
                      </ListItemIcon>
                      <ListItemText primary={rename} />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Box>
          )}

          {recommendation.safeAdditions?.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Paper sx={{ p: 2, bgcolor: 'success.light' }}>
                <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
                  <AddCircle color="success" sx={{ mr: 1 }} /> Safe Additions ({recommendation.safeAdditions.length})
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <List dense>
                  {recommendation.safeAdditions.map((addition, idx) => (
                    <ListItem key={idx}>
                      <ListItemIcon>
                        <AddCircle color="success" fontSize="small" />
                      </ListItemIcon>
                      <ListItemText primary={addition} />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Box>
          )}

          {recommendation.breakingChanges?.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Paper sx={{ p: 2, bgcolor: 'error.light' }}>
                <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
                  <RemoveCircle color="error" sx={{ mr: 1 }} /> Breaking Changes ({recommendation.breakingChanges.length})
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <List dense>
                  {recommendation.breakingChanges.map((change, idx) => (
                    <ListItem key={idx}>
                      <ListItemIcon>
                        <RemoveCircle color="error" fontSize="small" />
                      </ListItemIcon>
                      <ListItemText primary={change} />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Box>
          )}

          {recommendation.warnings?.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
                <Warning color="warning" sx={{ mr: 1 }} /> Other Warnings
              </Typography>
              <List dense>
                {recommendation.warnings
                  .filter(w => !w.includes('Suspected field rename'))
                  .map((warning, idx) => (
                  <ListItem key={idx}>
                    <ListItemIcon>
                      <Flag color="warning" fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={warning} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          <Divider sx={{ mb: 3 }} />

          <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
            <CheckCircle color="success" sx={{ mr: 1 }} /> Recommended Steps
          </Typography>
          <Stepper orientation="vertical" sx={{ mb: 3 }}>
            {recommendation.steps?.map((step, idx) => (
              <Step key={idx} active completed>
                <StepLabel>
                  <Typography variant="body1">{step}</Typography>
                </StepLabel>
              </Step>
            ))}
          </Stepper>

          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle1">
              Suggested Compatibility Level:{' '}
              <Chip label={recommendation.suggestedCompatibility} color="primary" />
            </Typography>
          </Box>
        </Paper>
      )}
    </div>
  );
}

export default EvolutionRecommendation;
