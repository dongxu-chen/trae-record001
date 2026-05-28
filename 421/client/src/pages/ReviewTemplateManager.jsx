import React, { useState, useEffect } from 'react';
import { 
  Container, Typography, Box, Button, Grid, Card, CardContent, 
  CardActions, Chip, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, MenuItem, Select, FormControl, InputLabel, IconButton,
  List, ListItem, ListItemText, Divider, Switch, FormControlLabel,
  Accordion, AccordionSummary, AccordionDetails, Alert
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PlaylistAddCheckIcon from '@mui/icons-material/PlaylistAddCheck';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const ReviewTemplateManager = () => {
  const { user } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: 'general',
    rules: [],
    checkpoints: [],
    settings: {
      autoCheck: true,
      checkOnSubmit: true,
      requireAllCheckpoints: false,
      maxSuggestions: 50,
      minConfidence: 0.5
    }
  });
  const [error, setError] = useState('');

  useEffect(() => {
    loadTemplates();
    initDefaultTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const res = await api.get('/api/templates');
      setTemplates(res.data);
    } catch (err) {
      console.error('Load templates error:', err);
    }
  };

  const initDefaultTemplates = async () => {
    try {
      await api.post('/api/templates/init-defaults');
    } catch (err) {
      console.error('Init defaults error:', err);
    }
  };

  const handleOpenCreate = () => {
    setEditingTemplate(null);
    setFormData({
      name: '',
      description: '',
      category: 'general',
      rules: [],
      checkpoints: [],
      settings: {
        autoCheck: true,
        checkOnSubmit: true,
        requireAllCheckpoints: false,
        maxSuggestions: 50,
        minConfidence: 0.5
      }
    });
    setOpenDialog(true);
  };

  const handleOpenEdit = (template) => {
    setEditingTemplate(template);
    setFormData({
      name: template.name,
      description: template.description,
      category: template.category,
      rules: [...template.rules],
      checkpoints: [...template.checkpoints],
      settings: { ...template.settings }
    });
    setOpenDialog(true);
  };

  const handleSave = async () => {
    try {
      setError('');
      
      if (!formData.name.trim()) {
        setError('请输入模板名称');
        return;
      }

      if (editingTemplate) {
        await api.put(`/api/templates/${editingTemplate._id}`, formData);
      } else {
        await api.post('/api/templates', formData);
      }
      
      setOpenDialog(false);
      loadTemplates();
    } catch (err) {
      setError(err.response?.data?.message || '保存失败');
    }
  };

  const handleDelete = async (templateId) => {
    if (!window.confirm('确定要删除这个模板吗？')) return;
    
    try {
      await api.delete(`/api/templates/${templateId}`);
      loadTemplates();
    } catch (err) {
      console.error('Delete template error:', err);
    }
  };

  const handleDuplicate = async (templateId) => {
    try {
      await api.post(`/api/templates/${templateId}/duplicate`);
      loadTemplates();
    } catch (err) {
      console.error('Duplicate template error:', err);
    }
  };

  const addRule = () => {
    const newRule = {
      id: `rule_${Date.now()}`,
      name: '新规则',
      description: '',
      category: 'custom',
      severity: 'medium',
      pattern: '',
      patternType: 'keyword',
      suggestedFix: '',
      enabled: true,
      priority: formData.rules.length + 1
    };
    setFormData(prev => ({
      ...prev,
      rules: [...prev.rules, newRule]
    }));
  };

  const updateRule = (index, updates) => {
    setFormData(prev => ({
      ...prev,
      rules: prev.rules.map((r, i) => i === index ? { ...r, ...updates } : r)
    }));
  };

  const removeRule = (index) => {
    setFormData(prev => ({
      ...prev,
      rules: prev.rules.filter((_, i) => i !== index)
    }));
  };

  const addCheckpoint = () => {
    const newCheckpoint = {
      id: `cp_${Date.now()}`,
      name: '新检查点',
      description: '',
      required: false
    };
    setFormData(prev => ({
      ...prev,
      checkpoints: [...prev.checkpoints, newCheckpoint]
    }));
  };

  const updateCheckpoint = (index, updates) => {
    setFormData(prev => ({
      ...prev,
      checkpoints: prev.checkpoints.map((c, i) => i === index ? { ...c, ...updates } : c)
    }));
  };

  const removeCheckpoint = (index) => {
    setFormData(prev => ({
      ...prev,
      checkpoints: prev.checkpoints.filter((_, i) => i !== index)
    }));
  };

  const categoryLabels = {
    general: '通用',
    technical: '技术',
    legal: '法律',
    academic: '学术',
    business: '商务',
    marketing: '营销',
    custom: '自定义'
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4">
          <PlaylistAddCheckIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          审核模板管理
        </Typography>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />}
          onClick={handleOpenCreate}
        >
          创建模板
        </Button>
      </Box>

      <Grid container spacing={3}>
        {templates.map((template) => (
          <Grid item xs={12} md={6} lg={4} key={template._id}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box display="flex" justifyContent="space-between" alignItems="start">
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      {template.name}
                      {template.isDefault && (
                        <Chip 
                          label="默认" 
                          size="small" 
                          color="primary" 
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {template.description || '暂无描述'}
                    </Typography>
                  </Box>
                  <Chip 
                    label={categoryLabels[template.category]} 
                    size="small" 
                    color={template.category === 'general' ? 'default' : 'primary'}
                  />
                </Box>

                <Box mt={2}>
                  <Typography variant="body2" color="text.secondary">
                    规则数量: {template.rules.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    检查点: {template.checkpoints.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    使用次数: {template.usageCount || 0}
                  </Typography>
                </Box>

                {template.rules.length > 0 && (
                  <Box mt={2}>
                    <Typography variant="caption" color="text.secondary">
                      规则:
                    </Typography>
                    <Box display="flex" gap={0.5} flexWrap="wrap" mt={0.5}>
                      {template.rules.slice(0, 5).map((rule, idx) => (
                        <Chip 
                          key={idx} 
                          label={rule.name} 
                          size="small" 
                          variant="outlined"
                        />
                      ))}
                      {template.rules.length > 5 && (
                        <Chip 
                          label={`+${template.rules.length - 5}`} 
                          size="small"
                        />
                      )}
                    </Box>
                  </Box>
                )}
              </CardContent>
              <CardActions>
                <IconButton 
                  size="small" 
                  onClick={() => handleOpenEdit(template)}
                  title="编辑"
                >
                  <EditIcon />
                </IconButton>
                <IconButton 
                  size="small" 
                  onClick={() => handleDuplicate(template._id)}
                  title="复制"
                >
                  <ContentCopyIcon />
                </IconButton>
                {!template.isDefault && template.author?._id === user?.id && (
                  <IconButton 
                    size="small" 
                    color="error"
                    onClick={() => handleDelete(template._id)}
                    title="删除"
                  >
                    <DeleteIcon />
                  </IconButton>
                )}
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog 
        open={openDialog} 
        onClose={() => setOpenDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingTemplate ? '编辑模板' : '创建模板'}
        </DialogTitle>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          
          <TextField
            fullWidth
            label="模板名称"
            value={formData.name}
            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
            sx={{ mb: 2 }}
          />
          
          <TextField
            fullWidth
            label="描述"
            value={formData.description}
            onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
            multiline
            rows={2}
            sx={{ mb: 2 }}
          />
          
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>类别</InputLabel>
            <Select
              value={formData.category}
              label="类别"
              onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
            >
              {Object.entries(categoryLabels).map(([key, label]) => (
                <MenuItem key={key} value={key}>{label}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <Divider sx={{ my: 2 }} />

          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">审核规则</Typography>
            <Button size="small" startIcon={<AddIcon />} onClick={addRule}>
              添加规则
            </Button>
          </Box>

          {formData.rules.map((rule, index) => (
            <Accordion key={rule.id} sx={{ mb: 1 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>规则 {index + 1}: {rule.name}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      size="small"
                      label="规则名称"
                      value={rule.name}
                      onChange={(e) => updateRule(index, { name: e.target.value })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth size="small">
                      <InputLabel>类别</InputLabel>
                      <Select
                        value={rule.category}
                        label="类别"
                        onChange={(e) => updateRule(index, { category: e.target.value })}
                      >
                        <MenuItem value="spelling">拼写</MenuItem>
                        <MenuItem value="grammar">语法</MenuItem>
                        <MenuItem value="punctuation">标点</MenuItem>
                        <MenuItem value="style">风格</MenuItem>
                        <MenuItem value="clarity">清晰度</MenuItem>
                        <MenuItem value="format">格式</MenuItem>
                        <MenuItem value="consistency">一致性</MenuItem>
                        <MenuItem value="terminology">术语</MenuItem>
                        <MenuItem value="custom">自定义</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth size="small">
                      <InputLabel>严重程度</InputLabel>
                      <Select
                        value={rule.severity}
                        label="严重程度"
                        onChange={(e) => updateRule(index, { severity: e.target.value })}
                      >
                        <MenuItem value="low">低</MenuItem>
                        <MenuItem value="medium">中</MenuItem>
                        <MenuItem value="high">高</MenuItem>
                        <MenuItem value="critical">严重</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      size="small"
                      label="描述"
                      value={rule.description}
                      onChange={(e) => updateRule(index, { description: e.target.value })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={8}>
                    <TextField
                      fullWidth
                      size="small"
                      label="匹配模式"
                      value={rule.pattern}
                      onChange={(e) => updateRule(index, { pattern: e.target.value })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <FormControl fullWidth size="small">
                      <InputLabel>模式类型</InputLabel>
                      <Select
                        value={rule.patternType}
                        label="模式类型"
                        onChange={(e) => updateRule(index, { patternType: e.target.value })}
                      >
                        <MenuItem value="keyword">关键词</MenuItem>
                        <MenuItem value="regex">正则表达式</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      size="small"
                      label="建议修改"
                      value={rule.suggestedFix}
                      onChange={(e) => updateRule(index, { suggestedFix: e.target.value })}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <FormControlLabel
                        control={
                          <Switch
                            checked={rule.enabled}
                            onChange={(e) => updateRule(index, { enabled: e.target.checked })}
                          />
                        }
                        label="启用"
                      />
                      <Button 
                        size="small" 
                        color="error"
                        onClick={() => removeRule(index)}
                      >
                        删除
                      </Button>
                    </Box>
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>
          ))}

          <Divider sx={{ my: 2 }} />

          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">检查点</Typography>
            <Button size="small" startIcon={<AddIcon />} onClick={addCheckpoint}>
              添加检查点
            </Button>
          </Box>

          {formData.checkpoints.map((checkpoint, index) => (
            <Box key={checkpoint.id} sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    size="small"
                    label="检查点名称"
                    value={checkpoint.name}
                    onChange={(e) => updateCheckpoint(index, { name: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    size="small"
                    label="描述"
                    value={checkpoint.description}
                    onChange={(e) => updateCheckpoint(index, { description: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <Box display="flex" justifyContent="space-between">
                    <FormControlLabel
                      control={
                        <Switch
                          checked={checkpoint.required}
                          onChange={(e) => updateCheckpoint(index, { required: e.target.checked })}
                        />
                      }
                      label="必须通过"
                    />
                    <Button 
                      size="small" 
                      color="error"
                      onClick={() => removeCheckpoint(index)}
                    >
                      删除
                    </Button>
                  </Box>
                </Grid>
              </Grid>
            </Box>
          ))}

          <Divider sx={{ my: 2 }} />

          <Typography variant="h6" mb={2}>高级设置</Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.settings.autoCheck}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      settings: { ...prev.settings, autoCheck: e.target.checked }
                    }))}
                  />
                }
                label="自动检查"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.settings.checkOnSubmit}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      settings: { ...prev.settings, checkOnSubmit: e.target.checked }
                    }))}
                  />
                }
                label="提交时检查"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.settings.requireAllCheckpoints}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      settings: { ...prev.settings, requireAllCheckpoints: e.target.checked }
                    }))}
                  />
                }
                label="要求所有检查点通过"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="最大建议数"
                value={formData.settings.maxSuggestions}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  settings: { ...prev.settings, maxSuggestions: parseInt(e.target.value) }
                }))}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="最小置信度 (0-1)"
                inputProps={{ min: 0, max: 1, step: 0.1 }}
                value={formData.settings.minConfidence}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  settings: { ...prev.settings, minConfidence: parseFloat(e.target.value) }
                }))}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>取消</Button>
          <Button onClick={handleSave} variant="contained">
            {editingTemplate ? '保存' : '创建'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ReviewTemplateManager;
