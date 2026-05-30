import { useEffect, useState } from 'react'
import { 
  Box, Typography, Paper, Button, FormControl, InputLabel, Select, MenuItem,
  Card, CardContent, Chip, LinearProgress, List, ListItem, ListItemText,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Alert, CircularProgress, Tabs, Tab
} from '@mui/material'
import { 
  PlayArrow as ApplyIcon, 
  Assessment as EvalIcon, 
  Backup as BackupIcon,
  Warning as WarningIcon,
  Check as CheckIcon,
  Error as ErrorIcon
} from '@mui/icons-material'
import axios from 'axios'
import type { 
  PolicyRecommendation, CoverageReport, BatchApplyResult, 
  EffectEvaluation, TrafficDelta, TrafficSummary, ApplyResult 
} from '../types'

interface PolicyRecommendationsProps {
  namespace: string
  onNamespaceChange: (ns: string) => void
}

export default function PolicyRecommendations({ namespace, onNamespaceChange }: PolicyRecommendationsProps) {
  const [recommendations, setRecommendations] = useState<PolicyRecommendation[]>([])
  const [coverage, setCoverage] = useState<CoverageReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [namespaces, setNamespaces] = useState<string[]>(['default', 'kube-system'])
  const [batchResult, setBatchResult] = useState<BatchApplyResult | null>(null)
  const [evaluation, setEvaluation] = useState<EffectEvaluation | null>(null)
  const [activeTab, setActiveTab] = useState(0)
  const [beforeSnapshot, setBeforeSnapshot] = useState<any>(null)

  useEffect(() => {
    fetchNamespaces()
    fetchRecommendations()
  }, [namespace])

  const fetchNamespaces = async () => {
    try {
      const res = await axios.get('/api/k8s/namespaces')
      setNamespaces(res.data)
    } catch (err) {
      console.error('Failed to fetch namespaces:', err)
    }
  }

  const fetchRecommendations = async () => {
    setLoading(true)
    setBatchResult(null)
    setEvaluation(null)
    try {
      const res = await axios.get(`/api/policies/${namespace}/recommend`)
      setRecommendations(res.data.recommendations || [])
      setCoverage(res.data.coverage || null)
    } catch (err) {
      console.error('Failed to fetch recommendations:', err)
      setRecommendations([
        {
          name: 'default-deny-all',
          namespace: 'default',
          description: 'Default deny all ingress and egress traffic - least privilege baseline',
          policy: {
            metadata: { name: 'default-deny-all', namespace: 'default', labels: { 'policy-type': 'default-deny' } },
            spec: {
              podSelector: { matchLabels: {} },
              policyTypes: ['Ingress', 'Egress'],
            },
          },
          reasoning: ['Enable zero-trust networking by default', 'Explicitly allow only required traffic'],
          confidence: 0.95,
          coveredPairs: [],
        },
        {
          name: 'allow-podpair-0',
          namespace: 'default',
          description: 'Allow ingress from {app:frontend} to {app:backend}',
          policy: {
            metadata: { name: 'allow-podpair-0', namespace: 'default', labels: {} },
            spec: {
              podSelector: { matchLabels: { app: 'backend' } },
              ingress: [{ from: [{ podSelector: { matchLabels: { app: 'frontend' } } }], ports: [{ protocol: 'TCP', port: { type: 0, intVal: 8080 } }] }],
              policyTypes: ['Ingress'],
            },
          },
          reasoning: ['Observed traffic from pods matching {app:frontend} to pods matching {app:backend}'],
          confidence: 0.80,
          coveredPairs: [
            { source: 'default/frontend-abc123', destination: 'default/backend-def456', protocol: 'TCP', port: 8080, sourceType: 'pod', destType: 'pod', sourceLabel: { app: 'frontend' }, destLabel: { app: 'backend' } },
          ],
        },
        {
          name: 'allow-dns-egress',
          namespace: 'default',
          description: 'Allow DNS egress traffic for name resolution',
          policy: {
            metadata: { name: 'allow-dns-egress', namespace: 'default', labels: {} },
            spec: {
              podSelector: { matchLabels: {} },
              egress: [{ ports: [{ protocol: 'UDP', port: { type: 0, intVal: 53 } }] }],
              policyTypes: ['Egress'],
            },
          },
          reasoning: ['DNS is required for service discovery in Kubernetes'],
          confidence: 0.9,
          coveredPairs: [],
        },
      ])
      setCoverage({
        totalPairs: 5,
        coveredPairs: 4,
        coverageRatio: 0.8,
        uncoveredPairs: [
          { source: 'default/frontend-abc123', destination: 'default/redis-jkl012', protocol: 'TCP', port: 6379, sourceType: 'pod', destType: 'pod', sourceLabel: { app: 'frontend' }, destLabel: { app: 'redis' } },
        ],
        coveredByPolicy: {
          'allow-podpair-0': [
            { source: 'default/frontend-abc123', destination: 'default/backend-def456', protocol: 'TCP', port: 8080, sourceType: 'pod', destType: 'pod', sourceLabel: { app: 'frontend' }, destLabel: { app: 'backend' } },
          ],
        },
      })
    }
    setLoading(false)
  }

  const createBackup = async () => {
    try {
      const res = await axios.post(`/api/policies/${namespace}/backup`, { reason: 'pre-apply-backup' })
      alert(`Backup created: ${res.data.id}`)
      return res.data
    } catch (err) {
      console.error('Failed to create backup:', err)
      alert('Failed to create backup')
      throw err
    }
  }

  const takeBeforeSnapshot = async () => {
    try {
      const res = await axios.post(`/api/policies/${namespace}/snapshot`)
      setBeforeSnapshot(res.data)
      return res.data
    } catch (err) {
      console.error('Failed to take snapshot:', err)
      throw err
    }
  }

  const applyAllPolicies = async () => {
    if (!window.confirm(`Apply all ${recommendations.length} recommended policies? A backup will be created first.`)) {
      return
    }

    setApplying(true)
    setBatchResult(null)
    try {
      await takeBeforeSnapshot()

      const res = await axios.post(`/api/policies/${namespace}/batch-apply`, {
        recommendations: recommendations
      })
      setBatchResult(res.data)

      if (res.data.failedCount > 0) {
        alert(`Applied ${res.data.successCount}/${res.data.totalPolicies} policies. ${res.data.failedCount} failed. Backup ID: ${res.data.backupId}`)
      } else {
        alert(`Successfully applied all ${res.data.totalPolicies} policies! Backup ID: ${res.data.backupId}`)
      }
    } catch (err) {
      console.error('Failed to apply policies:', err)
      alert('Failed to apply policies')
    }
    setApplying(false)
  }

  const evaluatePolicyEffect = async () => {
    if (!beforeSnapshot && !batchResult) {
      alert('Please apply policies first, or take a before snapshot')
      return
    }

    setEvaluating(true)
    setEvaluation(null)
    try {
      const waitSeconds = 5
      const res = await axios.post(`/api/policies/${namespace}/evaluate`, {
        backupId: batchResult?.backupId || '',
        waitSeconds: waitSeconds
      })
      setEvaluation(res.data)
      setActiveTab(1)
    } catch (err) {
      console.error('Failed to evaluate effect:', err)
      alert('Failed to evaluate effect')
    }
    setEvaluating(false)
  }

  const getSeverityColor = (confidence: number) => {
    if (confidence >= 0.9) return 'success'
    if (confidence >= 0.7) return 'primary'
    return 'warning'
  }

  const getApplyResultIcon = (status: string) => {
    if (status === 'success') return <CheckIcon color="success" />
    return <ErrorIcon color="error" />
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Typography variant="h5">Policy Recommendations</Typography>
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
        <Button variant="contained" onClick={fetchRecommendations} disabled={applying || evaluating}>
          Refresh
        </Button>
        <Button 
          variant="contained" 
          color="success" 
          onClick={applyAllPolicies}
          disabled={applying || recommendations.length === 0}
          startIcon={applying ? <CircularProgress size={16} /> : <ApplyIcon />}
        >
          {applying ? 'Applying...' : `Apply All (${recommendations.length})`}
        </Button>
        <Button 
          variant="contained" 
          color="info" 
          onClick={evaluatePolicyEffect}
          disabled={evaluating || (!beforeSnapshot && !batchResult)}
          startIcon={evaluating ? <CircularProgress size={16} /> : <EvalIcon />}
        >
          {evaluating ? 'Evaluating...' : 'Evaluate Effect'}
        </Button>
        <Button 
          variant="outlined" 
          onClick={createBackup}
          startIcon={<BackupIcon />}
        >
          Create Backup
        </Button>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {batchResult && (
        <Alert 
          severity={batchResult.failedCount > 0 ? 'warning' : 'success'} 
          sx={{ mb: 3 }}
          icon={batchResult.failedCount > 0 ? <WarningIcon /> : <CheckIcon />}
        >
          <Typography variant="subtitle2">
            Batch Apply Complete — {batchResult.successCount}/{batchResult.totalPolicies} succeeded, {batchResult.failedCount} failed
          </Typography>
          <Typography variant="body2">Backup ID: {batchResult.backupId}</Typography>
          {batchResult.results.some((r: ApplyResult) => r.error) && (
            <Box sx={{ mt: 1 }}>
              {batchResult.results.filter((r: ApplyResult) => r.error).map((r: ApplyResult, idx: number) => (
                <Typography key={idx} variant="caption" color="error" display="block">
                  • {r.policyName}: {r.error}
                </Typography>
              ))}
            </Box>
          )}
        </Alert>
      )}

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
          <Tab label="Recommendations" />
          <Tab label={`Effect Evaluation${evaluation ? ' ✓' : ''}`} disabled={!evaluation} />
        </Tabs>
      </Box>

      {activeTab === 0 && (
        <>
          {coverage && (
            <Paper sx={{ p: 2, mb: 3 }}>
              <Typography variant="h6" gutterBottom>Coverage Report</Typography>
              <Box sx={{ display: 'flex', gap: 3, mb: 2, flexWrap: 'wrap' }}>
                <Box>
                  <Typography variant="body2" color="text.secondary">Total Communication Pairs</Typography>
                  <Typography variant="h4">{coverage.totalPairs}</Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="success.main">Covered</Typography>
                  <Typography variant="h4" color="success.main">{coverage.coveredPairs}</Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="error">Uncovered</Typography>
                  <Typography variant="h4" color="error">{coverage.uncoveredPairs?.length || 0}</Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">Coverage Ratio</Typography>
                  <Typography variant="h4">{(coverage.coverageRatio * 100).toFixed(0)}%</Typography>
                </Box>
              </Box>
              <Box sx={{ width: '100%', bgcolor: '#e0e0e0', borderRadius: 1, height: 8 }}>
                <Box sx={{ width: `${coverage.coverageRatio * 100}%`, bgcolor: 'success.main', borderRadius: 1, height: 8 }} />
              </Box>
              {coverage.uncoveredPairs && coverage.uncoveredPairs.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" color="error" gutterBottom>Uncovered Communication Pairs:</Typography>
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Source</TableCell>
                          <TableCell>Destination</TableCell>
                          <TableCell>Protocol</TableCell>
                          <TableCell>Port</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {coverage.uncoveredPairs.map((pair, idx) => (
                          <TableRow key={idx}>
                            <TableCell>{pair.source}</TableCell>
                            <TableCell>{pair.destination}</TableCell>
                            <TableCell>{pair.protocol}</TableCell>
                            <TableCell>{pair.port}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}
            </Paper>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {recommendations.map((rec, recIdx) => (
              <Card key={rec.name} elevation={2}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                    <Box sx={{ flex: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {batchResult && batchResult.results[recIdx] && getApplyResultIcon(batchResult.results[recIdx].status)}
                        <Typography variant="h6" gutterBottom sx={{ mb: 0 }}>
                          {rec.name}
                        </Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {rec.description}
                      </Typography>
                      
                      <Chip
                        label={`${(rec.confidence * 100).toFixed(0)}% confidence`}
                        color={getSeverityColor(rec.confidence) as 'success' | 'primary' | 'warning'}
                        size="small"
                        sx={{ mr: 1, mb: 2 }}
                      />

                      {rec.coveredPairs && rec.coveredPairs.length > 0 && (
                        <Chip
                          label={`Covers ${rec.coveredPairs.length} pairs`}
                          color="info"
                          size="small"
                          sx={{ mr: 1, mb: 2 }}
                        />
                      )}

                      <Typography variant="subtitle2" gutterBottom>Reasoning:</Typography>
                      <List dense disablePadding sx={{ mb: 2 }}>
                        {rec.reasoning.map((r, i) => (
                          <ListItem key={i} disableGutters>
                            <ListItemText primary={`• ${r}`} sx={{ my: 0 }} />
                          </ListItem>
                        ))}
                      </List>

                      {rec.coveredPairs && rec.coveredPairs.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="subtitle2" gutterBottom>Covered Communication Pairs:</Typography>
                          <TableContainer component={Paper} variant="outlined">
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Source</TableCell>
                                  <TableCell>Destination</TableCell>
                                  <TableCell>Protocol</TableCell>
                                  <TableCell>Port</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {rec.coveredPairs.map((pair, idx) => (
                                  <TableRow key={idx}>
                                    <TableCell>{pair.source}</TableCell>
                                    <TableCell>{pair.destination}</TableCell>
                                    <TableCell>{pair.protocol}</TableCell>
                                    <TableCell>{pair.port}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        </Box>
                      )}

                      <Paper variant="outlined" sx={{ p: 2, bgcolor: '#f5f5f5' }}>
                        <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap', fontSize: '0.75rem' }}>
                          {JSON.stringify(rec.policy.spec, null, 2)}
                        </Typography>
                      </Paper>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        </>
      )}

      {activeTab === 1 && evaluation && (
        <Box>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>Policy Effect Evaluation</Typography>
            <Typography variant="caption" color="text.secondary" gutterBottom display="block">
              Evaluated at: {new Date(evaluation.evaluationTime).toLocaleString()}
            </Typography>
            {evaluation.backupId && (
              <Typography variant="caption" color="text.secondary" display="block">
                Backup ID: {evaluation.backupId}
              </Typography>
            )}
            
            <Box sx={{ display: 'flex', gap: 3, mb: 3, mt: 2, flexWrap: 'wrap' }}>
              <Box>
                <Typography variant="body2" color="text.secondary">Flows Before</Typography>
                <Typography variant="h4">{evaluation.totalFlowsBefore}</Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">Flows After</Typography>
                <Typography variant="h4">{evaluation.totalFlowsAfter}</Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="error">Blocked/Lost Flows</Typography>
                <Typography variant="h4" color="error">{evaluation.blockedFlowCount}</Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="success.main">New Flows</Typography>
                <Typography variant="h4" color="success.main">{evaluation.newFlowCount}</Typography>
              </Box>
            </Box>

            {evaluation.blockedFlowCount > 0 && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                <WarningIcon sx={{ mr: 1 }} />
                {evaluation.blockedFlowCount} flow(s) were blocked or lost after policy application. Consider rolling back if this is unexpected.
              </Alert>
            )}

            {evaluation.lostFlows.length > 0 && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom color="error">Blocked / Lost Flows:</Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Source</TableCell>
                        <TableCell>Destination</TableCell>
                        <TableCell>Protocol</TableCell>
                        <TableCell>Port</TableCell>
                        <TableCell align="right">Last Count</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {evaluation.lostFlows.map((flow: TrafficSummary, idx: number) => (
                        <TableRow key={idx}>
                          <TableCell>{flow.source}</TableCell>
                          <TableCell>{flow.destination}</TableCell>
                          <TableCell>{flow.protocol}</TableCell>
                          <TableCell>{flow.port}</TableCell>
                          <TableCell align="right">{flow.count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {evaluation.changedFlows.length > 0 && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>Changed Flow Counts:</Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Source</TableCell>
                        <TableCell>Destination</TableCell>
                        <TableCell>Protocol</TableCell>
                        <TableCell>Port</TableCell>
                        <TableCell align="right">Before</TableCell>
                        <TableCell align="right">After</TableCell>
                        <TableCell align="right">Delta</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {evaluation.changedFlows.map((flow: TrafficDelta, idx: number) => (
                        <TableRow key={idx}>
                          <TableCell>{flow.source}</TableCell>
                          <TableCell>{flow.destination}</TableCell>
                          <TableCell>{flow.protocol}</TableCell>
                          <TableCell>{flow.port}</TableCell>
                          <TableCell align="right">{flow.countBefore}</TableCell>
                          <TableCell align="right">{flow.countAfter}</TableCell>
                          <TableCell align="right" sx={{ color: flow.delta < 0 ? 'error.main' : 'success.main' }}>
                            {flow.delta > 0 ? `+${flow.delta}` : flow.delta}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {evaluation.newFlows.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom color="success.main">New Flows After Policy:</Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Source</TableCell>
                        <TableCell>Destination</TableCell>
                        <TableCell>Protocol</TableCell>
                        <TableCell>Port</TableCell>
                        <TableCell align="right">Count</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {evaluation.newFlows.map((flow: TrafficSummary, idx: number) => (
                        <TableRow key={idx}>
                          <TableCell>{flow.source}</TableCell>
                          <TableCell>{flow.destination}</TableCell>
                          <TableCell>{flow.protocol}</TableCell>
                          <TableCell>{flow.port}</TableCell>
                          <TableCell align="right">{flow.count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </Paper>
        </Box>
      )}
    </Box>
  )
}
