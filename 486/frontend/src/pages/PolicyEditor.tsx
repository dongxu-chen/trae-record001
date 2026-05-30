import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Alert,
  CircularProgress,
} from '@mui/material';
import { ArrowBack as ArrowBackIcon, Save as SaveIcon } from '@mui/icons-material';

import type { Policy, PolicyType } from '../types';
import { policyApi } from '../services/api';

const PolicyEditor: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id && id !== 'new';

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<Partial<Policy>>({
    name: '',
    type: 'mtls',
    namespace: 'default',
    description: '',
    status: 'active',
    spec: {},
  });

  useEffect(() => {
    if (isEdit && id) {
      loadPolicy(id);
    }
  }, [id, isEdit]);

  const loadPolicy = async (policyId: string) => {
    setLoading(true);
    try {
      const response = await policyApi.getPolicy(policyId);
      setFormData(response.data);
    } catch (error) {
      console.error('Failed to load policy:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      if (isEdit && id) {
        await policyApi.updatePolicy(id, formData);
      } else {
        const newPolicy = {
          ...formData,
          id: `policy-${Date.now()}`,
          created_by: 'admin',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        await policyApi.createPolicy(newPolicy as Policy);
      }
      navigate('/policies');
    } catch (error: any) {
      setError(error.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value });
  };

  const handleSpecChange = (field: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      spec: { ...prev.spec, [field]: value },
    }));
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/policies')}
          sx={{ mr: 2 }}
        >
          返回
        </Button>
        <Typography variant="h4">
          {isEdit ? '编辑策略' : '创建策略'}
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  基本信息
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="策略名称"
                      value={formData.name}
                      onChange={(e) => handleChange('name', e.target.value)}
                      required
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth>
                      <InputLabel>策略类型</InputLabel>
                      <Select
                        value={formData.type}
                        label="策略类型"
                        onChange={(e) => handleChange('type', e.target.value)}
                        required
                      >
                        <MenuItem value="mtls">mTLS 策略</MenuItem>
                        <MenuItem value="authorization">授权策略</MenuItem>
                        <MenuItem value="requestauth">请求认证</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="命名空间"
                      value={formData.namespace}
                      onChange={(e) => handleChange('namespace', e.target.value)}
                      required
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth>
                      <InputLabel>状态</InputLabel>
                      <Select
                        value={formData.status}
                        label="状态"
                        onChange={(e) => handleChange('status', e.target.value)}
                      >
                        <MenuItem value="active">活跃</MenuItem>
                        <MenuItem value="disabled">禁用</MenuItem>
                        <MenuItem value="pending">待发布</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      multiline
                      rows={3}
                      label="描述"
                      value={formData.description}
                      onChange={(e) => handleChange('description', e.target.value)}
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  策略配置
                </Typography>

                {formData.type === 'mtls' && (
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <FormControl fullWidth>
                        <InputLabel>mTLS 模式</InputLabel>
                        <Select
                          value={formData.spec?.mode || 'PERMISSIVE'}
                          label="mTLS 模式"
                          onChange={(e) => handleSpecChange('mode', e.target.value)}
                        >
                          <MenuItem value="DISABLE">DISABLE</MenuItem>
                          <MenuItem value="PERMISSIVE">PERMISSIVE</MenuItem>
                          <MenuItem value="STRICT">STRICT</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                  </Grid>
                )}

                {formData.type === 'authorization' && (
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <FormControl fullWidth>
                        <InputLabel>操作类型</InputLabel>
                        <Select
                          value={formData.spec?.action || 'ALLOW'}
                          label="操作类型"
                          onChange={(e) => handleSpecChange('action', e.target.value)}
                        >
                          <MenuItem value="ALLOW">ALLOW</MenuItem>
                          <MenuItem value="DENY">DENY</MenuItem>
                          <MenuItem value="AUDIT">AUDIT</MenuItem>
                          <MenuItem value="CUSTOM">CUSTOM</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        multiline
                        rows={6}
                        label="规则配置 (JSON)"
                        value={JSON.stringify(formData.spec?.rules || [], null, 2)}
                        onChange={(e) => {
                          try {
                            handleSpecChange('rules', JSON.parse(e.target.value));
                          } catch {}
                        }}
                      />
                    </Grid>
                  </Grid>
                )}

                {formData.type === 'requestauth' && (
                  <Grid container spacing={2}>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        label="JWT Issuer"
                        value={formData.spec?.issuer || ''}
                        onChange={(e) => handleSpecChange('issuer', e.target.value)}
                        placeholder="https://issuer.example.com"
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        label="JWKS URI"
                        value={formData.spec?.jwksUri || ''}
                        onChange={(e) => handleSpecChange('jwksUri', e.target.value)}
                        placeholder="https://issuer.example.com/.well-known/jwks.json"
                      />
                    </Grid>
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Audiences (逗号分隔)"
                      value={formData.spec?.audiences || ''}
                      onChange={(e) => handleSpecChange('audiences', e.target.value.split(','))}
                      placeholder="audience1,audience2"
                    />
                  </Grid>
                  </Grid>
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  操作
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    startIcon={<SaveIcon />}
                    disabled={saving}
                  >
                    {saving ? <CircularProgress size={20} sx={{ mr: 1 }} /> : null}
                    {isEdit ? '保存更改' : '创建策略'}
                  </Button>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={() => navigate('/policies')}
                  >
                    取消
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </form>
    </Box>
  );
};

export default PolicyEditor;
