import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  Alert,
  LinearProgress,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material'
import {
  VpnKey as VpnKeyIcon,
  Refresh as RefreshIcon,
  Autorenew as RotateIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon
} from '@mui/icons-material'
import { kmsApi } from '../api/client'

function KMS() {
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const [rotateDialogOpen, setRotateDialogOpen] = useState(false)
  const [rotating, setRotating] = useState(false)

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    try {
      const res = await kmsApi.status()
      setStatus(res.data)
      setError('')
    } catch (err) {
      setError('无法连接到KMS服务')
      setStatus(null)
    } finally {
      setLoading(false)
    }
  }

  const handleRotate = async () => {
    setRotating(true)
    try {
      const res = await kmsApi.rotate()
      alert(`密钥轮转成功! 新密钥ID: ${res.data.newKeyId}`)
      loadStatus()
    } catch (err) {
      alert('密钥轮转失败: ' + (err.response?.data?.error || err.message))
    } finally {
      setRotating(false)
      setRotateDialogOpen(false)
    }
  }

  if (loading) {
    return <LinearProgress />
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">KMS 密钥管理</Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadStatus}
        >
          刷新状态
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {status && !status.enabled && (
        <Alert severity="info" sx={{ mb: 3 }}>
          KMS 未启用。请配置 KMS_PROVIDER 环境变量来启用 KMS 密钥管理。
          支持的提供商: local, vault, aws
        </Alert>
      )}

      {status && status.enabled && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <VpnKeyIcon color="primary" sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5">KMS 状态</Typography>
                </Box>

                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">
                    健康状态
                  </Typography>
                  {status.healthy ? (
                    <Chip
                      icon={<CheckCircleIcon />}
                      label="健康"
                      color="success"
                      sx={{ mt: 0.5 }}
                    />
                  ) : (
                    <Chip
                      icon={<ErrorIcon />}
                      label="异常"
                      color="error"
                      sx={{ mt: 0.5 }}
                    />
                  )}
                </Box>

                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">
                    当前活跃密钥
                  </Typography>
                  <Chip
                    icon={<VpnKeyIcon />}
                    label={status.activeKeyId || 'N/A'}
                    color="primary"
                    variant="outlined"
                    sx={{ mt: 0.5 }}
                  />
                </Box>

                {status.error && (
                  <Alert severity="warning" sx={{ mt: 2 }}>
                    {status.error}
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <RotateIcon color="primary" sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5">密钥轮转</Typography>
                </Box>

                <Typography variant="body2" color="text.secondary" paragraph>
                  密钥轮转将生成新的主密钥。已有备份将使用旧密钥解密，
                  新备份将使用新密钥加密。系统支持同时使用多个密钥版本。
                </Typography>

                <Typography variant="body2" color="text.secondary" paragraph>
                  <strong>当前密钥:</strong> {status.activeKeyId || 'N/A'}
                </Typography>

                <Button
                  variant="contained"
                  color="warning"
                  startIcon={<RotateIcon />}
                  onClick={() => setRotateDialogOpen(true)}
                  disabled={!status.healthy || rotating}
                  fullWidth
                >
                  {rotating ? '轮转中...' : '执行密钥轮转'}
                </Button>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  KMS 配置说明
                </Typography>

                <Box mt={2}>
                  <Typography variant="subtitle2" gutterBottom>Local KMS（本地模式）</Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    用于开发和测试环境。密钥存储在本地文件系统中。
                  </Typography>
                  <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, overflow: 'auto' }}>
{`KMS_PROVIDER=local
KMS_ENDPOINT=./data/kms-keys`}
                  </pre>
                </Box>

                <Box mt={2}>
                  <Typography variant="subtitle2" gutterBottom>HashiCorp Vault</Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    企业级密钥管理，支持自动轮转和审计日志。
                  </Typography>
                  <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, overflow: 'auto' }}>
{`KMS_PROVIDER=vault
KMS_ENDPOINT=http://vault:8200
KMS_KEY_ID=etcd-backup-key
KMS_TOKEN=your-vault-token`}
                  </pre>
                </Box>

                <Box mt={2}>
                  <Typography variant="subtitle2" gutterBottom>AWS KMS</Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    使用 AWS Key Management Service，支持自动密钥轮转策略。
                  </Typography>
                  <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, overflow: 'auto' }}>
{`KMS_PROVIDER=aws
KMS_REGION=us-east-1
KMS_KEY_ID=alias/etcd-backup-key
KMS_ACCESS_KEY=your-access-key
KMS_SECRET_KEY=your-secret-key`}
                  </pre>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Dialog open={rotateDialogOpen} onClose={() => setRotateDialogOpen(false)}>
        <DialogTitle>确认密钥轮转</DialogTitle>
        <DialogContent>
          <Typography variant="body1">
            确定要执行密钥轮转吗？
          </Typography>
          <Typography variant="body2" color="text.secondary" mt={1}>
            轮转后，新备份将使用新密钥加密。已有备份仍可使用旧密钥解密。
            此操作不可撤销。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRotateDialogOpen(false)}>取消</Button>
          <Button onClick={handleRotate} variant="contained" color="warning">
            确认轮转
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default KMS
