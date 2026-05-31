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
  Tabs,
  Tab,
  Alert,
  IconButton,
} from '@mui/material';
import {
  Code,
  ContentCopy,
  Download,
  CheckCircle,
} from '@mui/icons-material';
import schemaApi from '../services/api';

function CodeGeneration() {
  const [formData, setFormData] = useState({
    type: 'AVRO',
    language: 'all',
    schema: '',
    packageName: 'com.schemaregistry.generated',
    className: '',
  });
  const [generatedCodes, setGeneratedCodes] = useState([]);
  const [activeTab, setActiveTab] = useState(0);
  const [copiedIndex, setCopiedIndex] = useState(null);

  const loadSampleSchema = () => {
    if (formData.type === 'AVRO') {
      setFormData({
        ...formData,
        className: 'User',
        schema: JSON.stringify({
          type: 'record',
          name: 'User',
          fields: [
            { name: 'id', type: 'string' },
            { name: 'name', type: 'string' },
            { name: 'email', type: ['null', 'string'], default: null },
            { name: 'age', type: 'int' },
          ],
        }, null, 2),
      });
    } else if (formData.type === 'JSON_SCHEMA') {
      setFormData({
        ...formData,
        className: 'User',
        schema: JSON.stringify({
          type: 'object',
          properties: {
            id: { type: 'string' },
            name: { type: 'string' },
            email: { type: 'string', default: '' },
            age: { type: 'integer', default: 0 },
          },
          required: ['id'],
        }, null, 2),
      });
    } else {
      setFormData({
        ...formData,
        className: 'User',
        schema: `syntax = "proto3";
message User {
  string id = 1;
  string name = 2;
  optional string email = 3;
  int32 age = 4;
}`,
      });
    }
  };

  const handleGenerate = async () => {
    try {
      const response = await schemaApi.generateCodeDirect(
        formData.type,
        formData.language !== 'all' ? formData.language : null,
        formData.packageName,
        formData.className,
        formData.schema
      );
      setGeneratedCodes(response.data);
      setActiveTab(0);
    } catch (error) {
      console.error('Code generation failed:', error);
    }
  };

  const handleCopyToClipboard = (code, index) => {
    navigator.clipboard.writeText(code);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleDownload = (code, fileName) => {
    const element = document.createElement('a');
    const file = new Blob([code], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = fileName;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const getLanguageColor = (language) => {
    switch (language) {
      case 'Java': return 'primary';
      case 'Python': return 'success';
      case 'Go': return 'secondary';
      default: return 'default';
    }
  };

  return (
    <div>
      <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
        <Code sx={{ mr: 2 }} /> Cross-Language Code Generation
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
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
          <Grid item xs={12} md={3}>
            <FormControl fullWidth>
              <InputLabel>Target Language</InputLabel>
              <Select
                value={formData.language}
                label="Target Language"
                onChange={(e) => setFormData({ ...formData, language: e.target.value })}
              >
                <MenuItem value="all">All Languages</MenuItem>
                <MenuItem value="java">Java</MenuItem>
                <MenuItem value="python">Python</MenuItem>
                <MenuItem value="go">Go</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField
              fullWidth
              label="Class Name"
              value={formData.className}
              onChange={(e) => setFormData({ ...formData, className: e.target.value })}
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

        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Package Name (Java only)"
              value={formData.packageName}
              onChange={(e) => setFormData({ ...formData, packageName: e.target.value })}
            />
          </Grid>
        </Grid>

        <TextField
          fullWidth
          label="Schema Definition"
          multiline
          rows={12}
          value={formData.schema}
          onChange={(e) => setFormData({ ...formData, schema: e.target.value })}
          sx={{ mb: 3 }}
        />

        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          <Button
            variant="contained"
            size="large"
            startIcon={<Code />}
            onClick={handleGenerate}
            disabled={!formData.schema}
          >
            Generate Code
          </Button>
        </Box>
      </Paper>

      {generatedCodes.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Generated Code ({generatedCodes.length} {generatedCodes.length === 1 ? 'file' : 'files'})
          </Typography>

          <Alert severity="success" sx={{ mb: 2 }}>
            Code generated successfully for {formData.type} schema!
          </Alert>

          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tabs
              value={activeTab}
              onChange={(e, newValue) => setActiveTab(newValue)}
              variant="scrollable"
              scrollButtons="auto"
            >
              {generatedCodes.map((code, idx) => (
                <Tab
                  key={idx}
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={code.language}
                        size="small"
                        color={getLanguageColor(code.language)}
                        variant="outlined"
                      />
                      <span>{code.fileName}</span>
                    </Box>
                  }
                />
              ))}
            </Tabs>
          </Box>

          {generatedCodes.map((code, idx) => (
            idx === activeTab && (
              <Box key={idx}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Box>
                    <Chip label={code.language} color={getLanguageColor(code.language)} sx={{ mr: 1 }} />
                    <span style={{ fontWeight: 'medium' }}>{code.fileName}</span>
                    {code.packageName && (
                      <Chip label={`package: ${code.packageName}`} size="small" variant="outlined" sx={{ ml: 1 }} />
                    )}
                  </Box>
                  <Box>
                    <IconButton
                      onClick={() => handleCopyToClipboard(code.code, idx)}
                      color="primary"
                      size="small"
                      title="Copy to clipboard"
                    >
                      {copiedIndex === idx ? <CheckCircle color="success" /> : <ContentCopy />}
                    </IconButton>
                    <IconButton
                      onClick={() => handleDownload(code.code, code.fileName)}
                      color="primary"
                      size="small"
                      title="Download file"
                    >
                      <Download />
                    </IconButton>
                  </Box>
                </Box>
                <Paper
                  sx={{
                    p: 2,
                    bgcolor: 'grey.900',
                    color: 'grey.100',
                    maxHeight: '500px',
                    overflow: 'auto',
                  }}
                >
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '12px' }}>
                    {code.code}
                  </pre>
                </Paper>
              </Box>
            )
          ))}
        </Paper>
      )}
    </div>
  );
}

export default CodeGeneration;
