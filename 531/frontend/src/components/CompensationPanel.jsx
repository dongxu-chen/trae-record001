import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
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
  Divider,
  Paper,
  Alert,
} from '@mui/material';
import {
  AttachMoney as AttachMoneyIcon,
  Check as CheckIcon,
  Done as DoneIcon,
  Add as AddIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { compensationApi, serviceApi } from '../services/api';

const severityColors = {
  MINOR: 'info',
  MODERATE: 'warning',
  SEVERE: 'error',
  CRITICAL: 'error',
};

const severityLabels = {
  MINOR: '轻微',
  MODERATE: '一般',
  SEVERE: '严重',
  CRITICAL: '致命',
};

const compensationTypeLabels = {
  SERVICE_CREDIT: '服务信用额度',
  EXTENDED_SUPPORT: '延长支持',
  UPGRADE_TIER: '升级等级',
  REFUND: '退款',
  CUSTOM: '自定义',
};

function CompensationPanel() {
  const [compensations, setCompensations] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [pendingCompensations, setPendingCompensations] = useState([]);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [openDialog, setOpenDialog] = useState(false);
  const [manualForm, setManualForm] = useState({
    serviceName: '',
    severity: 'MODERATE',
    reason: '',
  });

  useEffect(() => {
    fetchData();
  }, [filter]);

  const fetchData = async () => {
    try {
      const [compRes, statsRes, pendingRes, servicesRes] = await Promise.all([
        filter === 'pending' ? compensationApi.getPending() : compensationApi.getAll({ days: 30 }),
        compensationApi.getStatistics(),
        compensationApi.getPending(),
        serviceApi.getAll(),
      ]);

      setCompensations(compRes.data || []);
      setStatistics(statsRes.data);
      setPendingCompensations(pendingRes.data || []);
      setServices(servicesRes.data || []);
    } catch (error) {
      console.error('Failed to fetch compensation data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id) => {
    try {
      await compensationApi.approve(id, 'admin');
      fetchData();
    } catch (error) {
      console.error('Failed to approve compensation:', error);
    }
  };

  const handleResolve = async (id) => {
    try {
      await compensationApi.resolve(id);
      fetchData();
    } catch (error) {
      console.error('Failed to resolve compensation:', error);
    }
  };

  const handleCheckService = async (serviceName) => {
    try {
      await compensationApi.check(serviceName);
      fetchData();
    } catch (error) {
      console.error('Failed to check service:', error);
    }
  };

  const handleManualSubmit = async () => {
    try {
      await compensationApi.createManual(manualForm);
      setOpenDialog(false);
      setManualForm({ serviceName: '', severity: 'MODERATE', reason: '' });
      fetchData();
    } catch (error) {
      console.error('Failed to create manual compensation:', error);
    }
  };

  const displayedCompensations = filter === 'pending'
    ? pendingCompensations
    : compensations;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4">SLA 补偿建议</Typography>
          <Typography variant="subtitle1" color="textSecondary">
            SLA违规后自动生成补偿方案，支持审批和执行
          </Typography>
        </Box>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchData}
          >
            刷新
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenDialog(true)}
          >
            手动生成补偿
          </Button>
        </Box>
      </Box>

      {statistics && (
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      总补偿次数
                    </Typography>
                    <Typography variant="h4">
                      {statistics.totalCompensations}
                    </Typography>
                  </Box>
                  <AttachMoneyIcon sx={{ fontSize: 40, color: 'primary.main' }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      待审批
                    </Typography>
                    <Typography variant="h4" color="warning.main">
                      {statistics.pendingCompensations}
                    </Typography>
                  </Box>
                  <Chip
                    label={statistics.pendingCompensations > 0 ? '待处理' : '正常'}
                    color={statistics.pendingCompensations > 0 ? 'warning' : 'success'}
                    size="small"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      致命/严重违规
                    </Typography>
                    <Typography variant="h4" color="error.main">
                      {statistics.criticalViolations + statistics.severeViolations}
                    </Typography>
                  </Box>
                  <Chip
                    label="严重"
                    color="error"
                    size="small"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      累计赔偿比例
                    </Typography>
                    <Typography variant="h4" color="primary.main">
                      {statistics.totalCreditPercent?.toFixed(1)}%
                    </Typography>
                  </Box>
                  <AttachMoneyIcon sx={{ fontSize: 40, color: 'success.main' }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" gap={2} flexWrap="wrap">
          <Button
            variant={filter === 'all' ? 'contained' : 'outlined'}
            onClick={() => setFilter('all')}
          >
            全部补偿
          </Button>
          <Button
            variant={filter === 'pending' ? 'contained' : 'outlined'}
            onClick={() => setFilter('pending')}
          >
            待审批 ({pendingCompensations.length})
          </Button>
          {services.map((service) => (
            <Button
              key={service.serviceName}
              variant="outlined"
              onClick={() => handleCheckService(service.serviceName)}
              size="small"
            >
              检查 {service.serviceName}
            </Button>
          ))}
        </Box>
      </Paper>

      {pendingCompensations.length > 0 && filter === 'all' && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          有 {pendingCompensations.length} 条补偿建议等待审批
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>服务名称</TableCell>
              <TableCell>违规等级</TableCell>
              <TableCell>补偿类型</TableCell>
              <TableCell>可用性缺口</TableCell>
              <TableCell>预计宕机</TableCell>
              <TableCell>赔偿比例</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>创建时间</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {displayedCompensations.map((comp) => (
              <TableRow key={comp.id} hover>
                <TableCell>
                  <Box>
                    <Typography fontWeight="bold">{comp.serviceName}</Typography>
                    {comp.slaTier && (
                      <Typography variant="caption" color="textSecondary">
                        {comp.slaTier.tierName}
                      </Typography>
                    )}
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    label={severityLabels[comp.violationSeverity]}
                    color={severityColors[comp.violationSeverity]}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {compensationTypeLabels[comp.compensationType]}
                </TableCell>
                <TableCell>
                  <Typography color="error">
                    -{comp.availabilityDeficit?.toFixed(2)}%
                  </Typography>
                </TableCell>
                <TableCell>
                  {comp.downtimeMinutes?.toFixed(1)} 分钟
                </TableCell>
                <TableCell>
                  <Typography color="primary" fontWeight="bold">
                    {comp.creditPercent?.toFixed(1)}%
                  </Typography>
                </TableCell>
                <TableCell>
                  {comp.approved ? (
                    <Chip icon={<CheckIcon />} label="已审批" color="success" size="small" />
                  ) : (
                    <Chip label="待审批" color="warning" size="small" />
                  )}
                  {comp.resolvedAt && (
                    <Chip icon={<DoneIcon />} label="已执行" color="info" size="small" sx={{ ml: 1 }} />
                  )}
                </TableCell>
                <TableCell>
                  {new Date(comp.createdAt).toLocaleString('zh-CN')}
                </TableCell>
                <TableCell>
                  {!comp.approved && (
                    <IconButton
                      color="success"
                      size="small"
                      onClick={() => handleApprove(comp.id)}
                      title="批准"
                    >
                      <CheckIcon />
                    </IconButton>
                  )}
                  {comp.approved && !comp.resolvedAt && (
                    <IconButton
                      color="primary"
                      size="small"
                      onClick={() => handleResolve(comp.id)}
                      title="执行完成"
                    >
                      <DoneIcon />
                    </IconButton>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>手动生成补偿</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel>选择服务</InputLabel>
              <Select
                value={manualForm.serviceName}
                label="选择服务"
                onChange={(e) => setManualForm({ ...manualForm, serviceName: e.target.value })}
              >
                {services.map((s) => (
                  <MenuItem key={s.serviceName} value={s.serviceName}>
                    {s.serviceName}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>违规等级</InputLabel>
              <Select
                value={manualForm.severity}
                label="违规等级"
                onChange={(e) => setManualForm({ ...manualForm, severity: e.target.value })}
              >
                {Object.entries(severityLabels).map(([key, label]) => (
                  <MenuItem key={key} value={key}>{label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              fullWidth
              multiline
              rows={3}
              label="补偿原因"
              value={manualForm.reason}
              onChange={(e) => setManualForm({ ...manualForm, reason: e.target.value })}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>取消</Button>
          <Button variant="contained" onClick={handleManualSubmit}>生成</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default CompensationPanel;
