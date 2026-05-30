import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Panel,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Box,
  Button,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  FormControlLabel,
  Tooltip,
  Chip,
  Paper,
  Divider,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import UnfoldMoreIcon from '@mui/icons-material/UnfoldMore';
import FoldMoreIcon from '@mui/icons-material/FoldMore';
import { getFullGraph, clearDatabase, expandAggregatedEdge, getColumnMappingChains } from '../services/api';

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
      padding: '12px',
      borderRadius: '8px',
      border: `3px solid ${colors.border}`,
      backgroundColor: colors.bg,
      minWidth: '180px',
      textAlign: 'center',
      boxShadow: data.is_intermediate ? 'none' : '0 2px 8px rgba(0,0,0,0.15)',
      opacity: data.is_intermediate ? 0.8 : 1,
    }}>
      <div style={{ fontWeight: 'bold', color: colors.text, fontSize: '14px' }}>
        {data.label}
      </div>
      <div style={{ fontSize: '10px', color: colors.text, marginTop: '4px', fontWeight: 500 }}>
        {typeLabel}
      </div>
      {data.alias_chain && data.alias_chain.length > 0 && (
        <div style={{ fontSize: '9px', color: '#999', marginTop: '2px' }}>
          别名链: {data.alias_chain.join(' ← ')}
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
      borderRadius: '6px',
      border: `2px solid ${colors.border}`,
      backgroundColor: colors.bg,
      minWidth: '140px',
      textAlign: 'center',
      boxShadow: data.is_intermediate ? 'none' : '0 2px 6px rgba(0,0,0,0.1)',
      opacity: data.is_intermediate ? 0.8 : 1,
    }}>
      <div style={{ fontWeight: 'bold', color: colors.text, fontSize: '12px' }}>
        {data.label}
      </div>
      <div style={{ fontSize: '9px', color: colors.text, marginTop: '2px', fontWeight: 500 }}>
        {typeLabel}
      </div>
    </div>
  );
};

const AggregatedEdge = ({ data, source, target, onClick }) => {
  return (
    <g>
      <path
        d={`M ${source.x} ${source.y} L ${target.x} ${target.y}`}
        fill="none"
        stroke="#9e9e9e"
        strokeWidth="4"
        strokeDasharray="8,4"
        markerEnd="url(#arrowhead-gray)"
        style={{ cursor: 'pointer' }}
        onClick={onClick}
      />
      <text
        x={(source.x + target.x) / 2}
        y={(source.y + target.y) / 2 - 10}
        textAnchor="middle"
        fill="#666"
        fontSize="10"
        style={{ cursor: 'pointer' }}
        onClick={onClick}
      >
        折叠 {data?.intermediate_count || 0} 层 →
      </text>
    </g>
  );
};

const nodeTypes = {
  table: TableNode,
  column: ColumnNode,
};

function GraphPage() {
  const navigate = useNavigate();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [showType, setShowType] = useState('all');
  const [collapseIntermediate, setCollapseIntermediate] = useState(true);
  const [confirmClear, setConfirmClear] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [mappingChains, setMappingChains] = useState([]);
  const [showMappingChains, setShowMappingChains] = useState(false);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const loadGraph = useCallback(async () => {
    try {
      const response = await getFullGraph(collapseIntermediate);
      const graphData = response.data;

      let filteredNodes = graphData.nodes;
      let filteredEdges = graphData.edges;

      if (showType === 'table') {
        filteredNodes = graphData.nodes.filter(n => n.type === 'table');
        filteredEdges = graphData.edges.filter(e => 
          e.type === 'TRANSFORMS_TO' || e.type === 'AGGREGATED_TRANSFORMS_TO'
        );
      } else if (showType === 'column') {
        filteredNodes = graphData.nodes.filter(n => n.type === 'column');
        filteredEdges = graphData.edges.filter(e => 
          e.type === 'FLOWS_TO' || e.type === 'AGGREGATED_FLOWS_TO'
        );
      }

      const laidOutNodes = layoutNodes(filteredNodes, filteredEdges);
      
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

      const styledEdges = filteredEdges.map(edge => {
        const isAggregated = edge.type?.startsWith('AGGREGATED');
        const strokeColor = isAggregated 
          ? '#9e9e9e' 
          : (edge.type === 'TRANSFORMS_TO' || edge.type === 'AGGREGATED_TRANSFORMS_TO' 
              ? '#1976d2' 
              : '#388e3c');
        
        return {
          ...edge,
          animated: !isAggregated,
          style: {
            stroke: strokeColor,
            strokeWidth: isAggregated ? 3 : 2,
            strokeDasharray: isAggregated ? '8,4' : 'none',
            cursor: isAggregated ? 'pointer' : 'default',
          },
          label: isAggregated 
            ? `折叠 ${edge.intermediate_count} 层` 
            : undefined,
          labelStyle: {
            fill: '#666',
            fontSize: 10,
            cursor: 'pointer',
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: strokeColor,
          },
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
      console.error('Failed to load graph:', err);
    }
  }, [showType, collapseIntermediate, setNodes, setEdges]);

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
          return [
            ...filteredEdges,
            ...expandedData.edges.map(e => ({
              ...e,
              animated: true,
              style: {
                stroke: e.type === 'TRANSFORMS_TO' ? '#1976d2' : '#388e3c',
                strokeWidth: 2,
              },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: e.type === 'TRANSFORMS_TO' ? '#1976d2' : '#388e3c',
              },
              data: { ...e, is_collapsed: false },
            })),
          ];
        });
      } catch (err) {
        console.error('Failed to expand edge:', err);
      }
    }
  }, [nodes, setNodes, setEdges]);

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

  const layoutNodes = (nodes, edges) => {
    if (nodes.length === 0) return nodes;

    const levels = {};
    nodes.forEach(node => {
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
    const levelWidth = collapseIntermediate ? 350 : 280;
    const nodeHeight = collapseIntermediate ? 100 : 85;

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

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const handleClearDatabase = async () => {
    try {
      await clearDatabase();
      setNodes([]);
      setEdges([]);
      setConfirmClear(false);
    } catch (err) {
      console.error('Failed to clear database:', err);
    }
  };

  const toggleCollapse = () => {
    setCollapseIntermediate(!collapseIntermediate);
  };

  const stats = useMemo(() => {
    const sourceTables = nodes.filter(n => n.type === 'table' && n.node_type === 'source').length;
    const targetTables = nodes.filter(n => n.type === 'table' && n.node_type === 'target').length;
    const cteTables = nodes.filter(n => n.type === 'table' && n.node_type === 'cte').length;
    const sourceColumns = nodes.filter(n => n.type === 'column' && n.node_type === 'source').length;
    const targetColumns = nodes.filter(n => n.type === 'column' && n.node_type === 'target').length;
    const aggregatedEdges = edges.filter(e => e.data?.is_collapsed).length;
    
    return {
      sourceTables,
      targetTables,
      cteTables,
      sourceColumns,
      targetColumns,
      aggregatedEdges,
      totalNodes: nodes.length,
      totalEdges: edges.length,
    };
  }, [nodes, edges]);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 1 }}>
            血缘图谱
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip label={`源表: ${stats.sourceTables}`} color="success" size="small" />
            <Chip label={`目标表: ${stats.targetTables}`} color="error" size="small" />
            <Chip label={`CTE: ${stats.cteTables}`} color="warning" size="small" />
            <Chip label={`源字段: ${stats.sourceColumns}`} color="success" size="small" variant="outlined" />
            <Chip label={`目标字段: ${stats.targetColumns}`} color="error" size="small" variant="outlined" />
            {stats.aggregatedEdges > 0 && (
              <Chip label={`折叠边: ${stats.aggregatedEdges}`} color="default" size="small" />
            )}
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <FormControlLabel
            control={
              <Switch
                checked={collapseIntermediate}
                onChange={toggleCollapse}
                color="primary"
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                {collapseIntermediate ? <FoldMoreIcon fontSize="small" /> : <UnfoldMoreIcon fontSize="small" />}
                {collapseIntermediate ? '折叠中间层' : '展开中间层'}
              </Box>
            }
          />
          
          <ToggleButtonGroup
            value={showType}
            exclusive
            onChange={(e, value) => value && setShowType(value)}
            size="small"
          >
            <ToggleButton value="all">全部</ToggleButton>
            <ToggleButton value="table">表</ToggleButton>
            <ToggleButton value="column">字段</ToggleButton>
          </ToggleButtonGroup>
          
          <Tooltip title="点击折叠边可展开">
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={loadGraph}
              size="small"
            >
              刷新
            </Button>
          </Tooltip>
          
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={() => setConfirmClear(true)}
            size="small"
          >
            清空
          </Button>
          
          <Button
            variant="outlined"
            onClick={() => navigate('/')}
            size="small"
          >
            解析SQL
          </Button>
        </Box>
      </Box>

      <Box sx={{ height: 'calc(100vh - 200px)', border: '1px solid #e0e0e0', borderRadius: '8px' }}>
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
          <Panel position="top-left">
            <Paper sx={{ p: 2, minWidth: 180 }}>
              <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
                图例
              </Typography>
              <Box sx={{ mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                  <Box sx={{ width: 16, height: 16, backgroundColor: '#e8f5e9', border: '2px solid #2e7d32', mr: 1 }}></Box>
                  <Typography variant="caption">源节点</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                  <Box sx={{ width: 16, height: 16, backgroundColor: '#ffebee', border: '2px solid #c62828', mr: 1 }}></Box>
                  <Typography variant="caption">目标节点</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                  <Box sx={{ width: 16, height: 16, backgroundColor: '#fff3e0', border: '2px solid #f57c00', mr: 1 }}></Box>
                  <Typography variant="caption">CTE节点</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                  <Box sx={{ width: 16, height: 16, backgroundColor: '#f3e5f5', border: '2px solid #7b1fa2', mr: 1 }}></Box>
                  <Typography variant="caption">子查询节点</Typography>
                </Box>
              </Box>
              <Divider sx={{ my: 1 }} />
              <Box sx={{ mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                  <Box sx={{ width: 30, height: 3, backgroundColor: '#1976d2', mr: 1 }}></Box>
                  <Typography variant="caption">表流转</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                  <Box sx={{ width: 30, height: 3, backgroundColor: '#388e3c', mr: 1 }}></Box>
                  <Typography variant="caption">字段流转</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Box sx={{ width: 30, height: 3, backgroundColor: '#9e9e9e', mr: 1, borderStyle: 'dashed' }}></Box>
                  <Typography variant="caption">聚合边(点击展开)</Typography>
                </Box>
              </Box>
            </Paper>
          </Panel>
          <MiniMap
            nodeColor={(node) => {
              const colors = getNodeColor(node.data?.node_type);
              return colors.bg;
            }}
          />
          <Controls />
          <Background />
        </ReactFlow>
      </Box>

      <Dialog open={confirmClear} onClose={() => setConfirmClear(false)}>
        <DialogTitle>确认清空</DialogTitle>
        <DialogContent>
          <Typography>确定要清空所有血缘数据吗？此操作不可恢复。</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmClear(false)}>取消</Button>
          <Button onClick={handleClearDatabase} color="error">确认清空</Button>
        </DialogActions>
      </Dialog>

      <Dialog 
        open={showMappingChains} 
        onClose={() => setShowMappingChains(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          字段映射链 - {selectedNode?.data?.label}
        </DialogTitle>
        <DialogContent dividers>
          {mappingChains.length > 0 ? (
            <List>
              {mappingChains.map((chain, idx) => (
                <ListItem key={idx} divider={idx < mappingChains.length - 1}>
                  <ListItemText
                    primary={
                      <Box sx={{ fontFamily: 'monospace', fontSize: '14px' }}>
                        {chain.full_chain}
                      </Box>
                    }
                    secondary={
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          深度: {chain.chain_depth} | 
                          源表: {chain.source_tables?.join(', ')} |
                          源字段: {chain.source_columns?.join(', ')}
                        </Typography>
                        {chain.links && chain.links.length > 0 && (
                          <Box sx={{ mt: 1, pl: 2, borderLeft: '2px solid #e0e0e0' }}>
                            {chain.links.map((link, linkIdx) => (
                              <Typography key={linkIdx} variant="caption" display="block">
                                层级 {link.level}: {link.display_name}
                                {link.expression && (
                                  <Box component="code" sx={{ display: 'block', ml: 2, color: '#666', fontSize: '11px' }}>
                                    {link.expression}
                                  </Box>
                                )}
                              </Typography>
                            ))}
                          </Box>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography color="text.secondary">暂无映射链数据</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowMappingChains(false)}>关闭</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default GraphPage;
