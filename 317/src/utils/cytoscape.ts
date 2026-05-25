import { Device, Link } from '../types';
import { ElementDefinition, Stylesheet } from 'cytoscape';

export const deviceToNode = (device: Device): ElementDefinition => ({
  group: 'nodes',
  data: {
    id: device.id,
    label: device.name,
    type: device.type,
    status: device.status,
    cpu: device.cpu,
    memory: device.memory,
    ip: device.ip,
  },
});

export const linkToEdge = (link: Link): ElementDefinition => ({
  group: 'edges',
  data: {
    id: link.id,
    source: link.source,
    target: link.target,
    label: `${link.utilization.toFixed(0)}%`,
    bandwidth: link.bandwidth,
    latency: link.latency,
    packetLoss: link.packetLoss,
    status: link.status,
    utilization: link.utilization,
  },
});

export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'online':
    case 'up':
      return '#22c55e';
    case 'warning':
    case 'degraded':
      return '#f59e0b';
    case 'offline':
    case 'down':
      return '#ef4444';
    default:
      return '#6b7280';
  }
};

export const getDeviceIcon = (type: string): string => {
  switch (type) {
    case 'router':
      return '\u{1F4E1}';
    case 'switch':
      return '\u{1F50C}';
    case 'server':
      return '\u{1F5A5}';
    default:
      return '\u{2753}';
  }
};

export const getCytoscapeStyles = (): Stylesheet[] => [
  {
    selector: 'node',
    style: {
      'background-color': '#1e293b',
      'border-width': 3,
      'border-color': (ele: any) => getStatusColor(ele.data('status')),
      'label': 'data(label)',
      'color': '#f8fafc',
      'font-size': 12,
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 8,
      'text-wrap': 'wrap',
      'text-max-width': 120,
      'width': 50,
      'height': 50,
      'content': (ele: any) => getDeviceIcon(ele.data('type')),
      'font-size-label': 24,
      'text-valign-icon': 'center',
      'text-halign-icon': 'center',
    },
  },
  {
    selector: 'node[status = "online"]',
    style: {
      'background-color': '#0f172a',
      'border-color': '#22c55e',
      'shadow-color': '#22c55e',
      'shadow-blur': 10,
      'shadow-opacity': 0.5,
    },
  },
  {
    selector: 'node[status = "warning"]',
    style: {
      'background-color': '#0f172a',
      'border-color': '#f59e0b',
      'shadow-color': '#f59e0b',
      'shadow-blur': 15,
      'shadow-opacity': 0.6,
    },
  },
  {
    selector: 'node[status = "offline"]',
    style: {
      'background-color': '#1e293b',
      'border-color': '#ef4444',
      'opacity': 0.6,
    },
  },
  {
    selector: 'node:selected',
    style: {
      'border-width': 4,
      'border-color': '#3b82f6',
      'shadow-color': '#3b82f6',
      'shadow-blur': 20,
      'shadow-opacity': 0.8,
    },
  },
  {
    selector: 'edge',
    style: {
      'width': (ele: any) => {
        const util = ele.data('utilization') || 0;
        return Math.max(2, Math.min(8, util / 15));
      },
      'line-color': (ele: any) => getStatusColor(ele.data('status')),
      'target-arrow-color': (ele: any) => getStatusColor(ele.data('status')),
      'target-arrow-shape': 'triangle',
      'arrow-scale': 1.2,
      'curve-style': 'bezier',
      'label': 'data(label)',
      'color': '#94a3b8',
      'font-size': 10,
      'text-rotation': 'autorotate',
      'text-margin-y': -8,
      'text-background-color': '#0f172a',
      'text-background-opacity': 0.8,
      'text-background-padding': 2,
    },
  },
  {
    selector: 'edge[status = "up"]',
    style: {
      'line-color': '#22c55e',
      'target-arrow-color': '#22c55e',
    },
  },
  {
    selector: 'edge[status = "degraded"]',
    style: {
      'line-color': '#f59e0b',
      'target-arrow-color': '#f59e0b',
      'line-style': 'dashed',
    },
  },
  {
    selector: 'edge[status = "down"]',
    style: {
      'line-color': '#ef4444',
      'target-arrow-color': '#ef4444',
      'opacity': 0.4,
      'line-style': 'dotted',
    },
  },
  {
    selector: 'edge:selected',
    style: {
      'width': 6,
      'line-color': '#3b82f6',
      'target-arrow-color': '#3b82f6',
      'shadow-color': '#3b82f6',
      'shadow-blur': 10,
      'shadow-opacity': 0.6,
    },
  },
  {
    selector: '.highlighted',
    style: {
      'transition-property': 'border-color, line-color, shadow-opacity',
      'transition-duration': 0.3,
    },
  },
];
