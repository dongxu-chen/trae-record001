import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  Chip,
  IconButton,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  Security as SecurityIcon,
  VerifiedUser as VerifiedUserIcon,
  Lock as LockIcon,
} from '@mui/icons-material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';

import type { Policy } from '../types';
import { policyApi } from '../services/api';

const Policies: React.FC = () => {
  const navigate = useNavigate();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [deleteDialog, setDeleteDialog] = useState<string | null>(null);

  useEffect(() => {
    loadPolicies();
  }, [filterType, filterStatus]);

  const loadPolicies = async () => {
    try {
      const typeParam = filterType === 'all' ? undefined : filterType;
      const response = await policyApi.listPolicies(typeParam);
      setPolicies(response.data.items);
    } catch (error) {
      console.error('Failed to load policies:', error);
      setPolicies([
        {
          id: '1',
          name: 'global-mtls-policy',
          type: 'mtls',
          namespace: 'istio-system',
          description: 'Global mTLS policy for all services',
          spec: { mode: 'STRICT' },
          status: 'active',
          labels: {},
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-01-15T10:00:00Z',
          created_by: 'admin',
        },
        {
          id: '2',
          name: 'frontend-auth-policy',
          type: 'authorization',
          namespace: 'default',
          description: 'Authorization policy for frontend service',
          spec: { action: 'ALLOW', rules: [] },
          status: 'active',
          labels: {},
          created_at: '2024-01-16T14:30:00Z',
          updated_at: '2024-01-16T14:30:00Z',
          created_by: 'admin',
        },
        {
          id: '3',
          name: 'api-jwt-authentication',
          type: 'requestauth',
          namespace: 'default',
          description: 'JWT authentication for API gateway',
          spec: { jwt_rules: [{ issuer: 'https://auth.example.com' }] },
          status: 'active',
          labels: {},
          created_at: '2024-01-17T09:15:00Z',
          updated_at: '2024-01-17T09:15:00Z',
          created_by: 'admin',
        },
      ]);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await policyApi.deletePolicy(id);
      setDeleteDialog(null);
      loadPolicies();
    } catch (error) {
      console.error('Failed to delete policy:', error);
      setPolicies(policies.filter(p => p.id !== id));
      setDeleteDialog(null);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'mtls':
        return <LockIcon color="primary" />;
      case 'authorization':
        return <VerifiedUserIcon color="secondary" />;
      case 'requestauth':
        return <SecurityIcon color="action" />;
      default:
        return <SecurityIcon />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'canary':
        return 'warning';
      case 'disabled':
        return 'default';
      default:
        return 'default';
    }
  };

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: '策略名称',
      flex: 1,
      renderCell: (params) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {getTypeIcon(params.row.type)}
          <Typography variant="body2">{params.value}</Typography>
        </Box>
      ),
    },
    {
      field: 'type',
      headerName: '类型',
      width: 150,
      renderCell: (params) => (
        <Chip
          label={params.value.toUpperCase()}
          size="small"
          color={
            params.value === 'mtls'
              ? 'primary'
              : params.value === 'authorization'
              ? 'secondary'
              : 'default'
          }
        />
      ),
    },
    {
      field: 'namespace',
      headerName: '命名空间',
      width: 150,
    },
    {
      field: 'status',
      headerName: '状态',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={getStatusColor(params.value) as any}
        />
      ),
    },
    {
      field: 'created_at',
      headerName: '创建时间',
      width: 200,
      valueFormatter: (params) => new Date(params.value).toLocaleString(),
    },
    {
      field: 'actions',
      headerName: '操作',
      width: 150,
      sortable: false,
      renderCell: (params) => (
        <Box>
          <IconButton
            size="small"
            onClick={() => navigate(`/policies/${params.id}`)}
            title="查看"
          >
            <VisibilityIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            onClick={() => navigate(`/policies/edit/${params.id}`)}
            title="编辑"
          >
            <EditIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            onClick={() => setDeleteDialog(params.id as string)}
            title="删除"
            color="error"
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Box>
      ),
    },
  ];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">策略管理</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/policies/new')}
        >
          创建策略
        </Button>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel>策略类型</InputLabel>
                <Select
                  value={filterType}
                  label="策略类型"
                  onChange={(e) => setFilterType(e.target.value)}
                >
                  <MenuItem value="all">全部</MenuItem>
                  <MenuItem value="mtls">mTLS</MenuItem>
                  <MenuItem value="authorization">授权策略</MenuItem>
                  <MenuItem value="requestauth">请求认证</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel>状态</InputLabel>
                <Select
                  value={filterStatus}
                  label="状态"
                  onChange={(e) => setFilterStatus(e.target.value)}
                >
                  <MenuItem value="all">全部</MenuItem>
                  <MenuItem value="active">活跃</MenuItem>
                  <MenuItem value="canary">灰度发布中</MenuItem>
                  <MenuItem value="disabled">已禁用</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Box sx={{ height: 500, width: '100%' }}>
            <DataGrid
              rows={policies}
              columns={columns}
              initialState={{
                pagination: { paginationModel: { page: 0, pageSize: 10 } },
              }}
              pageSizeOptions={[5, 10, 25]}
              disableRowSelectionOnClick
            />
          </Box>
        </CardContent>
      </Card>

      <Dialog open={!!deleteDialog} onClose={() => setDeleteDialog(null)}>
        <DialogTitle>确认删除</DialogTitle>
        <DialogContent>
          <Typography>确定要删除这个策略吗？此操作不可撤销。</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog(null)}>取消</Button>
          <Button
            onClick={() => deleteDialog && handleDelete(deleteDialog)}
            color="error"
            variant="contained"
          >
            删除
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Policies;
