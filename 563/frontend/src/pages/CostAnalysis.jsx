import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Card, CardContent, Grid, LinearProgress,
  FormControl, InputLabel, Select, MenuItem, Chip, Alert,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  Tooltip
} from '@mui/material'
import {
  TrendingDown as TrendingDownIcon,
  Speed as SpeedIcon,
  Savings as SavingsIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon
} from '@mui/icons-material'
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  Title, Tooltip, Legend
} from 'chart.js'
import { costApi, clusterApi, backupApi } from '../api/client'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

function CostAnalysis() {
  const [loading, setLoading] = useState(true)
  const [clusters, setClusters] = useState([])
  const [selectedCluster, setSelectedCluster] = useState('')
  const [period, setPeriod] = useState('30d')
  const [analysis, setAnalysis] = useState(null)

  useEffect(() => { loadClusters() }, [])

  const loadClusters = async () => {
    try {
      const res = await clusterApi.list()
      setClusters(res.data || [])
      if (res.data?.length > 0) {
        setSelectedCluster(res.data[0].id)
        loadAnalysis(res.data[0].id, period)
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const loadAnalysis = async (clusterId, p) => {
    if (!clusterId) return
    try {
      const res = await costApi.getAnalysis(clusterId, p || period)
      setAnalysis(res.data)
    } catch (e) { console.error(e) }
  }

  const handleClusterChange = (id) => {
    setSelectedCluster(id)
    loadAnalysis(id, period)
  }

  const handlePeriodChange = (p) => {
    setPeriod(p)
    loadAnalysis(selectedCluster, p)
  }

  const formatSize = (bytes) => {
    if (!bytes) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatRTO = (seconds) => {
    if (!seconds) return '-'
    if (seconds < 60) return `${seconds}秒`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
    return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`
  }

  if (loading) return <LinearProgress />

  const chartData = analysis?.storageTrend ? {
    labels: analysis.storageTrend.map(t => t.date?.substring(5) || ''),
    datasets: [
      {
        label: '全量备份',
        data: analysis.storageTrend.map(t => t.fullSize / 1024 / 1024),
        backgroundColor: 'rgba(25, 118, 210, 0.7)',
      },
      {
        label: '增量备份',
        data: analysis.storageTrend.map(t => t.incrSize / 1024 / 1024),
        backgroundColor: 'rgba(156, 39, 176, 0.7)',
      }
    ]
  } : null

  const costChartData = analysis?.storageTrend ? {
    labels: analysis.storageTrend.map(t => t.date?.substring(5) || ''),
    datasets: [{
      label: '累计成本 ($)',
      data: analysis.storageTrend.map(t => t.cost),
      backgroundColor: 'rgba(255, 152, 0, 0.7)',
    }]
  } : null

  const priorityColor = (p) => p === 'high' ? 'error' : p === 'medium' ? 'warning' : 'info'

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">备份成本分析</Typography>
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>选择集群</InputLabel>
            <Select value={selectedCluster} label="选择集群" onChange={(e) => handleClusterChange(e.target.value)}>
              {clusters.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>时间范围</InputLabel>
            <Select value={period} label="时间范围" onChange={(e) => handlePeriodChange(e.target.value)}>
              <MenuItem value="7d">近 7 天</MenuItem>
              <MenuItem value="30d">近 30 天</MenuItem>
              <MenuItem value="90d">近 90 天</MenuItem>
              <MenuItem value="1y">近 1 年</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Box>

      {!analysis && (
        <Alert severity="info">请选择集群查看成本分析数据</Alert>
      )}

      {analysis && (
        <>
          <Grid container spacing={3} mb={3}>
            <Grid item xs={12} sm={3}>
              <Card><CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <SavingsIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">总成本</Typography>
                </Box>
                <Typography variant="h4">${analysis.totalCost?.toFixed(2) || '0.00'}</Typography>
                <Typography variant="caption" color="text.secondary">
                  存储 ${analysis.storageCost?.toFixed(2)} | 网络 ${analysis.networkCost?.toFixed(2)} | 计算 ${analysis.computeCost?.toFixed(2)}
                </Typography>
              </CardContent></Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card><CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <InfoIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">存储空间</Typography>
                </Box>
                <Typography variant="h4">{formatSize(analysis.totalSizeBytes)}</Typography>
                <Typography variant="caption" color="text.secondary">
                  全量 {analysis.fullCount} 个 ({formatSize(analysis.fullSizeBytes)}) | 增量 {analysis.incrementalCount} 个 ({formatSize(analysis.incrementalSizeBytes)})
                </Typography>
              </CardContent></Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card><CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <SpeedIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">预计 RTO</Typography>
                </Box>
                <Typography variant="h4">{formatRTO(analysis.estimatedRto)}</Typography>
                <Typography variant="caption" color="text.secondary">恢复时间目标</Typography>
              </CardContent></Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card><CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <TrendingDownIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">预计 RPO</Typography>
                </Box>
                <Typography variant="h4">
                  {analysis.estimatedRpo >= 60
                    ? `${Math.floor(analysis.estimatedRpo / 60)}时`
                    : `${analysis.estimatedRpo}分`}
                </Typography>
                <Typography variant="caption" color="text.secondary">恢复点目标</Typography>
                {analysis.savingsPercent > 0 && (
                  <Chip size="small" label={`增量节省 ${analysis.savingsPercent.toFixed(0)}%`} color="success" sx={{ mt: 0.5 }} />
                )}
              </CardContent></Card>
            </Grid>
          </Grid>

          <Grid container spacing={3} mb={3}>
            <Grid item xs={12} md={6}>
              <Card><CardContent>
                <Typography variant="h6" gutterBottom>备份大小趋势 (MB)</Typography>
                {chartData ? <Bar data={chartData} options={{ maintainAspectRatio: false, responsive: true }} height={250} /> : <Typography>暂无数据</Typography>}
              </CardContent></Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card><CardContent>
                <Typography variant="h6" gutterBottom>成本趋势 ($)</Typography>
                {costChartData ? <Bar data={costChartData} options={{ maintainAspectRatio: false, responsive: true }} height={250} /> : <Typography>暂无数据</Typography>}
              </CardContent></Card>
            </Grid>
          </Grid>

          {analysis.recommendations?.length > 0 && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>优化建议</Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>优先级</TableCell>
                        <TableCell>类型</TableCell>
                        <TableCell>当前</TableCell>
                        <TableCell>建议</TableCell>
                        <TableCell>节省</TableCell>
                        <TableCell>原因</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {analysis.recommendations.map((rec, i) => (
                        <TableRow key={i}>
                          <TableCell>
                            <Chip size="small" label={rec.priority === 'high' ? '高' : rec.priority === 'medium' ? '中' : '低'}
                              color={priorityColor(rec.priority)} />
                          </TableCell>
                          <TableCell>
                            <Chip size="small" label={rec.type} variant="outlined" />
                          </TableCell>
                          <TableCell>{rec.current}</TableCell>
                          <TableCell><strong>{rec.suggested}</strong></TableCell>
                          <TableCell>
                            {rec.savingsPct > 0 ? (
                              <Chip size="small" icon={<TrendingDownIcon />} label={`${rec.savingsPct}%`} color="success" />
                            ) : '-'}
                          </TableCell>
                          <TableCell><Typography variant="body2">{rec.reason}</Typography></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>RTO / RPO 权衡分析</Typography>
              <Alert severity="info" sx={{ mb: 2 }}>
                RTO (Recovery Time Objective): 系统恢复所需最长时间 | RPO (Recovery Point Objective): 可接受的最大数据丢失时间窗口
              </Alert>
              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom>当前策略</Typography>
                      <Typography variant="body2">RTO: <strong>{formatRTO(analysis.estimatedRto)}</strong></Typography>
                      <Typography variant="body2">RPO: <strong>{analysis.estimatedRpo >= 60 ? `${Math.floor(analysis.estimatedRpo / 60)}时` : `${analysis.estimatedRpo}分`}</strong></Typography>
                      <Typography variant="body2">月成本: <strong>${analysis.totalCost?.toFixed(2)}</strong></Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Card variant="outlined" sx={{ borderColor: 'success.main' }}>
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom color="success.main">高性能方案</Typography>
                      <Typography variant="body2">RTO: <strong>&lt; 2分钟</strong></Typography>
                      <Typography variant="body2">RPO: <strong>&lt; 5分钟</strong></Typography>
                      <Typography variant="body2">月成本: <strong>${(analysis.totalCost * 2.5)?.toFixed(2)}</strong></Typography>
                      <Chip size="small" label="5分钟增量备份+热备" color="success" sx={{ mt: 1 }} />
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Card variant="outlined" sx={{ borderColor: 'warning.main' }}>
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom color="warning.main">经济方案</Typography>
                      <Typography variant="body2">RTO: <strong>&lt; 30分钟</strong></Typography>
                      <Typography variant="body2">RPO: <strong>&lt; 24小时</strong></Typography>
                      <Typography variant="body2">月成本: <strong>${(analysis.totalCost * 0.4)?.toFixed(2)}</strong></Typography>
                      <Chip size="small" label="日全量+Glacier归档" color="warning" sx={{ mt: 1 }} />
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  )
}

export default CostAnalysis
