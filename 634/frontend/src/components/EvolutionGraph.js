import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Paper, Box, Typography, CircularProgress, Button, Chip, Slider, FormControlLabel, Switch } from '@mui/material';
import { DataSet, Network } from 'vis-network/standalone';
import { evolutionApi } from '../services/api';
import { wsService } from '../services/websocketService';

const lifecycleColors = {
  emerging: '#4caf50',
  growing: '#2196f3',
  bursting: '#f44336',
  declining: '#ff9800',
  stable: '#9e9e9e'
};

const ANIMATION_DURATION = 800;
const ANIMATION_EASING_FUNCTION = 'easeInOutQuad';

function EvolutionGraph({ onTopicSelect }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const nodesRef = useRef(null);
  const edgesRef = useRef(null);
  const animationTimeoutRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [animationSpeed, setAnimationSpeed] = useState(800);
  const [rawGraphData, setRawGraphData] = useState({ nodes: [], edges: [] });

  const createNodeData = useCallback((node) => ({
    id: node.id,
    label: node.name || node.id.slice(0, 8),
    title: `
      话题: ${node.name}<br/>
      文章数: ${node.size}<br/>
      生命周期: ${node.lifecycle}<br/>
      影响力: ${((node.influence || 0) * 100).toFixed(1)}%<br/>
      转发: ${node.total_shares || 0} | 点赞: ${node.total_likes || 0} | 评论: ${node.total_comments || 0}
    `,
    color: {
      background: lifecycleColors[node.lifecycle] || '#9e9e9e',
      border: '#2c3e50'
    },
    size: 20 + (node.size || 1) * 2,
    font: { color: '#fff' },
    version: node.version || 0
  }), []);

  const createEdgeData = useCallback((edge) => ({
    from: edge.source,
    to: edge.target,
    label: edge.type,
    title: `类型: ${edge.type}<br/>相似度: ${((edge.weight || 0) * 100).toFixed(1)}%`,
    width: 1 + (edge.weight || 0) * 3,
    color: {
      color: '#3498db',
      highlight: '#e74c3c'
    },
    arrows: 'to',
    version: edge.version || 0
  }), []);

  const animateNodeUpdate = useCallback((nodeId, oldValue, newValue) => {
    if (!networkRef.current) return;

    const startTime = Date.now();
    const duration = animationSpeed;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      
      const interpolatedSize = oldValue.size + (newValue.size - oldValue.size) * easeProgress;
      const interpolatedColor = interpolateColor(
        oldValue.color.background,
        newValue.color.background,
        easeProgress
      );

      nodesRef.current.updateOnly({
        id: nodeId,
        size: interpolatedSize,
        color: {
          background: interpolatedColor,
          border: '#2c3e50'
        }
      });

      if (progress < 1) {
        animationTimeoutRef.current = requestAnimationFrame(animate);
      } else {
        nodesRef.current.updateOnly({
          id: nodeId,
          ...newValue
        });
      }
    };

    animate();
  }, [animationSpeed]);

  const interpolateColor = (color1, color2, factor) => {
    const c1 = hexToRgb(color1);
    const c2 = hexToRgb(color2);
    
    const r = Math.round(c1.r + (c2.r - c1.r) * factor);
    const g = Math.round(c1.g + (c2.g - c1.g) * factor);
    const b = Math.round(c1.b + (c2.b - c1.b) * factor);
    
    return rgbToHex(r, g, b);
  };

  const hexToRgb = (hex) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : { r: 0, g: 0, b: 0 };
  };

  const rgbToHex = (r, g, b) => {
    return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  };

  const animateNodeAdd = useCallback((nodeData) => {
    if (!networkRef.current) return;
    
    const startTime = Date.now();
    const duration = animationSpeed;
    
    const tempNode = {
      ...nodeData,
      size: 5,
      color: {
        background: nodeData.color.background,
        border: nodeData.color.border
      },
      opacity: 0
    };
    
    nodesRef.current.add(tempNode);
    
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      
      const currentSize = 5 + (nodeData.size - 5) * easeProgress;
      const currentOpacity = easeProgress;
      
      nodesRef.current.updateOnly({
        id: nodeData.id,
        size: currentSize,
        opacity: currentOpacity
      });
      
      if (progress < 1) {
        animationTimeoutRef.current = requestAnimationFrame(animate);
      } else {
        nodesRef.current.updateOnly({
          id: nodeData.id,
          ...nodeData
        });
      }
    };
    
    animate();
  }, [animationSpeed]);

  const animateNodeRemove = useCallback((nodeId) => {
    if (!networkRef.current) return;
    
    const startTime = Date.now();
    const duration = animationSpeed * 0.6;
    const node = nodesRef.current.get(nodeId);
    
    if (!node) return;
    
    const originalSize = node.size;
    
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeProgress = Math.pow(progress, 2);
      
      const currentSize = originalSize * (1 - easeProgress);
      const currentOpacity = 1 - easeProgress;
      
      nodesRef.current.updateOnly({
        id: nodeId,
        size: currentSize,
        opacity: currentOpacity
      });
      
      if (progress < 1) {
        animationTimeoutRef.current = requestAnimationFrame(animate);
      } else {
        nodesRef.current.remove(nodeId);
      }
    };
    
    animate();
  }, [animationSpeed]);

  const animateEdgeUpdate = useCallback((edgeId, oldValue, newValue) => {
    if (!networkRef.current) return;

    const startTime = Date.now();
    const duration = animationSpeed;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeProgress = 1 - Math.pow(1 - progress, 3);

      const interpolatedWidth = oldValue.width + (newValue.width - oldValue.width) * easeProgress;

      edgesRef.current.updateOnly({
        id: edgeId,
        width: interpolatedWidth
      });

      if (progress < 1) {
        animationTimeoutRef.current = requestAnimationFrame(animate);
      } else {
        edgesRef.current.updateOnly({
          id: edgeId,
          ...newValue
        });
      }
    };

    animate();
  }, [animationSpeed]);

  const animateEdgeAdd = useCallback((edgeData) => {
    if (!networkRef.current) return;
    
    const startTime = Date.now();
    const duration = animationSpeed;
    const edgeId = `${edgeData.from}->${edgeData.to}`;
    
    const tempEdge = {
      ...edgeData,
      id: edgeId,
      width: 0.1,
      opacity: 0
    };
    
    edgesRef.current.add(tempEdge);
    
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      
      const currentWidth = 0.1 + (edgeData.width - 0.1) * easeProgress;
      const currentOpacity = easeProgress;
      
      edgesRef.current.updateOnly({
        id: edgeId,
        width: currentWidth,
        opacity: currentOpacity
      });
      
      if (progress < 1) {
        animationTimeoutRef.current = requestAnimationFrame(animate);
      } else {
        edgesRef.current.updateOnly({
          id: edgeId,
          ...edgeData
        });
      }
    };
    
    animate();
  }, [animationSpeed]);

  const animateEdgeRemove = useCallback((edgeId) => {
    if (!networkRef.current) return;
    
    const startTime = Date.now();
    const duration = animationSpeed * 0.6;
    const edge = edgesRef.current.get(edgeId);
    
    if (!edge) return;
    
    const originalWidth = edge.width;
    
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeProgress = Math.pow(progress, 2);
      
      const currentWidth = originalWidth * (1 - easeProgress);
      const currentOpacity = 1 - easeProgress;
      
      edgesRef.current.updateOnly({
        id: edgeId,
        width: currentWidth,
        opacity: currentOpacity
      });
      
      if (progress < 1) {
        animationTimeoutRef.current = requestAnimationFrame(animate);
      } else {
        edgesRef.current.remove(edgeId);
      }
    };
    
    animate();
  }, [animationSpeed]);

  const applyIncrementalUpdate = useCallback((updateData) => {
    if (!nodesRef.current || !edgesRef.current) return;

    const { added_nodes, updated_nodes, removed_nodes, added_edges, updated_edges, removed_edges } = updateData;

    added_nodes.forEach(node => {
      const nodeData = createNodeData(node);
      animateNodeAdd(nodeData);
    });

    updated_nodes.forEach(node => {
      const nodeData = createNodeData(node);
      const oldNode = nodesRef.current.get(node.id);
      if (oldNode) {
        animateNodeUpdate(node.id, oldNode, nodeData);
      } else {
        nodesRef.current.add(nodeData);
      }
    });

    removed_nodes.forEach(node => {
      animateNodeRemove(node.id);
    });

    added_edges.forEach(edge => {
      const edgeId = `${edge.source}->${edge.target}`;
      const edgeData = { ...createEdgeData(edge), id: edgeId };
      animateEdgeAdd(edgeData);
    });

    updated_edges.forEach(edge => {
      const edgeId = `${edge.source}->${edge.target}`;
      const edgeData = { ...createEdgeData(edge), id: edgeId };
      const oldEdge = edgesRef.current.get(edgeId);
      if (oldEdge) {
        animateEdgeUpdate(edgeId, oldEdge, edgeData);
      } else {
        edgesRef.current.add(edgeData);
      }
    });

    removed_edges.forEach(edge => {
      const edgeId = `${edge.source}->${edge.target}`;
      animateEdgeRemove(edgeId);
    });

    setStats({
      nodes: nodesRef.current.length,
      edges: edgesRef.current.length
    });
  }, [createNodeData, createEdgeData, animateNodeAdd, animateNodeUpdate, animateNodeRemove, animateEdgeAdd, animateEdgeUpdate, animateEdgeRemove]);

  const initGraph = useCallback(async () => {
    try {
      setLoading(true);
      const response = await evolutionApi.getFullGraphWithVersions();
      const data = response.data;
      
      setRawGraphData({
        nodes: data.nodes || [],
        edges: data.edges || []
      });
      
      if (containerRef.current) {
        renderGraph(data);
        setStats({
          nodes: data.nodes?.length || 0,
          edges: data.edges?.length || 0
        });
      }
    } catch (error) {
      console.error('Failed to fetch graph:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const renderGraph = useCallback((data) => {
    const nodeArray = data.nodes?.map(node => createNodeData(node)) || [];
    const edgeArray = data.edges?.map(edge => ({
      ...createEdgeData(edge),
      id: `${edge.source}->${edge.target}`
    })) || [];

    nodesRef.current = new DataSet(nodeArray);
    edgesRef.current = new DataSet(edgeArray);

    const options = {
      nodes: {
        shape: 'dot',
        borderWidth: 2,
        shadow: true,
        font: {
          color: '#fff',
          size: 12,
          face: 'Arial'
        }
      },
      edges: {
        smooth: {
          type: 'continuous',
          forceDirection: 'none',
          roundness: 0.5
        },
        font: {
          size: 10,
          align: 'middle',
          background: 'rgba(255, 255, 255, 0.8)'
        }
      },
      physics: {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -3000,
          centralGravity: 0.3,
          springLength: 150,
          springConstant: 0.04,
          damping: 0.09,
          avoidOverlap: 0.5
        },
        stabilization: {
          enabled: true,
          iterations: 100,
          updateInterval: 25
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        multiselect: false,
        navigationButtons: true
      },
      configure: {
        enabled: false
      }
    };

    if (networkRef.current) {
      networkRef.current.destroy();
    }

    networkRef.current = new Network(
      containerRef.current,
      { nodes: nodesRef.current, edges: edgesRef.current },
      options
    );

    networkRef.current.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = rawGraphData.nodes?.find(n => n.id === nodeId);
        if (node && onTopicSelect) {
          onTopicSelect(node);
        }
      }
    });

    networkRef.current.on('stabilizationIterationsDone', () => {
    });
  }, [createNodeData, createEdgeData, rawGraphData, onTopicSelect]);

  useEffect(() => {
    initGraph();

    const handleIncrementalUpdate = (data) => {
      if (autoRefresh) {
        applyIncrementalUpdate(data);
      }
    };

    const handleEvolution = () => {
      if (autoRefresh) {
        initGraph();
      }
    };

    wsService.addListener('graph_incremental_update', handleIncrementalUpdate);
    wsService.addListener('evolution', handleEvolution);

    return () => {
      wsService.removeListener('graph_incremental_update', handleIncrementalUpdate);
      wsService.removeListener('evolution', handleEvolution);
      if (animationTimeoutRef.current) {
        cancelAnimationFrame(animationTimeoutRef.current);
      }
    };
  }, [initGraph, autoRefresh, applyIncrementalUpdate]);

  useEffect(() => {
    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
      }
      if (animationTimeoutRef.current) {
        cancelAnimationFrame(animationTimeoutRef.current);
      }
    };
  }, []);

  const handleAnimationSpeedChange = (event, newValue) => {
    setAnimationSpeed(newValue);
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Box display="flex" gap={2} alignItems="center">
          <Typography variant="h6">话题演化图谱</Typography>
          <Chip label={`话题: ${stats.nodes}`} size="small" />
          <Chip label={`关系: ${stats.edges}`} size="small" />
        </Box>
        <Box display="flex" gap={2} alignItems="center">
          <FormControlLabel
            control={
              <Switch
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                size="small"
              />
            }
            label="自动更新"
          />
          <Button variant="contained" size="small" onClick={initGraph}>刷新</Button>
        </Box>
      </Box>

      <Box display="flex" gap={1} mb={2} flexWrap="wrap" alignItems="center">
        {Object.entries(lifecycleColors).map(([stage, color]) => (
          <Chip
            key={stage}
            label={stage}
            size="small"
            sx={{ backgroundColor: color, color: 'white' }}
          />
        ))}
        
        <Box sx={{ width: 200, ml: 2 }}>
          <Typography variant="caption" display="block" gutterBottom>
            动画速度: {animationSpeed}ms
          </Typography>
          <Slider
            value={animationSpeed}
            onChange={handleAnimationSpeedChange}
            min={200}
            max={2000}
            step={100}
            size="small"
          />
        </Box>
      </Box>

      <Paper sx={{ height: '600px', position: 'relative' }}>
        {loading && (
          <Box 
            display="flex" 
            justifyContent="center" 
            alignItems="center"
            position="absolute"
            top={0}
            left={0}
            right={0}
            bottom={0}
            zIndex={10}
            bgcolor="rgba(255, 255, 255, 0.9)"
          >
            <CircularProgress />
          </Box>
        )}
        <div 
          ref={containerRef} 
          style={{ width: '100%', height: '100%' }}
        />
      </Paper>
      
      <Box mt={1} display="flex" justifyContent="space-between" alignItems="center">
        <Typography variant="caption" color="textSecondary">
          点击节点查看话题详情 | 滚轮缩放 | 拖拽移动
        </Typography>
        <Typography variant="caption" color="textSecondary">
          ✨ 新增节点 | 🔄 更新节点 | 💫 平滑过渡
        </Typography>
      </Box>
    </Box>
  );
}

export default EvolutionGraph;
