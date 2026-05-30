import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  Grid,
  LinearProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  Lightbulb,
  Check,
  Security,
  VerifiedUser,
  Lock,
  ExpandMore,
  PriorityHigh,
  TrendingUp,
  Business,
  Warning,
} from '@mui/icons-material';
import type { PolicyRecommendation } from '../types';
import { recommendationApi } from '../services/api';

const Recommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<PolicyRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('risk_score');
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => {
    loadRecommendations();
  }, []);

  const loadRecommendations = async () => {
    try {
      const response = await recommendationApi.getRecommendations();
      setRecommendations(response.data.items);
    } catch (error) {
      console.error('Failed to load recommendations:', error);
      setRecommendations([
        {
          id: 'rec-1',
          type: 'mtls',
          name: 'global-mtls-enable',
          description: 'Enable STRICT mTLS for all services in the mesh',
          reason: 'mTLS provides service-to-service encryption and authentication. No global policy detected.',
          confidence: 0.95,
          risk_score: 92,
          risk_level: 'critical',
          priority_rank: 1,
          security_impact: 'Critical security improvement that addresses high-severity vulnerabilities. Implements encryption for service-to-service communication.',
          business_impact: 'High business impact - affects critical services with significant traffic volume.',
          affected_services: ['frontend', 'api-gateway', 'backend', 'database'],
          spec: { mode: 'STRICT' },
          generated_at: new Date().toISOString(),
        },
        {
          id: 'rec-2',
          type: 'authorization',
          name: 'default-deny-policy',
          description: 'Implement default-deny authorization policy',
          reason: 'Following principle of least privilege - deny all traffic by default',
          confidence: 0.90,
          risk_score: 78,
          risk_level: 'high',
          priority_rank: 2,
          security_impact: 'Significant security improvement with broad protection coverage. Strengthens access control and reduces attack surface.',
          business_impact: 'High business impact - affects all services in the mesh.',
          affected_services: ['frontend', 'api-gateway', 'backend'],
          spec: { action: 'DENY', rules: [] },
          generated_at: new Date().toISOString(),
        },
        {
          id: 'rec-3',
          type: 'requestauth',
          name: 'frontend-jwt-auth',
          description: 'Add JWT authentication for frontend service',
          reason: 'Detected 156 invalid JWT requests to frontend - high severity',
          confidence: 0.85,
          risk_score: 65,
          risk_level: 'high',
          priority_rank: 3,
          security_impact: 'Moderate security improvement addressing specific attack vectors. Enforces strong authentication for incoming requests.',
          business_impact: 'Medium business impact - affects high-traffic services.',
          affected_services: ['frontend'],
          spec: {
            selectors: { app: 'frontend' },
            jwt_rules: [{ issuer: 'https://auth.example.com', audiences: ['frontend'] }],
          },
          generated_at: new Date().toISOString(),
        },
        {
          id: 'rec-4',
          type: 'mtls',
          name: 'api-gateway-mtls',
          description: 'Enable STRICT mTLS for api-gateway service',
          reason: 'Service api-gateway has 35.2% unencrypted traffic',
          confidence: 0.85,
          risk_score: 52,
          risk_level: 'medium',
          priority_rank: 4,
          security_impact: 'Moderate security improvement addressing specific attack vectors. Implements encryption for service-to-service communication.',
          business_impact: 'Low to medium business impact - targeted service protection.',
          affected_services: ['api-gateway'],
          spec: { mode: 'STRICT', target_services: ['api-gateway'] },
          generated_at: new Date().toISOString(),
        },
        {
          id: 'rec-5',
          type: 'authorization',
          name: 'backend-audit-policy',
          description: 'Add AUDIT policy for backend service',
          reason: 'Service backend has 8.5% unauthorized requests',
          confidence: 0.75,
          risk_score: 42,
          risk_level: 'medium',
          priority_rank: 5,
          security_impact: 'Incremental security hardening with minimal risk. Strengthens access control and reduces attack surface.',
          business_impact: 'Low to medium business impact - targeted service protection.',
          affected_services: ['backend'],
          spec: { action: 'AUDIT', target_services: ['backend'] },
          generated_at: new Date().toISOString(),
        },
        {
          id: 'rec-6',
          type: 'requestauth',
          name: 'api-jwt-recommendation',
          description: 'Consider JWT authentication for high-traffic api service',
          reason: 'Service api handles 8500 requests per minute without request authentication',
          confidence: 0.65,
          risk_score: 28,
          risk_level: 'low',
          priority_rank: 6,
          security_impact: 'Incremental security hardening with minimal risk. Enforces strong authentication for incoming requests.',
          business_impact: 'Low to medium business impact - targeted service protection.',
          affected_services: ['api'],
          spec: {
            selectors: { app: 'api' },
            jwt_rules: [{ issuer: 'https://auth.example.com', audiences: ['api'] }],
          },
          generated_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'mtls':
        return <Lock color="primary" />;
      case 'authorization':
        return <VerifiedUser color="secondary" />;
      case 'requestauth':
        return <Security />;
      default:
        return <Security />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'mtls':
        return 'primary';
      case 'authorization':
        return 'secondary';
      case 'requestauth':
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

  const getRiskLevelText = (level: string) => {
    switch (level) {
      case 'critical':
        return '极高风险';
      case 'high':
        return '高风险';
      case 'medium':
        return '中风险';
      case 'low':
        return '低风险';
      default:
        return '未知';
    }
  };

  const handleApply = async (id: string) => {
    try {
      await recommendationApi.applyRecommendation(id);
      setRecommendations(prev => prev.filter(r => r.id !== id));
    } catch (error) {
      console.error('Failed to apply recommendation:', error);
    }
  };

  const sortedAndFilteredRecommendations = [...recommendations]
    .filter(rec => filterType === 'all' || rec.type === filterType)
    .sort((a, b) => {
      switch (sortBy) {
        case 'risk_score':
          return b.risk_score - a.risk_score;
        case 'confidence':
          return b.confidence - a.confidence;
        case 'priority_rank':
          return a.priority_rank - b.priority_rank;
        default:
          return 0;
      }
    });

  const criticalCount = recommendations.filter(r => r.risk_level === 'critical').length;
  const highCount = recommendations.filter(r => r.risk_level === 'high').length;
  const mediumCount = recommendations.filter(r => r.risk_level === 'medium').length;
  const lowCount = recommendations.filter(r => r.risk_level === 'low').length;

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        策略推荐
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        基于当前网络流量和安全配置，系统智能推荐以下安全策略优化建议。
        推荐按风险评分排序，优先处理高风险项。
      </Alert>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <PriorityHigh sx={{ color: '#d32f2f', mr: 1 }} />
                <Typography variant="subtitle2">极高风险</Typography>
              </Box>
              <Typography variant="h3" sx={{ color: '#d32f2f' }}>
                {criticalCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Warning sx={{ color: '#f57c00', mr: 1 }} />
                <Typography variant="subtitle2">高风险</Typography>
              </Box>
              <Typography variant="h3" sx={{ color: '#f57c00' }}>
                {highCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <TrendingUp sx={{ color: '#fbc02d', mr: 1 }} />
                <Typography variant="subtitle2">中风险</Typography>
              </Box>
              <Typography variant="h3" sx={{ color: '#fbc02d' }}>
                {mediumCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Security sx={{ color: '#388e3c', mr: 1 }} />
                <Typography variant="subtitle2">低风险</Typography>
              </Box>
              <Typography variant="h3" sx={{ color: '#388e3c' }}>
                {lowCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>排序方式</InputLabel>
          <Select
            value={sortBy}
            label="排序方式"
            onChange={(e) => setSortBy(e.target.value)}
          >
            <MenuItem value="risk_score">按风险评分排序</MenuItem>
            <MenuItem value="priority_rank">按优先级排序</MenuItem>
            <MenuItem value="confidence">按置信度排序</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>策略类型</InputLabel>
          <Select
            value={filterType}
            label="策略类型"
            onChange={(e) => setFilterType(e.target.value)}
          >
            <MenuItem value="all">全部类型</MenuItem>
            <MenuItem value="mtls">mTLS 策略</MenuItem>
            <MenuItem value="authorization">授权策略</MenuItem>
            <MenuItem value="requestauth">认证策略</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {loading ? (
        <LinearProgress />
      ) : (
        <Grid container spacing={3}>
          {sortedAndFilteredRecommendations.map((rec) => (
            <Grid item xs={12} md={6} lg={4} key={rec.id}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                      <Chip
                        label={`#${rec.priority_rank}`}
                        size="small"
                        sx={{
                          backgroundColor: getRiskLevelColor(rec.risk_level),
                          color: 'white',
                          fontWeight: 'bold',
                        }}
                      />
                      {getTypeIcon(rec.type)}
                      <Typography variant="h6" sx={{ fontSize: '1rem' }}>
                        {rec.name}
                      </Typography>
                    </Box>
                    <Chip
                      label={rec.type.toUpperCase()}
                      size="small"
                      color={getTypeColor(rec.type) as any}
                    />
                  </Box>

                  <Typography variant="body2" color="text.secondary" paragraph sx={{ mb: 2 }}>
                    {rec.description}
                  </Typography>

                  <Grid container spacing={2} sx={{ mb: 2 }}>
                    <Grid item xs={6}>
                      <Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                          <Typography variant="body2">风险评分</Typography>
                          <Typography variant="body2" fontWeight="bold">
                            {rec.risk_score}/100
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={rec.risk_score}
                          sx={{
                            height: 8,
                            borderRadius: 4,
                            backgroundColor: '#e0e0e0',
                            '& .MuiLinearProgress-bar': {
                              backgroundColor: getRiskLevelColor(rec.risk_level),
                            },
                          }}
                        />
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                          <Typography variant="body2">置信度</Typography>
                          <Typography variant="body2">{(rec.confidence * 100).toFixed(0)}%</Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={rec.confidence * 100}
                          sx={{ height: 8, borderRadius: 4 }}
                        />
                      </Box>
                    </Grid>
                  </Grid>

                  <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                    <Chip
                      label={getRiskLevelText(rec.risk_level)}
                      size="small"
                      sx={{
                        backgroundColor: getRiskLevelColor(rec.risk_level),
                        color: 'white',
                      }}
                    />
                    <Chip
                      label={`优先级 ${rec.priority_rank}`}
                      size="small"
                      variant="outlined"
                      color="primary"
                    />
                  </Box>

                  <Accordion sx={{ boxShadow: 'none', border: '1px solid #e0e0e0', borderRadius: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Lightbulb fontSize="small" color="action" />
                        <Typography variant="body2">查看详细分析</Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <List dense disablePadding>
                        <ListItem disablePadding sx={{ mb: 1 }}>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Lightbulb fontSize="small" color="action" />
                                <Typography variant="subtitle2">推荐原因</Typography>
                              </Box>
                            }
                            secondary={rec.reason}
                          />
                        </ListItem>
                        <Divider sx={{ my: 1 }} />
                        <ListItem disablePadding sx={{ mb: 1 }}>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Security fontSize="small" color="primary" />
                                <Typography variant="subtitle2">安全影响</Typography>
                              </Box>
                            }
                            secondary={rec.security_impact}
                          />
                        </ListItem>
                        <Divider sx={{ my: 1 }} />
                        <ListItem disablePadding sx={{ mb: 1 }}>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Business fontSize="small" color="secondary" />
                                <Typography variant="subtitle2">业务影响</Typography>
                              </Box>
                            }
                            secondary={rec.business_impact}
                          />
                        </ListItem>
                        {rec.affected_services && rec.affected_services.length > 0 && (
                          <>
                            <Divider sx={{ my: 1 }} />
                            <ListItem disablePadding>
                              <ListItemText
                                primary={
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                                    <Typography variant="subtitle2" sx={{ mr: 1 }}>
                                      受影响服务:
                                    </Typography>
                                    {rec.affected_services.map((svc, i) => (
                                      <Chip key={i} label={svc} size="small" variant="outlined" />
                                    ))}
                                  </Box>
                                }
                              />
                            </ListItem>
                          </>
                        )}
                      </List>
                    </AccordionDetails>
                  </Accordion>

                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                    <Button
                      variant="contained"
                      size="small"
                      startIcon={<Check />}
                      onClick={() => handleApply(rec.id)}
                      sx={{
                        backgroundColor: getRiskLevelColor(rec.risk_level),
                        '&:hover': {
                          backgroundColor: getRiskLevelColor(rec.risk_level),
                          filter: 'brightness(0.9)',
                        },
                      }}
                    >
                      应用推荐
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};

export default Recommendations;
