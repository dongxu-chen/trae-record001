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
} from '@mui/material';
import {
  Security as SecurityIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  PlayArrow as PlayArrowIcon,
  Build as BuildIcon,
} from '@mui/icons-material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { ComplianceCheckResult, ComplianceControl, ComplianceStandard } from '../types';

const standards = [
  { id: 'pci_dss', name: 'PCI DSS', description: '支付卡行业数据安全标准', color: '#1976d2' },
  { id: 'gdpr', name: 'GDPR', description: '欧盟通用数据保护条例', color: '#2e7d32' },
  { id: 'hipaa', name: 'HIPAA', description: '医疗信息保护', color: '#ed6c02' },
  { id: 'soc2', name: 'SOC 2', description: '服务组织控制报告', color: '#7b1fa2' },
  { id: 'iso27001', name: 'ISO 27001', description: '信息安全管理体系', color: '#0288d1' },
];

const mockPCIResult: ComplianceCheckResult = {
  check_id: 'check-1735000000',
  standard: 'pci_dss',
  standard_name: 'PCI DSS',
  overall_score: 72.5,
  compliance_rate: 66.7,
  status: 'completed',
  checked_at: '2024-12-23T10:00:00Z',
  summary: {
    total_controls: 6,
    passed_controls: 4,
    failed_controls: 2,
    critical_failures: 1,
    high_failures: 1,
    medium_failures: 0,
    low_failures: 0,
    estimated_remediation_time: '约 12 小时',
  },
  controls: [],
  passed_controls: [
    {
      id: 'pci-dss-2.1',
      name: '传输加密要求',
      description: '使用强加密技术传输持卡人数据',
      requirement: '所有持卡人数据传输必须使用 TLS 1.2 或更高版本',
      category: '加密传输',
      severity: 'critical',
      status: 'passed',
      passed: true,
      evidence: ['所有命名空间已配置 mTLS STRICT 模式', 'Ingress 网关配置 TLS 1.2+'],
      references: ['PCI DSS Requirement 2.2.3', 'PCI DSS Requirement 4.1'],
    },
    {
      id: 'pci-dss-6.2',
      name: '访问控制',
      description: '按业务需要限制系统访问',
      requirement: '实施最小权限原则',
      category: '访问控制',
      severity: 'high',
      status: 'passed',
      passed: true,
      passed: true,
      evidence: ['已配置 23 条 AuthorizationPolicy', '默认拒绝策略已启用'],
      references: ['PCI DSS Requirement 7.1'],
    },
    {
      id: 'pci-dss-10.1',
      name: '审计日志',
      description: '跟踪和监控对资源的访问',
      requirement: '所有访问必须记录审计日志',
      category: '审计',
      severity: 'medium',
      status: 'passed',
      passed: true,
      evidence: ['已启用访问日志', '授权决策已记录'],
      references: ['PCI DSS Requirement 10.2'],
    },
  ],
  failed_controls: [
    {
      id: 'pci-dss-3.1',
      name: '静态数据加密',
      description: '保护存储的持卡人数据',
      requirement: '存储的持卡人数据必须加密',
      category: '数据保护',
      severity: 'critical',
      status: 'failed',
      passed: false,
      failed_reasons: ['未检测到静态数据加密策略', '数据库连接未强制加密'],
      affected_resources: ['prod/payment-service', 'prod/card-vault-service'],
      remediation_guidance: '1. 配置数据库连接加密 2. 启用静态数据加密',
      references: ['PCI DSS Requirement 3.4'],
    },
    {
      id: 'pci-dss-7.1',
      name: '身份认证',
      description: '唯一标识和验证用户',
      requirement: '所有用户必须经过身份验证',
      category: '身份认证',
      severity: 'high',
      status: 'warning',
      passed: false,
      failed_reasons: ['部分服务未配置 JWT 认证', '存在匿名访问路径'],
      affected_resources: ['staging/public-api', 'dev/user-service'],
      remediation_guidance: '1. 为所有 API 配置 JWT 认证 2. 关闭匿名访问',
      references: ['PCI DSS Requirement 8.1'],
    },
  ],
};

const CompliancePage: React.FC = () => {
  const [selectedStandard, setSelectedStandard] = useState<ComplianceStandard>('pci_dss');
  const [isChecking, setIsChecking] = useState(false);
  const [result, setResult] = useState<ComplianceCheckResult | null>(null);

  const handleRunCheck = () => {
    setIsChecking(true);
    setTimeout(() => {
      setResult(mockPCIResult);
      setIsChecking(false);
    }, 2000);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (control: ComplianceControl) => {
    if (control.passed) {
      return <CheckCircleIcon color="success" />;
    }
    if (control.status === 'warning') {
      return <WarningIcon color="warning" />;
    }
    return <ErrorIcon color="error" />;
  };

  const chartData = result
    ? [
        { name: '通过', value: result.summary.passed_controls, fill: '#4caf50' },
        { name: '失败', value: result.summary.failed_controls, fill: '#f44336' },
      ]
    : [];

  const severityData = result
    ? [
        { name: '严重', value: result.summary.critical_failures, fill: '#d32f2f' },
        { name: '高', value: result.summary.high_failures, fill: '#f57c00' },
        { name: '中', value: result.summary.medium_failures, fill: '#ffb300' },
        { name: '低', value: result.summary.low_failures, fill: '#1976d2' },
      ]
    : [];

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        合规检查
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              合规标准
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {standards.map((std) => (
                <Button
                  key={std.id}
                  variant={selectedStandard === std.id ? 'contained' : 'outlined'}
                  onClick={() => setSelectedStandard(std.id as ComplianceStandard)}
                  sx={{ justifyContent: 'flex-start', textAlign: 'left', padding: '12px 16px' }}
                >
                  <Box sx={{ mr: 2, width: 8, height: 8, borderRadius: '50%', bgcolor: std.color }} />
                  <Box>
                    <Typography variant="subtitle2">{std.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {std.description}
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
              onClick={handleRunCheck}
              disabled={isChecking}
              sx={{ mt: 3 }}
            >
              {isChecking ? '检查中...' : '开始检查'}
            </Button>

            {isChecking && (
              <Box sx={{ mt: 2 }}>
                <LinearProgress />
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={9}>
          {result ? (
            <Box>
              <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} md={4}>
                  <Card>
                    <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <SecurityIcon color="primary" sx={{ mr: 2 }} />
                      <Box>
                        <Typography variant="h4">
                          {result.overall_score.toFixed(1)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          合规评分
                        </Typography>
                      </Box>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={result.overall_score}
                      color={result.overall_score >= 80 ? 'success' : result.overall_score >= 60 ? 'warning' : 'error'}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography variant="h4" sx={{ mb: 1 }}>
                      {result.compliance_rate.toFixed(0)}%
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      合规率
                    </Typography>
                    <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                      <Chip
                        label={`通过 ${result.summary.passed_controls}`}
                        size="small"
                        color="success"
                      />
                      <Chip
                        label={`失败 ${result.summary.failed_controls}`}
                        size="small"
                        color="error"
                      />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      预计修复时间
                    </Typography>
                    <Typography variant="h5">
                      {result.summary.estimated_remediation_time}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      严重: {result.summary.critical_failures} | 高: {result.summary.high_failures}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            <Grid container spacing={3} sx={{ mb: 3 }}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2, height: 200 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    控制项分布
                  </Typography>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={chartData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={60}
                        label
                      >
                        {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Pie>
                      <RechartsTooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2, height: 200 }}>
                  <Typography variant="subtitle1" gutterBottom>
                  失败严重程度分布
                  </Typography>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={severityData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <RechartsTooltip />
                      <Bar dataKey="value">
                        {severityData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>
            </Grid>

            {result.failed_controls.length > 0 && (
              <Alert severity="error" sx={{ mb: 3 }}>
                <strong>需要修复 {result.failed_controls.length} 个控制项
              </Alert>
            )}

            <Accordion defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <ErrorIcon color="error" sx={{ mr: 1 }} />
                  <Typography variant="h6">未通过控制项 ({result.failed_controls.length})</Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>控制项</TableCell>
                        <TableCell>分类</TableCell>
                        <TableCell>严重程度</TableCell>
                        <TableCell>影响资源</TableCell>
                        <TableCell>操作</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {result.failed_controls.map((control) => (
                        <TableRow key={control.id}>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'flex-start', flexDirection: 'column' }}>
                              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                {getStatusIcon(control)}
                                <Typography variant="subtitle2" sx={{ ml: 1 }}>
                                  {control.name}
                                </Typography>
                              </Box>
                              <Typography variant="caption" color="text.secondary">
                                {control.description}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip label={control.category} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={control.severity.toUpperCase()}
                              size="small"
                              color={getSeverityColor(control.severity) as any}
                            />
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                              {control.affected_resources?.map((res) => (
                                <Chip key={res} label={res} size="small" />
                              ))}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Tooltip title="自动修复">
                              <IconButton size="small">
                                <BuildIcon />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    通过控制项 ({result.passed_controls.length})
                  </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>控制项</TableCell>
                          <TableCell>分类</TableCell>
                          <TableCell>严重程度</TableCell>
                          <TableCell>证据</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {result.passed_controls.map((control) => (
                          <TableRow key={control.id}>
                            <TableCell>
                              <Box sx={{ display: 'flex', alignItems: 'flex-start', flexDirection: 'column' }}>
                                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                  {getStatusIcon(control)}
                                  <Typography variant="subtitle2" sx={{ ml: 1 }}>
                                    {control.name}
                                  </Typography>
                                </Box>
                                <Typography variant="caption" color="text.secondary">
                                  {control.description}
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Chip label={control.category} size="small" variant="outlined" />
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={control.severity.toUpperCase()}
                                size="small"
                                color="success"
                              />
                            </TableCell>
                            <TableCell>
                              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                {control.evidence?.slice(0, 2).map((ev, i) => (
                                  <Chip key={i} label={ev} size="small" />
                                ))}
                              </Box>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </AccordionDetails>
              </Accordion>
            </Box>
          ) : (
            <Paper sx={{ p: 6, textAlign: 'center' }}>
              <SecurityIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                选择标准并开始检查
              </Typography>
              <Typography variant="body2" color="text.secondary">
                选择一个合规标准，然后点击"开始检查"
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default CompliancePage;
