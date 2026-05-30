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
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  AccountTree as AccountTreeIcon,
  Warning as WarningIcon,
  ArrowForward as ArrowForwardIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Search as SearchIcon,
  TrendingDown as TrendingDownIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material';
import { dependencyApi, serviceApi } from '../services/api';

const impactColors = {
  CRITICAL: 'error',
  HIGH: 'warning',
  MEDIUM: 'info',
  LOW: 'success',
  INFORMATIONAL: 'success',
};

const impactLabels = {
  CRITICAL: '关键',
  HIGH: '高',
  MEDIUM: '中',
  LOW: '低',
  INFORMATIONAL: '信息',
};

const dependencyTypeLabels = {
  SYNCHRONOUS: '同步调用',
  ASYNCHRONOUS: '异步调用',
  DATABASE: '数据库',
  CACHE: '缓存',
  MESSAGE_QUEUE: '消息队列',
  EXTERNAL_API: '外部API',
  STORAGE: '存储',
};

const riskColors = {
  CRITICAL: 'error',
  HIGH: 'warning',
  WARNING: 'warning',
  NORMAL: 'success',
};

function DependencyGraph() {
  const [dependencies, setDependencies] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [riskAnalysis, setRiskAnalysis] = useState(null);
  const [services, setServices] = useState([]);
  const [selectedService, setSelectedService] = useState('');
  const [serviceDeps, setServiceDeps] = useState(null);
  const [propagationResult, setPropagationResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [newDependency, setNewDependency] = useState({
    downstreamService: '',
    upstreamService: '',
    dependencyType: 'SYNCHRONOUS',
    impactLevel: 'MEDIUM',
    slaImpactFactor: 1.0,
    description: '',
  });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (selectedService) {
      fetchServiceDependencies();
    }
  }, [selectedService]);

  const fetchData = async () => {
    try {
      const [depsRes, graphRes, riskRes, servicesRes] = await Promise.all([
        dependencyApi.getAll(),
        dependencyApi.getGraph(),
        dependencyApi.getRiskAnalysis(),
        serviceApi.getAll(),
      ]);

      setDependencies(depsRes.data || []);
      setGraphData(graphRes.data || { nodes: [], edges: [] });
      setRiskAnalysis(riskRes.data);
      setServices(servicesRes.data || []);
    } catch (error) {
      console.error('Failed to fetch dependency data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchServiceDependencies = async () => {
    try {
      const [depsRes, propagationRes] = await Promise.all([
        dependencyApi.getByService(selectedService),
        dependencyApi.analyze(selectedService),
      ]);

      setServiceDeps(depsRes.data);
      setPropagationResult(propagationRes.data);
    } catch (error) {
      console.error('Failed to fetch service dependencies:', error);
    }
  };

  const handleAddDependency = async () => {
    try {
      await dependencyApi.add(newDependency);
      setOpenAddDialog(false);
      setNewDependency({
        downstreamService: '',
        upstreamService: '',
        dependencyType: 'SYNCHRONOUS',
        impactLevel: 'MEDIUM',
        slaImpactFactor: 1.0,
        description: '',
      });
      fetchData();
    } catch (error) {
      console.error('Failed to add dependency:', error);
    }
  };

  const handleRemoveDependency = async (id) => {
    try {
      await dependencyApi.remove(id);
      fetchData();
      if (selectedService) {
        fetchServiceDependencies();
      }
    } catch (error) {
      console.error('Failed to remove dependency:', error);
    }
  };

  const renderDependencyGraph = () => {
    const nodes = graphData.nodes || [];
    const edges = graphData.edges || [];

    const nodePositions = {};
    const spacing = 150;
    const centerX = 300;
    const centerY = 200;

    nodes.forEach((node, index) => {
      const angle = (index / nodes.length) * 2 * Math.PI - Math.PI / 2;
      nodePositions[node] = {
        x: centerX + Math.cos(angle) * spacing,
        y: centerY + Math.sin(angle) * spacing,
      };
    });

    return (
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          服务依赖关系图
        </Typography>
        <svg width="600" height="400" viewBox="0 0 600 400">
          {edges.map((edge, index) => {
            const from = nodePositions[edge.from];
            const to = nodePositions[edge.to];
            if (!from || !to) return null;

            const midX = (from.x + to.x) / 2;
            const midY = (from.y + to.y) / 2;

            const strokeColor = edge.impact === 'CRITICAL' ? '#f44336' :
              edge.impact === 'HIGH' ? '#ff9800' : '#2196f3';

            return (
              <g key={index}>
                <line
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke={strokeColor}
                  strokeWidth={parseFloat(edge.weight) * 3}
                  markerEnd="url(#arrowhead)"
                />
                <circle cx={midX} cy={midY} r="10" fill="white" stroke={strokeColor} />
                <text
                  x={midX}
                  y={midY + 4}
                  textAnchor="middle"
                  fontSize="10"
                  fill={strokeColor}
                >
                  {edge.weight}
                </text>
              </g>
            );
          })}

          {nodes.map((node) => {
            const pos = nodePositions[node];
            if (!pos) return null;

            return (
              <g key={node}>
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r="40"
                  fill="#3f51b5"
                  stroke="white"
                  strokeWidth="3"
                />
                <text
                  x={pos.x}
                  y={pos.y + 5}
                  textAnchor="middle"
                  fill="white"
                  fontSize="12"
                  fontWeight="bold"
                >
                  {node.replace('-service', '')}
                </text>
              </g>
            );
          })}

          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#999" />
            </marker>
          </defs>
        </svg>

        <Box display="flex" gap={2} mt={2} flexWrap="wrap">
          <Box display="flex" alignItems="center" gap={1}>
            <Box width={12} height={12} bgcolor="error.main" />
            <Typography variant="caption">关键影响</Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Box width={12} height={12} bgcolor="warning.main" />
            <Typography variant="caption">高影响</Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Box width={12} height={12} bgcolor="primary.main" />
            <Typography variant="caption">中/低影响</Typography>
          </Box>
        </Box>
      </Paper>
    );
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4">服务依赖</Typography>
          <Typography variant="subtitle1" color="textSecondary">
            管理服务依赖关系，分析SLA传导影响
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
            onClick={() => setOpenAddDialog(true)}
          >
            添加依赖
          </Button>
        </Box>
      </Box>

      {riskAnalysis && riskAnalysis.criticalDependencies > 0 && (
        <Alert severity="error" icon={<WarningIcon />} sx={{ mb: 3 }}>
          检测到 {riskAnalysis.criticalDependencies} 个关键服务依赖，需要重点关注
        </Alert>
      )}

      {riskAnalysis && (
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      总依赖数
                    </Typography>
                    <Typography variant="h4">{riskAnalysis.totalDependencies}</Typography>
                  </Box>
                  <AccountTreeIcon sx={{ fontSize: 40, color: 'primary.main' }} />
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
                      关键依赖
                    </Typography>
                    <Typography variant="h4" color="error.main">
                      {riskAnalysis.criticalDependencies}
                    </Typography>
                  </Box>
                  <WarningIcon sx={{ fontSize: 40, color: 'error.main' }} />
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
                      高影响依赖
                    </Typography>
                    <Typography variant="h4" color="warning.main">
                      {riskAnalysis.highImpactDependencies}
                    </Typography>
                  </Box>
                  <TrendingUpIcon sx={{ fontSize: 40, color: 'warning.main' }} />
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
                      节点数
                    </Typography>
                    <Typography variant="h4" color="primary.main">
                      {graphData.nodes?.length || 0}
                    </Typography>
                  </Box>
                  <AccountTreeIcon sx={{ fontSize: 40, color: 'info.main' }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {renderDependencyGraph()}

      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" gap={2} flexWrap="wrap" alignItems="center">
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>选择服务分析</InputLabel>
            <Select
              value={selectedService}
              label="选择服务分析"
              onChange={(e) => setSelectedService(e.target.value)}
              startAdornment={<SearchIcon sx={{ mr: 1, color: 'action.active' }} />}
            >
              {services.map((s) => (
                <MenuItem key={s.serviceName} value={s.serviceName}>
                  {s.serviceName}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {selectedService && (
            <Button
              variant="contained"
              onClick={fetchServiceDependencies}
              startIcon={<TrendingDownIcon />}
            >
              分析传导风险
            </Button>
          )}
        </Box>
      </Paper>

      {propagationResult && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              SLA传导分析结果 - {selectedService}
            </Typography>

            <Grid container spacing={2} mb={2}>
              <Grid item xs={12} md={4}>
                <Box textAlign="center">
                  <Typography variant="h4" color={riskColors[propagationResult.overallRiskLevel]}>
                    {propagationResult.overallRiskLevel === 'CRITICAL' ? '危急' :
                     propagationResult.overallRiskLevel === 'HIGH' ? '高风险' :
                     propagationResult.overallRiskLevel === 'WARNING' ? '警告' : '正常'}
                  </Typography>
                  <Typography variant="caption" color="textSecondary">整体风险等级</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={4}>
                <Box textAlign="center">
                  <Typography variant="h4" color="error">
                    -{propagationResult.combinedAvailabilityImpact?.toFixed(2)}%
                  </Typography>
                  <Typography variant="caption" color="textSecondary">可用性传导影响</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={4}>
                <Box textAlign="center">
                  <Typography variant="h4" color="warning">
                    +{propagationResult.combinedLatencyImpact?.toFixed(1)}%
                  </Typography>
                  <Typography variant="caption" color="textSecondary">延迟传导影响</Typography>
                </Box>
              </Grid>
            </Grid>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" gutterBottom>建议措施</Typography>
            <List dense>
              {propagationResult.recommendations?.map((rec, idx) => (
                <ListItem key={idx}>
                  <ListItemIcon>
                    <ArrowForwardIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText primary={rec} />
                </ListItem>
              ))}
            </List>

            {propagationResult.dependencyImpacts && propagationResult.dependencyImpacts.length > 0 && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" gutterBottom>上游依赖影响详情</Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>上游服务</TableCell>
                      <TableCell>依赖类型</TableCell>
                      <TableCell>影响等级</TableCell>
                      <TableCell>可用性影响</TableCell>
                      <TableCell>延迟影响</TableCell>
                      <TableCell>错误率影响</TableCell>
                      <TableCell>风险状态</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {propagationResult.dependencyImpacts.map((impact, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{impact.upstreamService}</TableCell>
                        <TableCell>{dependencyTypeLabels[impact.dependencyType]}</TableCell>
                        <TableCell>
                          <Chip
                            label={impactLabels[impact.impactLevel]}
                            color={impactColors[impact.impactLevel]}
                            size="small"
                          />
                        </TableCell>
                        <TableCell color="error">-{impact.availabilityImpact?.toFixed(2)}%</TableCell>
                        <TableCell color="warning">+{impact.latencyImpact?.toFixed(1)}%</TableCell>
                        <TableCell color="error">+{impact.errorRateImpact?.toFixed(2)}%</TableCell>
                        <TableCell>
                          {impact.criticalViolation ? (
                            <Chip label="有风险" color="error" size="small" />
                          ) : (
                            <Chip label="正常" color="success" size="small" />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </>
            )}
          </CardContent>
        </Card>
      )}

      <Typography variant="h6" gutterBottom>
        所有依赖关系
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>下游服务</TableCell>
              <TableCell>上游服务</TableCell>
              <TableCell>依赖类型</TableCell>
              <TableCell>影响等级</TableCell>
              <TableCell>SLA影响系数</TableCell>
              <TableCell>描述</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {dependencies.map((dep) => (
              <TableRow key={dep.id} hover>
                <TableCell>
                  <Typography fontWeight="bold">{dep.downstreamService}</Typography>
                </TableCell>
                <TableCell>
                  <Box display="flex" alignItems="center" gap={1}>
                    <ArrowForwardIcon color="action" fontSize="small" />
                    <Typography>{dep.upstreamService}</Typography>
                  </Box>
                </TableCell>
                <TableCell>{dependencyTypeLabels[dep.dependencyType]}</TableCell>
                <TableCell>
                  <Chip
                    label={impactLabels[dep.impactLevel]}
                    color={impactColors[dep.impactLevel]}
                    size="small"
                  />
                </TableCell>
                <TableCell>{dep.slaImpactFactor}</TableCell>
                <TableCell>{dep.description}</TableCell>
                <TableCell>
                  <IconButton
                    color="error"
                    size="small"
                    onClick={() => handleRemoveDependency(dep.id)}
                    title="删除"
                  >
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openAddDialog} onClose={() => setOpenAddDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>添加服务依赖</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel>下游服务（依赖方）</InputLabel>
              <Select
                value={newDependency.downstreamService}
                label="下游服务（依赖方）"
                onChange={(e) => setNewDependency({ ...newDependency, downstreamService: e.target.value })}
              >
                {services.map((s) => (
                  <MenuItem key={s.serviceName} value={s.serviceName}>
                    {s.serviceName}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>上游服务（被依赖方）</InputLabel>
              <Select
                value={newDependency.upstreamService}
                label="上游服务（被依赖方）"
                onChange={(e) => setNewDependency({ ...newDependency, upstreamService: e.target.value })}
              >
                {services.map((s) => (
                  <MenuItem key={s.serviceName} value={s.serviceName}>
                    {s.serviceName}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>依赖类型</InputLabel>
              <Select
                value={newDependency.dependencyType}
                label="依赖类型"
                onChange={(e) => setNewDependency({ ...newDependency, dependencyType: e.target.value })}
              >
                {Object.entries(dependencyTypeLabels).map(([key, label]) => (
                  <MenuItem key={key} value={key}>{label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>影响等级</InputLabel>
              <Select
                value={newDependency.impactLevel}
                label="影响等级"
                onChange={(e) => setNewDependency({ ...newDependency, impactLevel: e.target.value })}
              >
                {Object.entries(impactLabels).map(([key, label]) => (
                  <MenuItem key={key} value={key}>{label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              fullWidth
              type="number"
              label="SLA影响系数"
              value={newDependency.slaImpactFactor}
              onChange={(e) => setNewDependency({ ...newDependency, slaImpactFactor: parseFloat(e.target.value) })}
              inputProps={{ step: 0.1, min: 0, max: 2 }}
            />
            <TextField
              fullWidth
              multiline
              rows={2}
              label="描述"
              value={newDependency.description}
              onChange={(e) => setNewDependency({ ...newDependency, description: e.target.value })}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAddDialog(false)}>取消</Button>
          <Button variant="contained" onClick={handleAddDependency}>添加</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default DependencyGraph;
