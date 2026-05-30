import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  Chip,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  IconButton,
  InputAdornment,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import RefreshIcon from '@mui/icons-material/Refresh';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import { format } from 'date-fns';
import { secretApi } from '../services/api';
import { UpdateSecretRequest } from '../types';

const SecretDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showValue, setShowValue] = useState(false);
  const [rotateDialog, setRotateDialog] = useState(false);
  const [newValue, setNewValue] = useState('');
  const [editDialog, setEditDialog] = useState(false);
  const [editData, setEditData] = useState<UpdateSecretRequest>({});

  const { data, isLoading } = useQuery(['secret', id], () => secretApi.get(id!), {
    enabled: !!id,
  });

  const updateMutation = useMutation(
    (data: { id: string; update: UpdateSecretRequest }) => secretApi.update(data.id, data.update),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['secret', id]);
        setEditDialog(false);
      },
    }
  );

  const rotateMutation = useMutation(
    (data: { id: string; newValue: string }) => secretApi.rotate(data.id, data.newValue),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['secret', id]);
        setRotateDialog(false);
        setNewValue('');
      },
    }
  );

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const secret = data?.data;
  if (!secret) {
    return <Typography>Secret not found</Typography>;
  }

  const handleRotate = () => {
    if (id && newValue) {
      rotateMutation.mutate({ id, newValue });
    }
  };

  const handleUpdate = () => {
    if (id && Object.keys(editData).length > 0) {
      updateMutation.mutate({ id, update: editData });
    }
  };

  return (
    <Box>
      <Box display="flex" alignItems="center" mb={3}>
        <IconButton onClick={() => navigate('/secrets')} sx={{ mr: 2 }}>
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4">Secret Details</Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h5">{secret.name}</Typography>
                <Box>
                  <Button
                    startIcon={<EditIcon />}
                    onClick={() => {
                      setEditData({ description: secret.description });
                      setEditDialog(true);
                    }}
                    sx={{ mr: 1 }}
                  >
                    Edit
                  </Button>
                  <Button
                    startIcon={<RefreshIcon />}
                    variant="contained"
                    color="secondary"
                    onClick={() => setRotateDialog(true)}
                  >
                    Rotate
                  </Button>
                </Box>
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography color="textSecondary">Type</Typography>
                  <Chip label={secret.type} />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography color="textSecondary">Version</Typography>
                  <Typography variant="h6">{secret.version}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography color="textSecondary">Description</Typography>
                  <Typography>{secret.description || 'No description'}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography color="textSecondary">Value</Typography>
                  <TextField
                    fullWidth
                    type={showValue ? 'text' : 'password'}
                    value={secret.value}
                    InputProps={{
                      readOnly: true,
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton onClick={() => setShowValue(!showValue)}>
                            {showValue ? <VisibilityOffIcon /> : <VisibilityIcon />}
                          </IconButton>
                        </InputAdornment>
                      ),
                    }}
                    sx={{ mt: 1 }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography color="textSecondary">Created</Typography>
                  <Typography>{format(new Date(secret.created_at), 'yyyy-MM-dd HH:mm:ss')}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography color="textSecondary">Last Updated</Typography>
                  <Typography>{format(new Date(secret.updated_at), 'yyyy-MM-dd HH:mm:ss')}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography color="textSecondary">Status</Typography>
                  <Chip
                    label={secret.is_rotated ? 'Rotated' : 'Active'}
                    color={secret.is_rotated ? 'secondary' : 'success'}
                  />
                </Grid>
                <Grid item xs={12}>
                  <Typography color="textSecondary">Labels</Typography>
                  <Box mt={1}>
                    {Object.entries(secret.labels || {}).map(([k, v]) => (
                      <Chip key={k} label={`${k}=${v}`} sx={{ mr: 0.5, mb: 0.5 }} />
                    ))}
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Dialog open={editDialog} onClose={() => setEditDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Secret</DialogTitle>
        <DialogContent>
          <TextField
            margin="normal"
            fullWidth
            label="Description"
            value={editData.description || ''}
            onChange={(e) => setEditData({ ...editData, description: e.target.value })}
          />
          <TextField
            margin="normal"
            fullWidth
            label="New Value (optional)"
            type="password"
            value={editData.value || ''}
            onChange={(e) => setEditData({ ...editData, value: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialog(false)}>Cancel</Button>
          <Button onClick={handleUpdate} variant="contained">
            Update
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={rotateDialog} onClose={() => setRotateDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Rotate Secret</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="textSecondary" mb={2}>
            This will create a new version of the secret. The old version will be preserved.
          </Typography>
          <TextField
            margin="normal"
            fullWidth
            label="New Secret Value"
            type="password"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRotateDialog(false)}>Cancel</Button>
          <Button
            onClick={handleRotate}
            variant="contained"
            color="secondary"
            disabled={!newValue}
          >
            Rotate
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SecretDetail;
