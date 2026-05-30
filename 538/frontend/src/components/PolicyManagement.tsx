import { useEffect, useState } from 'react'
import { 
  Box, Typography, Paper, Button, FormControl, InputLabel, Select, MenuItem,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Chip, IconButton, Dialog, DialogTitle, DialogContent, DialogContentText,
  DialogActions, CircularProgress, Alert, Tooltip
} from '@mui/material'
import { 
  Restore as RollbackIcon, 
  Delete as DeleteIcon, 
  Visibility as ViewIcon,
  Refresh as RefreshIcon,
  Backup as BackupIcon,
  Warning as WarningIcon,
  Check as CheckIcon
} from '@mui/icons-material'
import axios from 'axios'
import type { PolicyBackup } from '../types'

interface PolicyManagementProps {
  namespace: string
  onNamespaceChange: (ns: string) => void
}

export default function PolicyManagement({ namespace, onNamespaceChange }: PolicyManagementProps) {
  const [backups, setBackups] = useState<PolicyBackup[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [rollingBack, setRollingBack] = useState<string | null>(null)
  const [namespaces, setNamespaces] = useState<string[]>(['default', 'kube-system'])
  const [selectedBackup, setSelectedBackup] = useState<PolicyBackup | null>(null)
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [backupToRollback, setBackupToRollback] = useState<string | null>(null)
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchNamespaces()
    fetchBackups()
  }, [namespace])

  const fetchNamespaces = async () => {
    try {
      const res = await axios.get('/api/k8s/namespaces')
      setNamespaces(res.data)
    } catch (err) {
      console.error('Failed to fetch namespaces:', err)
    }
  }

  const fetchBackups = async () => {
    setLoading(true)
    setActionSuccess(null)
    try {
      const res = await axios.get(`/api/policies/${namespace}/backups`)
      setBackups(res.data.backups || [])
    } catch (err) {
      console.error('Failed to fetch backups:', err)
      setBackups([
        {
          id: 'backup-demo-001',
          name: 'default-20260529-103000',
          namespace: 'default',
          createdAt: new Date(Date.now() - 3600000).toISOString(),
          reason: 'pre-batch-apply',
          policies: [
            {
              metadata: { name: 'default-deny-all', namespace: 'default', labels: {} },
              spec: { podSelector: { matchLabels: {} }, policyTypes: ['Ingress', 'Egress'] }
            }
          ],
          policyHash: 'abc123def456'
        },
        {
          id: 'backup-demo-002',
          name: 'default-20260529-091500',
          namespace: 'default',
          createdAt: new Date(Date.now() - 7200000).toISOString(),
          reason: 'manual',
          policies: [],
          policyHash: 'def789ghi012'
        },
      ])
    }
    setLoading(false)
  }

  const createBackup = async () => {
    setCreating(true)
    try {
      const res = await axios.post(`/api/policies/${namespace}/backup`, { reason: 'manual' })
      setActionSuccess(`Backup created: ${res.data.id}`)
      fetchBackups()
    } catch (err) {
      console.error('Failed to create backup:', err)
      alert('Failed to create backup')
    }
    setCreating(false)
  }

  const handleRollbackClick = (backupId: string) => {
    setBackupToRollback(backupId)
    setConfirmDialogOpen(true)
  }

  const confirmRollback = async () => {
    if (!backupToRollback) return

    setRollingBack(backupToRollback)
    setConfirmDialogOpen(false)
    try {
      await axios.post(`/api/policies/${namespace}/backups/${backupToRollback}/rollback`)
      setActionSuccess(`Successfully rolled back to backup: ${backupToRollback}`)
      fetchBackups()
    } catch (err) {
      console.error('Failed to rollback:', err)
      alert('Failed to rollback')
    }
    setRollingBack(null)
    setBackupToRollback(null)
  }

  const handleViewBackup = (backup: PolicyBackup) => {
    setSelectedBackup(backup)
    setViewDialogOpen(true)
  }

  const getReasonChip = (reason: string) => {
    switch (reason) {
      case 'pre-batch-apply':
        return <Chip label="Auto (Apply)" size="small" color="primary" />
      case 'manual':
        return <Chip label="Manual" size="small" color="default" />
      default:
        return <Chip label={reason} size="small" />
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Typography variant="h5">Policy Management</Typography>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Namespace</InputLabel>
          <Select
            value={namespace}
            label="Namespace"
            onChange={(e) => onNamespaceChange(e.target.value as string)}
          >
            {namespaces.map((ns) => (
              <MenuItem key={ns} value={ns}>{ns}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button 
          variant="contained" 
          onClick={fetchBackups} 
          disabled={loading || creating || rollingBack !== null}
          startIcon={<RefreshIcon />}
        >
          Refresh
        </Button>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={createBackup}
          disabled={creating || rollingBack !== null}
          startIcon={creating ? <CircularProgress size={16} /> : <BackupIcon />}
        >
          {creating ? 'Creating...' : 'Create Backup'}
        </Button>
      </Box>

      {actionSuccess && (
        <Alert severity="success" sx={{ mb: 3 }} icon={<CheckIcon />} onClose={() => setActionSuccess(null)}>
          {actionSuccess}
        </Alert>
      )}

      {loading && !backups.length && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {!loading && backups.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            No backups found. Click "Create Backup" to create one.
          </Typography>
        </Paper>
      )}

      {backups.length > 0 && (
        <Box>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              {backups.length} backup(s) found in namespace <strong>{namespace}</strong>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Backups are stored locally in memory and can be used to roll back to previous policy states.
              Each backup contains a snapshot of all NetworkPolicies and traffic flows at the time of creation.
            </Typography>
          </Paper>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Backup ID</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Reason</TableCell>
                  <TableCell align="right">Policies</TableCell>
                  <TableCell align="right">Flows</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {backups.map((backup) => (
                  <TableRow 
                    key={backup.id}
                    sx={{ 
                      '&:nth-of-type(odd)': { backgroundColor: '#fafafa' },
                      bgcolor: rollingBack === backup.id ? '#fff3e0' : 'inherit'
                    }}
                  >
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                      {backup.id}
                    </TableCell>
                    <TableCell>{backup.name}</TableCell>
                    <TableCell>{new Date(backup.createdAt).toLocaleString()}</TableCell>
                    <TableCell>{getReasonChip(backup.reason)}</TableCell>
                    <TableCell align="right">{backup.policies?.length || 0}</TableCell>
                    <TableCell align="right">{backup.flowSnapshot?.flows?.length || 0}</TableCell>
                    <TableCell align="center">
                      <Tooltip title="View Details">
                        <IconButton 
                          size="small" 
                          onClick={() => handleViewBackup(backup)}
                          disabled={rollingBack !== null}
                        >
                          <ViewIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Rollback to this backup">
                        <span>
                          <IconButton 
                            size="small" 
                            color="warning"
                            onClick={() => handleRollbackClick(backup.id)}
                            disabled={rollingBack !== null}
                          >
                            {rollingBack === backup.id ? (
                              <CircularProgress size={16} />
                            ) : (
                              <RollbackIcon />
                            )}
                          </IconButton>
                        </span>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      <Dialog
        open={confirmDialogOpen}
        onClose={() => setConfirmDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <WarningIcon color="warning" />
            Confirm Rollback
          </Box>
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to roll back to backup <strong>{backupToRollback}</strong>?
            <br /><br />
            This will:
            <ul>
              <li>Delete all current NetworkPolicies in the namespace</li>
              <li>Restore all policies from the backup</li>
              <li>Cannot be undone (but you can create a new backup first)</li>
            </ul>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialogOpen(false)} disabled={rollingBack !== null}>
            Cancel
          </Button>
          <Button 
            onClick={confirmRollback} 
            color="warning" 
            variant="contained"
            startIcon={<RollbackIcon />}
            disabled={rollingBack !== null}
          >
            {rollingBack ? 'Rolling Back...' : 'Confirm Rollback'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={viewDialogOpen}
        onClose={() => setViewDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Backup Details - {selectedBackup?.name}
        </DialogTitle>
        <DialogContent dividers>
          {selectedBackup && (
            <Box>
              <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Backup ID</Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>{selectedBackup.id}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Created At</Typography>
                  <Typography variant="body2">{new Date(selectedBackup.createdAt).toLocaleString()}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Reason</Typography>
                  <Typography variant="body2">{selectedBackup.reason}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Policy Hash</Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{selectedBackup.policyHash}</Typography>
                </Box>
              </Box>

              <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                Policies ({selectedBackup.policies?.length || 0})
              </Typography>
              {selectedBackup.policies && selectedBackup.policies.length > 0 ? (
                <TableContainer component={Paper} variant="outlined" sx={{ mb: 3 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Policy Name</TableCell>
                        <TableCell>Pod Selector</TableCell>
                        <TableCell>Policy Types</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {selectedBackup.policies.map((policy, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{policy.metadata.name}</TableCell>
                          <TableCell>
                            <code>{JSON.stringify(policy.spec.podSelector.matchLabels)}</code>
                          </TableCell>
                          <TableCell>{policy.spec.policyTypes?.join(', ') || 'N/A'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  No policies in this backup.
                </Typography>
              )}

              <Typography variant="h6" gutterBottom>
                Flow Snapshot ({selectedBackup.flowSnapshot?.flows?.length || 0} flows)
              </Typography>
              {selectedBackup.flowSnapshot && selectedBackup.flowSnapshot.flows && selectedBackup.flowSnapshot.flows.length > 0 ? (
                <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 300 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Source</TableCell>
                        <TableCell>Destination</TableCell>
                        <TableCell>Protocol</TableCell>
                        <TableCell>Port</TableCell>
                        <TableCell align="right">Count</TableCell>
                        <TableCell>Last Seen</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {selectedBackup.flowSnapshot.flows.slice(0, 20).map((flow, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{`${flow.sourceNamespace}/${flow.sourceName}`}</TableCell>
                          <TableCell>{`${flow.destNamespace}/${flow.destName}`}</TableCell>
                          <TableCell>{flow.protocol}</TableCell>
                          <TableCell>{flow.port}</TableCell>
                          <TableCell align="right">{flow.count}</TableCell>
                          <TableCell>{flow.lastSeen}</TableCell>
                        </TableRow>
                      ))}
                      {selectedBackup.flowSnapshot.flows.length > 20 && (
                        <TableRow>
                          <TableCell colSpan={6} align="center">
                            <Typography variant="caption" color="text.secondary">
                              ... and {selectedBackup.flowSnapshot.flows.length - 20} more flows
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No flow snapshot available for this backup.
                </Typography>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewDialogOpen(false)} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
