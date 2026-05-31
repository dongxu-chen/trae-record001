import { GPSPoint, PrivacyConfig, Photo } from '@/types';
import { getPhotoEffectiveGPS } from './export';

function snapToGrid(value: number, gridSize: number): number {
  return Math.round(value / gridSize) * gridSize;
}

function randomOffset(value: number, maxOffset: number, seed: number): number {
  const x = Math.sin(seed) * 10000;
  const rand = x - Math.floor(x);
  const offset = (rand - 0.5) * 2 * maxOffset;
  return value + offset;
}

function deterministicRandom(photoId: string): number {
  let hash = 0;
  for (let i = 0; i < photoId.length; i++) {
    const char = photoId.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return Math.abs(hash);
}

export function obfuscateGPS(
  gps: GPSPoint,
  config: PrivacyConfig,
  photoId?: string
): GPSPoint {
  if (!config.enabled) return gps;

  const seed = photoId ? deterministicRandom(photoId) : Math.random() * 10000;

  switch (config.mode) {
    case 'blur': {
      const latOffset = (Math.random() - 0.5) * config.blurRadius * 2 / 111320;
      const lngOffset = (Math.random() - 0.5) * config.blurRadius * 2 / (111320 * Math.cos(gps.lat * Math.PI / 180));
      return {
        lat: gps.lat + latOffset,
        lng: gps.lng + lngOffset,
        elevation: gps.elevation,
      };
    }
    case 'snap': {
      const latGrid = config.snapGridSize / 111320;
      const lngGrid = config.snapGridSize / (111320 * Math.cos(gps.lat * Math.PI / 180));
      return {
        lat: snapToGrid(gps.lat, latGrid),
        lng: snapToGrid(gps.lng, lngGrid),
        elevation: gps.elevation,
      };
    }
    case 'random': {
      const latMaxOffset = config.randomOffset / 111320;
      const lngMaxOffset = config.randomOffset / (111320 * Math.cos(gps.lat * Math.PI / 180));
      return {
        lat: randomOffset(gps.lat, latMaxOffset, seed),
        lng: randomOffset(gps.lng, lngMaxOffset, seed + 1),
        elevation: gps.elevation,
      };
    }
    case 'remove': {
      const factor = Math.pow(10, -config.removePrecision);
      return {
        lat: Math.round(gps.lat / factor) * factor,
        lng: Math.round(gps.lng / factor) * factor,
      };
    }
    default:
      return gps;
  }
}

export function obfuscatePhotoGPS(
  photo: Photo,
  config: PrivacyConfig
): GPSPoint | undefined {
  const gps = getPhotoEffectiveGPS(photo);
  if (!gps) return undefined;
  return obfuscateGPS(gps, config, photo.id);
}

export function getDisplayGPS(
  photo: Photo,
  privacyConfig: PrivacyConfig
): GPSPoint | undefined {
  const gps = getPhotoEffectiveGPS(photo);
  if (!gps) return undefined;
  if (privacyConfig.enabled && privacyConfig.applyToDisplay) {
    return obfuscateGPS(gps, privacyConfig, photo.id);
  }
  return gps;
}

export function getExportGPS(
  photo: Photo,
  privacyConfig: PrivacyConfig
): GPSPoint | undefined {
  const gps = getPhotoEffectiveGPS(photo);
  if (!gps) return undefined;
  if (privacyConfig.enabled && privacyConfig.applyToExport) {
    return obfuscateGPS(gps, privacyConfig, photo.id);
  }
  return gps;
}

export function getPrivacyDescription(config: PrivacyConfig): string {
  if (!config.enabled) return '未启用';
  switch (config.mode) {
    case 'blur':
      return `模糊化: ±${config.blurRadius}米范围随机偏移`;
    case 'snap':
      return `网格吸附: ${config.snapGridSize}米网格`;
    case 'random':
      return `随机偏移: 最大${config.randomOffset}米确定性偏移`;
    case 'remove':
      return `精度降低: 保留${config.removePrecision}位小数`;
    default:
      return '未知';
  }
}
