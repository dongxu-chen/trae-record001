import { useEffect, useState } from 'react'
import { 
  Box, Typography, Paper, Button, FormControl, InputLabel, Select, MenuItem,
  Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Collapse, IconButton
} from '@mui/material'
import { Error as ErrorIcon, Warning as WarningIcon, Info as InfoIcon, ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon } from '@mui/icons-material'
import axios from 'axios'
import type { PolicyConflict } from '../types'

interface ConflictDetectionProps {
  namespace: string
  onNamespaceChange: (ns: string) => void
}

export default function ConflictDetection({ namespace, onNamespaceChange }: ConflictDetectionProps) {
  const [conflicts, setConflicts] = useState<PolicyConflict[]>([])
  const [totalPolicies, setTotalPolicies] = useState(0)
  const [loading, setLoading] = useState(false)
  const [namespaces, setNamespaces] = useState<string[]>(['default', 'kube-system'])
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())

  useEffect(() => {
    fetchNamespaces()
    detectConflicts()
  }, [namespace])

  const fetchNamespaces = async () => {
    try {
      const res = await axios.get('/api/k8s/namespaces')
      setNamespaces(res.data)
    } catch (err) {
      console.error('Failed to fetch namespaces:', err)
    }
  }

  const detectConflicts = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`/api/policies/${namespace}/conflicts`)
      setConflicts(res.data.conflicts || [])
      setTotalPolicies(res.data.totalPolicies || 0)
    } catch (err) {
      console.error('Failed to detect conflicts:', err)
      setConflicts([
        {
          type: 'ALLOW_DENY_CLASH',
          severity: 'HIGH',
          policyA: 'allow-backend-ingress',
          policyB: 'default-deny-all',
          description: "ALLOW policy 'allow-backend-ingress' and DENY policy 'default-deny-all' target overlapping pods - traffic may be implicitly blocked",
          recommendation: 'Review the deny policy scope; ensure ALLOW rules are not unintentionally blocked by the default-deny',
          affectedTraffic: [
            { source: 'pod(labels={app:frontend})', destination: 'pod(labels={app:backend})', port: 8080, protocol: 'TCP', direction: 'ingress' },
          ],
        },
        {
          type: 'IMPLICIT_DENY',
          severity: 'HIGH',
          policyA: 'allow-all-ingress',
          policyB: 'allow-specific-ingress',
          description: "Policy 'allow-specific-ingress' selects specific pods but has no allow rules, while 'allow-all-ingress' allows traffic to all pods",
          recommendation: 'Add explicit allow rules to the narrow policy or remove the empty policy types',
          affectedTraffic: [
            { source: 'various', destination: 'all-pods', port: 8080, protocol: 'TCP', direction: 'ingress' },
          ],
        },
        {
          type: 'SHADOWING',
          severity: 'HIGH',
          policyA: 'default-deny-all',
          policyB: 'allow-backend-ingress',
          description: "Policy 'default-deny-all' (selects all pods) may shadow 'allow-backend-ingress' for overlapping traffic",
          recommendation: 'Consider reordering or merging policies, or make selectors more specific',
        },
        {
          type: 'OVERLAP',
          severity: 'MEDIUM',
          policyA: 'allow-frontend',
          policyB: 'allow-backend',
          description: 'Policies have overlapping pod selectors and traffic rules',
          recommendation: 'Review the overlapping rules and consider consolidation',
        },
        {
          type: 'REDUNDANCY',
          severity: 'LOW',
          policyA: 'allow-dns-egress-1',
          policyB: 'allow-dns-egress-2',
          description: 'Policies are identical - one is redundant',
          recommendation: 'Remove one of the duplicate policies',
        },
      ])
      setTotalPolicies(5)
    }
    setLoading(false)
  }

  const toggleRow = (idx: number) => {
    setExpandedRows(prev => {
      const next = new Set(prev)
      if (next.has(idx)) {
        next.delete(idx)
      } else {
        next.add(idx)
      }
      return next
    })
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'HIGH':
        return <ErrorIcon color="error" />
      case 'MEDIUM':
        return <WarningIcon color="warning" />
      default:
        return <InfoIcon color="info" />
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'HIGH':
        return 'error'
      case 'MEDIUM':
        return 'warning'
      default:
        return 'info'
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'ALLOW_DENY_CLASH':
        return 'error'
      case 'IMPLICIT_DENY':
        return 'warning'
      case 'SHADOWING':
        return 'secondary'
      case 'OVERLAP':
        return 'default'
      case 'REDUNDANCY':
        return 'info'
      default:
        return 'default'
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="h5">Policy Conflict Detection</Typography>
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
        <Button variant="contained" onClick={detectConflicts}>
          Detect Conflicts
        </Button>
      </Box>

      <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Paper sx={{ p: 2, minWidth: 120 }}>
          <Typography variant="body2" color="text.secondary">Total Policies</Typography>
          <Typography variant="h4">{totalPolicies}</Typography>
        </Paper>
        <Paper sx={{ p: 2, minWidth: 120 }}>
          <Typography variant="body2" color="error">ALLOW/DENY Clash</Typography>
          <Typography variant="h4" color="error">
            {conflicts.filter(c => c.type === 'ALLOW_DENY_CLASH').length}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, minWidth: 120 }}>
          <Typography variant="body2" color="warning.main">Implicit Deny</Typography>
          <Typography variant="h4" color="warning.main">
            {conflicts.filter(c => c.type === 'IMPLICIT_DENY').length}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, minWidth: 120 }}>
          <Typography variant="body2" color="text.secondary">High</Typography>
          <Typography variant="h4" color="error">
            {conflicts.filter(c => c.severity === 'HIGH').length}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, minWidth: 120 }}>
          <Typography variant="body2" color="text.secondary">Medium</Typography>
          <Typography variant="h4" color="warning.main">
            {conflicts.filter(c => c.severity === 'MEDIUM').length}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, minWidth: 120 }}>
          <Typography variant="body2" color="text.secondary">Low</Typography>
          <Typography variant="h4" color="info.main">
            {conflicts.filter(c => c.severity === 'LOW').length}
          </Typography>
        </Paper>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Severity</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Policy A</TableCell>
              <TableCell>Policy B</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Recommendation</TableCell>
              <TableCell>Affected Traffic</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {conflicts.map((conflict, idx) => (
              <>
                <TableRow key={idx} sx={{ bgcolor: conflict.type === 'ALLOW_DENY_CLASH' || conflict.type === 'IMPLICIT_DENY' ? '#fff3e0' : 'inherit' }}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getSeverityIcon(conflict.severity)}
                      <Chip
                        label={conflict.severity}
                        size="small"
                        color={getSeverityColor(conflict.severity) as 'error' | 'warning' | 'info'}
                      />
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={conflict.type}
                      size="small"
                      color={getTypeColor(conflict.type) as 'error' | 'warning' | 'secondary' | 'default' | 'info'}
                      sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}
                    />
                  </TableCell>
                  <TableCell>{conflict.policyA}</TableCell>
                  <TableCell>{conflict.policyB}</TableCell>
                  <TableCell>{conflict.description}</TableCell>
                  <TableCell>{conflict.recommendation}</TableCell>
                  <TableCell>
                    {conflict.affectedTraffic && conflict.affectedTraffic.length > 0 ? (
                      <IconButton size="small" onClick={() => toggleRow(idx)}>
                        {expandedRows.has(idx) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    ) : (
                      <Typography variant="caption" color="text.secondary">N/A</Typography>
                    )}
                  </TableCell>
                </TableRow>
                {conflict.affectedTraffic && conflict.affectedTraffic.length > 0 && (
                  <TableRow key={`${idx}-detail`}>
                    <TableCell colSpan={7} sx={{ py: 0 }}>
                      <Collapse in={expandedRows.has(idx)} timeout="auto">
                        <Box sx={{ py: 2, px: 1 }}>
                          <Typography variant="subtitle2" gutterBottom>Affected Traffic Flows:</Typography>
                          <TableContainer component={Paper} variant="outlined">
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Direction</TableCell>
                                  <TableCell>Source</TableCell>
                                  <TableCell>Destination</TableCell>
                                  <TableCell>Protocol</TableCell>
                                  <TableCell>Port</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {conflict.affectedTraffic!.map((flow, fIdx) => (
                                  <TableRow key={fIdx}>
                                    <TableCell>
                                      <Chip
                                        label={flow.direction}
                                        size="small"
                                        color={flow.direction === 'ingress' ? 'primary' : 'secondary'}
                                      />
                                    </TableCell>
                                    <TableCell>{flow.source}</TableCell>
                                    <TableCell>{flow.destination}</TableCell>
                                    <TableCell>{flow.protocol}</TableCell>
                                    <TableCell>{flow.port}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                )}
              </>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}
