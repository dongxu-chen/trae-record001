import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import { Add, Delete, Visibility } from '@mui/icons-material';
import schemaApi from '../services/api';

function SchemaList() {
  const [schemas, setSchemas] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [newSchema, setNewSchema] = useState({
    subject: '',
    type: 'AVRO',
    schema: '',
    description: '',
  });

  useEffect(() => {
    loadSchemas();
  }, []);

  const loadSchemas = async () => {
    try {
      const response = await schemaApi.getAllSchemas();
      setSchemas(response.data);
    } catch (error) {
      console.error('Error loading schemas:', error);
    }
  };

  const handleCreateSchema = async () => {
    try {
      await schemaApi.createSchema(newSchema);
      setOpenDialog(false);
      setNewSchema({ subject: '', type: 'AVRO', schema: '', description: '' });
      loadSchemas();
    } catch (error) {
      console.error('Error creating schema:', error);
    }
  };

  const handleDeleteSchema = async (subject) => {
    if (window.confirm(`Are you sure you want to delete schema "${subject}"?`)) {
      try {
        await schemaApi.deleteSchema(subject);
        loadSchemas();
      } catch (error) {
        console.error('Error deleting schema:', error);
      }
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

  return (
    <div>
      <Typography variant="h4" gutterBottom>
        Schema Registry
      </Typography>
      <Button
        variant="contained"
        startIcon={<Add />}
        onClick={() => setOpenDialog(true)}
        sx={{ mb: 2 }}
      >
        Register New Schema
      </Button>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Subject</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Compatibility</TableCell>
              <TableCell>Versions</TableCell>
              <TableCell>Created At</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {schemas.map((schema) => (
              <TableRow key={schema.id}>
                <TableCell>{schema.subject}</TableCell>
                <TableCell>
                  <Chip label={schema.type} color={getTypeColor(schema.type)} size="small" />
                </TableCell>
                <TableCell>
                  <Chip label={schema.compatibilityLevel} variant="outlined" size="small" />
                </TableCell>
                <TableCell>{schema.versions?.length || 0}</TableCell>
                <TableCell>{new Date(schema.createdAt).toLocaleDateString()}</TableCell>
                <TableCell>
                  <IconButton component={Link} to={`/schema/${schema.subject}`} size="small">
                    <Visibility />
                  </IconButton>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => handleDeleteSchema(schema.subject)}
                  >
                    <Delete />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Register New Schema</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Subject"
            value={newSchema.subject}
            onChange={(e) => setNewSchema({ ...newSchema, subject: e.target.value })}
            sx={{ mt: 2, mb: 2 }}
          />
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Schema Type</InputLabel>
            <Select
              value={newSchema.type}
              label="Schema Type"
              onChange={(e) => setNewSchema({ ...newSchema, type: e.target.value })}
            >
              <MenuItem value="AVRO">Avro</MenuItem>
              <MenuItem value="PROTOBUF">Protobuf</MenuItem>
              <MenuItem value="JSON_SCHEMA">JSON Schema</MenuItem>
            </Select>
          </FormControl>
          <TextField
            fullWidth
            label="Schema Definition"
            multiline
            rows={10}
            value={newSchema.schema}
            onChange={(e) => setNewSchema({ ...newSchema, schema: e.target.value })}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Description"
            value={newSchema.description}
            onChange={(e) => setNewSchema({ ...newSchema, description: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateSchema} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}

export default SchemaList;
