import { Photo, Track, TrackPoint, GPSPoint, MatchConfig, DeviceConfig, MatchResult } from '@/types';
import { smoothTrackWithKalman } from './kalman';

function findNearestPoints(points: TrackPoint[], targetTime: Date): { prev: TrackPoint | null; next: TrackPoint | null; prevIndex: number; nextIndex: number } {
  const target = targetTime.getTime();
  
  let left = 0;
  let right = points.length - 1;
  
  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const midTime = points[mid].time.getTime();
    
    if (midTime === target) {
      return { prev: points[mid], next: points[mid], prevIndex: mid, nextIndex: mid };
    } else if (midTime < target) {
      left = mid + 1;
    } else {
      right = mid - 1;
    }
  }
  
  return {
    prev: right >= 0 ? points[right] : null,
    next: left < points.length ? points[left] : null,
    prevIndex: right,
    nextIndex: left,
  };
}

function interpolatePoint(prev: TrackPoint, next: TrackPoint, targetTime: Date): GPSPoint {
  const prevTime = prev.time.getTime();
  const nextTime = next.time.getTime();
  const target = targetTime.getTime();
  
  if (prevTime === nextTime) {
    return { lat: prev.lat, lng: prev.lng, elevation: prev.elevation };
  }
  
  const ratio = (target - prevTime) / (nextTime - prevTime);
  
  return {
    lat: prev.lat + (next.lat - prev.lat) * ratio,
    lng: prev.lng + (next.lng - prev.lng) * ratio,
    elevation: prev.elevation !== undefined && next.elevation !== undefined
      ? prev.elevation + (next.elevation - prev.elevation) * ratio
      : undefined,
  };
}

function splineInterpolate(
  points: TrackPoint[],
  targetTime: Date,
  prevIndex: number,
  nextIndex: number
): GPSPoint {
  const n = points.length;
  const i0 = Math.max(0, prevIndex - 1);
  const i1 = prevIndex;
  const i2 = nextIndex;
  const i3 = Math.min(n - 1, nextIndex + 1);
  
  if (i0 < 0 || i3 >= n || i1 < 0 || i2 >= n || i1 === i2) {
    return interpolatePoint(points[i1] || points[i0], points[i2] || points[i3], targetTime);
  }
  
  const p0 = points[i0];
  const p1 = points[i1];
  const p2 = points[i2];
  const p3 = points[i3];
  
  const t0 = p1.time.getTime();
  const t1 = p2.time.getTime();
  const t = targetTime.getTime();
  const mu = (t - t0) / (t1 - t0);
  
  const mu2 = mu * mu;
  const mu3 = mu2 * mu;
  
  function catmullRom(v0: number, v1: number, v2: number, v3: number): number {
    return 0.5 * (
      (2 * v1) +
      (-v0 + v2) * mu +
      (2 * v0 - 5 * v1 + 4 * v2 - v3) * mu2 +
      (-v0 + 3 * v1 - 3 * v2 + v3) * mu3
    );
  }
  
  return {
    lat: catmullRom(p0.lat, p1.lat, p2.lat, p3.lat),
    lng: catmullRom(p0.lng, p1.lng, p2.lng, p3.lng),
    elevation: p0.elevation !== undefined && p1.elevation !== undefined && 
               p2.elevation !== undefined && p3.elevation !== undefined
      ? catmullRom(p0.elevation, p1.elevation, p2.elevation, p3.elevation)
      : undefined,
  };
}

function getPhotoConfig(
  photo: Photo,
  globalConfig: MatchConfig,
  devices: DeviceConfig[]
): {
  timeOffset: number;
  maxTimeDiff: number;
  interpolation: 'linear' | 'nearest' | 'spline';
  kalmanEnabled: boolean;
} {
  if (globalConfig.useDeviceConfig && photo.deviceId) {
    const deviceConfig = devices.find(d => d.id === photo.deviceId);
    if (deviceConfig) {
      return {
        timeOffset: deviceConfig.timeOffset,
        maxTimeDiff: deviceConfig.maxTimeDiff,
        interpolation: deviceConfig.interpolation,
        kalmanEnabled: deviceConfig.kalmanFilterEnabled,
      };
    }
  }
  
  return {
    timeOffset: globalConfig.globalTimeOffset,
    maxTimeDiff: globalConfig.globalMaxTimeDiff,
    interpolation: globalConfig.interpolation,
    kalmanEnabled: globalConfig.enableKalmanFilter,
  };
}

function getTrackPointsForMatching(
  track: Track,
  useKalman: boolean,
  processNoise: number,
  measurementNoise: number
): TrackPoint[] {
  if (useKalman && track.filteredPoints) {
    return track.filteredPoints;
  }
  
  if (useKalman) {
    const { smoothed } = smoothTrackWithKalman(
      track.points,
      processNoise,
      measurementNoise
    );
    return smoothed;
  }
  
  return track.points;
}

export function matchPhotoToTrack(
  photo: Photo,
  tracks: Track[],
  globalConfig: MatchConfig,
  devices: DeviceConfig[] = []
): MatchResult | null {
  if (!photo.exifData.dateTimeOriginal || tracks.length === 0) return null;
  
  const photoConfig = getPhotoConfig(photo, globalConfig, devices);
  
  const photoTime = new Date(
    photo.exifData.dateTimeOriginal.getTime() + photoConfig.timeOffset * 1000
  );
  const photoTimeMs = photoTime.getTime();
  
  let bestMatch: MatchResult | null = null;
  let minTimeDiff = Infinity;
  
  for (const track of tracks) {
    if (track.points.length === 0) continue;
    
    const trackPoints = getTrackPointsForMatching(
      track,
      photoConfig.kalmanEnabled,
      globalConfig.kalmanProcessNoise,
      globalConfig.kalmanMeasurementNoise
    );
    
    const { prev, next, prevIndex, nextIndex } = findNearestPoints(trackPoints, photoTime);
    
    if (!prev && !next) continue;
    
    let timeDiff: number;
    let gps: GPSPoint;
    let interpolationMethod = photoConfig.interpolation;
    
    if (prev && next) {
      const prevDiff = Math.abs(photoTimeMs - prev.time.getTime());
      const nextDiff = Math.abs(photoTimeMs - next.time.getTime());
      
      if (photoConfig.interpolation === 'spline') {
        gps = splineInterpolate(trackPoints, photoTime, prevIndex, nextIndex);
        timeDiff = Math.min(prevDiff, nextDiff);
      } else if (photoConfig.interpolation === 'linear') {
        gps = interpolatePoint(prev, next, photoTime);
        const midTime = (prev.time.getTime() + next.time.getTime()) / 2;
        timeDiff = Math.abs(photoTimeMs - midTime);
      } else {
        gps = prevDiff <= nextDiff
          ? { lat: prev.lat, lng: prev.lng, elevation: prev.elevation }
          : { lat: next.lat, lng: next.lng, elevation: next.elevation };
        timeDiff = Math.min(prevDiff, nextDiff);
        interpolationMethod = 'nearest';
      }
    } else if (prev) {
      timeDiff = Math.abs(photoTimeMs - prev.time.getTime());
      gps = { lat: prev.lat, lng: prev.lng, elevation: prev.elevation };
      interpolationMethod = 'nearest';
    } else {
      timeDiff = Math.abs(photoTimeMs - next!.time.getTime());
      gps = { lat: next!.lat, lng: next!.lng, elevation: next!.elevation };
      interpolationMethod = 'nearest';
    }
    
    if (timeDiff <= photoConfig.maxTimeDiff * 1000 && timeDiff < minTimeDiff) {
      minTimeDiff = timeDiff;
      const confidence = Math.max(0, 1 - timeDiff / (photoConfig.maxTimeDiff * 1000));
      
      bestMatch = {
        photoId: photo.id,
        gps,
        confidence,
        timeDiff: timeDiff / 1000,
        trackPointIndex: prevIndex >= 0 ? prevIndex : nextIndex,
        trackId: track.id,
        interpolationMethod,
      };
    }
  }
  
  return bestMatch;
}

export function matchAllPhotos(
  photos: Photo[],
  tracks: Track[],
  globalConfig: MatchConfig,
  devices: DeviceConfig[] = []
): Map<string, MatchResult> {
  const results = new Map<string, MatchResult>();
  
  photos.forEach(photo => {
    const match = matchPhotoToTrack(photo, tracks, globalConfig, devices);
    if (match) {
      results.set(photo.id, match);
    }
  });
  
  return results;
}

export function preprocessTracksWithKalman(
  tracks: Track[],
  processNoise: number,
  measurementNoise: number
): Track[] {
  return tracks.map(track => {
    const { smoothed, driftAnalysis } = smoothTrackWithKalman(
      track.points,
      processNoise,
      measurementNoise
    );
    
    return {
      ...track,
      filteredPoints: smoothed,
    };
  });
}
