import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  Security,
  VerifiedUser,
  Lock,
  Warning,
  CheckCircle,
  Error,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState({
    totalPolicies: 0,
    mtlsPolicies: 0,
    authzPolicies: 0,
    authPolicies: 0,
    activePolicies: 0,
    conflicts: 0,
    recommendations: 0,
    canaryDeployments: 0,
  });

  const [policyTrend] = useState([
    { date: 'Mon', policies: 12 },
    { date: 'Tue', policies: 15 },
    { date: 'Wed', policies: 18 },
    { date: 'Thu', policies: 22 },
    { date: 'Fri', policies: 25 },
    { date: 'Sat', policies: 25 },
    { date: 'Sun', policies: 28 },
  ]);

  const [policyDistribution] = useState([
    { name: 'mTLS', value: 8, color: '#3f51b5' },
    { name: 'Authorization', value: 12, color: '#f50057' },
    { name: 'Request Auth', value: 5, color: '#4caf50' },
  ]);

  useEffect(() => {
    setStats({
      totalPolicies: 25,
      mtlsPolicies: 8,
      authzPolicies: 12,
      authPolicies: 5,
      activePolicies: 23,
      conflicts: 2,
      recommendations: 5,
      canaryDeployments: 3,
    });
  }, []);

  const StatCard = ({ title, value, icon: Icon, color, subtitle }: any) => (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography color="textSecondary" gutterBottom variant="body2">
              {title}
            </Typography>
            <Typography variant="h4" component="div" sx={{ fontWeight: 'bold' }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="body2" color="textSecondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box sx={{ color, '& svg': { fontSize: 48, opacity: 0.3 } }}>
            <Icon />
          </Box>
        </Box>
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        Dashboard
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="总策略数"
            value={stats.totalPolicies}
            icon={Security}
            color="#1976d2"
            subtitle={`${stats.activePolicies} 个活跃`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="mTLS 策略"
            value={stats.mtlsPolicies}
            icon={Lock}
            color="#388e3c"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="授权策略"
            value={stats.authzPolicies}
            icon={VerifiedUser}
            color="#f57c00"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="请求认证"
            value={stats.authPolicies}
            icon={Lock}
            color="#7b1fa2"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Warning color="warning" sx={{ mr: 1 }} />
                <Typography variant="h6">策略冲突</Typography>
              </Box>
              <Typography variant="h3" color="warning.main">
                {stats.conflicts}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={(stats.conflicts / stats.totalPolicies) * 100}
                color="warning"
                sx={{ mt: 2 }}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <CheckCircle color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">智能推荐</Typography>
              </Box>
              <Typography variant="h3" color="success.main">
                {stats.recommendations}
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
                点击查看可优化的安全策略
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Error color="info" sx={{ mr: 1 }} />
                <Typography variant="h6">灰度发布中</Typography>
              </Box>
              <Typography variant="h3" color="info.main">
                {stats.canaryDeployments}
              </Typography>
              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                <Chip label="进行中" color="primary" size="small" />
                <Chip label="监控中" color="secondary" size="small" />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                策略增长趋势
              </Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={policyTrend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="policies"
                      stroke="#1976d2"
                      strokeWidth={2}
                      dot={{ fill: '#1976d2' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                策略类型分布
              </Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={policyDistribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {policyDistribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 2 }}>
                {policyDistribution.map((item) => (
                  <Box key={item.name} sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box
                      sx={{
                        width: 12,
                        height: 12,
                        backgroundColor: item.color,
                        mr: 1,
                      }}
                    />
                    <Typography variant="body2">
                      {item.name}: {item.value}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
