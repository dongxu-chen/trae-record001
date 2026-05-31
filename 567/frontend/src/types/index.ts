export interface GPSPoint {
  lat: number;
  lng: number;
  elevation?: number;
}

export interface GPSQuality {
  hdop?: number;
  vdop?: number;
  pdop?: number;
  satellites?: number;
  fixType?: 'none' | '2d' | '3d' | 'dgps' | 'pps';
  signalToNoiseRatio?: number;
}

export interface TrackPoint {
  lat: number;
  lng: number;
  time: Date;
  elevation?: number;
  quality?: GPSQuality;
  speed?: number;
  heading?: number;
}

export interface KalmanState {
  x: number;
  y: number;
  vx: number;
  vy: number;
  P: number[][];
  timestamp: number;
}

export interface Track {
  id: string;
  name: string;
  points: TrackPoint[];
  filteredPoints?: TrackPoint[];
  startTime: Date;
  endTime: Date;
  deviceId?: string;
}

export interface ExifData {
  make?: string;
  model?: string;
  dateTimeOriginal?: Date;
  gps?: GPSPoint;
  exposureTime?: string;
  fNumber?: number;
  iso?: number;
  focalLength?: number;
  serialNumber?: string;
  software?: string;
}

export interface DeviceConfig {
  id: string;
  name: string;
  make?: string;
  model?: string;
  serialNumber?: string;
  timeOffset: number;
  maxTimeDiff: number;
  timeDriftRate: number;
  autoCalibrationEnabled: boolean;
  minConfidenceForCalibration: number;
  kalmanFilterEnabled: boolean;
  kalmanProcessNoise: number;
  kalmanMeasurementNoise: number;
  interpolation: 'linear' | 'nearest' | 'spline';
  color: string;
}

export interface HighConfidencePoint {
  photoId: string;
  photoTime: Date;
  photoGps: GPSPoint;
  trackPoint: TrackPoint;
  trackTime: Date;
  trackGps: GPSPoint;
  distance: number;
  timeDiff: number;
  confidence: number;
}

export interface CalibrationResult {
  deviceId: string;
  timeOffset: number;
  confidence: number;
  sampleCount: number;
  calibrationPoints: HighConfidencePoint[];
  rmse: number;
}

export interface Photo {
  id: string;
  name: string;
  file?: File;
  thumbnail: string;
  originalUrl: string;
  exifData: ExifData;
  deviceId?: string;
  originalGps?: GPSPoint;
  matchedGps?: GPSPoint;
  manualGps?: GPSPoint;
  matched: boolean;
  selected: boolean;
  timeOffset?: number;
  matchConfidence?: number;
  matchTimeDiff?: number;
  calibrationWeight?: number;
}

export interface MatchConfig {
  globalTimeOffset: number;
  globalMaxTimeDiff: number;
  interpolation: 'linear' | 'nearest' | 'spline';
  useDeviceConfig: boolean;
  enableKalmanFilter: boolean;
  enableAutoCalibration: boolean;
  minCalibrationConfidence: number;
  minCalibrationPoints: number;
  maxCalibrationDistance: number;
  kalmanProcessNoise: number;
  kalmanMeasurementNoise: number;
}

export interface MatchResult {
  photoId: string;
  gps: GPSPoint;
  confidence: number;
  timeDiff: number;
  trackPointIndex: number;
  trackId: string;
  interpolationMethod: string;
}

export interface DriftAnalysisResult {
  hasLargeDrift: boolean;
  driftMagnitude: number;
  driftDirection: 'left' | 'right' | 'stationary';
  outliers: number[];
  maxSpeed: number;
  avgSpeed: number;
}

export interface PhotoCluster {
  id: string;
  center: GPSPoint;
  photos: Photo[];
  radius: number;
  color: string;
}

export interface AnimationState {
  isPlaying: boolean;
  currentIndex: number;
  speed: number;
  loop: boolean;
  showTrail: boolean;
  trailLength: number;
}

export interface PrivacyConfig {
  enabled: boolean;
  mode: 'blur' | 'snap' | 'random' | 'remove';
  blurRadius: number;
  snapGridSize: number;
  randomOffset: number;
  removePrecision: number;
  applyToExport: boolean;
  applyToDisplay: boolean;
}
