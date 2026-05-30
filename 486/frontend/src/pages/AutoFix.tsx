import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Chip,
  LinearProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  IconButton,
  Divider,
} from '@mui/material';
import {
  Build as BuildIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  PlayArrow as PlayArrowIcon,
  Check as CheckIcon,
  Code as CodeIcon,
} from '@mui/icons-material';
import { PolicyPatch, PatchChange } from '../types';

const availableFixes = [
  {
    id: 'tls_mode_to_strict',
    name: '强制 mTLS 加密',
    description: '将 PERMISSIVE 模式升级为 STRICT 模式',
    risk: 'low',
    applies_to: 'PeerAuthentication',
  },
  {
    id: 'add_jwt_authentication',
    name: '添加 JWT 认证',
    description: '为 API 端点添加 JWT 身份验证',
    risk: 'medium',
    applies_to: 'RequestAuthentication',
  },
  {
    id: 'add_authorization_policy',
    name: '添加访问控制',
    description: '添加基于角色的授权策略',
    risk: 'medium',
    applies_to: 'AuthorizationPolicy',
  },
  {
    id: 'add_default_deny',
    name: '默认拒绝策略',
    description: '添加默认拒绝所有请求的策略',
    risk: 'high',
    applies_to: 'AuthorizationPolicy',
  },
  {
    id: 'update_tls_version',
    name: '升级 TLS 版本',
    description: '强制使用 TLS 1.2+ 和安全密码套件',
    risk: 'medium',
    applies_to: 'Gateway',
  },
  {
    id: 'add_audit_logging',
    name: '启用审计日志',
    description: '记录所有访问和授权决策',
    risk: 'low',
    applies_to: 'All',
  },
];

const mockPatch: PolicyPatch = {
  patch_id: 'patch-1735000000',
  policy_id: 'policy-1',
  issue_type: 'tls_mode_to_strict',
  description: '将 mTLS 模式从 PERMISSIVE 升级为 STRICT',
  risk_level: 'low',
  confidence: 0.95,
  applied: false,
  created_at: '2024-12-23T10:00:00Z',
  original_spec: {
    mode: 'PERMISSIVE',
    selector: {
      matchLabels: {
        app: 'frontend',
      },
    },
    selector: {
      matchLabels: {
        istio: 'ingressgateway',
      },
    },
  },
  patched_spec: {
    mode: 'STRICT',
    selector: {
      matchLabels: {
        istio: 'ingressgateway',
      },
    },
  },
  changes: [
    {
      operation: 'replace',
      path: '/spec/mode',
      old_value: 'PERMISSIVE',
      new_value: 'STRICT',
      reason: 'PCI DSS / GDPR 要求强制加密传输，PERMISSIVE 模式允许明文通信',
    },
  ],
};

const AutoFixPage: React.FC = () => {
  const [selectedPolicy, setSelectedPolicy] = useState('');
  const [selectedFixType, setSelectedFixType] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [patch, setPatch] = useState<PolicyPatch | null>(null);

  const handleGeneratePatch = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setPatch(mockPatch);
      setIsGenerating(false);
    }, 1500);
  };

  const handleApplyPatch = () => {
    if (patch) {
      setPatch({ ...patch, applied: true });
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  const getOperationColor = (operation: string) => {
    switch (operation) {
      case 'replace':
        return 'warning';
      case 'add':
        return 'success';
      case 'remove':
        return 'error';
      default:
        return 'default';
    }
  };

  const getOperationLabel = (operation: string) => {
    switch (operation) {
      case 'replace':
        return '修改';
      case 'add':
        return '新增';
      case 'remove':
        return '删除';
      default:
        return operation;
    }
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        策略自动修复
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              修复配置
            </Typography>

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>选择策略</InputLabel>
              <Select
                value={selectedPolicy}
                label="选择策略"
                onChange={(e) => setSelectedPolicy(e.target.value)}
              >
                <MenuItem value="policy-1">mTLS-PERMISSIVE - 生产环境</MenuItem>
                <MenuItem value="policy-2">ALLOW-ALL - 支付服务</MenuItem>
                <MenuItem value="policy-3">No-Auth - API网关</MenuItem>
              </Select>
            </FormControl>

            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1, mt: 2 }}>
              可用修复类型
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 2 }}>
              {availableFixes.map((fix) => (
                <Button
                  key={fix.id}
                  variant={selectedFixType === fix.id ? 'contained' : 'outlined'}
                  onClick={() => setSelectedFixType(fix.id)}
                  sx={{ justifyContent: 'flex-start', textAlign: 'left', padding: '10px 14px', textTransform: 'none' }}
                >
                  <Box sx={{ flex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Typography variant="subtitle2">{fix.name}</Typography>
                      <Chip
                        label={fix.risk.toUpperCase()}
                        size="small"
                        color={getRiskColor(fix.risk) as any}
                      />
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {fix.description}
                    </Typography>
                  </Box>
                </Button>
              ))}
            </Box>

            <Button
              fullWidth
              variant="contained"
              color="primary"
              size="large"
              startIcon={<PlayArrowIcon />}
              onClick={handleGeneratePatch}
              disabled={isGenerating || !selectedPolicy || !selectedFixType}
              sx={{ mt: 2 }}
            >
              {isGenerating ? '生成中...' : '生成修复补丁'}
            </Button>

            {isGenerating && (
              <Box sx={{ mt: 2 }}>
                <LinearProgress />
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          {patch ? (
            <Box>
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={4}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <BuildIcon color="primary" sx={{ mr: 1 }} />
                        <Typography variant="h6">{patch.description}</Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {patch.patch_id}
                      </Typography>
                    </Grid>
                    <Grid item xs={6} md={2}>
                      <Typography variant="body2" color="text.secondary">
                        风险等级
                      </Typography>
                      <Chip
                        label={patch.risk_level.toUpperCase()}
                        color={getRiskColor(patch.risk_level) as any}
                      />
                    </Grid>
                    <Grid item xs={6} md={2}>
                      <Typography variant="body2" color="text.secondary">
                        置信度
                      </Typography>
                      <Typography variant="h6">{(patch.confidence * 100).toFixed(0)}%
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        状态
                      </Typography>
                      <Chip
                        label={patch.applied ? '已应用' : '待应用'}
                        color={patch.applied ? 'success' : 'warning'}
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <CodeIcon sx={{ mr: 1 }} />
                    <Typography variant="h6">变更详情 ({patch.changes.length} 项变更</Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>操作</TableCell>
                          <TableCell>路径</TableCell>
                          <TableCell>原值</TableCell>
                          <TableCell>新值</TableCell>
                          <TableCell>原因</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {patch.changes.map((change, index) => (
                          <TableRow key={index}>
                            <TableCell>
                              <Chip
                                label={getOperationLabel(change.operation)}
                                size="small"
                                color={getOperationColor(change.operation) as any}
                              />
                            </TableCell>
                            <TableCell>
                              <code>{change.path}</code>
                            </TableCell>
                            <TableCell>{JSON.stringify(change.old_value)}</TableCell>
                            <TableCell>{JSON.stringify(change.new_value)}</TableCell>
                            <TableCell>{change.reason}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </AccordionDetails>
              </Accordion>

              <Accordion sx={{ mt: 2 }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <InfoIcon sx={{ mr: 1 }} />
                    <Typography variant="h6">修改前后对比</Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 2, bgcolor: '#fff3e0' }}>
                        <Typography variant="subtitle2" gutterBottom>
                          修改前
                        </Typography>
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                          {JSON.stringify(patch.original_spec, null, 2)}
                        </pre>
                      </Paper>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 2, bgcolor: '#e8f5e9' }}>
                        <Typography variant="subtitle2" gutterBottom>
                          修改后
                        </Typography>
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                          {JSON.stringify(patch.patched_spec, null, 2)}
                        </pre>
                      </Paper>
                    </Grid>
                  </Grid>
                </AccordionDetails>
              </Accordion>

              <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                <Button variant="outlined" onClick={() => setPatch(null)}>
                  取消
                </Button>
                <Button
                  variant="contained"
                  color="success"
                  startIcon={<CheckIcon />}
                  onClick={handleApplyPatch}
                  disabled={patch.applied}
                >
                  {patch.applied ? '已应用' : '应用补丁'}
                </Button>
              </Box>
            </Box>
          ) : (
            <Paper sx={{ p: 6, textAlign: 'center' }}>
              <BuildIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                选择策略和修复类型
              </Typography>
              <Typography variant="body2" color="text.secondary">
                选择一个策略和修复类型，然后点击"生成修复补丁"
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default AutoFixPage;
