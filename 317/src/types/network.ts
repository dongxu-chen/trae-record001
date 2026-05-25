export type DeviceType = 'router' | 'switch' | 'server';

export interface Device {
  id: string;
  name: string;
  type: DeviceType;
  ip: string;
  mac: string;
  location: string;
  status: 'online' | 'offline' | 'warning';
  cpu: number;
  memory: number;
  uptime: string;
  description: string;
  interfaces: NetworkInterface[];
}

export interface NetworkInterface {
  name: string;
  status: 'up' | 'down';
  speed: string;
  mac: string;
}

export interface Link {
  id: string;
  source: string;
  target: string;
  bandwidth: number;
  latency: number;
  packetLoss: number;
  status: 'up' | 'down' | 'degraded';
  utilization: number;
}

export interface TopologyData {
  devices: Device[];
  links: Link[];
}

export interface LinkMetrics {
  linkId: string;
  timestamp: number;
  bandwidth: number;
  latency: number;
  packetLoss: number;
  utilization: number;
}

export interface DeviceMetrics {
  deviceId: string;
  timestamp: number;
  cpu: number;
  memory: number;
}

export interface FaultEvent {
  id: string;
  type: 'device_fault' | 'link_fault';
  targetId: string;
  timestamp: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  affectedDevices: string[];
  affectedLinks: string[];
}

export interface HistorySnapshot {
  timestamp: number;
  devices: Device[];
  links: Link[];
  healthScore: number;
  faultEvents: FaultEvent[];
}

export interface HealthScore {
  overall: number;
  deviceScore: number;
  linkScore: number;
  availabilityScore: number;
  details: {
    onlineDevices: number;
    totalDevices: number;
    upLinks: number;
    totalLinks: number;
    avgLatency: number;
    avgPacketLoss: number;
    avgUtilization: number;
    activeFaults: number;
  };
}

export interface TimeTravelState {
  isEnabled: boolean;
  currentIndex: number;
  snapshots: HistorySnapshot[];
  playbackSpeed: number;
  isPlaying: boolean;
}

export type WebSocketMessage =
  | { type: 'INIT'; data: TopologyData }
  | { type: 'LINK_UPDATE'; data: LinkMetrics }
  | { type: 'DEVICE_UPDATE'; data: DeviceMetrics }
  | { type: 'DEVICE_ADDED'; data: Device }
  | { type: 'DEVICE_REMOVED'; data: { deviceId: string } }
  | { type: 'LINK_ADDED'; data: Link }
  | { type: 'LINK_REMOVED'; data: { linkId: string } }
  | { type: 'PING'; timestamp: number }
  | { type: 'PONG'; timestamp: number }
  | { type: 'SYNC_REQUEST' }
  | { type: 'SYNC_RESPONSE'; data: TopologyData }
  | { type: 'FAULT_EVENT'; data: FaultEvent }
  | { type: 'HEALTH_SCORE'; data: HealthScore }
  | { type: 'HISTORY_SNAPSHOT'; data: HistorySnapshot }
  | { type: 'TIME_TRAVEL_ENABLE'; data: { enabled: boolean } }
  | { type: 'TIME_TRAVEL_JUMP'; data: { index: number } };
