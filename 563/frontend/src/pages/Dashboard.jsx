import React, { useState, useEffect } from 'react'
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Chip
} from '@mui/material'
import {
  Storage as StorageIcon,
  Backup as BackupIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon
} from '@mui/icons-material'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { clusterApi, backupApi } from '../api/client'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [clusters, setClusters] = useState([])
  const [backups, setBackups] = useState([])
  const [stats, setStats] = useState({
    totalClusters: 0,
    healthyClusters: 0,
    totalBackups: 0,
    successfulBackups: 0,
    totalSize: 0
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [clusterRes, backupRes] = await Promise.all([
        clusterApi.list(),
        backupApi.list()
      ])
      
      setClusters(clusterRes.data || [])
      setBackups(backupRes.data || [])
      
      const successfulBackups = backupRes.data?.filter(b => b.status === 'completed').length || 0
      const totalSize = backupRes.data?.reduce((sum, b) => sum + (b.size || 0), 0) || 0
      
      setStats({
        totalClusters: clusterRes.data?.length || 0,
        healthyClusters: Math.max(0, (clusterRes.data?.length || 0) - 1),
        totalBackups: backupRes.data?.length || 0,
        successfulBackups,
        totalSize
      })
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const chartData = {
    labels: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    datasets: [
      {
        label: '备份数量',
        data: [3, 5, 4, 6, 3, 7, 5],
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      },
    ],
  }

  if (loading) {
    return <LinearProgress />
  }

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        仪表盘
      </Typography>

      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <StorageIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">集群总数</Typography>
              </Box>
              <Typography variant="h3">{stats.totalClusters}</Typography>
              <Chip 
                size="small" 
                icon={<CheckCircleIcon />} 
                label={`${stats.healthyClusters} 个健康`}
                color="success"
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <BackupIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">备份总数</Typography>
              </Box>
              <Typography variant="h3">{stats.totalBackups}</Typography>
              <Chip 
                size="small" 
                icon={<CheckCircleIcon />} 
                label={`${stats.successfulBackups} 个成功`}
                color="success"
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <StorageIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">存储总量</Typography>
              </Box>
              <Typography variant="h3">{formatSize(stats.totalSize)}</Typography>
              <Typography variant="body2" color="text.secondary" mt={1}>
                已使用存储空间
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <CheckCircleIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">成功率</Typography>
              </Box>
              <Typography variant="h3">
                {stats.totalBackups > 0 
                  ? Math.round((stats.successfulBackups / stats.totalBackups) * 100)
                  : 0}%
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={stats.totalBackups > 0 
                  ? (stats.successfulBackups / stats.totalBackups) * 100 
                  : 0}
                sx={{ mt: 2 }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                备份趋势
              </Typography>
              <Box height={300}>
                <Line data={chartData} options={{ maintainAspectRatio: false }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                最近备份
              </Typography>
              {backups.slice(0, 5).map((backup) => (
                <Box key={backup.id} py={1} borderBottom="1px solid #eee">
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2">
                      {backup.clusterName}
                    </Typography>
                    <Chip 
                      size="small"
                      label={backup.type === 'full' ? '完整' : '增量'}
                      color={backup.type === 'full' ? 'primary' : 'default'}
                    />
                  </Box>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mt={1}>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(backup.createdAt).toLocaleString()}
                    </Typography>
                    {backup.status === 'completed' ? (
                      <CheckCircleIcon color="success" fontSize="small" />
                    ) : backup.status === 'failed' ? (
                      <ErrorIcon color="error" fontSize="small" />
                    ) : (
                      <LinearProgress size="small" />
                    )}
                  </Box>
                </Box>
              ))}
              {backups.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  暂无备份记录
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Dashboard
