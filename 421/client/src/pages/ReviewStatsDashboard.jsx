import React, { useState, useEffect } from 'react';
import { 
  Container, Typography, Box, Grid, Card, CardContent, 
  Chip, Tabs, Tab, Paper, Table, TableBody, TableCell, 
  TableContainer, TableHead, TableRow, LinearProgress,
  Select, MenuItem, FormControl, InputLabel, Divider
} from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import PeopleIcon from '@mui/icons-material/People';
import DescriptionIcon from '@mui/icons-material/Description';
import BarChartIcon from '@mui/icons-material/BarChart';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const ReviewStatsDashboard = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('personal');
  const [period, setPeriod] = useState('month');
  const [stats, setStats] = useState(null);
  const [workload, setWorkload] = useState(null);
  const [efficiency, setEfficiency] = useState(null);
  const [aiStats, setAiStats] = useState(null);
  const [teamStats, setTeamStats] = useState(null);
  const [overallStats, setOverallStats] = useState(null);

  useEffect(() => {
    if (user?.role === 'reviewer' || user?.role === 'admin') {
      loadPersonalStats();
    }
    if (user?.role === 'admin') {
      loadTeamStats();
      loadOverallStats();
    }
  }, [user, period]);

  const loadPersonalStats = async () => {
    try {
      const res = await api.get('/api/stats/reviewer/overview', {
        params: { period }
      });
      setStats(res.data.stats);
      setWorkload(res.data.workload);
      setEfficiency(res.data.efficiency);
      setAiStats(res.data.aiStats);
    } catch (err) {
      console.error('Load personal stats error:', err);
    }
  };

  const loadTeamStats = async () => {
    try {
      const res = await api.get('/api/stats/team');
      setTeamStats(res.data);
    } catch (err) {
      console.error('Load team stats error:', err);
    }
  };

  const loadOverallStats = async () => {
    try {
      const res = await api.get('/api/stats/overall');
      setOverallStats(res.data);
    } catch (err) {
      console.error('Load overall stats error:', err);
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '-';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}小时${minutes}分钟`;
    return `${minutes}分钟`;
  };

  const StatCard = ({ title, value, subtitle, icon, color }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box display="flex" alignItems="center" mb={1}>
          {icon && React.createElement(icon, { color, sx: { mr: 1 } })}
          <Typography variant="body2" color="text.secondary">
            {title}
          </Typography>
        </Box>
        <Typography variant="h4" gutterBottom>
          {value}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  const WorkloadChart = ({ data }) => {
    if (!data?.periods) return null;

    const maxValue = Math.max(...data.periods.map(p => p.count), 1);

    return (
      <Box>
        <Typography variant="h6" gutterBottom>审核工作量趋势</Typography>
        <Box sx={{ height: 200, display: 'flex', alignItems: 'flex-end', gap: 2 }}>
          {data.periods.map((period, index) => (
            <Box key={index} sx={{ flex: 1, textAlign: 'center' }}>
              <Box
                sx={{
                  backgroundColor: 'primary.main',
                  height: `${(period.count / maxValue) * 150}px`,
                  width: '100%',
                  borderRadius: 1,
                  mb: 1,
                  minHeight: 4
                }}
              />
              <Typography variant="caption">
                {period.label}
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {period.count}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
    );
  };

  const ReviewerRankingTable = ({ reviewers }) => {
    if (!reviewers?.length) return null;

    return (
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>排名</TableCell>
              <TableCell>审核人</TableCell>
              <TableCell align="center">审核数</TableCell>
              <TableCell align="center">通过</TableCell>
              <TableCell align="center">拒绝</TableCell>
              <TableCell align="center">通过率</TableCell>
              <TableCell align="center">平均耗时</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {reviewers.map((reviewer, index) => (
              <TableRow key={reviewer._id}>
                <TableCell>
                  <Chip 
                    size="small"
                    label={index + 1}
                    color={index === 0 ? 'warning' : index === 1 ? 'info' : 'default'}
                  />
                </TableCell>
                <TableCell>{reviewer.username}</TableCell>
                <TableCell align="center">{reviewer.reviewedCount}</TableCell>
                <TableCell align="center">
                  <Chip size="small" label={reviewer.approvedCount} color="success" />
                </TableCell>
                <TableCell align="center">
                  <Chip size="small" label={reviewer.rejectedCount} color="error" />
                </TableCell>
                <TableCell align="center">
                  {reviewer.reviewedCount > 0 
                    ? Math.round((reviewer.approvedCount / reviewer.reviewedCount) * 100) 
                    : 0}%
                </TableCell>
                <TableCell align="center">
                  {formatDuration(reviewer.avgReviewTime)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4">
          <BarChartIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          审核统计
        </Typography>
        <FormControl size="small">
          <InputLabel>统计周期</InputLabel>
          <Select
            value={period}
            label="统计周期"
            onChange={(e) => setPeriod(e.target.value)}
          >
            <MenuItem value="week">本周</MenuItem>
            <MenuItem value="month">本月</MenuItem>
            <MenuItem value="quarter">本季度</MenuItem>
            <MenuItem value="year">本年</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Tabs 
        value={activeTab} 
        onChange={(e, v) => setActiveTab(v)}
        sx={{ mb: 4 }}
      >
        <Tab value="personal" label="个人统计" />
        <Tab value="team" label="团队统计" disabled={user?.role !== 'admin'} />
        <Tab value="system" label="系统统计" disabled={user?.role !== 'admin'} />
      </Tabs>

      {activeTab === 'personal' && (
        <Box>
          <Grid container spacing={3} mb={4}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="审核任务总数"
                value={stats?.totalReviews || 0}
                subtitle={`待审核: ${stats?.pendingReviews || 0}`}
                icon={DescriptionIcon}
                color="primary"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="通过率"
                value={`${stats?.approvalRate || 0}%`}
                subtitle={`通过: ${stats?.approvedCount || 0} / 拒绝: ${stats?.rejectedCount || 0}`}
                icon={CheckCircleIcon}
                color="success"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="平均审核耗时"
                value={formatDuration(efficiency?.avgReviewTime)}
                subtitle={`最快: ${formatDuration(efficiency?.fastestReviewTime)} / 最慢: ${formatDuration(efficiency?.slowestReviewTime)}`}
                icon={AccessTimeIcon}
                color="info"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="AI建议接受率"
                value={`${aiStats?.acceptanceRate || 0}%`}
                subtitle={`总建议: ${aiStats?.totalSuggestions || 0}`}
                icon={AutoAwesomeIcon}
                color="warning"
              />
            </Grid>
          </Grid>

          <Paper sx={{ p: 3, mb: 4 }}>
            <WorkloadChart data={workload} />
          </Paper>

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>审核效率详情</Typography>
                <Divider sx={{ my: 2 }} />
                
                <Box display="flex" justifyContent="space-between" mb={2}>
                  <Typography color="text.secondary">平均审核时间</Typography>
                  <Typography fontWeight="bold">
                    {formatDuration(efficiency?.avgReviewTime)}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between" mb={2}>
                  <Typography color="text.secondary">最快审核时间</Typography>
                  <Typography fontWeight="bold">
                    {formatDuration(efficiency?.fastestReviewTime)}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between" mb={2}>
                  <Typography color="text.secondary">最慢审核时间</Typography>
                  <Typography fontWeight="bold">
                    {formatDuration(efficiency?.slowestReviewTime)}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between" mb={2}>
                  <Typography color="text.secondary">本周审核数</Typography>
                  <Typography fontWeight="bold">
                    {efficiency?.thisWeekCount || 0}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography color="text.secondary">上周审核数</Typography>
                  <Typography fontWeight="bold">
                    {efficiency?.lastWeekCount || 0}
                  </Typography>
                </Box>
                
                {efficiency?.thisWeekCount !== undefined && efficiency?.lastWeekCount !== undefined && (
                  <Box mt={2}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <TrendingUpIcon color={efficiency.thisWeekCount >= efficiency.lastWeekCount ? 'success' : 'error'} />
                      <Typography>
                        较上周 {efficiency.thisWeekCount >= efficiency.lastWeekCount ? '增长' : '下降'} 
                        {Math.abs(efficiency.thisWeekCount - efficiency.lastWeekCount)} 个
                      </Typography>
                    </Box>
                  </Box>
                )}
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>AI建议统计</Typography>
                <Divider sx={{ my: 2 }} />
                
                <Box display="flex" justifyContent="space-between" mb={2}>
                  <Typography color="text.secondary">总建议数</Typography>
                  <Typography fontWeight="bold">{aiStats?.totalSuggestions || 0}</Typography>
                </Box>
                <Box display="flex" justifyContent="space-between" mb={2}>
                  <Typography color="text.secondary">已接受</Typography>
                  <Typography fontWeight="bold" color="success.main">
                    {aiStats?.acceptedSuggestions || 0}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between" mb={2}>
                  <Typography color="text.secondary">已忽略</Typography>
                  <Typography fontWeight="bold" color="text.secondary">
                    {aiStats?.ignoredSuggestions || 0}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography color="text.secondary">接受率</Typography>
                  <Typography fontWeight="bold">{aiStats?.acceptanceRate || 0}%</Typography>
                </Box>

                <Box mt={3}>
                  <Typography variant="subtitle2" gutterBottom>建议类型分布</Typography>
                  {aiStats?.byType && Object.entries(aiStats.byType).map(([type, count]) => (
                    <Box key={type} mb={1}>
                      <Box display="flex" justifyContent="space-between">
                        <Typography variant="body2">{type}</Typography>
                        <Typography variant="body2">{count}</Typography>
                      </Box>
                      <LinearProgress 
                        variant="determinate" 
                        value={(count / (aiStats.totalSuggestions || 1)) * 100}
                        sx={{ height: 6, borderRadius: 3 }}
                      />
                    </Box>
                  ))}
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </Box>
      )}

      {activeTab === 'team' && user?.role === 'admin' && (
        <Box>
          <Grid container spacing={3} mb={4}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="团队审核总数"
                value={teamStats?.totalReviews || 0}
                icon={DescriptionIcon}
                color="primary"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="团队通过率"
                value={`${teamStats?.overallApprovalRate || 0}%`}
                icon={CheckCircleIcon}
                color="success"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="活跃审核人"
                value={teamStats?.activeReviewers || 0}
                icon={PeopleIcon}
                color="info"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="平均审核耗时"
                value={formatDuration(teamStats?.avgReviewTime)}
                icon={AccessTimeIcon}
                color="warning"
              />
            </Grid>
          </Grid>

          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>审核人工作量排名</Typography>
            <ReviewerRankingTable reviewers={teamStats?.reviewerRanking} />
          </Paper>
        </Box>
      )}

      {activeTab === 'system' && user?.role === 'admin' && (
        <Box>
          <Grid container spacing={3} mb={4}>
            <Grid item xs={12} sm={6} md={4}>
              <StatCard
                title="文档总数"
                value={overallStats?.totalDocuments || 0}
                icon={DescriptionIcon}
                color="primary"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <StatCard
                title="审核总数"
                value={overallStats?.totalReviews || 0}
                icon={CheckCircleIcon}
                color="success"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <StatCard
                title="评论总数"
                value={overallStats?.totalComments || 0}
                icon={PeopleIcon}
                color="info"
              />
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>AI建议统计</Typography>
                <Divider sx={{ my: 2 }} />
                <Box display="flex" justifyContent="space-between" mb={2}>
                  <Typography color="text.secondary">总AI建议数</Typography>
                  <Typography fontWeight="bold">
                    {overallStats?.aiSuggestions?.total || 0}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography color="text.secondary">接受率</Typography>
                  <Typography fontWeight="bold">
                    {overallStats?.aiSuggestions?.acceptanceRate || 0}%
                  </Typography>
                </Box>
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>系统使用统计</Typography>
                <Divider sx={{ my: 2 }} />
                <Box display="flex" justifyContent="space-between" mb={2}>
                  <Typography color="text.secondary">用户总数</Typography>
                  <Typography fontWeight="bold">
                    {overallStats?.totalUsers || 0}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between" mb={2}>
                  <Typography color="text.secondary">活跃用户</Typography>
                  <Typography fontWeight="bold">
                    {overallStats?.activeUsers || 0}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography color="text.secondary">今日活跃</Typography>
                  <Typography fontWeight="bold">
                    {overallStats?.todayActiveUsers || 0}
                  </Typography>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </Box>
      )}
    </Container>
  );
};

export default ReviewStatsDashboard;
