import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  LinearProgress,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Star as StarIcon,
} from '@mui/icons-material';
import { slaTierApi, serviceApi } from '../services/api';

function SlaTierConfig() {
  const [tiers, setTiers] = useState([]);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingTier, setEditingTier] = useState(null);
  const [formData, setFormData] = useState({
    tierName: '',
    tierCode: '',
    description: '',
    availabilityTarget: 99.9,
    latencyTargetMs: 500,
    errorRateTarget: 1.0,
    monthlyAvailabilityTarget: 99.8,
    quarterlyAvailabilityTarget: 99.9,
    priorityLevel: 3,
    responseTimeSla: '',
    resolutionTimeSla: '',
    uptimeCreditPercent: 10,
    active: true,
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [tiersRes, servicesRes] = await Promise.all([
        slaTierApi.getAll(true),
        serviceApi.getAll(),
      ]);
      setTiers(tiersRes.data);
      setServices(servicesRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getServiceCountForTier = (tierId) => {
    return services.filter((s) => s.slaTier?.id === tierId).length;
  };

  const getTierColor = (priorityLevel) => {
    if (priorityLevel <= 2) return 'error';
    if (priorityLevel <= 3) return 'primary';
    return 'info';
  };

  const getTierStars = (priorityLevel) => {
    return 6 - priorityLevel;
  };

  const handleOpenCreate = () => {
    setEditingTier(null);
    setFormData({
      tierName: '',
      tierCode: '',
      description: '',
      availabilityTarget: 99.9,
      latencyTargetMs: 500,
      errorRateTarget: 1.0,
      monthlyAvailabilityTarget: 99.8,
      quarterlyAvailabilityTarget: 99.9,
      priorityLevel: 3,
      responseTimeSla: '',
      resolutionTimeSla: '',
      uptimeCreditPercent: 10,
      active: true,
    });
    setOpenDialog(true);
  };

  const handleOpenEdit = (tier) => {
    setEditingTier(tier);
    setFormData({ ...tier });
    setOpenDialog(true);
  };

  const handleSave = async () => {
    try {
      if (editingTier) {
        await slaTierApi.update(editingTier.id, formData);
      } else {
        await slaTierApi.create(formData);
      }
      setOpenDialog(false);
      fetchData();
    } catch (error) {
      console.error('Failed to save tier:', error);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('确定要删除此SLA等级吗？')) {
      try {
        await slaTierApi.delete(id);
        fetchData();
      } catch (error) {
        console.error('Failed to delete tier:', error);
      }
    }
  };

  if (loading) {
    return <LinearProgress />;
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">SLA 等级配置</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreate}
        >
          新增等级
        </Button>
      </Box>

      <Grid container spacing={3} mb={3}>
        {tiers.map((tier) => (
          <Grid item xs={12} md={6} lg={4} key={tier.id}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Box>
                    <Typography variant="h6">{tier.tierName}</Typography>
                    <Typography variant="caption" color="textSecondary">
                      {tier.tierCode}
                    </Typography>
                  </Box>
                  <Box display="flex">
                    {Array.from({ length: getTierStars(tier.priorityLevel) }).map((_, i) => (
                      <StarIcon key={i} color={getTierColor(tier.priorityLevel)} />
                    ))}
                  </Box>
                </Box>

                <Typography variant="body2" color="textSecondary" mb={2}>
                  {tier.description}
                </Typography>

                <Grid container spacing={2} mb={2}>
                  <Grid item xs={4}>
                    <Typography variant="caption" color="textSecondary">
                      可用性
                    </Typography>
                    <Typography variant="body1" fontWeight="bold">
                      {tier.availabilityTarget}%
                    </Typography>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="caption" color="textSecondary">
                      延迟目标
                    </Typography>
                    <Typography variant="body1" fontWeight="bold">
                      {tier.latencyTargetMs}ms
                    </Typography>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="caption" color="textSecondary">
                      错误率
                    </Typography>
                    <Typography variant="body1" fontWeight="bold">
                      {tier.errorRateTarget}%
                    </Typography>
                  </Grid>
                </Grid>

                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Chip
                    label={`${getServiceCountForTier(tier.id)} 个服务`}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                  <Box>
                    <IconButton size="small" onClick={() => handleOpenEdit(tier)}>
                      <EditIcon />
                    </IconButton>
                    <IconButton size="small" onClick={() => handleDelete(tier.id)} color="error">
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            服务等级分配
          </Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>服务名称</TableCell>
                  <TableCell>SLA等级</TableCell>
                  <TableCell>可用性目标</TableCell>
                  <TableCell>延迟目标</TableCell>
                  <TableCell>错误率目标</TableCell>
                  <TableCell>使用等级配置</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {services.map((service) => (
                  <TableRow key={service.id}>
                    <TableCell>{service.serviceName}</TableCell>
                    <TableCell>
                      {service.slaTier ? (
                        <Chip
                          label={service.slaTier.tierName}
                          color={getTierColor(service.slaTier.priorityLevel)}
                          size="small"
                        />
                      ) : (
                        <Chip label="未分配" size="small" />
                      )}
                    </TableCell>
                    <TableCell>{service.effectiveAvailabilityTarget || service.availabilityTarget}%</TableCell>
                    <TableCell>{service.effectiveLatencyTarget || service.latencyTargetMs}ms</TableCell>
                    <TableCell>{service.effectiveErrorRateTarget || service.errorRateTarget}%</TableCell>
                    <TableCell>
                      <Chip
                        label={service.useTierTargets ? '是' : '否'}
                        color={service.useTierTargets ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingTier ? '编辑SLA等级' : '新增SLA等级'}</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="等级名称"
                value={formData.tierName}
                onChange={(e) => setFormData({ ...formData, tierName: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="等级代码"
                value={formData.tierCode}
                onChange={(e) => setFormData({ ...formData, tierCode: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="描述"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                type="number"
                label="可用性目标 (%)"
                value={formData.availabilityTarget}
                onChange={(e) => setFormData({ ...formData, availabilityTarget: parseFloat(e.target.value) })}
                inputProps={{ step: '0.01' }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                type="number"
                label="延迟目标 (ms)"
                value={formData.latencyTargetMs}
                onChange={(e) => setFormData({ ...formData, latencyTargetMs: parseFloat(e.target.value) })}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                type="number"
                label="错误率目标 (%)"
                value={formData.errorRateTarget}
                onChange={(e) => setFormData({ ...formData, errorRateTarget: parseFloat(e.target.value) })}
                inputProps={{ step: '0.01' }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                type="number"
                label="月度可用性目标 (%)"
                value={formData.monthlyAvailabilityTarget}
                onChange={(e) => setFormData({ ...formData, monthlyAvailabilityTarget: parseFloat(e.target.value) })}
                inputProps={{ step: '0.01' }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                type="number"
                label="季度可用性目标 (%)"
                value={formData.quarterlyAvailabilityTarget}
                onChange={(e) => setFormData({ ...formData, quarterlyAvailabilityTarget: parseFloat(e.target.value) })}
                inputProps={{ step: '0.01' }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                type="number"
                label="优先级 (1-5, 1最高)"
                value={formData.priorityLevel}
                onChange={(e) => setFormData({ ...formData, priorityLevel: parseInt(e.target.value) })}
                inputProps={{ min: 1, max: 5 }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="响应时间SLA"
                value={formData.responseTimeSla}
                onChange={(e) => setFormData({ ...formData, responseTimeSla: e.target.value })}
                placeholder="例如: 15分钟"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="解决时间SLA"
                value={formData.resolutionTimeSla}
                onChange={(e) => setFormData({ ...formData, resolutionTimeSla: e.target.value })}
                placeholder="例如: 2小时"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                type="number"
                label="宕机赔偿比例 (%)"
                value={formData.uptimeCreditPercent}
                onChange={(e) => setFormData({ ...formData, uptimeCreditPercent: parseFloat(e.target.value) })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>取消</Button>
          <Button onClick={handleSave} variant="contained">
            保存
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default SlaTierConfig;
