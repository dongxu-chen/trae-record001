import { Photo, Track, TrackPoint, DeviceConfig, HighConfidencePoint, CalibrationResult, GPSPoint } from '@/types';

const EARTH_RADIUS = 6371000;

function calculateDistance(p1: GPSPoint, p2: GPSPoint): number {
  const dLat = (p2.lat - p1.lat) * Math.PI / 180;
  const dLng = (p2.lng - p1.lng) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return EARTH_RADIUS * c;
}

function findNearestTrackPoint(track: Track, photoTime: Date): { point: TrackPoint; timeDiff: number; index: number } | null {
  const targetTime = photoTime.getTime();
  let minDiff = Infinity;
  let nearestPoint: TrackPoint | null = null;
  let nearestIndex = -1;
  
  for (let i = 0; i < track.points.length; i++) {
    const diff = Math.abs(track.points[i].time.getTime() - targetTime);
    if (diff < minDiff) {
      minDiff = diff;
      nearestPoint = track.points[i];
      nearestIndex = i;
    }
  }
  
  if (!nearestPoint) return null;
  
  return { point: nearestPoint, timeDiff: minDiff / 1000, index: nearestIndex };
}

function calculateGPSConfidence(quality?: { hdop?: number; satellites?: number; fixType?: string }): number {
  if (!quality) return 0.5;
  
  let confidence = 1.0;
  
  if (quality.hdop) {
    if (quality.hdop < 1) confidence *= 1.0;
    else if (quality.hdop < 2) confidence *= 0.9;
    else if (quality.hdop < 5) confidence *= 0.7;
    else if (quality.hdop < 10) confidence *= 0.5;
    else confidence *= 0.3;
  }
  
  if (quality.satellites) {
    if (quality.satellites >= 8) confidence *= 1.0;
    else if (quality.satellites >= 6) confidence *= 0.9;
    else if (quality.satellites >= 4) confidence *= 0.7;
    else if (quality.satellites >= 3) confidence *= 0.5;
    else confidence *= 0.2;
  }
  
  if (quality.fixType) {
    switch (quality.fixType) {
      case 'pps': confidence *= 1.0; break;
      case 'dgps': confidence *= 0.95; break;
      case '3d': confidence *= 0.85; break;
      case '2d': confidence *= 0.6; break;
      default: confidence *= 0.3;
    }
  }
  
  return Math.min(1, Math.max(0, confidence));
}

function calculatePointConfidence(
  photoGps: GPSPoint,
  trackGps: GPSPoint,
  distance: number,
  trackQuality?: any,
  timeDiff: number,
  maxDistance: number,
  maxTimeDiff: number
): number {
  const distanceScore = Math.max(0, 1 - distance / maxDistance);
  const timeScore = Math.max(0, 1 - timeDiff / maxTimeDiff);
  const gpsQualityScore = calculateGPSConfidence(trackQuality);
  
  const weights = {
    distance: 0.4,
    time: 0.3,
    gpsQuality: 0.3,
  };
  
  return (
    distanceScore * weights.distance +
    timeScore * weights.time +
    gpsQualityScore * weights.gpsQuality
  );
}

export function findHighConfidencePoints(
  photos: Photo[],
  tracks: Track[],
  maxDistance: number = 50,
  maxTimeDiff: number = 60,
  minConfidence: number = 0.7
): HighConfidencePoint[] {
  const highConfidencePoints: HighConfidencePoint[] = [];
  
  const photosWithGPS = photos.filter(p => p.originalGps && p.exifData.dateTimeOriginal);
  
  for (const photo of photosWithGPS) {
    if (!photo.originalGps || !photo.exifData.dateTimeOriginal) continue;
    
    const photoTime = photo.exifData.dateTimeOriginal;
    
    for (const track of tracks) {
      const nearest = findNearestTrackPoint(track, photoTime);
      if (!nearest) continue;
      
      const distance = calculateDistance(photo.originalGps, {
        lat: nearest.point.lat,
        lng: nearest.point.lng,
      });
      
      if (distance > maxDistance || nearest.timeDiff > maxTimeDiff) continue;
      
      const confidence = calculatePointConfidence(
        photo.originalGps,
        { lat: nearest.point.lat, lng: nearest.point.lng },
        distance,
        nearest.point.quality,
        nearest.timeDiff,
        maxDistance,
        maxTimeDiff
      );
      
      if (confidence >= minConfidence) {
        highConfidencePoints.push({
          photoId: photo.id,
          photoTime,
          photoGps: photo.originalGps,
          trackPoint: nearest.point,
          trackTime: nearest.point.time,
          trackGps: { lat: nearest.point.lat, lng: nearest.point.lng },
          distance,
          timeDiff: nearest.timeDiff,
          confidence,
        });
      }
    }
  }
  
  return highConfidencePoints.sort((a, b) => b.confidence - a.confidence);
}

export function calculateTimeOffsetFromPoints(points: HighConfidencePoint[]): number {
  if (points.length === 0) return 0;
  
  const offsets: number[] = points.map(p => 
    (p.trackTime.getTime() - p.photoTime.getTime()) / 1000
  );
  
  offsets.sort((a, b) => a - b);
  
  const q1 = offsets[Math.floor(offsets.length * 0.25)];
  const q3 = offsets[Math.floor(offsets.length * 0.75)];
  const iqr = q3 - q1;
  const lowerBound = q1 - 1.5 * iqr;
  const upperBound = q3 + 1.5 * iqr;
  
  const filteredOffsets = offsets.filter(o => o >= lowerBound && o <= upperBound);
  
  if (filteredOffsets.length === 0) {
    return offsets[Math.floor(offsets.length / 2)];
  }
  
  const weightedSum = filteredOffsets.reduce((sum, offset, idx) => {
    const weight = points[idx]?.confidence || 1;
    return sum + offset * weight;
  }, 0);
  
  const totalWeight = filteredOffsets.reduce((sum, _, idx) => {
    return sum + (points[idx]?.confidence || 1);
  }, 0);
  
  return weightedSum / totalWeight;
}

export function calculateRMSE(points: HighConfidencePoint[], timeOffset: number): number {
  if (points.length === 0) return Infinity;
  
  const squaredErrors = points.map(p => {
    const adjustedPhotoTime = new Date(p.photoTime.getTime() + timeOffset * 1000);
    const timeError = (adjustedPhotoTime.getTime() - p.trackTime.getTime()) / 1000;
    return timeError * timeError;
  });
  
  const mse = squaredErrors.reduce((a, b) => a + b, 0) / squaredErrors.length;
  return Math.sqrt(mse);
}

export function calibrateDevice(
  deviceId: string,
  photos: Photo[],
  tracks: Track[],
  config: {
    maxDistance: number;
    maxTimeDiff: number;
    minConfidence: number;
    minPoints: number;
  }
): CalibrationResult | null {
  const devicePhotos = photos.filter(p => p.deviceId === deviceId || !p.deviceId);
  
  const highConfidencePoints = findHighConfidencePoints(
    devicePhotos,
    tracks,
    config.maxDistance,
    config.maxTimeDiff,
    config.minConfidence
  );
  
  if (highConfidencePoints.length < config.minPoints) {
    return null;
  }
  
  const timeOffset = calculateTimeOffsetFromPoints(highConfidencePoints);
  const rmse = calculateRMSE(highConfidencePoints, timeOffset);
  
  const confidence = Math.max(0, 1 - rmse / config.maxTimeDiff);
  
  return {
    deviceId,
    timeOffset,
    confidence,
    sampleCount: highConfidencePoints.length,
    calibrationPoints: highConfidencePoints,
    rmse,
  };
}

export function autoCalibrateDevices(
  photos: Photo[],
  tracks: Track[],
  devices: DeviceConfig[],
  globalConfig: {
    maxDistance: number;
    maxTimeDiff: number;
    minConfidence: number;
    minPoints: number;
  }
): Map<string, CalibrationResult> {
  const results = new Map<string, CalibrationResult>();
  
  const uniqueDevices = new Set(photos.map(p => p.deviceId).filter(Boolean));
  
  if (uniqueDevices.size === 0) {
    const result = calibrateDevice('default', photos, tracks, globalConfig);
    if (result) {
      results.set('default', result);
    }
  } else {
    for (const deviceId of uniqueDevices) {
      const deviceConfig = devices.find(d => d.id === deviceId);
      if (deviceConfig && !deviceConfig.autoCalibrationEnabled) continue;
      
      const result = calibrateDevice(deviceId || 'default', photos, tracks, globalConfig);
      if (result) {
        results.set(deviceId || 'default', result);
      }
    }
  }
  
  return results;
}

export function estimatePhotoGPSQuality(photo: Photo): number {
  if (!photo.originalGps) return 0;
  
  let quality = 0.5;
  
  if (photo.exifData.make && photo.exifData.model) {
    quality += 0.1;
  }
  
  if (photo.matchConfidence) {
    quality = photo.matchConfidence;
  }
  
  return Math.min(1, quality);
}
