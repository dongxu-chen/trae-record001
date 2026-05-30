import { useEffect, useState } from 'react'
import { Box, Typography, Paper, Select, MenuItem, FormControl, InputLabel } from '@mui/material'
import CytoscapeComponent from 'react-cytoscapejs'
import axios from 'axios'
import type { PodNode, FlowEdge } from '../types'

interface TopologyViewProps {
  namespace: string
  onNamespaceChange: (ns: string) => void
}

export default function TopologyView({ namespace, onNamespaceChange }: TopologyViewProps) {
  const [pods, setPods] = useState<PodNode[]>([])
  const [flows, setFlows] = useState<FlowEdge[]>([])
  const [namespaces, setNamespaces] = useState<string[]>(['default', 'kube-system'])

  useEffect(() => {
    fetchTopology()
    fetchNamespaces()
  }, [namespace])

  const fetchNamespaces = async () => {
    try {
      const res = await axios.get('/api/k8s/namespaces')
      setNamespaces(res.data)
    } catch (err) {
      console.error('Failed to fetch namespaces:', err)
    }
  }

  const fetchTopology = async () => {
    try {
      const res = await axios.get(namespace ? `/api/topology/namespace/${namespace}` : '/api/topology')
      setPods(res.data.pods || [])
      setFlows(res.data.flows || [])
    } catch (err) {
      console.error('Failed to fetch topology:', err)
      setPods([
        { name: 'frontend-abc123', namespace: 'default', labels: { app: 'frontend' }, ip: '10.0.0.1', podSelector: {} },
        { name: 'backend-def456', namespace: 'default', labels: { app: 'backend' }, ip: '10.0.0.2', podSelector: {} },
        { name: 'database-ghi789', namespace: 'default', labels: { app: 'database' }, ip: '10.0.0.3', podSelector: {} },
      ])
      setFlows([
        { sourceName: 'frontend-abc123', sourceNamespace: 'default', destName: 'backend-def456', destNamespace: 'default', protocol: 'TCP', port: 8080, count: 100, lastSeen: '' },
        { sourceName: 'backend-def456', sourceNamespace: 'default', destName: 'database-ghi789', destNamespace: 'default', protocol: 'TCP', port: 5432, count: 75, lastSeen: '' },
      ])
    }
  }

  const elements = [
    ...pods.map((pod) => ({
      data: {
        id: pod.name,
        label: pod.name,
        namespace: pod.namespace,
        type: 'pod',
      },
    })),
    ...flows.map((flow, idx) => ({
      data: {
        id: `flow-${idx}`,
        source: flow.sourceName,
        target: flow.destName,
        label: `${flow.protocol}:${flow.port}`,
        count: flow.count,
      },
    })),
  ]

  const layout = {
    name: 'cose',
    animate: true,
    nodeRepulsion: 400000,
    nodeOverlap: 20,
    idealEdgeLength: 100,
    edgeElasticity: 100,
    padding: 30,
  }

  const stylesheet = [
    {
      selector: 'node',
      style: {
        'background-color': '#1976d2',
        label: 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'font-size': '12px',
        'text-outline-width': 2,
        'text-outline-color': '#fff',
        width: 60,
        height: 60,
      },
    },
    {
      selector: 'edge',
      style: {
        width: 2,
        'line-color': '#999',
        'target-arrow-color': '#999',
        'target-arrow-shape': 'triangle',
        label: 'data(label)',
        'font-size': '10px',
        'text-rotation': 'autorotate',
        'curve-style': 'bezier',
      },
    },
  ]

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="h5">Network Topology</Typography>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Namespace</InputLabel>
          <Select
            value={namespace}
            label="Namespace"
            onChange={(e) => onNamespaceChange(e.target.value as string)}
          >
            <MenuItem value="">All</MenuItem>
            {namespaces.map((ns) => (
              <MenuItem key={ns} value={ns}>{ns}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Paper elevation={3} sx={{ height: 600, p: 2 }}>
        <CytoscapeComponent
          elements={elements}
          style={{ width: '100%', height: '100%' }}
          stylesheet={stylesheet}
          layout={layout}
        />
      </Paper>

      <Box sx={{ mt: 3, display: 'flex', gap: 3 }}>
        <Paper sx={{ p: 2, flex: 1 }}>
          <Typography variant="h6" gutterBottom>Pods ({pods.length})</Typography>
          {pods.map((pod) => (
            <Box key={pod.name} sx={{ py: 1, borderBottom: '1px solid #eee' }}>
              <Typography variant="body2">
                <strong>{pod.name}</strong> ({pod.namespace})
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {pod.ip} | {JSON.stringify(pod.labels)}
              </Typography>
            </Box>
          ))}
        </Paper>
        <Paper sx={{ p: 2, flex: 1 }}>
          <Typography variant="h6" gutterBottom>Flows ({flows.length})</Typography>
          {flows.slice(0, 8).map((flow, idx) => (
            <Box key={idx} sx={{ py: 1, borderBottom: '1px solid #eee' }}>
              <Typography variant="body2">
                {flow.sourceName} → {flow.destName}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {flow.protocol}:{flow.port} ({flow.count} pkts)
              </Typography>
            </Box>
          ))}
        </Paper>
      </Box>
    </Box>
  )
}
