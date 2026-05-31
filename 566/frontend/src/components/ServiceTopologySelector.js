import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  CircularProgress,
  Alert,
  Tooltip,
  Grid,
  Card,
  CardContent,
} from '@mui/material';
import {
  Info as InfoIcon,
  Check as CheckIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { serviceApi } from '../services/api';

function ServiceTopologySelector({ open, onClose, onSelect, selectedService, selectedVersion }) {
  const [topology, setTopology] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hoveredService, setHoveredService] = useState(null);

  useEffect(() => {
    if (open) {
      loadTopology();
    }
  }, [open]);

  const loadTopology = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await serviceApi.getTopology();
      setTopology(data);
    } catch (err) {
      setError('加载服务拓扑失败');
    } finally {
      setLoading(false);
    }
  };

  const handleServiceClick = (service, version = null) => {
    onSelect({
      service: service.name,
      version: version,
      namespace: service.namespace,
    });
    onClose();
  };

  const getServicePosition = (index, total) => {
    const angle = (2 * Math.PI * index) / total - Math.PI / 2;
    const radius = 180;
    const centerX = 300;
    const centerY = 250;
    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  };

  if (!open) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">选择服务</Typography>
          <IconButton onClick={loadTopology} size="small">
            <RefreshIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
            <CircularProgress />
          </Box>
        ) : topology ? (
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    服务拓扑图
                  </Typography>
                  <Box
                    sx={{
                      position: 'relative',
                      width: '100%',
                      height: 500,
                      backgroundColor: '#fafafa',
                      borderRadius: 2,
                      overflow: 'hidden',
                    }}
                  >
                    <svg width="100%" height="100%" viewBox="0 0 600 500">
                      <defs>
                        <marker
                          id="arrowhead"
                          markerWidth="10"
                          markerHeight="7"
                          refX="9"
                          refY="3.5"
                          orient="auto"
                        >
                          <polygon points="0 0, 10 3.5, 0 7" fill="#bdbdbd" />
                        </marker>
                      </defs>

                      {topology.connections?.map((conn, idx) => {
                        const sourceIdx = topology.services?.findIndex((s) => s.name === conn.source);
                        const destIdx = topology.services?.findIndex((s) => s.name === conn.destination);
                        if (sourceIdx === -1 || destIdx === -1) return null;

                        const sourcePos = getServicePosition(sourceIdx, topology.services?.length || 1);
                        const destPos = getServicePosition(destIdx, topology.services?.length || 1);

                        const isHighlighted =
                          hoveredService === conn.source || hoveredService === conn.destination;

                        return (
                          <line
                            key={idx}
                            x1={sourcePos.x}
                            y1={sourcePos.y}
                            x2={destPos.x}
                            y2={destPos.y}
                            stroke={isHighlighted ? '#1976d2' : '#bdbdbd'}
                            strokeWidth={isHighlighted ? 2 : 1}
                            markerEnd="url(#arrowhead)"
                            style={{ transition: 'all 0.3s' }}
                          />
                        );
                      })}
                    </svg>

                    {topology.services?.map((service, index) => {
                      const pos = getServicePosition(index, topology.services?.length || 1);
                      const isSelected = selectedService === service.name;
                      const isHovered = hoveredService === service.name;

                      return (
                        <Box
                          key={service.name}
                          sx={{
                            position: 'absolute',
                            left: pos.x - 60,
                            top: pos.y - 40,
                            width: 120,
                            cursor: 'pointer',
                            zIndex: isHovered || isSelected ? 10 : 1,
                          }}
                          onMouseEnter={() => setHoveredService(service.name)}
                          onMouseLeave={() => setHoveredService(null)}
                          onClick={() => handleServiceClick(service)}
                        >
                          <Card
                            variant="outlined"
                            sx={{
                              borderColor: isSelected
                                ? '#1976d2'
                                : isHovered
                                ? '#64b5f6'
                                : '#e0e0e0',
                              borderWidth: isSelected ? 2 : 1,
                              backgroundColor: isSelected ? '#e3f2fd' : 'white',
                              transition: 'all 0.3s',
                              '&:hover': {
                                boxShadow: 2,
                              },
                            }}
                          >
                            <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                              <Box display="flex" alignItems="center" justifyContent="center" gap={0.5}>
                                {isSelected && <CheckIcon color="primary" fontSize="small" />}
                                <Typography
                                  variant="body2"
                                  fontWeight={isSelected ? 'bold' : 'normal'}
                                  noWrap
                                  textAlign="center"
                                >
                                  {service.name}
                                </Typography>
                              </Box>
                              <Box display="flex" gap={0.5} justifyContent="center" mt={0.5} flexWrap="wrap">
                                {service.versions?.map((version) => (
                                  <Chip
                                    key={version}
                                    label={version}
                                    size="small"
                                    variant={selectedVersion === version ? 'filled' : 'outlined'}
                                    color={selectedVersion === version ? 'primary' : 'default'}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleServiceClick(service, version);
                                    }}
                                    sx={{ cursor: 'pointer' }}
                                  />
                                ))}
                              </Box>
                            </CardContent>
                          </Card>
                        </Box>
                      );
                    })}
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    服务详情
                  </Typography>
                  {hoveredService && (
                    <>
                      {(() => {
                        const service = topology.services?.find((s) => s.name === hoveredService);
                        if (!service) return null;

                        const incoming = topology.connections?.filter(
                          (c) => c.destination === hoveredService
                        );
                        const outgoing = topology.connections?.filter(
                          (c) => c.source === hoveredService
                        );

                        return (
                          <Box>
                            <Typography variant="h6" gutterBottom>
                              {service.name}
                            </Typography>
                            <Box display="flex" alignItems="center" gap={1} mb={2}>
                              <Chip
                                label={service.status || 'Running'}
                                color="success"
                                size="small"
                              />
                              <Typography variant="body2" color="text.secondary">
                                {service.namespace}
                              </Typography>
                            </Box>

                            {service.labels && Object.keys(service.labels).length > 0 && (
                              <Box mb={2}>
                                <Typography variant="caption" color="text.secondary">
                                  标签
                                </Typography>
                                <Box display="flex" flexWrap="wrap" gap={0.5} mt={0.5}>
                                  {Object.entries(service.labels).map(([key, value]) => (
                                    <Chip
                                      key={key}
                                      label={`${key}: ${value}`}
                                      size="small"
                                      variant="outlined"
                                    />
                                  ))}
                                </Box>
                              </Box>
                            )}

                            {incoming?.length > 0 && (
                              <Box mb={2}>
                                <Typography variant="caption" color="text.secondary">
                                  上游服务
                                </Typography>
                                <Box display="flex" flexWrap="wrap" gap={0.5} mt={0.5}>
                                  {incoming.map((c, i) => (
                                    <Chip key={i} label={c.source} size="small" color="primary" />
                                  ))}
                                </Box>
                              </Box>
                            )}

                            {outgoing?.length > 0 && (
                              <Box mb={2}>
                                <Typography variant="caption" color="text.secondary">
                                  下游服务
                                </Typography>
                                <Box display="flex" flexWrap="wrap" gap={0.5} mt={0.5}>
                                  {outgoing.map((c, i) => (
                                    <Chip key={i} label={c.destination} size="small" color="secondary" />
                                  ))}
                                </Box>
                              </Box>
                            )}

                            <Button
                              fullWidth
                              variant="contained"
                              onClick={() => handleServiceClick(service)}
                              sx={{ mt: 2 }}
                            >
                              选择此服务
                            </Button>
                          </Box>
                        );
                      })()}
                    </>
                  )}
                  {!hoveredService && (
                    <Box display="flex" flexDirection="center" alignItems="center" py={4}>
                      <InfoIcon color="action" sx={{ mr: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        悬停查看服务详情，点击选择服务
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>取消</Button>
      </DialogActions>
    </Dialog>
  );
}

export default ServiceTopologySelector;
