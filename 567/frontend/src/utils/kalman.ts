import { TrackPoint, KalmanState, DriftAnalysisResult } from '@/types';

const EARTH_RADIUS = 6371000;

function toMeters(lat: number, lng: number, refLat: number, refLng: number): { x: number; y: number } {
  const x = (lng - refLng) * Math.PI / 180 * EARTH_RADIUS * Math.cos(refLat * Math.PI / 180);
  const y = (lat - refLat) * Math.PI / 180 * EARTH_RADIUS;
  return { x, y };
}

function fromMeters(x: number, y: number, refLat: number, refLng: number): { lat: number; lng: number } {
  const lat = refLat + y * 180 / Math.PI / EARTH_RADIUS;
  const lng = refLng + x * 180 / Math.PI / EARTH_RADIUS / Math.cos(refLat * Math.PI / 180);
  return { lat, lng };
}

function calculateDistance(p1: { lat: number; lng: number }, p2: { lat: number; lng: number }): number {
  const dLat = (p2.lat - p1.lat) * Math.PI / 180;
  const dLng = (p2.lng - p1.lng) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return EARTH_RADIUS * c;
}

function initializeKalmanState(initialPoint: TrackPoint): KalmanState {
  const refLat = initialPoint.lat;
  const refLng = initialPoint.lng;
  const { x, y } = toMeters(initialPoint.lat, initialPoint.lng, refLat, refLng);
  
  return {
    x,
    y,
    vx: 0,
    vy: 0,
    P: [
      [1, 0, 0, 0],
      [0, 1, 0, 0],
      [0, 0, 1, 0],
      [0, 0, 0, 1],
    ],
    timestamp: initialPoint.time.getTime(),
  };
}

function kalmanPredict(state: KalmanState, dt: number, processNoise: number): KalmanState {
  const F = [
    [1, 0, dt, 0],
    [0, 1, 0, dt],
    [0, 0, 1, 0],
    [0, 0, 0, 1],
  ];
  
  const Q = [
    [processNoise * dt, 0, processNoise * dt * dt / 2, 0],
    [0, processNoise * dt, 0, processNoise * dt * dt / 2],
    [processNoise * dt * dt / 2, 0, processNoise * dt * dt * dt / 3, 0],
    [0, processNoise * dt * dt / 2, 0, processNoise * dt * dt * dt / 3],
  ];
  
  const x = F[0][0] * state.x + F[0][2] * state.vx;
  const y = F[1][1] * state.y + F[1][3] * state.vy;
  const vx = F[2][2] * state.vx;
  const vy = F[3][3] * state.vy;
  
  const P = [
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
  ];
  
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      for (let k = 0; k < 4; k++) {
        P[i][j] += F[i][k] * state.P[k][j];
      }
    }
  }
  
  const P_ = [
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
  ];
  
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      for (let k = 0; k < 4; k++) {
        P_[i][j] += P[i][k] * F[j][k];
      }
      P_[i][j] += Q[i][j];
    }
  }
  
  return { x, y, vx, vy, P: P_, timestamp: state.timestamp + dt * 1000 };
}

function kalmanUpdate(
  state: KalmanState,
  measurement: { x: number; y: number },
  measurementNoise: number
): KalmanState {
  const H = [
    [1, 0, 0, 0],
    [0, 1, 0, 0],
  ];
  
  const R = [
    [measurementNoise, 0],
    [0, measurementNoise],
  ];
  
  const y1 = measurement.x - H[0][0] * state.x;
  const y2 = measurement.y - H[1][1] * state.y;
  
  const S = [
    [0, 0],
    [0, 0],
  ];
  
  for (let i = 0; i < 2; i++) {
    for (let j = 0; j < 2; j++) {
      for (let k = 0; k < 4; k++) {
        S[i][j] += H[i][k] * state.P[k][j === 0 ? 0 : 1];
      }
      S[i][j] += R[i][j];
    }
  }
  
  const det = S[0][0] * S[1][1] - S[0][1] * S[1][0];
  const S_inv = [
    [S[1][1] / det, -S[0][1] / det],
    [-S[1][0] / det, S[0][0] / det],
  ];
  
  const K = [
    [0, 0],
    [0, 0],
    [0, 0],
    [0, 0],
  ];
  
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 2; j++) {
      for (let k = 0; k < 2; k++) {
        K[i][j] += state.P[i][k === 0 ? 0 : 1] * S_inv[k][j];
      }
    }
  }
  
  const newX = state.x + K[0][0] * y1 + K[0][1] * y2;
  const newY = state.y + K[1][0] * y1 + K[1][1] * y2;
  const newVx = state.vx + K[2][0] * y1 + K[2][1] * y2;
  const newVy = state.vy + K[3][0] * y1 + K[3][1] * y2;
  
  const I = [
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 0],
    [0, 0, 0, 1],
  ];
  
  const KH = [
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
  ];
  
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      for (let k = 0; k < 2; k++) {
        KH[i][j] += K[i][k] * H[k][j];
      }
    }
  }
  
  const I_KH = [
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
  ];
  
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      I_KH[i][j] = I[i][j] - KH[i][j];
    }
  }
  
  const newP = [
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
  ];
  
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      for (let k = 0; k < 4; k++) {
        newP[i][j] += I_KH[i][k] * state.P[k][j];
      }
    }
  }
  
  return {
    x: newX,
    y: newY,
    vx: newVx,
    vy: newVy,
    P: newP,
    timestamp: state.timestamp,
  };
}

export function applyKalmanFilter(
  points: TrackPoint[],
  processNoise: number = 0.1,
  measurementNoise: number = 5.0
): TrackPoint[] {
  if (points.length < 3) return points;
  
  const filteredPoints: TrackPoint[] = [];
  const refLat = points[0].lat;
  const refLng = points[0].lng;
  
  let state = initializeKalmanState(points[0]);
  filteredPoints.push({ ...points[0] });
  
  for (let i = 1; i < points.length; i++) {
    const point = points[i];
    const dt = (point.time.getTime() - state.timestamp) / 1000;
    
    if (dt <= 0) {
      filteredPoints.push({ ...point });
      continue;
    }
    
    state = kalmanPredict(state, dt, processNoise);
    
    const { x, y } = toMeters(point.lat, point.lng, refLat, refLng);
    let noise = measurementNoise;
    
    if (point.quality?.hdop) {
      noise = measurementNoise * point.quality.hdop / 2;
    }
    
    state = kalmanUpdate(state, { x, y }, noise);
    
    const { lat, lng } = fromMeters(state.x, state.y, refLat, refLng);
    
    filteredPoints.push({
      ...point,
      lat,
      lng,
      speed: Math.sqrt(state.vx * state.vx + state.vy * state.vy),
    });
  }
  
  return filteredPoints;
}

export function analyzeDrift(points: TrackPoint[]): DriftAnalysisResult {
  if (points.length < 5) {
    return {
      hasLargeDrift: false,
      driftMagnitude: 0,
      driftDirection: 'stationary',
      outliers: [],
      maxSpeed: 0,
      avgSpeed: 0,
    };
  }
  
  const speeds: number[] = [];
  const distances: number[] = [];
  const outliers: number[] = [];
  
  for (let i = 1; i < points.length; i++) {
    const distance = calculateDistance(points[i - 1], points[i]);
    const timeDiff = (points[i].time.getTime() - points[i - 1].time.getTime()) / 1000;
    const speed = timeDiff > 0 ? distance / timeDiff : 0;
    
    distances.push(distance);
    speeds.push(speed);
  }
  
  const avgSpeed = speeds.reduce((a, b) => a + b, 0) / speeds.length;
  const maxSpeed = Math.max(...speeds);
  const speedStdDev = Math.sqrt(
    speeds.reduce((sum, s) => sum + Math.pow(s - avgSpeed, 2), 0) / speeds.length
  );
  
  const threshold = avgSpeed + 3 * speedStdDev;
  for (let i = 0; i < speeds.length; i++) {
    if (speeds[i] > threshold && speeds[i] > 25) {
      outliers.push(i + 1);
    }
  }
  
  const driftMagnitude = outliers.length > 0 
    ? outliers.reduce((max, idx) => Math.max(max, distances[idx - 1]), 0)
    : 0;
  
  let driftDirection: 'left' | 'right' | 'stationary' = 'stationary';
  if (avgSpeed > 1) {
    driftDirection = Math.random() > 0.5 ? 'right' : 'left';
  }
  
  return {
    hasLargeDrift: outliers.length > 0 || maxSpeed > 50,
    driftMagnitude,
    driftDirection,
    outliers,
    maxSpeed,
    avgSpeed,
  };
}

export function detectOutliers(points: TrackPoint[], threshold: number = 3): number[] {
  if (points.length < 5) return [];
  
  const distances: number[] = [];
  for (let i = 1; i < points.length; i++) {
    distances.push(calculateDistance(points[i - 1], points[i]));
  }
  
  const avgDistance = distances.reduce((a, b) => a + b, 0) / distances.length;
  const stdDev = Math.sqrt(
    distances.reduce((sum, d) => sum + Math.pow(d - avgDistance, 2), 0) / distances.length
  );
  
  const outliers: number[] = [];
  for (let i = 0; i < distances.length; i++) {
    if (distances[i] > avgDistance + threshold * stdDev) {
      outliers.push(i + 1);
    }
  }
  
  return outliers;
}

export function removeOutliers(points: TrackPoint[], threshold: number = 3): TrackPoint[] {
  const outliers = detectOutliers(points, threshold);
  if (outliers.length === 0) return points;
  
  const outlierSet = new Set(outliers);
  return points.filter((_, idx) => !outlierSet.has(idx));
}

export function smoothTrackWithKalman(
  points: TrackPoint[],
  processNoise: number = 0.1,
  measurementNoise: number = 5.0
): {
  smoothed: TrackPoint[];
  driftAnalysis: DriftAnalysisResult;
} {
  const driftAnalysis = analyzeDrift(points);
  
  let processedPoints = points;
  if (driftAnalysis.hasLargeDrift) {
    processedPoints = removeOutliers(points, 3);
  }
  
  const smoothed = applyKalmanFilter(processedPoints, processNoise, measurementNoise);
  
  return { smoothed, driftAnalysis };
}
