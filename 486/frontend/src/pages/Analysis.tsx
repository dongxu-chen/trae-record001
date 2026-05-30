import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  Tabs,
  Tab,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
} from '@mui/material';
import {
  Warning,
  CheckCircle,
  Info,
  ExpandMore,
  PriorityHigh,
  VisibilityOff,
  Security,
} from '@mui/icons-material';
import type { ConflictInfo, VersionMatrixEntry, VersionDiffRisk } from '../types';

const Analysis: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [conflicts] = useState<ConflictInfo[]>([
    {
      conflict_type: 'mtls_mode_conflict',
      policy_a: 'global-mtls',
      policy_b: 'frontend-mtls',
      description: 'mTLS mode mismatch: global uses STRICT, frontend uses PERMISSIVE',
      severity: 'high',
      affected_resources: ['frontend-service', 'api-gateway'],
      is_implicit: false,
      priority_a: 150,
      priority_b: 110,
      winning_policy: 'global-mtls',
    },
    {
      conflict_type: 'namespace_override',
      policy_a: 'istio-system-mtls',
      policy_b: 'default-ns-mtls',
      description: 'Global policy may be overridden by namespace-specific policy',
      severity: 'medium',
      affected_resources: ['default/*'],
      is_implicit: true,
      priority_a: 180,
      priority_b: 130,
      winning_policy: 'istio-system-mtls',
    },
    {
      conflict_type: 'selector_shadowing',
      policy_a: 'wildcard-auth',
      policy_b: 'specific-api-auth',
      description: 'Wildcard policy may shadow specific policy for /api/v2/users',
      severity: 'high',
      affected_resources: ['api-service'],
      is_implicit: true,
      priority_a: 60,
      priority_b: 90,
      winning_policy: 'specific-api-auth',
    },
  ]);

  const [versionMatrix] = useState<VersionMatrixEntry[]>([
    {
      version: '1.19.0',
      istio_version: '1.19.0',
      k8s_version: '1.27-1.28',
      release_date: '2023-08-30',
      changes: ['Ambient Mesh GA', 'Kubernetes Gateway API v1 support', 'Enhanced mTLS certificate management'],
      breaking_changes: ['Removed support for Kubernetes 1.23 and earlier', 'Deprecated authentication.istio.io/v1alpha2'],
      security_fixes: ['CVE-2023-1234: Envoy request parsing vulnerability', 'Fixed JWT token validation edge case'],
    },
    {
      version: '1.18.5',
      istio_version: '1.18.5',
      k8s_version: '1.25-1.27',
      release_date: '2023-07-25',
      changes: ['Improved sidecar injection performance', 'Added support for SPIFFE certificates', 'Enhanced telemetry collection'],
      deprecations: ['Legacy mixer configuration'],
      security_fixes: ['CVE-2023-1001: mTLS handshake timeout'],
    },
    {
      version: '1.17.8',
      istio_version: '1.17.8',
      k8s_version: '1.24-1.26',
      release_date: '2023-06-15',
      changes: ['Wasm extension support', 'Gateway API improvements', 'Distributed tracing enhancements'],
      security_fixes: ['CVE-2023-0987: AuthorizationPolicy bypass'],
    },
  ]);

  const [versionDiffRisks] = useState<VersionDiffRisk[]>([
    {
      from_version: '1.18.5',
      to_version: '1.19.0',
      risk_level: 'high',
      risk_score: 65,
      risk_items: [
        {
          field: 'breaking_change',
          old_value: '1.18.5',
          new_value: '1.19.0',
          impact: 'Removed support for Kubernetes 1.23 and earlier',
          severity: 'high',
        },
        {
          field: 'breaking_change',
          old_value: '1.18.5',
          new_value: '1.19.0',
          impact: 'Deprecated authentication.istio.io/v1alpha2',
          severity: 'high',
        },
        {
          field: 'security_fix',
          old_value: '1.18.5',
          new_value: '1.19.0',
          impact: 'CVE-2023-1234: Envoy request parsing vulnerability',
          severity: 'low',
        },
      ],
      mitigation: '2 breaking changes require compatibility testing. 1 security fixes included. Recommended: staging environment validation, incremental rollout',
    },
    {
      from_version: '2024-01-15',
      to_version: '2024-01-20',
      risk_level: 'critical',
      risk_score: 85,
      risk_items: [
        {
          field: 'spec.mtls.mode',
          old_value: 'PERMISSIVE',
          new_value: 'STRICT',
          impact: 'mTLS mode changed from PERMISSIVE to STRICT - affects all service-to-service communication',
          severity: 'high',
        },
        {
          field: 'spec.target_services',
          old_value: '["frontend"]',
          new_value: '<not set>',
          impact: 'Target services removed - policy scope has changed to all services',
          severity: 'high',
        },
      ],
      mitigation: 'CRITICAL: Requires full change review. Deploy only during maintenance window. Rollback plan required. Recommend canary deployment with 10% initial traffic.',
    },
  ]);

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

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'critical':
        return '#d32f2f';
      case 'high':
        return '#f57c00';
      case 'medium':
        return '#fbc02d';
      case 'low':
        return '#388e3c';
      default:
        return '#757575';
    }
  };

  const explicitConflicts = conflicts.filter(c => !c.is_implicit);
  const implicitConflicts = conflicts.filter(c => c.is_implicit);

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        策略分析
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <PriorityHigh color="error" sx={{ mr: 1 }} />
                <Typography variant="h6">高危冲突</Typography>
              </Box>
              <Typography variant="h3" color="error.main">
                {conflicts.filter(c => c.severity === 'high' || c.severity === 'critical').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Warning color="warning" sx={{ mr: 1 }} />
                <Typography variant="h6">中等风险</Typography>
              </Box>
              <Typography variant="h3" color="warning.main">
                {conflicts.filter(c => c.severity === 'medium').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <VisibilityOff color="action" sx={{ mr: 1 }} />
                <Typography variant="h6">隐式冲突</Typography>
              </Box>
              <Typography variant="h3" color="text.primary">
                {implicitConflicts.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <CheckCircle color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">通过检查</Typography>
              </Box>
              <Typography variant="h3" color="success.main">
                23
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
            <Tab label={`显式冲突 (${explicitConflicts.length})`} />
            <Tab label={`隐式冲突 (${implicitConflicts.length})`} />
            <Tab label="版本矩阵" />
            <Tab label="版本差异风险" />
          </Tabs>
        </CardContent>
      </Card>

      {activeTab === 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <Warning color="error" />
              显式冲突检测
            </Typography>
            {explicitConflicts.length === 0 ? (
              <Alert severity="success">未检测到任何显式策略冲突</Alert>
            ) : (
              <List>
                {explicitConflicts.map((conflict, idx) => (
                  <ListItem key={idx} divider>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                          <Typography variant="subtitle1">
                            {conflict.policy_a} ↔ {conflict.policy_b}
                          </Typography>
                          <Chip
                            label={conflict.severity.toUpperCase()}
                            color={getSeverityColor(conflict.severity) as any}
                            size="small"
                          />
                          <Chip
                            label={`优先级: ${conflict.priority_a} vs ${conflict.priority_b}`}
                            color="primary"
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`获胜: ${conflict.winning_policy}`}
                            color="success"
                            size="small"
                          />
                        </Box>
                      }
                      secondary={
                        <>
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            类型: {conflict.conflict_type}
                          </Typography>
                          <Typography variant="body2">{conflict.description}</Typography>
                          {conflict.affected_resources && conflict.affected_resources.length > 0 && (
                            <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <Info fontSize="small" color="action" />
                              <Typography variant="body2" color="text.secondary">
                                受影响资源: {conflict.affected_resources.join(', ')}
                              </Typography>
                            </Box>
                          )}
                        </>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 1 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <VisibilityOff color="action" />
              隐式冲突检测
            </Typography>
            <Alert severity="info" sx={{ mb: 3 }}>
              隐式冲突是指由于策略优先级、命名空间覆盖、选择器匹配等机制导致的非直观冲突。
              这些冲突可能在特定条件下导致意外的策略行为。
            </Alert>
            {implicitConflicts.length === 0 ? (
              <Alert severity="success">未检测到任何隐式策略冲突</Alert>
            ) : (
              <List>
                {implicitConflicts.map((conflict, idx) => (
                  <ListItem key={idx} divider>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                          <Chip label="隐式" color="warning" size="small" sx={{ mr: 1 }} />
                          <Typography variant="subtitle1">
                            {conflict.policy_a} ↔ {conflict.policy_b}
                          </Typography>
                          <Chip
                            label={conflict.severity.toUpperCase()}
                            color={getSeverityColor(conflict.severity) as any}
                            size="small"
                          />
                          <Chip
                            label={`优先级: ${conflict.priority_a} vs ${conflict.priority_b}`}
                            color="primary"
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <>
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            类型: {conflict.conflict_type}
                          </Typography>
                          <Typography variant="body2">{conflict.description}</Typography>
                          <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
                            {conflict.affected_resources && conflict.affected_resources.length > 0 && (
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <Info fontSize="small" color="action" />
                                <Typography variant="body2" color="text.secondary">
                                  受影响: {conflict.affected_resources.join(', ')}
                                </Typography>
                              </Box>
                            )}
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <PriorityHigh fontSize="small" color="action" />
                              <Typography variant="body2" color="text.secondary">
                                获胜策略: {conflict.winning_policy}
                              </Typography>
                            </Box>
                          </Box>
                        </>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 2 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <Security color="primary" />
              版本兼容性矩阵
            </Typography>
            <Alert severity="info" sx={{ mb: 3 }}>
              当前运行版本: <strong>1.18.5</strong>，最新版本: <strong>1.19.0</strong>
            </Alert>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>版本</TableCell>
                  <TableCell>Istio 版本</TableCell>
                  <TableCell>K8s 版本</TableCell>
                  <TableCell>发布日期</TableCell>
                  <TableCell>主要变更</TableCell>
                  <TableCell>风险</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {versionMatrix.map((entry, idx) => (
                  <TableRow key={idx} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="subtitle2" fontWeight="bold">
                          {entry.version}
                        </Typography>
                        {entry.version === '1.19.0' && (
                          <Chip label="最新" color="primary" size="small" />
                        )}
                        {entry.version === '1.18.5' && (
                          <Chip label="当前" color="success" size="small" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>{entry.istio_version}</TableCell>
                    <TableCell>{entry.k8s_version}</TableCell>
                    <TableCell>{entry.release_date}</TableCell>
                    <TableCell>
                      <Box>
                        {entry.changes.slice(0, 2).map((change, i) => (
                          <Typography key={i} variant="body2">
                            • {change}
                          </Typography>
                        ))}
                        {entry.changes.length > 2 && (
                          <Typography variant="body2" color="text.secondary">
                            + {entry.changes.length - 2} 更多
                          </Typography>
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>
                      {idx === 0 ? (
                        <Chip label="推荐升级" color="success" size="small" />
                      ) : idx === 1 ? (
                        <Chip label="稳定" color="info" size="small" />
                      ) : (
                        <Chip label="旧版本" color="warning" size="small" />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <Box sx={{ mt: 4 }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
                版本详情
              </Typography>
              {versionMatrix.map((entry, idx) => (
                <Accordion key={idx} defaultExpanded={idx === 0}>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {entry.version}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        发布于 {entry.release_date}
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={3}>
                      <Grid item xs={12} md={4}>
                        <Typography variant="subtitle2" gutterBottom>
                          主要变更
                        </Typography>
                        <List dense>
                          {entry.changes.map((change, i) => (
                            <ListItem key={i}>
                              <ListItemText primary={`• ${change}`} />
                            </ListItem>
                          ))}
                        </List>
                      </Grid>
                      {entry.breaking_changes && entry.breaking_changes.length > 0 && (
                        <Grid item xs={12} md={4}>
                          <Typography variant="subtitle2" gutterBottom sx={{ color: 'error.main' }}>
                            破坏性变更
                          </Typography>
                          <List dense>
                            {entry.breaking_changes.map((bc, i) => (
                              <ListItem key={i}>
                                <ListItemText primary={`• ${bc}`} />
                              </ListItem>
                            ))}
                          </List>
                        </Grid>
                      )}
                      {entry.deprecations && entry.deprecations.length > 0 && (
                        <Grid item xs={12} md={4}>
                          <Typography variant="subtitle2" gutterBottom sx={{ color: 'warning.main' }}>
                            已废弃
                          </Typography>
                          <List dense>
                            {entry.deprecations.map((d, i) => (
                              <ListItem key={i}>
                                <ListItemText primary={`• ${d}`} />
                              </ListItem>
                            ))}
                          </List>
                        </Grid>
                      )}
                      {entry.security_fixes && entry.security_fixes.length > 0 && (
                        <Grid item xs={12} md={4}>
                          <Typography variant="subtitle2" gutterBottom sx={{ color: 'success.main' }}>
                            安全修复
                          </Typography>
                          <List dense>
                            {entry.security_fixes.map((sf, i) => (
                              <ListItem key={i}>
                                <ListItemText primary={`• ${sf}`} />
                              </ListItem>
                            ))}
                          </List>
                        </Grid>
                      )}
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {activeTab === 3 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <Warning color="warning" />
              版本差异风险分析
            </Typography>
            {versionDiffRisks.length === 0 ? (
              <Alert severity="success">未检测到版本差异风险</Alert>
            ) : (
              <Box>
                {versionDiffRisks.map((diff, idx) => (
                  <Card key={idx} variant="outlined" sx={{ mb: 3 }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                          <Typography variant="h6">
                            {diff.from_version} → {diff.to_version}
                          </Typography>
                          <Chip
                            label={diff.risk_level.toUpperCase()}
                            sx={{
                              backgroundColor: getRiskLevelColor(diff.risk_level),
                              color: 'white',
                            }}
                            size="small"
                          />
                        </Box>
                        <Box sx={{ width: 200 }}>
                          <Typography variant="body2" gutterBottom>
                            风险评分: {diff.risk_score}/100
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={diff.risk_score}
                            sx={{
                              height: 8,
                              borderRadius: 4,
                              backgroundColor: '#e0e0e0',
                              '& .MuiLinearProgress-bar': {
                                backgroundColor: getRiskLevelColor(diff.risk_level),
                              },
                            }}
                          />
                        </Box>
                      </Box>

                      <Table size="small" sx={{ mb: 2 }}>
                        <TableHead>
                          <TableRow>
                            <TableCell>字段</TableCell>
                            <TableCell>原值</TableCell>
                            <TableCell>新值</TableCell>
                            <TableCell>影响</TableCell>
                            <TableCell>严重性</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {diff.risk_items.map((item, i) => (
                            <TableRow key={i}>
                              <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>
                                {item.field}
                              </TableCell>
                              <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>
                                {item.old_value}
                              </TableCell>
                              <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>
                                {item.new_value}
                              </TableCell>
                              <TableCell>{item.impact}</TableCell>
                              <TableCell>
                                <Chip
                                  label={item.severity.toUpperCase()}
                                  color={getSeverityColor(item.severity) as any}
                                  size="small"
                                />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>

                      <Alert severity={diff.risk_level === 'critical' ? 'error' : diff.risk_level === 'high' ? 'warning' : 'info'}>
                        <Typography variant="subtitle2">缓解措施:</Typography>
                        <Typography variant="body2">{diff.mitigation}</Typography>
                      </Alert>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default Analysis;
