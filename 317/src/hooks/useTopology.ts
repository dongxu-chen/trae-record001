import { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Device, Link, WebSocketMessage, DeviceMetrics, LinkMetrics,
  HealthScore, HistorySnapshot, FaultEvent, TimeTravelState
} from '../types';
import { wsClient } from '../services/websocket';

interface UseTopologyReturn {
  devices: Device[];
  links: Link[];
  selectedDevice: Device | null;
  selectedLink: Link | null;
  isConnected: boolean;
  linkMetricsHistory: Map<string, LinkMetrics[]>;
  deviceMetricsHistory: Map<string, DeviceMetrics[]>;
  healthScore: HealthScore | null;
  historySnapshots: HistorySnapshot[];
  timeTravel: TimeTravelState;
  faultEvents: FaultEvent[];
  setSelectedDevice: (device: Device | null) => void;
  setSelectedLink: (link: Link | null) => void;
  addDevice: (device: Omit<Device, 'id'>) => void;
  removeDevice: (deviceId: string) => void;
  addLink: (link: Omit<Link, 'id'>) => void;
  removeLink: (linkId: string) => void;
  requestSync: () => void;
  enableTimeTravel: (enabled: boolean) => void;
  jumpToSnapshot: (index: number) => void;
  playHistory: () => void;
  pauseHistory: () => void;
  setPlaybackSpeed: (speed: number) => void;
  triggerFault: (deviceId: string) => void;
}

export const useTopology = (): UseTopologyReturn => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [links, setLinks] = useState<Link[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [selectedLink, setSelectedLink] = useState<Link | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [healthScore, setHealthScore] = useState<HealthScore | null>(null);
  const [historySnapshots, setHistorySnapshots] = useState<HistorySnapshot[]>([]);
  const [timeTravel, setTimeTravel] = useState<TimeTravelState>({
    isEnabled: false,
    currentIndex: -1,
    snapshots: [],
    playbackSpeed: 1,
    isPlaying: false
  });
  const [faultEvents, setFaultEvents] = useState<FaultEvent[]>([]);
  
  const linkMetricsHistory = useRef<Map<string, LinkMetrics[]>>(new Map());
  const deviceMetricsHistory = useRef<Map<string, DeviceMetrics[]>>(new Map());
  const wasConnected = useRef(false);
  const playbackIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const realDevicesRef = useRef<Device[]>([]);
  const realLinksRef = useRef<Link[]>([]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'INIT':
      case 'SYNC_RESPONSE': {
        console.log(`Received ${message.type} data with ${message.data.devices.length} devices and ${message.data.links.length} links`);
        setDevices(message.data.devices);
        setLinks(message.data.links);
        realDevicesRef.current = message.data.devices;
        realLinksRef.current = message.data.links;
        deviceMetricsHistory.current.clear();
        linkMetricsHistory.current.clear();
        break;
      }
      case 'DEVICE_ADDED':
        if (!timeTravel.isEnabled) {
          if (message.data) {
            setDevices((prev) => [...prev, message.data]);
            realDevicesRef.current = [...realDevicesRef.current, message.data];
          }
        }
        break;
      case 'DEVICE_REMOVED':
        if (!timeTravel.isEnabled) {
          setDevices((prev) => prev.filter((d) => d.id !== message.data.deviceId));
          setLinks((prev) => prev.filter((l) => l.source !== message.data.deviceId && l.target !== message.data.deviceId));
          realDevicesRef.current = realDevicesRef.current.filter((d) => d.id !== message.data.deviceId);
          realLinksRef.current = realLinksRef.current.filter((l) => l.source !== message.data.deviceId && l.target !== message.data.deviceId);
          setSelectedDevice((prev) => (prev?.id === message.data.deviceId ? null : prev));
          deviceMetricsHistory.current.delete(message.data.deviceId);
        }
        break;
      case 'DEVICE_UPDATE': {
        const metrics = message.data;
        const history = deviceMetricsHistory.current.get(metrics.deviceId) || [];
        history.push(metrics);
        if (history.length > 60) history.shift();
        deviceMetricsHistory.current.set(metrics.deviceId, history);

        if (!timeTravel.isEnabled) {
          setDevices((prev) =>
            prev.map((d) =>
              d.id === metrics.deviceId
                ? { ...d, cpu: metrics.cpu, memory: metrics.memory }
                : d
            )
          );
          realDevicesRef.current = realDevicesRef.current.map((d) =>
            d.id === metrics.deviceId
              ? { ...d, cpu: metrics.cpu, memory: metrics.memory }
              : d
          );
          setSelectedDevice((prev) =>
            prev?.id === metrics.deviceId
              ? { ...prev, cpu: metrics.cpu, memory: metrics.memory }
              : prev
          );
        }
        break;
      }
      case 'LINK_ADDED':
        if (!timeTravel.isEnabled && message.data) {
          setLinks((prev) => [...prev, message.data]);
          realLinksRef.current = [...realLinksRef.current, message.data];
        }
        break;
      case 'LINK_REMOVED':
        if (!timeTravel.isEnabled) {
          setLinks((prev) => prev.filter((l) => l.id !== message.data.linkId));
          realLinksRef.current = realLinksRef.current.filter((l) => l.id !== message.data.linkId);
          setSelectedLink((prev) => (prev?.id === message.data.linkId ? null : prev));
          linkMetricsHistory.current.delete(message.data.linkId);
        }
        break;
      case 'LINK_UPDATE': {
        const metrics = message.data;
        const history = linkMetricsHistory.current.get(metrics.linkId) || [];
        history.push(metrics);
        if (history.length > 60) history.shift();
        linkMetricsHistory.current.set(metrics.linkId, history);

        if (!timeTravel.isEnabled) {
          setLinks((prev) =>
            prev.map((l) =>
              l.id === metrics.linkId
                ? {
                    ...l,
                    latency: metrics.latency,
                    packetLoss: metrics.packetLoss,
                    utilization: metrics.utilization,
                  }
                : l
            )
          );
          realLinksRef.current = realLinksRef.current.map((l) =>
            l.id === metrics.linkId
              ? {
                  ...l,
                  latency: metrics.latency,
                  packetLoss: metrics.packetLoss,
                  utilization: metrics.utilization,
                }
              : l
          );
          setSelectedLink((prev) =>
            prev?.id === metrics.linkId
              ? {
                  ...prev,
                  latency: metrics.latency,
                  packetLoss: metrics.packetLoss,
                  utilization: metrics.utilization,
                }
              : prev
          );
        }
        break;
      }
      case 'HEALTH_SCORE':
        setHealthScore(message.data);
        break;
      case 'HISTORY_SNAPSHOT': {
        const data = message.data;
        if (Array.isArray(data)) {
          setHistorySnapshots(data);
        } else {
          setHistorySnapshots((prev) => {
            const updated = [...prev, data];
            if (updated.length > 60) updated.shift();
            return updated;
          });
        }
        break;
      }
      case 'FAULT_EVENT':
        setFaultEvents((prev) => [...prev, message.data]);
        if (!timeTravel.isEnabled) {
          const fault = message.data;
          setDevices((prev) =>
            prev.map((d) =>
            fault.affectedDevices.includes(d.id)
              ? { ...d, status: 'offline', cpu: 0, memory: 0 }
              : d
          )
        );
          realDevicesRef.current = realDevicesRef.current.map((d) =>
            fault.affectedDevices.includes(d.id)
              ? { ...d, status: 'offline', cpu: 0, memory: 0 }
              : d
          );
          setLinks((prev) =>
            prev.map((l) =>
              fault.affectedLinks.includes(l.id)
                ? { ...l, status: 'down', utilization: 0, latency: 0, packetLoss: 100 }
                : l
            )
          );
          realLinksRef.current = realLinksRef.current.map((l) =>
            fault.affectedLinks.includes(l.id)
              ? { ...l, status: 'down', utilization: 0, latency: 0, packetLoss: 100 }
              : l
          );
        }
        break;
      case 'TIME_TRAVEL_JUMP': {
          const { index, snapshot } = message.data;
          if (timeTravel.isEnabled && snapshot) {
            setDevices(snapshot.devices);
            setLinks(snapshot.links);
            setTimeTravel((prev) => ({ ...prev, currentIndex: index }));
          }
          break;
        }
    }
  }, [timeTravel.isEnabled]);

  const handleConnectionChange = useCallback((connected: boolean) => {
    setIsConnected(connected);
    
    if (connected && wasConnected.current) {
      console.log('Reconnected to WebSocket, requesting state sync...');
      setTimeout(() => {
        wsClient.requestSync();
      }, 500);
    }
    
    wasConnected.current = connected;
  }, []);

  const requestSync = useCallback(() => {
    wsClient.requestSync();
  }, []);

  useEffect(() => {
    const cleanupMessage = wsClient.onMessage(handleMessage);
    const cleanupConnection = wsClient.onConnectionChange(handleConnectionChange);
    
    wsClient.connect();

    return () => {
      cleanupMessage();
      cleanupConnection();
      wsClient.disconnect();
      wasConnected.current = false;
    };
  }, [handleMessage, handleConnectionChange]);

  const addDevice = useCallback((device: Omit<Device, 'id'>) => {
    wsClient.addDevice(device);
  }, []);

  const removeDevice = useCallback((deviceId: string) => {
    wsClient.removeDevice(deviceId);
  }, []);

  const addLink = useCallback((link: Omit<Link, 'id'>) => {
    wsClient.addLink(link);
  }, []);

  const removeLink = useCallback((linkId: string) => {
    wsClient.removeLink(linkId);
  }, []);

  const enableTimeTravel = useCallback((enabled: boolean) => {
    if (enabled) {
      setTimeTravel((prev) => ({
        ...prev,
        isEnabled: true,
        currentIndex: historySnapshots.length - 1,
        snapshots: historySnapshots
      }));
    } else {
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current);
        playbackIntervalRef.current = null;
      }
      setDevices(realDevicesRef.current);
      setLinks(realLinksRef.current);
      setTimeTravel((prev) => ({
        ...prev,
        isEnabled: false,
        currentIndex: -1,
        isPlaying: false
      }));
    }
  }, [historySnapshots]);

  const jumpToSnapshot = useCallback((index: number) => {
    if (index >= 0 && index < historySnapshots.length) {
      const snapshot = historySnapshots[index];
      setDevices(snapshot.devices);
      setLinks(snapshot.links);
      setTimeTravel((prev) => ({ ...prev, currentIndex: index }));
    }
  }, [historySnapshots]);

  const playHistory = useCallback(() => {
    setTimeTravel((prev) => ({ ...prev, isPlaying: true }));
    
    if (playbackIntervalRef.current) {
      clearInterval(playbackIntervalRef.current);
    }

    playbackIntervalRef.current = setInterval(() => {
      setTimeTravel((prev) => {
        const nextIndex = prev.currentIndex + 1;
        if (nextIndex >= historySnapshots.length) {
          if (playbackIntervalRef.current) {
            clearInterval(playbackIntervalRef.current);
            playbackIntervalRef.current = null;
          }
          return { ...prev, isPlaying: false };
        }
        
        const snapshot = historySnapshots[nextIndex];
        setDevices(snapshot.devices);
        setLinks(snapshot.links);
        return { ...prev, currentIndex: nextIndex };
      });
    }, 2000 / timeTravel.playbackSpeed);
  }, [historySnapshots, timeTravel.playbackSpeed]);

  const pauseHistory = useCallback(() => {
    if (playbackIntervalRef.current) {
      clearInterval(playbackIntervalRef.current);
      playbackIntervalRef.current = null;
    }
    setTimeTravel((prev) => ({ ...prev, isPlaying: false }));
  }, []);

  const setPlaybackSpeed = useCallback((speed: number) => {
    setTimeTravel((prev) => ({ ...prev, playbackSpeed: speed }));
    
    if (timeTravel.isPlaying && playbackIntervalRef.current) {
      clearInterval(playbackIntervalRef.current);
      playbackIntervalRef.current = setInterval(() => {
        setTimeTravel((prev) => {
          const nextIndex = prev.currentIndex + 1;
          if (nextIndex >= historySnapshots.length) {
            if (playbackIntervalRef.current) {
              clearInterval(playbackIntervalRef.current);
              playbackIntervalRef.current = null;
            }
            return { ...prev, isPlaying: false };
          }
          
          const snapshot = historySnapshots[nextIndex];
          setDevices(snapshot.devices);
          setLinks(snapshot.links);
          return { ...prev, currentIndex: nextIndex };
        });
      }, 2000 / speed);
    }
  }, [historySnapshots, timeTravel.isPlaying]);

  const triggerFault = useCallback((deviceId: string) => {
    if (wsClient.isConnected()) {
      wsClient.send('TRIGGER_FAULT', { deviceId });
    }
  }, []);

  useEffect(() => {
    return () => {
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current);
      }
    };
  }, []);

  return {
    devices,
    links,
    selectedDevice,
    selectedLink,
    isConnected,
    linkMetricsHistory: linkMetricsHistory.current,
    deviceMetricsHistory: deviceMetricsHistory.current,
    healthScore,
    historySnapshots,
    timeTravel,
    faultEvents,
    setSelectedDevice,
    setSelectedLink,
    addDevice,
    removeDevice,
    addLink,
    removeLink,
    requestSync,
    enableTimeTravel,
    jumpToSnapshot,
    playHistory,
    pauseHistory,
    setPlaybackSpeed,
    triggerFault,
  };
};
