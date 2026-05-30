import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  FormControlLabel,
  Switch,
  Chip,
} from '@mui/material';
import { getTableLineage, getColumnLineage, getAllTables, getTableColumns, getColumnMappingChains, expandAggregatedEdge } from '../services/api';

const getNodeColor = (nodeType) => {
  switch (nodeType) {
    case 'source':
      return { border: '#2e7d32', bg: '#e8f5e9', text: '#2e7d32' };
    case 'target':
      return { border: '#c62828', bg: '#ffebee', text: '#c62828' };
    case 'cte':
      return { border: '#f57c00', bg: '#fff3e0', text: '#e65100' };
    case 'subquery':
      return { border: '#7b1fa2', bg: '#f3e5f5', text: '#6a1b9a' };
    case 'intermediate':
    default:
      return { border: '#1976d2', bg: '#e3f2fd', text: '#1976d2' };
  }
};

const TableNode = ({ data }) => {
  const colors = getNodeColor(data.node_type);
  const typeLabel = {
    source: '源表',
    target: '目标表',
    cte: 'CTE',
    subquery: '子查询',
    intermediate: '中间表',
  }[data.node_type] || '表';

  return (
    <div style={{
      padding: '10px',
      borderRadius: '6px',
      border: `2px solid ${colors.border}`,
      backgroundColor: colors.bg,
      minWidth: '150px',
      textAlign: 'center',
      boxShadow: data.is_intermediate ? 'none' : '0 2px 6px rgba(0,0,0,0.1)',
      opacity: data.is_intermediate ? 0.85 : 1,
    }}>
      <div style={{ fontWeight: 'bold', color: colors.text, fontSize: '13px' }}>
        {data.label}
      </div>
      <div style={{ fontSize: '11px', color: colors.text, marginTop: '2px', fontWeight: 500 }}>
        {typeLabel}
      </div>
      {data.alias_chain && data.alias_chain.length > 0 && (
        <div style={{ fontSize: '9px', color: '#999', marginTop: '2px' }}>
          别名: {data.alias_chain.join('←')}
        </div>
      )}
    </div>
  );
};

const ColumnNode = ({ data }) => {
  const colors = getNodeColor(data.node_type);
  const typeLabel = {
    source: '源字段',
    target: '目标字段',
    cte: 'CTE字段',
    subquery: '子查询字段',
    intermediate: '中间字段',
  }[data.node_type] || '字段';

  return (
    <div style={{
      padding: '8px',
      borderRadius: '5px',
      border: `2px solid ${colors.border}`,
      backgroundColor: colors.bg,
      minWidth: '130px',
      textAlign: 'center',
      fontSize: '12px',
      boxShadow: data.is_intermediate ? 'none' : '0 2px 4px rgba(0,0,0,0.1)',
      opacity: data.is_intermediate ? 0.85 : 1,
    }}>
      <div style={{ fontWeight: 'bold', color: colors.text }}>{data.label}</div>
      <div style={{ fontSize: '10px', color: colors.text, marginTop: '2px' }}>{typeLabel}</div>
    </div>
  );
};

const nodeTypes = {
  table: TableNode,
  column: ColumnNode,
};

function LineagePage() {
  const navigate = useNavigate();
  const [lineageType, setLineageType] = useState('table');
  const [tables, setTables] = useState([]);
  const [columns, setColumns] = useState([]);
  const [selectedTable, setSelectedTable] = useState('');
  const [selectedColumn, setSelectedColumn] = useState('');
  const [depth, setDepth] = useState(3);
  const [collapseIntermediate, setCollapseIntermediate] = useState(true);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [error, setError] = useState('');
  const [mappingChains, setMappingChains] = useState([]);
  const [showMappingChains, setShowMappingChains] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    loadTables();
  }, []);

  useEffect(() => {
    if (selectedTable) {
      loadColumns(selectedTable);
    }
  }, [selectedTable]);

  const loadTables = async () => {
    try {
      const response = await getAllTables();
      setTables(response.data.tables);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
  };

  const loadColumns = async (tableName) => {
    try {
      const response = await getTableColumns(tableName);
      setColumns(response.data.columns);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
  };

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const layoutNodes = (nodes, edges) => {
    const levels = {};
    const nodeMap = {};
    
    nodes.forEach(node => {
      nodeMap[node.id] = node;
      levels[node.id] = 0;
    });

    let changed = true;
    let iterations = 0;
    while (changed && iterations < 100) {
      changed = false;
      iterations++;
      edges.forEach(edge => {
        const sourceLevel = levels[edge.source] || 0;
        if ((levels[edge.target] || 0) <= sourceLevel) {
          levels[edge.target] = sourceLevel + 1;
          changed = true;
        }
      });
    }

    const maxLevel = Math.max(...Object.values(levels), 0);
    const levelWidth = collapseIntermediate ? 300 : 250;
    const nodeHeight = 90;

    const levelNodes = {};
    Object.entries(levels).forEach(([id, level]) => {
      if (!levelNodes[level]) levelNodes[level] = [];
      levelNodes[level].push(id);
    });

    return nodes.map(node => ({
      ...node,
      draggable: true,
      position: {
        x: levels[node.id] * levelWidth + 50,
        y: (levelNodes[levels[node.id]].indexOf(node.id)) * nodeHeight + 50,
      },
    }));
  };

  const handleEdgeClick = useCallback(async (event, edge) => {
    if (edge.data?.is_collapsed && edge.data?.intermediate_nodes) {
      try {
        const expandResponse = await expandAggregatedEdge(edge.source, edge.target);
        const expandedData = expandResponse.data;
        
        const existingNodeIds = new Set(nodes.map(n => n.id));
        const newNodes = expandedData.nodes.filter(n => !existingNodeIds.has(n.id));
        const laidOutNewNodes = layoutNodes(newNodes, expandedData.edges);
        
        setNodes(nds => [
          ...nds,
          ...laidOutNewNodes.map(node => ({
            ...node,
            data: {
              ...node.data,
              label: node.label,
              node_type: node.node_type,
              is_intermediate: node.is_intermediate,
            },
          })),
        ]);
        
        setEdges(eds => {
          const filteredEdges = eds.filter(e => e.id !== edge.id);
          const strokeColor = lineageType === 'table' ? '#1976d2' : '#388e3c';
          return [
            ...filteredEdges,
            ...expandedData.edges.map(e => ({
              ...e,
              animated: true,
              style: { stroke: strokeColor, strokeWidth: 2 },
              markerEnd: { type: MarkerType.ArrowClosed, color: strokeColor },
              data: { ...e, is_collapsed: false },
            })),
          ];
        });
      } catch (err) {
        console.error('Failed to expand edge:', err);
      }
    }
  }, [nodes, setNodes, setEdges, lineageType]);

  const handleNodeClick = useCallback(async (event, node) => {
    setSelectedNode(node);
    
    if (node.type === 'column') {
      try {
        const response = await getColumnMappingChains(node.id);
        setMappingChains(response.data.mapping_chains || []);
        setShowMappingChains(true);
      } catch (err) {
        console.error('Failed to load mapping chains:', err);
      }
    }
  }, []);

  const loadTableLineage = async () => {
    if (!selectedTable) return;
    setError('');
    try {
      const response = await getTableLineage(selectedTable, depth, collapseIntermediate);
      const graphData = response.data;
      
      const laidOutNodes = layoutNodes(graphData.nodes, graphData.edges);
      
      const styledNodes = laidOutNodes.map(node => ({
        ...node,
        data: {
          ...node.data,
          label: node.label,
          node_type: node.node_type,
          is_intermediate: node.is_intermediate,
          alias_chain: node.data?.alias_chain,
        },
      }));
      
      const styledEdges = graphData.edges.map(edge => {
        const isAggregated = edge.type?.startsWith('AGGREGATED');
        const strokeColor = isAggregated ? '#9e9e9e' : '#1976d2';
        
        return {
          ...edge,
          animated: !isAggregated,
          style: {
            stroke: strokeColor,
            strokeWidth: isAggregated ? 3 : 2,
            strokeDasharray: isAggregated ? '8,4' : 'none',
            cursor: isAggregated ? 'pointer' : 'default',
          },
          label: isAggregated ? `折叠 ${edge.intermediate_count} 层` : undefined,
          labelStyle: { fill: '#666', fontSize: 10 },
          markerEnd: { type: MarkerType.ArrowClosed, color: strokeColor },
          data: {
            ...edge,
            is_collapsed: edge.is_collapsed,
            intermediate_count: edge.intermediate_count,
            intermediate_nodes: edge.intermediate_nodes,
          },
        };
      });

      setNodes(styledNodes);
      setEdges(styledEdges);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
  };

  const loadColumnLineage = async () => {
    if (!selectedColumn) return;
    setError('');
    try {
      const response = await getColumnLineage(selectedColumn, depth, collapseIntermediate);
      const graphData = response.data;
      
      const laidOutNodes = layoutNodes(graphData.nodes, graphData.edges);
      
      const styledNodes = laidOutNodes.map(node => ({
        ...node,
        data: {
          ...node.data,
          label: node.label,
          node_type: node.node_type,
          is_intermediate: node.is_intermediate,
        },
      }));
      
      const styledEdges = graphData.edges.map(edge => {
        const isAggregated = edge.type?.startsWith('AGGREGATED');
        const strokeColor = isAggregated ? '#9e9e9e' : '#388e3c';
        
        return {
          ...edge,
          animated: !isAggregated,
          style: {
            stroke: strokeColor,
            strokeWidth: isAggregated ? 3 : 2,
            strokeDasharray: isAggregated ? '8,4' : 'none',
            cursor: isAggregated ? 'pointer' : 'default',
          },
          label: isAggregated ? `折叠 ${edge.intermediate_count} 层` : undefined,
          labelStyle: { fill: '#666', fontSize: 10 },
          markerEnd: { type: MarkerType.ArrowClosed, color: strokeColor },
          data: {
            ...edge,
            is_collapsed: edge.is_collapsed,
            intermediate_count: edge.intermediate_count,
            intermediate_nodes: edge.intermediate_nodes,
          },
        };
      });

      setNodes(styledNodes);
      setEdges(styledEdges);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
  };

  const stats = {
    totalNodes: nodes.length,
    totalEdges: edges.length,
    sourceNodes: nodes.filter(n => n.node_type === 'source').length,
    targetNodes: nodes.filter(n => n.node_type === 'target').length,
    cteNodes: nodes.filter(n => n.node_type === 'cte').length,
    aggregatedEdges: edges.filter(e => e.data?.is_collapsed).length,
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        血缘查询
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Button
                variant="outlined"
                onClick={() => navigate('/')}
                sx={{ mb: 2 }}
                fullWidth
              >
                返回解析
              </Button>

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>血缘类型</InputLabel>
                <Select
                  value={lineageType}
                  label="血缘类型"
                  onChange={(e) => setLineageType(e.target.value)}
                >
                  <MenuItem value="table">表级血缘</MenuItem>
                  <MenuItem value="column">字段级血缘</MenuItem>
                </Select>
              </FormControl>

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>选择表</InputLabel>
                <Select
                  value={selectedTable}
                  label="选择表"
                  onChange={(e) => setSelectedTable(e.target.value)}
                >
                  {tables.map(table => (
                    <MenuItem key={table.full_name} value={table.full_name}>
                      {table.full_name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {lineageType === 'column' && (
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>选择字段</InputLabel>
                  <Select
                    value={selectedColumn}
                    label="选择字段"
                    onChange={(e) => setSelectedColumn(e.target.value)}
                  >
                    {columns.map(column => (
                      <MenuItem key={column.full_name} value={column.full_name}>
                        {column.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}

              <TextField
                label="查询深度"
                type="number"
                value={depth}
                onChange={(e) => setDepth(parseInt(e.target.value) || 1)}
                fullWidth
                sx={{ mb: 2 }}
                inputProps={{ min: 1, max: 10 }}
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={collapseIntermediate}
                    onChange={(e) => setCollapseIntermediate(e.target.checked)}
                    color="primary"
                  />
                }
                label={collapseIntermediate ? '折叠中间层' : '展开中间层'}
                sx={{ mb: 2, display: 'block' }}
              />

              <Button
                variant="contained"
                onClick={lineageType === 'table' ? loadTableLineage : loadColumnLineage}
                fullWidth
              >
                查询血缘
              </Button>

              {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {error}
                </Alert>
              )}

              {nodes.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
                    查询结果
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    <Chip label={`节点: ${stats.totalNodes}`} size="small" />
                    <Chip label={`边: ${stats.totalEdges}`} size="small" />
                    {stats.sourceNodes > 0 && (
                      <Chip label={`源: ${stats.sourceNodes}`} size="small" color="success" />
                    )}
                    {stats.targetNodes > 0 && (
                      <Chip label={`目标: ${stats.targetNodes}`} size="small" color="error" />
                    )}
                    {stats.cteNodes > 0 && (
                      <Chip label={`CTE: ${stats.cteNodes}`} size="small" color="warning" />
                    )}
                    {stats.aggregatedEdges > 0 && (
                      <Chip label={`折叠边: ${stats.aggregatedEdges}`} size="small" />
                    )}
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={9}>
          <Card sx={{ height: '75vh' }}>
            <CardContent sx={{ height: '100%', padding: 0 }}>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onEdgeClick={handleEdgeClick}
                onNodeClick={handleNodeClick}
                nodeTypes={nodeTypes}
                fitView
                proOptions={{ hideAttribution: true }}
              >
                <MiniMap
                  nodeColor={(node) => {
                    const colors = getNodeColor(node.data?.node_type);
                    return colors.bg;
                  }}
                />
                <Controls />
                <Background />
              </ReactFlow>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default LineagePage;
