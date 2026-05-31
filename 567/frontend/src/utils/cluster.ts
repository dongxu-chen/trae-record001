import { Photo, GPSPoint, PhotoCluster } from '@/types';
import { getPhotoEffectiveGPS } from './export';

const EARTH_RADIUS = 6371000;

function haversineDistance(p1: GPSPoint, p2: GPSPoint): number {
  const dLat = (p2.lat - p1.lat) * Math.PI / 180;
  const dLng = (p2.lng - p1.lng) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return EARTH_RADIUS * c;
}

function calculateCentroid(points: GPSPoint[]): GPSPoint {
  const sum = points.reduce(
    (acc, p) => ({ lat: acc.lat + p.lat, lng: acc.lng + p.lng }),
    { lat: 0, lng: 0 }
  );
  return { lat: sum.lat / points.length, lng: sum.lng / points.length };
}

function calculateClusterRadius(center: GPSPoint, points: GPSPoint[]): number {
  if (points.length <= 1) return 0;
  return Math.max(...points.map(p => haversineDistance(center, p)));
}

const CLUSTER_COLORS = [
  '#00d4ff', '#ff6b35', '#7c3aed', '#22c55e', '#f59e0b',
  '#ec4899', '#06b6d4', '#8b5cf6', '#ef4444', '#14b8a6',
];

export function clusterPhotos(
  photos: Photo[],
  maxDistance: number = 50
): PhotoCluster[] {
  const photosWithGps = photos.filter(p => getPhotoEffectiveGPS(p));
  if (photosWithGps.length === 0) return [];

  const visited = new Set<string>();
  const clusters: PhotoCluster[] = [];

  for (const photo of photosWithGps) {
    if (visited.has(photo.id)) continue;

    const gps = getPhotoEffectiveGPS(photo)!;
    const clusterPhotos_: Photo[] = [photo];
    visited.add(photo.id);

    const queue: Photo[] = [photo];
    while (queue.length > 0) {
      const current = queue.shift()!;
      const currentGps = getPhotoEffectiveGPS(current)!;

      for (const other of photosWithGps) {
        if (visited.has(other.id)) continue;
        const otherGps = getPhotoEffectiveGPS(other)!;
        if (haversineDistance(currentGps, otherGps) <= maxDistance) {
          visited.add(other.id);
          clusterPhotos_.push(other);
          queue.push(other);
        }
      }
    }

    const gpsPoints = clusterPhotos_.map(p => getPhotoEffectiveGPS(p)!);
    const center = calculateCentroid(gpsPoints);
    const radius = calculateClusterRadius(center, gpsPoints);

    clusters.push({
      id: `cluster-${clusters.length}`,
      center,
      photos: clusterPhotos_,
      radius,
      color: CLUSTER_COLORS[clusters.length % CLUSTER_COLORS.length],
    });
  }

  return clusters.sort((a, b) => b.photos.length - a.photos.length);
}

export function getPhotosSortedByTime(photos: Photo[]): Photo[] {
  return [...photos]
    .filter(p => getPhotoEffectiveGPS(p) && p.exifData.dateTimeOriginal)
    .sort((a, b) => {
      const timeA = a.exifData.dateTimeOriginal!.getTime();
      const timeB = b.exifData.dateTimeOriginal!.getTime();
      return timeA - timeB;
    });
}

export function getTimeRange(photos: Photo[]): { start: Date; end: Date } | null {
  const sorted = getPhotosSortedByTime(photos);
  if (sorted.length === 0) return null;
  return {
    start: sorted[0].exifData.dateTimeOriginal!,
    end: sorted[sorted.length - 1].exifData.dateTimeOriginal!,
  };
}
