import { create } from 'zustand';
import { Photo, Track, MatchConfig, GPSPoint, DeviceConfig, CalibrationResult, AnimationState, PrivacyConfig } from '@/types';

interface AppState {
  photos: Photo[];
  tracks: Track[];
  devices: DeviceConfig[];
  selectedPhotoId: string | null;
  selectedDeviceId: string | null;
  matchConfig: MatchConfig;
  isMatching: boolean;
  isCalibrating: boolean;
  calibrationResults: Map<string, CalibrationResult>;
  animation: AnimationState;
  privacy: PrivacyConfig;
  showClusters: boolean;
  clusterDistance: number;
  
  addPhotos: (photos: Photo[]) => void;
  removePhoto: (id: string) => void;
  clearPhotos: () => void;
  selectPhoto: (id: string | null) => void;
  togglePhotoSelection: (id: string) => void;
  selectAllPhotos: (selected: boolean) => void;
  setPhotoDevice: (photoId: string, deviceId: string | undefined) => void;
  
  addTrack: (track: Track) => void;
  removeTrack: (id: string) => void;
  clearTracks: () => void;
  setTrackFilteredPoints: (trackId: string, points: Track[]) => void;
  
  addDevice: (device: DeviceConfig) => void;
  removeDevice: (id: string) => void;
  updateDevice: (id: string, updates: Partial<DeviceConfig>) => void;
  selectDevice: (id: string | null) => void;
  clearDevices: () => void;
  
  setMatchConfig: (config: Partial<MatchConfig>) => void;
  setIsMatching: (isMatching: boolean) => void;
  setIsCalibrating: (isCalibrating: boolean) => void;
  setCalibrationResults: (results: Map<string, CalibrationResult>) => void;
  
  setMatchedGps: (photoId: string, gps: GPSPoint | undefined) => void;
  setManualGps: (photoId: string, gps: GPSPoint | undefined) => void;
  setPhotoMatched: (photoId: string, matched: boolean) => void;
  setPhotoMatchConfidence: (photoId: string, confidence: number, timeDiff?: number) => void;
  
  setAnimation: (updates: Partial<AnimationState>) => void;
  setPrivacy: (updates: Partial<PrivacyConfig>) => void;
  setShowClusters: (show: boolean) => void;
  setClusterDistance: (distance: number) => void;
  
  getSelectedPhotos: () => Photo[];
  getMatchedPhotos: () => Photo[];
  getPhotosByDevice: (deviceId: string) => Photo[];
  detectDevicesFromPhotos: () => DeviceConfig[];
}

const generateId = (): string => Math.random().toString(36).substring(2, 15);

const defaultColors = [
  '#00d4ff', '#ff6b35', '#7c3aed', '#22c55e', '#f59e0b',
  '#ec4899', '#06b6d4', '#8b5cf6',
];

export const useStore = create<AppState>((set, get) => ({
  photos: [],
  tracks: [],
  devices: [],
  selectedPhotoId: null,
  selectedDeviceId: null,
  matchConfig: {
    globalTimeOffset: 0,
    globalMaxTimeDiff: 300,
    interpolation: 'linear',
    useDeviceConfig: true,
    enableKalmanFilter: true,
    enableAutoCalibration: true,
    minCalibrationConfidence: 0.7,
    minCalibrationPoints: 5,
    maxCalibrationDistance: 50,
    kalmanProcessNoise: 0.1,
    kalmanMeasurementNoise: 5.0,
  },
  isMatching: false,
  isCalibrating: false,
  calibrationResults: new Map(),
  animation: {
    isPlaying: false,
    currentIndex: 0,
    speed: 1,
    loop: true,
    showTrail: true,
    trailLength: 10,
  },
  privacy: {
    enabled: false,
    mode: 'blur',
    blurRadius: 50,
    snapGridSize: 100,
    randomOffset: 50,
    removePrecision: 2,
    applyToExport: true,
    applyToDisplay: false,
  },
  showClusters: false,
  clusterDistance: 50,
  
  addPhotos: (photos) => set((state) => {
    const newPhotos = photos.map(photo => {
      if (photo.exifData.make || photo.exifData.model) {
        let existingDevice = state.devices.find(d => 
          (d.make === photo.exifData.make && d.model === photo.exifData.model)
        );
        if (!existingDevice) {
          existingDevice = {
            id: generateId(),
            name: `${photo.exifData.make || 'Unknown'} ${photo.exifData.model || 'Device'}`,
            make: photo.exifData.make,
            model: photo.exifData.model,
            timeOffset: 0,
            maxTimeDiff: 300,
            timeDriftRate: 0,
            autoCalibrationEnabled: true,
            minConfidenceForCalibration: 0.7,
            kalmanFilterEnabled: true,
            kalmanProcessNoise: 0.1,
            kalmanMeasurementNoise: 5.0,
            interpolation: 'linear',
            color: defaultColors[state.devices.length % defaultColors.length],
          };
          state.devices.push(existingDevice);
        }
        return { ...photo, deviceId: existingDevice.id };
      }
      return photo;
    });
    return { 
      photos: [...state.photos, ...newPhotos],
      devices: [...state.devices],
    };
  }),
  
  removePhoto: (id) => set((state) => ({
    photos: state.photos.filter(p => p.id !== id),
    selectedPhotoId: state.selectedPhotoId === id ? null : state.selectedPhotoId,
  })),
  
  clearPhotos: () => set({ photos: [], selectedPhotoId: null }),
  selectPhoto: (id) => set({ selectedPhotoId: id }),
  
  togglePhotoSelection: (id) => set((state) => ({
    photos: state.photos.map(p => 
      p.id === id ? { ...p, selected: !p.selected } : p
    ),
  })),
  
  selectAllPhotos: (selected) => set((state) => ({
    photos: state.photos.map(p => ({ ...p, selected })),
  })),
  
  setPhotoDevice: (photoId, deviceId) => set((state) => ({
    photos: state.photos.map(p =>
      p.id === photoId ? { ...p, deviceId } : p
    ),
  })),
  
  addTrack: (track) => set((state) => ({ tracks: [...state.tracks, track] })),
  removeTrack: (id) => set((state) => ({ tracks: state.tracks.filter(t => t.id !== id) })),
  clearTracks: () => set({ tracks: [] }),
  
  setTrackFilteredPoints: (trackId, filteredPoints) => set((state) => ({
    tracks: state.tracks.map(t => 
      t.id === trackId ? { ...t, filteredPoints: filteredPoints.find(ft => ft.id === trackId)?.filteredPoints } : t
    ),
  })),
  
  addDevice: (device) => set((state) => ({ devices: [...state.devices, device] })),
  removeDevice: (id) => set((state) => ({
    devices: state.devices.filter(d => d.id !== id),
    photos: state.photos.map(p => p.deviceId === id ? { ...p, deviceId: undefined } : p),
  })),
  
  updateDevice: (id, updates) => set((state) => ({
    devices: state.devices.map(d => d.id === id ? { ...d, ...updates } : d),
  })),
  
  selectDevice: (id) => set({ selectedDeviceId: id }),
  clearDevices: () => set({ devices: [] }),
  
  setMatchConfig: (config) => set((state) => ({
    matchConfig: { ...state.matchConfig, ...config },
  })),
  
  setIsMatching: (isMatching) => set({ isMatching }),
  setIsCalibrating: (isCalibrating) => set({ isCalibrating }),
  setCalibrationResults: (results) => set({ calibrationResults: results }),
  
  setMatchedGps: (photoId, gps) => set((state) => ({
    photos: state.photos.map(p => p.id === photoId ? { ...p, matchedGps: gps } : p),
  })),
  
  setManualGps: (photoId, gps) => set((state) => ({
    photos: state.photos.map(p => p.id === photoId ? { ...p, manualGps: gps } : p),
  })),
  
  setPhotoMatched: (photoId, matched) => set((state) => ({
    photos: state.photos.map(p => p.id === photoId ? { ...p, matched } : p),
  })),
  
  setPhotoMatchConfidence: (photoId, confidence, timeDiff) => set((state) => ({
    photos: state.photos.map(p =>
      p.id === photoId ? { ...p, matchConfidence: confidence, matchTimeDiff: timeDiff } : p
    ),
  })),
  
  setAnimation: (updates) => set((state) => ({
    animation: { ...state.animation, ...updates },
  })),
  
  setPrivacy: (updates) => set((state) => ({
    privacy: { ...state.privacy, ...updates },
  })),
  
  setShowClusters: (show) => set({ showClusters: show }),
  setClusterDistance: (distance) => set({ clusterDistance: distance }),
  
  getSelectedPhotos: () => get().photos.filter(p => p.selected),
  getMatchedPhotos: () => get().photos.filter(p => p.matchedGps || p.manualGps || p.originalGps),
  getPhotosByDevice: (deviceId) => get().photos.filter(p => p.deviceId === deviceId),
  
  detectDevicesFromPhotos: () => {
    const { photos } = get();
    const deviceMap = new Map<string, { make?: string; model?: string; count: number }>();
    photos.forEach(photo => {
      if (photo.exifData.make || photo.exifData.model) {
        const key = `${photo.exifData.make || ''}-${photo.exifData.model || ''}`;
        const existing = deviceMap.get(key);
        if (existing) { existing.count++; }
        else { deviceMap.set(key, { make: photo.exifData.make, model: photo.exifData.model, count: 1 }); }
      }
    });
    const devices: DeviceConfig[] = [];
    let colorIndex = 0;
    deviceMap.forEach((info) => {
      devices.push({
        id: generateId(),
        name: `${info.make || 'Unknown'} ${info.model || 'Device'} (${info.count})`,
        make: info.make, model: info.model,
        timeOffset: 0, maxTimeDiff: 300, timeDriftRate: 0,
        autoCalibrationEnabled: true, minConfidenceForCalibration: 0.7,
        kalmanFilterEnabled: true, kalmanProcessNoise: 0.1, kalmanMeasurementNoise: 5.0,
        interpolation: 'linear',
        color: defaultColors[colorIndex++ % defaultColors.length],
      });
    });
    return devices;
  },
}));
