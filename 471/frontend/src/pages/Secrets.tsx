import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useNavigate } from 'react-router-dom';
import {
  Box,
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
  CircularProgress,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import { format } from 'date-fns';
import { secretApi } from '../services/api';
import { CreateSecretRequest } from '../types';

const Secrets: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [openDialog, setOpenDialog] = useState(false);
  const [filterType, setFilterType] = useState('');
  const [newSecret, setNewSecret] = useState<CreateSecretRequest>({
    name: '',
    description: '',
    type: 'database',
    value: '',
    labels: {},
  });

  const { data, isLoading } = useQuery(['secrets', filterType], () =>
    secretApi.list(50, 0, filterType || undefined)
  );

  const createMutation = useMutation(secretApi.create, {
    onSuccess: () => {
      queryClient.invalidateQueries('secrets');
      setOpenDialog(false);
      setNewSecret({
        name: '',
        description: '',
        type: 'database',
        value: '',
        labels: {},
      });
    },
  });

  const deleteMutation = useMutation(secretApi.delete, {
    onSuccess: () => {
      queryClient.invalidateQueries('secrets');
    },
  });

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const handleCreate = () => {
    createMutation.mutate(newSecret);
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this secret?')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Secrets</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpenDialog(true)}
        >
          Add Secret
        </Button>
      </Box>

      <Box mb={2}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Filter by Type</InputLabel>
          <Select
            value={filterType}
            label="Filter by Type"
            onChange={(e) => setFilterType(e.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="database">Database</MenuItem>
            <MenuItem value="api-key">API Key</MenuItem>
            <MenuItem value="password">Password</MenuItem>
            <MenuItem value="certificate">Certificate</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Version</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Labels</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data?.data.secrets.map((secret) => (
              <TableRow key={secret.id}>
                <TableCell>{secret.name}</TableCell>
                <TableCell>
                  <Chip label={secret.type} size="small" />
                </TableCell>
                <TableCell>{secret.version}</TableCell>
                <TableCell>
                  {format(new Date(secret.created_at), 'yyyy-MM-dd HH:mm')}
                </TableCell>
                <TableCell>
                  <Chip
                    label={secret.is_rotated ? 'Rotated' : 'Active'}
                    color={secret.is_rotated ? 'secondary' : 'success'}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {Object.entries(secret.labels || {}).map(([k, v]) => (
                    <Chip key={k} label={`${k}=${v}`} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                  ))}
                </TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => navigate(`/secrets/${secret.id}`)}
                  >
                    <VisibilityIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(secret.id)}
                    color="error"
                  >
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Secret</DialogTitle>
        <DialogContent>
          <Box component="form" sx={{ mt: 1 }}>
            <TextField
              margin="normal"
              fullWidth
              label="Name"
              value={newSecret.name}
              onChange={(e) => setNewSecret({ ...newSecret, name: e.target.value })}
            />
            <TextField
              margin="normal"
              fullWidth
              label="Description"
              value={newSecret.description}
              onChange={(e) => setNewSecret({ ...newSecret, description: e.target.value })}
            />
            <FormControl fullWidth margin="normal">
              <InputLabel>Type</InputLabel>
              <Select
                value={newSecret.type}
                label="Type"
                onChange={(e) => setNewSecret({ ...newSecret, type: e.target.value })}
              >
                <MenuItem value="database">Database</MenuItem>
                <MenuItem value="api-key">API Key</MenuItem>
                <MenuItem value="password">Password</MenuItem>
                <MenuItem value="certificate">Certificate</MenuItem>
              </Select>
            </FormControl>
            <TextField
              margin="normal"
              fullWidth
              label="Value"
              type="password"
              value={newSecret.value}
              onChange={(e) => setNewSecret({ ...newSecret, value: e.target.value })}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button
            onClick={handleCreate}
            variant="contained"
            disabled={!newSecret.name || !newSecret.value}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Secrets;
