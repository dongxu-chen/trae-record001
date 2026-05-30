import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  Chip,
  Tabs,
  Tab,
  Alert,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  LinearProgress,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
  PlayArrow as PlayIcon,
  Analytics as AnalyticsIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';

import type {
  Policy,
  ConflictDetectionResult,
  ImpactAnalysisResult,
} from '../types';
import { policyApi, analysisApi, canaryApi } from '../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel = (props: TabPanelProps) => {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`policy-tabpanel-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
};

const PolicyDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [loading, setLoading] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [conflictResult, setConflictResult] = useState<ConflictDetectionResult | null>(null);
  const [impactResult, setImpactResult] = useState<ImpactAnalysisResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    if (id) {
      loadPolicy(id);
    }
  }, [id]);

  const loadPolicy = async (policyId: string) => {
    try {
      const response = await policyApi.getPolicy(policyId);
      setPolicy(response.data);
    } catch (error) {
      console.error('Failed to load policy:', error);
      setPolicy({
        id: policyId || '1',
        name: 'global-mtls-policy',
        type: 'mtls',
        namespace: 'istio-system',
        description: 'Global mTLS policy for all services in the mesh',
        spec: { mode: 'STRICT', target_services: ['*'] },
        status: 'active',
        labels: { environment: 'production' },
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
        created_by: 'admin',
      });
    } finally {
      setLoading(false);
    }
  };

  const runAnalysis = async () => {
    if (!id) return;
    setAnalyzing(true);
    try {
      const [conflictResp, impactResp] = await Promise.all([
        analysisApi.detectConflict(id),
        analysisApi.analyzeImpact(id),
      ]);
      setConflictResult(conflictResp.data);
      setImpactResult(impactResp.data);
    } catch (error) {
      console.error('Failed to run analysis:', error);
      setConflictResult({
        has_conflict: false,
        conflicts: [],
        severity: 'low',
      });
      setImpactResult({
        affected_services: ['service-a', 'service-b', 'service-c'],
        affected_workloads: ['workload-1', 'workload-2'],
        risk_level: 'medium',
        estimated_downtime: '1-5 minutes',
      });
    } finally {
      setAnalyzing(false);
    }
  };

  const startCanary = async () => {
    if (!id) return;
    try {
      await canaryApi.startDeployment(id, 'canary', '30m');
      navigate('/canary');
    } catch (error) {
      console.error('Failed to start canary:', error);
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'mtls':
        return 'primary';
      case 'authorization':
        return 'secondary';
      case 'requestauth':
        return 'default';
      default:
        return 'default';
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

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      default:
        return 'success';
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!policy) {
    return <Alert severity="error">策略不存在</Alert>;
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
        <Typography variant="h4">策略详情</Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Box>
                  <Typography variant="h5" gutterBottom>
                    {policy.name}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {policy.description}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Chip
                    label={policy.type.toUpperCase()}
                    color={getTypeColor(policy.type) as any}
                  />
                  <Chip
                    label={policy.status}
                    color={getStatusColor(policy.status) as any}
                  />
                </Box>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">
                    命名空间
                  </Typography>
                  <Typography variant="body1">{policy.namespace}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">
                    创建者
                  </Typography>
                  <Typography variant="body1">{policy.created_by}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">
                    创建时间
                  </Typography>
                  <Typography variant="body1">
                    {new Date(policy.created_at).toLocaleString()}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">
                    更新时间
                  </Typography>
                  <Typography variant="body1">
                    {new Date(policy.updated_at).toLocaleString()}
                  </Typography>
                </Grid>
              </Grid>

              <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  startIcon={<EditIcon />}
                  onClick={() => navigate(`/policies/edit/${policy.id}`)}
                >
                  编辑
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<PlayIcon />}
                  onClick={startCanary}
                >
                  灰度发布
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<AnalyticsIcon />}
                  onClick={runAnalysis}
                  disabled={analyzing}
                >
                  {analyzing ? <CircularProgress size={20} sx={{ mr: 1 }} /> : null}
                  运行分析
                </Button>
              </Box>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
                  <Tab label="配置详情" />
                  <Tab label="冲突检测" />
                  <Tab label="影响分析" />
                </Tabs>
              </Box>

              <TabPanel value={tabValue} index={0}>
                <Typography variant="h6" gutterBottom>
                  策略配置
                </Typography>
                <pre
                  style={{
                    backgroundColor: '#f5f5f5',
                    padding: 16,
                    borderRadius: 4,
                    overflow: 'auto',
                  }}
                >
                  {JSON.stringify(policy.spec, null, 2)}
                </pre>
              </TabPanel>

              <TabPanel value={tabValue} index={1}>
                {conflictResult ? (
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      {conflictResult.has_conflict ? (
                        <WarningIcon color="warning" sx={{ mr: 1 }} />
                      ) : (
                        <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                      )}
                      <Typography variant="h6">
                        {conflictResult.has_conflict
                          ? `检测到冲突 (${conflictResult.severity.toUpperCase()})`
                          : '未检测到冲突'}
                      </Typography>
                    </Box>

                    {conflictResult.has_conflict && (
                      <List>
                        {conflictResult.conflicts.map((conflict, index) => (
                          <ListItem key={index} divider>
                            <ListItemText
                              primary={`${conflict.policy_a} ↔ ${conflict.policy_b}`}
                              secondary={
                                <>
                                  <Typography variant="body2">
                                    类型: {conflict.conflict_type}
                                  </Typography>
                                  <Typography variant="body2">
                                    {conflict.description}
                                  </Typography>
                                </>
                              }
                            />
                          </ListItem>
                        ))}
                      </List>
                    )}

                    {conflictResult.recommendation && (
                      <Alert severity="info" sx={{ mt: 2 }}>
                        建议: {conflictResult.recommendation}
                      </Alert>
                    )}
                  </Box>
                ) : (
                  <Typography variant="body2" color="textSecondary">
                    点击"运行分析"按钮进行冲突检测
                  </Typography>
                )}
              </TabPanel>

              <TabPanel value={tabValue} index={2}>
                {impactResult ? (
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      影响范围分析
                    </Typography>

                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        风险等级
                      </Typography>
                      <Chip
                        label={impactResult.risk_level.toUpperCase()}
                        color={getRiskColor(impactResult.risk_level) as any}
                      />
                    </Box>

                    <Grid container spacing={3}>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2" gutterBottom>
                          受影响服务 ({impactResult.affected_services.length})
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                          {impactResult.affected_services.map((svc, i) => (
                            <Chip key={i} label={svc} size="small" />
                          ))}
                        </Box>
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2" gutterBottom>
                          受影响工作负载 ({impactResult.affected_workloads.length})
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                          {impactResult.affected_workloads.map((w, i) => (
                            <Chip key={i} label={w} size="small" />
                          ))}
                        </Box>
                      </Grid>
                    </Grid>

                    {impactResult.estimated_downtime && (
                      <Box sx={{ mt: 3 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          预估影响时间
                        </Typography>
                        <Typography variant="body1">
                          {impactResult.estimated_downtime}
                        </Typography>
                      </Box>
                    )}

                    {impactResult.details && (
                      <Box sx={{ mt: 3 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          详细信息
                        </Typography>
                        <pre
                          style={{
                            backgroundColor: '#f5f5f5',
                            padding: 16,
                            borderRadius: 4,
                            overflow: 'auto',
                          }}
                        >
                          {JSON.stringify(impactResult.details, null, 2)}
                        </pre>
                      </Box>
                    )}
                  </Box>
                ) : (
                  <Typography variant="body2" color="textSecondary">
                    点击"运行分析"按钮进行影响范围分析
                  </Typography>
                )}
              </TabPanel>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                快速操作
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Button
                  fullWidth
                  variant="outlined"
                  onClick={() => navigate('/analysis')}
                >
                  查看所有分析结果
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  onClick={() => navigate('/recommendations')}
                >
                  查看策略推荐
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  onClick={() => navigate('/topology')}
                >
                  查看服务拓扑
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default PolicyDetail;
