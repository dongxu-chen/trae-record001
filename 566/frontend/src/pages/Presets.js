import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  PlayArrow,
  Search,
  NetworkCheck,
  Dns,
  Storage,
  Shuffle,
  Info,
  Timer,
  Warning,
} from '@mui/icons-material';
import { presetApi, faultApi, serviceApi } from '../services/api';

const categoryConfig = {
  network: {
    label: '网络故障',
    icon: <NetworkCheck />,
    color: 'primary',
  },
  service: {
    label: '服务故障',
    icon: <Dns />,
    color: 'secondary',
  },
  database: {
    label: '数据库故障',
    icon: <Storage />,
    color: 'warning',
  },
  chaos: {
    label: '混沌测试',
    icon: <Shuffle />,
    color: 'error',
  },
};

const severityColors = {
  low: 'success',
  medium: 'info',
  high: 'warning',
  critical: 'error',
};

const severityLabels = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '严重',
};

function Presets() {
  const [presets, setPresets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [applyDialogOpen, setApplyDialogOpen] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [targetService, setTargetService] = useState('');
  const [customName, setCustomName] = useState('');
  const [services, setServices] = useState([]);
  const [applying, setApplying] = useState(false);
  const [applySuccess, setApplySuccess] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  useEffect(() => {
    loadPresets();
    loadServices();
  }, []);

  const loadPresets = async () => {
    try {
      setLoading(true);
      const data = await presetApi.list();
      setPresets(data);
    } catch (error) {
      console.error('Failed to load presets:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadServices = async () => {
    try {
      const data = await serviceApi.list();
      setServices(data);
    } catch (error) {
      console.error('Failed to load services:', error);
    }
  };

  const handleCategoryChange = async (category) => {
    setSelectedCategory(category);
    try {
      setLoading(true);
      if (category === 'all') {
        const data = await presetApi.list();
        setPresets(data);
      } else {
        const data = await presetApi.listByCategory(category);
        setPresets(data);
      }
    } catch (error) {
      console.error('Failed to filter presets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    const keyword = e.target.value;
    setSearchKeyword(keyword);
    if (keyword.trim()) {
      try {
        const data = await presetApi.search(keyword);
        setPresets(data);
      } catch (error) {
        console.error('Failed to search presets:', error);
      }
    } else {
      loadPresets();
    }
  };

  const handleOpenApplyDialog = (preset) => {
    setSelectedPreset(preset);
    setCustomName(preset.name);
    setTargetService('');
    setApplySuccess(false);
    setApplyDialogOpen(true);
  };

  const handleApplyPreset = async () => {
    if (!targetService || !selectedPreset) return;

    try {
      setApplying(true);
      await presetApi.apply(selectedPreset.id, {
        target_service: targetService,
        custom_name: customName,
      });
      setApplySuccess(true);
      setTimeout(() => {
        setApplyDialogOpen(false);
      }, 1500);
    } catch (error) {
      console.error('Failed to apply preset:', error);
    } finally {
      setApplying(false);
    }
  };

  const getFaultTypeLabel = (type) => {
    const labels = {
      delay: '延迟故障',
      abort: '中断故障',
      error: '错误故障',
    };
    return labels[type] || type;
  };

  const renderPresetCard = (preset) => {
    const category = categoryConfig[preset.category] || categoryConfig.network;

    return (
      <Card key={preset.id} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <CardContent sx={{ flexGrow: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Box sx={{ mr: 1, color: `${category.color}.main` }}>
              {category.icon}
            </Box>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              {preset.name}
            </Typography>
            <Chip
              label={severityLabels[preset.severity]}
              size="small"
              color={severityColors[preset.severity]}
              sx={{ ml: 1 }}
            />
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, minHeight: 48 }}>
            {preset.description}
          </Typography>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
            {preset.tags?.map((tag) => (
              <Chip key={tag} label={tag} size="small" variant="outlined" />
            ))}
          </Box>

          <Divider sx={{ my: 1 }} />

          <Grid container spacing={1} sx={{ mt: 1 }}>
            <Grid item xs={6}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Dns fontSize="small" color="action" sx={{ mr: 0.5 }} />
                <Typography variant="caption" color="text.secondary">
                  {getFaultTypeLabel(preset.fault_config?.type)}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Timer fontSize="small" color="action" sx={{ mr: 0.5 }} />
                <Typography variant="caption" color="text.secondary">
                  {preset.estimated_duration_seconds}秒
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Warning fontSize="small" color="action" sx={{ mr: 0.5 }} />
                <Typography variant="caption" color="text.secondary">
                  影响 {preset.fault_config?.percentage}%
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Info fontSize="small" color="action" sx={{ mr: 0.5 }} />
                <Typography variant="caption" color="text.secondary">
                  {category.label}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>

        <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
          <Tooltip title="查看详情">
            <IconButton size="small" onClick={() => { setSelectedPreset(preset); setDetailDialogOpen(true); }}>
              <Info fontSize="small" />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            size="small"
            startIcon={<PlayArrow />}
            onClick={() => handleOpenApplyDialog(preset)}
          >
            一键注入
          </Button>
        </CardActions>
      </Card>
    );
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">故障场景库</Typography>
      </Box>

      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <TextField
          placeholder="搜索场景..."
          size="small"
          value={searchKeyword}
          onChange={handleSearch}
          InputProps={{
            startAdornment: <Search fontSize="small" color="action" />,
          }}
          sx={{ width: 300 }}
        />

        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>分类筛选</InputLabel>
          <Select
            value={selectedCategory}
            label="分类筛选"
            onChange={(e) => handleCategoryChange(e.target.value)}
          >
            <MenuItem value="all">全部</MenuItem>
            <MenuItem value="network">网络故障</MenuItem>
            <MenuItem value="service">服务故障</MenuItem>
            <MenuItem value="database">数据库故障</MenuItem>
            <MenuItem value="chaos">混沌测试</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {presets.map((preset) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={preset.id}>
              {renderPresetCard(preset)}
            </Grid>
          ))}
        </Grid>
      )}

      <Dialog open={applyDialogOpen} onClose={() => setApplyDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>应用故障场景</DialogTitle>
        <DialogContent>
          {applySuccess ? (
            <Alert severity="success" sx={{ mt: 2 }}>
              故障场景已成功创建！
            </Alert>
          ) : (
            <Box sx={{ pt: 2 }}>
              <Typography variant="subtitle1" sx={{ mb: 2 }}>
                场景：{selectedPreset?.name}
              </Typography>

              <TextField
                fullWidth
                label="自定义名称"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                sx={{ mb: 2 }}
              />

              <FormControl fullWidth>
                <InputLabel>目标服务</InputLabel>
                <Select
                  value={targetService}
                  label="目标服务"
                  onChange={(e) => setTargetService(e.target.value)}
                >
                  {services.map((svc) => (
                    <MenuItem key={svc} value={svc}>
                      {svc}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Alert severity="info" sx={{ mt: 2 }}>
                将为服务 "{targetService || '未选择'}" 创建此故障场景，包含智能回滚保护。
              </Alert>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApplyDialogOpen(false)} disabled={applying}>
            {applySuccess ? '关闭' : '取消'}
          </Button>
          {!applySuccess && (
            <Button
              variant="contained"
              onClick={handleApplyPreset}
              disabled={!targetService || applying}
            >
              {applying ? <CircularProgress size={20} /> : '确认应用'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      <Dialog open={detailDialogOpen} onClose={() => setDetailDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>场景详情</DialogTitle>
        <DialogContent dividers>
          {selectedPreset && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>
                {selectedPreset.name}
              </Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>
                {selectedPreset.description}
              </Typography>

              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">分类</Typography>
                  <Typography variant="body2">
                    {categoryConfig[selectedPreset.category]?.label || selectedPreset.category}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">严重程度</Typography>
                  <Chip
                    label={severityLabels[selectedPreset.severity]}
                    size="small"
                    color={severityColors[selectedPreset.severity]}
                  />
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">预计时长</Typography>
                  <Typography variant="body2">{selectedPreset.estimated_duration_seconds} 秒</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">影响比例</Typography>
                  <Typography variant="body2">{selectedPreset.fault_config?.percentage}%</Typography>
                </Grid>
              </Grid>

              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>标签</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {selectedPreset.tags?.map((tag) => (
                  <Chip key={tag} label={tag} size="small" />
                ))}
              </Box>

              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>故障配置</Typography>
              <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4, overflow: 'auto' }}>
                {JSON.stringify(selectedPreset.fault_config, null, 2)}
              </pre>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>关闭</Button>
          <Button
            variant="contained"
            startIcon={<PlayArrow />}
            onClick={() => {
              setDetailDialogOpen(false);
              handleOpenApplyDialog(selectedPreset);
            }}
          >
            一键注入
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Presets;
