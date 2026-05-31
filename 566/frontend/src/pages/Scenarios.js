import React, { useState, useEffect } from 'react';
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
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Grid,
  CircularProgress,
  Alert,
  Tooltip,
  Chip,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  List as ListIcon,
} from '@mui/icons-material';
import { scenarioApi, faultApi } from '../services/api';

function Scenarios() {
  const [scenarios, setScenarios] = useState([]);
  const [faults, setFaults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingScenario, setEditingScenario] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    fault_ids: [],
    steps: [],
  });
  const [selectedFault, setSelectedFault] = useState('');
  const [stepDelay, setStepDelay] = useState(0);
  const [stepDuration, setStepDuration] = useState(60);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [scenariosData, faultsData] = await Promise.all([
        scenarioApi.list(),
        faultApi.list(),
      ]);
      setScenarios(scenariosData);
      setFaults(faultsData);
    } catch (err) {
      setError('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (scenario = null) => {
    if (scenario) {
      setEditingScenario(scenario);
      setFormData({
        name: scenario.name,
        description: scenario.description,
        fault_ids: scenario.fault_ids || [],
        steps: scenario.steps || [],
      });
    } else {
      setEditingScenario(null);
      setFormData({
        name: '',
        description: '',
        fault_ids: [],
        steps: [],
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingScenario(null);
  };

  const handleAddStep = () => {
    if (selectedFault) {
      const newStep = {
        fault_id: selectedFault,
        delay_before_seconds: stepDelay,
        duration_seconds: stepDuration,
      };
      setFormData({
        ...formData,
        steps: [...formData.steps, newStep],
        fault_ids: [...formData.fault_ids, selectedFault],
      });
      setSelectedFault('');
      setStepDelay(0);
      setStepDuration(60);
    }
  };

  const handleRemoveStep = (index) => {
    const newSteps = formData.steps.filter((_, i) => i !== index);
    const newFaultIds = formData.fault_ids.filter((_, i) => i !== index);
    setFormData({
      ...formData,
      steps: newSteps,
      fault_ids: newFaultIds,
    });
  };

  const handleSubmit = async () => {
    try {
      if (editingScenario) {
        await scenarioApi.update(editingScenario.id, formData);
      } else {
        await scenarioApi.create(formData);
      }
      handleCloseDialog();
      loadData();
    } catch (err) {
      setError('保存失败');
    }
  };

  const handleExecute = async (id) => {
    try {
      await scenarioApi.execute(id);
      loadData();
    } catch (err) {
      setError('执行场景失败');
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('确定要删除此场景吗？')) {
      try {
        await scenarioApi.delete(id);
        loadData();
      } catch (err) {
        setError('删除失败');
      }
    }
  };

  const getFaultName = (faultId) => {
    const fault = faults.find((f) => f.id === faultId);
    return fault ? fault.name : faultId;
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">场景编排</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          创建场景
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
          <TableRow>
            <TableCell>名称</TableCell>
            <TableCell>描述</TableCell>
            <TableCell>步骤数</TableCell>
            <TableCell>创建时间</TableCell>
            <TableCell>操作</TableCell>
          </TableRow>
          </TableHead>
          <TableBody>
            {scenarios.map((scenario) => (
              <TableRow key={scenario.id}>
                <TableCell>
                  <Typography variant="body2" fontWeight="bold">
                    {scenario.name}
                  </Typography>
                </TableCell>
                <TableCell>{scenario.description}</TableCell>
                <TableCell>
                  <Chip label={`${scenario.steps?.length || 0} 步`} size="small" />
                </TableCell>
                <TableCell>
                  {new Date(scenario.created_at).toLocaleString()}
                </TableCell>
                <TableCell>
                  <Tooltip title="编辑">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(scenario)}
                    >
                      <EditIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="执行">
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={() => handleExecute(scenario.id)}
                    >
                      <PlayIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="删除">
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(scenario.id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {scenarios.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography color="text.secondary">暂无场景记录</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingScenario ? '编辑场景' : '创建场景'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="场景名称"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="描述"
                multiline
                rows={2}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                添加步骤
              </Typography>
              <Grid container spacing={2} alignItems="flex-end">
                <Grid item xs={12} sm={4}>
                  <FormControl fullWidth>
                    <InputLabel>选择故障</InputLabel>
                    <Select
                      value={selectedFault}
                      onChange={(e) => setSelectedFault(e.target.value)}
                      label="选择故障"
                    >
                      {faults.map((f) => (
                        <MenuItem key={f.id} value={f.id}>
                          {f.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    label="前置等待(秒)"
                    type="number"
                    value={stepDelay}
                    onChange={(e) => setStepDelay(parseInt(e.target.value) || 0)}
                  />
                </Grid>
                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    label="持续时间(秒)"
                    type="number"
                    value={stepDuration}
                    onChange={(e) => setStepDuration(parseInt(e.target.value) || 60)}
                  />
                </Grid>
                <Grid item xs={12} sm={2}>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={handleAddStep}
                    disabled={!selectedFault}
                  >
                    添加
                  </Button>
                </Grid>
              </Grid>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
                步骤列表 ({formData.steps.length} 步
              </Typography>
              {formData.steps.length === 0 ? (
                <Typography color="text.secondary">
                  暂无步骤，请添加故障步骤
                </Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>序号</TableCell>
                        <TableCell>故障</TableCell>
                        <TableCell>前置等待</TableCell>
                        <TableCell>持续时间</TableCell>
                        <TableCell>操作</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {formData.steps.map((step, index) => (
                        <TableRow key={index}>
                          <TableCell>{index + 1}</TableCell>
                          <TableCell>{getFaultName(step.fault_id)}</TableCell>
                          <TableCell>{step.delay_before_seconds} 秒</TableCell>
                          <TableCell>{step.duration_seconds} 秒</TableCell>
                          <TableCell>
                            <IconButton
                              size="small"
                              onClick={() => handleRemoveStep(index)}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>取消</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingScenario ? '保存' : '创建'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Scenarios;
