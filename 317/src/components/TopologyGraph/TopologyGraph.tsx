import React, { useEffect, useRef, useCallback, useMemo } from 'react';
import cytoscape, { Core, ElementDefinition, LayoutOptions, EdgeSingular, NodeSingular } from 'cytoscape';
import cytoscapeDagre from 'cytoscape-dagre';
import cytoscapeCoseBilkent from 'cytoscape-cose-bilkent';
import { Device, Link } from '../../types';
import { deviceToNode, linkToEdge, getCytoscapeStyles, getStatusColor } from '../../utils/cytoscape';

cytoscape.use(cytoscapeDagre);
cytoscape.use(cytoscapeCoseBilkent);

interface TopologyGraphProps {
  devices: Device[];
  links: Link[];
  selectedDeviceId: string | null;
  selectedLinkId: string | null;
  onDeviceSelect: (device: Device | null) => void;
  onLinkSelect: (link: Link | null) => void;
}

interface LinkDiff {
  id: string;
  changes: Partial<Link>;
}

export const TopologyGraph: React.FC<TopologyGraphProps> = ({
  devices,
  links,
  selectedDeviceId,
  selectedLinkId,
  onDeviceSelect,
  onLinkSelect,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const devicesRef = useRef<Device[]>(devices);
  const linksRef = useRef<Link[]>(links);
  const prevLinksRef = useRef<Map<string, Link>>(new Map());
  const prevDevicesRef = useRef<Map<string, Device>>(new Map());
  const layoutAppliedRef = useRef(false);

  useEffect(() => {
    devicesRef.current = devices;
  }, [devices]);

  useEffect(() => {
    linksRef.current = links;
  }, [links]);

  const getDagreLayoutOptions = useCallback((): LayoutOptions => ({
    name: 'dagre',
    rankDir: 'LR',
    animate: false,
    fit: false,
    padding: 50,
    rankSep: 180,
    nodeSep: 100,
    edgeSep: 60,
  }), []);

  const getCoseLayoutOptions = useCallback((): LayoutOptions => ({
    name: 'cose-bilkent',
    animate: true,
    animationDuration: 800,
    animationEasing: 'ease-out-cubic',
    fit: true,
    padding: 50,
    randomize: false,
    componentSpacing: 100,
    nodeOverlap: 20,
    idealEdgeLength: 120,
    edgeElasticity: 0.8,
    nestingFactor: 5,
    gravity: 0.4,
    numIter: 1500,
    tile: true,
    tilingPaddingVertical: 30,
    tilingPaddingHorizontal: 30,
  }), []);

  const runHybridLayout = useCallback((cy: Core) => {
    if (cy.elements().length === 0) return;

    const dagreLayout = cy.layout(getDagreLayoutOptions());
    
    dagreLayout.promiseOn('layoutstop').then(() => {
      const coseLayout = cy.layout(getCoseLayoutOptions());
      coseLayout.run();
    });

    dagreLayout.run();
    layoutAppliedRef.current = true;
  }, [getDagreLayoutOptions, getCoseLayoutOptions]);

  const updateNodeStyles = useCallback((node: NodeSingular, device: Device, prevDevice?: Device) => {
    const needsUpdate = !prevDevice || 
      prevDevice.status !== device.status ||
      prevDevice.cpu !== device.cpu ||
      prevDevice.memory !== device.memory ||
      prevDevice.name !== device.name;

    if (!needsUpdate) return;

    node.data('status', device.status);
    node.data('cpu', device.cpu);
    node.data('memory', device.memory);
    node.data('label', device.name);

    const color = getStatusColor(device.status);
    node.style('border-color', color);
    
    if (device.status === 'online') {
      node.style('background-color', '#0f172a');
      node.style('shadow-color', color);
      node.style('shadow-blur', 10);
      node.style('shadow-opacity', 0.5);
      node.style('opacity', 1);
    } else if (device.status === 'warning') {
      node.style('background-color', '#0f172a');
      node.style('shadow-color', color);
      node.style('shadow-blur', 15);
      node.style('shadow-opacity', 0.6);
      node.style('opacity', 1);
    } else {
      node.style('background-color', '#1e293b');
      node.style('shadow-blur', 0);
      node.style('shadow-opacity', 0);
      node.style('opacity', 0.6);
    }
  }, []);

  const updateEdgeStyles = useCallback((edge: EdgeSingular, link: Link, changes: Partial<Link>) => {
    if (Object.keys(changes).length === 0) return;

    if (changes.status !== undefined) {
      edge.data('status', link.status);
      const color = getStatusColor(link.status);
      edge.style('line-color', color);
      edge.style('target-arrow-color', color);
      
      if (link.status === 'up') {
        edge.style('line-style', 'solid');
        edge.style('opacity', 1);
      } else if (link.status === 'degraded') {
        edge.style('line-style', 'dashed');
        edge.style('opacity', 1);
      } else {
        edge.style('line-style', 'dotted');
        edge.style('opacity', 0.4);
      }
    }

    if (changes.latency !== undefined) {
      edge.data('latency', link.latency);
    }

    if (changes.packetLoss !== undefined) {
      edge.data('packetLoss', link.packetLoss);
    }

    if (changes.utilization !== undefined) {
      edge.data('utilization', link.utilization);
      edge.data('label', `${link.utilization.toFixed(0)}%`);
      edge.style('width', Math.max(2, Math.min(8, link.utilization / 15)));
    }
  }, []);

  const diffLinks = useCallback((newLinks: Link[], prevLinks: Map<string, Link>): LinkDiff[] => {
    const diffs: LinkDiff[] = [];

    for (const link of newLinks) {
      const prev = prevLinks.get(link.id);
      if (!prev) continue;

      const changes: Partial<Link> = {};
      
      if (prev.status !== link.status) changes.status = link.status;
      if (prev.latency !== link.latency) changes.latency = link.latency;
      if (prev.packetLoss !== link.packetLoss) changes.packetLoss = link.packetLoss;
      if (prev.utilization !== link.utilization) changes.utilization = link.utilization;

      if (Object.keys(changes).length > 0) {
        diffs.push({ id: link.id, changes });
      }
    }

    return diffs;
  }, []);

  const diffDevices = useCallback((newDevices: Device[], prevDevices: Map<string, Device>): Set<string> => {
    const changed = new Set<string>();

    for (const device of newDevices) {
      const prev = prevDevices.get(device.id);
      if (!prev) continue;

      if (prev.status !== device.status ||
          prev.cpu !== device.cpu ||
          prev.memory !== device.memory ||
          prev.name !== device.name) {
        changed.add(device.id);
      }
    }

    return changed;
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const elements: ElementDefinition[] = [
      ...devices.map(deviceToNode),
      ...links.map(linkToEdge),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: getCytoscapeStyles(),
      wheelSensitivity: 0.3,
      minZoom: 0.3,
      maxZoom: 3,
    });

    cyRef.current = cy;

    cy.ready(() => {
      runHybridLayout(cy);
    });

    cy.on('tap', 'node', (event) => {
      const nodeId = event.target.id();
      const device = devicesRef.current.find((d) => d.id === nodeId);
      if (device) {
        onDeviceSelect(device);
        onLinkSelect(null);
      }
    });

    cy.on('tap', 'edge', (event) => {
      const edgeId = event.target.id();
      const link = linksRef.current.find((l) => l.id === edgeId);
      if (link) {
        onLinkSelect(link);
        onDeviceSelect(null);
      }
    });

    cy.on('tap', (event) => {
      if (event.target === cy) {
        onDeviceSelect(null);
        onLinkSelect(null);
      }
    });

    cy.on('mouseover', 'node, edge', (event) => {
      event.target.addClass('highlighted');
      containerRef.current!.style.cursor = 'pointer';
    });

    cy.on('mouseout', 'node, edge', (event) => {
      event.target.removeClass('highlighted');
      containerRef.current!.style.cursor = 'default';
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, []);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const prevDevices = prevDevicesRef.current;
    const currentNodeIds = new Set(cy.nodes().map((n) => n.id()));
    const newNodeIds = new Set(devices.map((d) => d.id));
    const changedDeviceIds = diffDevices(devices, prevDevices);
    const devicesMap = new Map(devices.map(d => [d.id, d]));

    let needsRelayout = false;

    devices.forEach((device) => {
      if (!currentNodeIds.has(device.id)) {
        cy.add(deviceToNode(device));
        needsRelayout = true;
      } else if (changedDeviceIds.has(device.id)) {
        const node = cy.getElementById(device.id);
        const prevDevice = prevDevices.get(device.id);
        updateNodeStyles(node as NodeSingular, device, prevDevice);
      }
    });

    currentNodeIds.forEach((id) => {
      if (!newNodeIds.has(id)) {
        cy.remove(cy.getElementById(id));
        needsRelayout = true;
      }
    });

    prevDevicesRef.current = devicesMap;

    if (needsRelayout && layoutAppliedRef.current) {
      cy.layout(getCoseLayoutOptions()).run();
    }
  }, [devices, diffDevices, updateNodeStyles, getCoseLayoutOptions]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const prevLinks = prevLinksRef.current;
    const currentEdgeIds = new Set(cy.edges().map((e) => e.id()));
    const newEdgeIds = new Set(links.map((l) => l.id));
    const linkDiffs = diffLinks(links, prevLinks);
    const linksMap = new Map(links.map(l => [l.id, l]));

    let needsRelayout = false;

    links.forEach((link) => {
      if (!currentEdgeIds.has(link.id)) {
        cy.add(linkToEdge(link));
        needsRelayout = true;
      }
    });

    currentEdgeIds.forEach((id) => {
      if (!newEdgeIds.has(id)) {
        cy.remove(cy.getElementById(id));
        needsRelayout = true;
      }
    });

    linkDiffs.forEach((diff) => {
      const edge = cy.getElementById(diff.id);
      const link = linksMap.get(diff.id);
      if (edge.length > 0 && link) {
        updateEdgeStyles(edge as EdgeSingular, link, diff.changes);
      }
    });

    prevLinksRef.current = linksMap;

    if (needsRelayout && layoutAppliedRef.current) {
      cy.layout(getCoseLayoutOptions()).run();
    }
  }, [links, diffLinks, updateEdgeStyles, getCoseLayoutOptions]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.elements().unselect();
    
    if (selectedDeviceId) {
      const node = cy.getElementById(selectedDeviceId);
      if (node.length > 0) {
        node.select();
        cy.animate({
          fit: {
            eles: node,
            padding: 100,
          },
          duration: 500,
        });
      }
    }
    
    if (selectedLinkId) {
      const edge = cy.getElementById(selectedLinkId);
      if (edge.length > 0) {
        edge.select();
        cy.animate({
          fit: {
            eles: edge,
            padding: 100,
          },
          duration: 500,
        });
      }
    }
  }, [selectedDeviceId, selectedLinkId]);

  const handleZoomIn = () => {
    cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
  };

  const handleZoomOut = () => {
    cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  };

  const handleFit = () => {
    cyRef.current?.fit(undefined, 50);
  };

  const handleResetLayout = () => {
    if (cyRef.current) {
      runHybridLayout(cyRef.current);
    }
  };

  return (
    <div className="topology-container">
      <div ref={containerRef} className="topology-canvas" />
      <div className="topology-controls">
        <button onClick={handleZoomIn} title="放大">+</button>
        <button onClick={handleZoomOut} title="缩小">-</button>
        <button onClick={handleFit} title="适应窗口">⤢</button>
        <button onClick={handleResetLayout} title="重新布局">⟳</button>
      </div>
    </div>
  );
};
