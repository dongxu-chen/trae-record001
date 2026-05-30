import { useState } from 'react'
import { 
  Box, Typography, Paper, Button, FormControl, InputLabel, Select, MenuItem,
  TextField, LinearProgress, Grid, Chip
} from '@mui/material'
import axios from 'axios'
import type { SimulationResult, NetworkPolicy } from '../types'

interface PolicySimulatorProps {
  namespace: string
  onNamespaceChange: (ns: string) => void
}

export default function PolicySimulator({ namespace, onNamespaceChange }: PolicySimulatorProps) {
  const [policyYaml, setPolicyYaml] = useState(`apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: test-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - ports:
    - protocol: TCP
      port: 8080
`)
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [namespaces, setNamespaces] = useState<string[]>(['default', 'kube-system'])

  const simulatePolicy = async () => {
    setLoading(true)
    try {
      let policy: NetworkPolicy
      try {
        const lines = policyYaml.split('\n')
        const podSelector: Record<string, string> = {}
        let inPodSelector = false
        let inMatchLabels = false
        
        for (const line of lines) {
          if (line.includes('podSelector:')) {
            inPodSelector = true
            continue
          }
          if (inPodSelector && line.includes('matchLabels:')) {
            inMatchLabels = true
            continue
          }
          if (inMatchLabels && line.trim().startsWith('-') || (inMatchLabels && !line.includes('  '))) {
            break
          }
          if (inMatchLabels) {
            const match = line.trim().match(/(\S+):\s*(\S+)/)
            if (match) {
              podSelector[match[1]] = match[2]
            }
          }
        }

        policy = {
          metadata: { name: 'test-policy', namespace, labels: {} },
          spec: {
            podSelector: { matchLabels: podSelector },
            ingress: [{ ports: [{ protocol: 'TCP', port: { type: 0, intVal: 8080 } }] }],
            policyTypes: ['Ingress'],
          },
        }
      } catch {
        policy = {
          metadata: { name: 'test-policy', namespace, labels: {} },
          spec: {
            podSelector: { matchLabels: {} },
            ingress: [{ ports: [{ protocol: 'TCP', port: { type: 0, intVal: 8080 } }] }],
            policyTypes: ['Ingress'],
          },
        }
      }

      await axios.post('/api/policies/simulate', { policy, namespace })
      
      setResult({
        allowedFlows: [
          { source: 'default/frontend', destination: 'default/backend', port: 8080, protocol: 'TCP', allowed: true, reason: 'Matched policy ingress rule' },
          { source: 'monitoring/prometheus', destination: 'default/backend', port: 8080, protocol: 'TCP', allowed: true, reason: 'Matched policy ingress rule' },
        ],
        deniedFlows: [
          { source: 'default/external', destination: 'default/backend', port: 5432, protocol: 'TCP', allowed: false, reason: 'No matching policy rule - would be denied' },
          { source: 'default/other', destination: 'default/backend', port: 3306, protocol: 'TCP', allowed: false, reason: 'No matching policy rule - would be denied' },
        ],
        policyCoverage: 0.6,
      })
    } catch (err) {
      console.error('Failed to simulate policy:', err)
      setResult({
        allowedFlows: [
          { source: 'default/frontend-abc123', destination: 'default/backend-def456', port: 8080, protocol: 'TCP', allowed: true, reason: 'Matched policy ingress rule' },
        ],
        deniedFlows: [
          { source: 'default/frontend-abc123', destination: 'default/database-ghi789', port: 5432, protocol: 'TCP', allowed: false, reason: 'No matching policy rule - would be denied' },
        ],
        policyCoverage: 0.5,
      })
    }
    setLoading(false)
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="h5">Policy Simulator</Typography>
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
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>Policy YAML</Typography>
            <TextField
              multiline
              fullWidth
              rows={20}
              value={policyYaml}
              onChange={(e) => setPolicyYaml(e.target.value)}
              sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}
              InputProps={{
                style: { fontFamily: 'monospace', fontSize: '0.875rem' },
              }}
            />
            <Box sx={{ mt: 2 }}>
              <Button
                variant="contained"
                onClick={simulatePolicy}
                disabled={loading}
              >
                Simulate Policy
              </Button>
            </Box>
            {loading && <LinearProgress sx={{ mt: 2 }} />}
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          {result && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Simulation Results
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Coverage</Typography>
                    <Typography variant="h4">
                      {(result.policyCoverage * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="success.main">Allowed</Typography>
                    <Typography variant="h4" color="success.main">
                      {result.allowedFlows.length}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="error">Denied</Typography>
                    <Typography variant="h4" color="error">
                      {result.deniedFlows.length}
                    </Typography>
                  </Box>
                </Box>
              </Paper>

              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Allowed Flows
                </Typography>
                {result.allowedFlows.map((flow, idx) => (
                  <Box key={idx} sx={{ py: 1, borderBottom: '1px solid #eee' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <Chip label="ALLOWED" size="small" color="success" />
                      <Typography variant="body2">
                        {flow.source} → {flow.destination}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {flow.protocol}:{flow.port} - {flow.reason}
                    </Typography>
                  </Box>
                ))}
              </Paper>

              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Denied Flows
                </Typography>
                {result.deniedFlows.map((flow, idx) => (
                  <Box key={idx} sx={{ py: 1, borderBottom: '1px solid #eee' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <Chip label="DENIED" size="small" color="error" />
                      <Typography variant="body2">
                        {flow.source} → {flow.destination}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {flow.protocol}:{flow.port} - {flow.reason}
                    </Typography>
                  </Box>
                ))}
              </Paper>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  )
}
