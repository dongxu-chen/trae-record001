import React, { useState, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Box,
  Typography,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
} from '@mui/material';
import type { ServiceTopology } from '../types';
import { topologyApi } from '../services/api';

const getNodeColor = (health: string) => {
  switch (health) {
    case 'healthy':
      return '#4caf50';
    case 'degraded':
      return '#ff9800';
    case 'unhealthy':
      return '#f44336';
    default:
      return '#2196f3';
  }
};

const CustomNode = ({ data }: any) => {
  return (
    <div
      style={{
        padding: '10px 16px', borderRadius: 8, border: '2px solid #e0e0e0', backgroundColor: '#fff', minWidth: 120, textAlign: 'center',
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>{data.label}</div>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 4 }}>
        <Chip
          size="small"
          label={data.type}
          sx={{ fontSize: 10 }}
        />
        <Chip
          size="small"
          label={data.health}
          sx={{
            fontSize: 10,
            backgroundColor: getNodeColor(data.health),
            color: '#fff',
          }}
        />
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

const Topology: React.FC = () => {
  const [topology, setTopology] = useState<ServiceTopology | null>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [namespace, setNamespace] = useState('default');
  const [namespaces, setNamespaces] = useState<string[]>(['default', 'istio-system']);

  useEffect(() => {
    loadNamespaces();
  }, []);

  useEffect(() => {
    loadTopology();
  }, [namespace]);

  const loadNamespaces = async () => {
    try {
      const response = await topologyApi.getNamespaces();
      setNamespaces(response.data.namespaces);
    } catch (error) {
      console.error('Failed to load namespaces:', error);
    }
  };

  const loadTopology = async () => {
    try {
      const response = await topologyApi.getTopology([namespace]);
      setTopology(response.data);

      const flowNodes: Node[] = response.data.nodes.map((node, index) => ({
        id: node.id,
        type: 'custom',
        position: { x: 150 + (index % 3) * 200, y: 100 + Math.floor(index / 3) * 150,
        data: {
          label: node.name,
          type: node.type,
          health: node.health,
        },
        style: {
          borderColor: getNodeColor(node.health),
        },
      }));

      const flowEdges: Edge[] = response.data.edges.map((edge) => ({
        id: `${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        label: `${edge.traffic} req/s`,
        animated: true,
        style: {
          stroke: '#1976d2',
        },
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (error) {
      console.error('Failed to load topology:', error);
      setNodes([
        {
          id: 'n1',
          type: 'custom',
          position: { x: 250, y: 50 },
          data: { label: 'frontend', type: 'service', health: 'healthy' },
        },
        {
          id: 'n2',
          type: 'custom',
          position: { x: 100, y: 200 },
          data: { label: 'productpage', type: 'workload', health: 'healthy' },
        },
        {
          id: 'n3',
          type: 'custom',
          position: { x: 400, y: 200 },
          data: { label: 'api-gateway', type: 'service', health: 'degraded' },
        },
        {
          id: 'n4',
          type: 'custom',
          position: { x: 100, y: 350 },
          data: { label: 'backend', type: 'workload', health: 'healthy' },
        },
        {
          id: 'n5',
          type: 'custom',
          position: { x: 400, y: 350 },
          data: { label: 'database', type: 'service', health: 'healthy' },
        },
      ]);
      setEdges([
        { id: 'e1', source: 'n1', target: 'n2', label: '500 req/s', animated: true },
        { id: 'e2', source: 'n1', target: 'n3', label: '300 req/s', animated: true },
        { id: 'e3', source: 'n3', target: 'n4', label: '200 req/s', animated: true },
        { id: 'e4', source: 'n4', target: 'n5', label: '150 req/s', animated: true },
      ]);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        服务拓扑
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>命名空间</InputLabel>
              <Select
                value={namespace}
                label="命名空间"
                onChange={(e) => setNamespace(e.target.value)}
              >
                {namespaces.map((ns) => (
                  <MenuItem key={ns} value={ns}>
                    {ns}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <Chip label="服务" sx={{ backgroundColor: '#2196f3', color: '#fff' }} />
            <Chip label="工作负载" sx={{ backgroundColor: '#9c27b0', color: '#fff' }} />
            <Chip label="健康" sx={{ backgroundColor: '#4caf50', color: '#fff' }} />
            <Chip label="降级" sx={{ backgroundColor: '#ff9800', color: '#fff' }} />
            <Chip label="异常" sx={{ backgroundColor: '#f44336', color: '#fff' }} />
          </Box>

          <Box sx={{ height: 500, border: '1px solid #e0e0e0', borderRadius: 1 }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              fitView
            >
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Topology;
