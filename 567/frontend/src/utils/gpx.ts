import { gpx } from '@tmcw/togeojson';
import { Track, TrackPoint } from '@/types';
import { generateId } from './exif';

export function parseGPX(file: File): Promise<Track> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const parser = new DOMParser();
        const xml = parser.parseFromString(text, 'text/xml');
        const geoJSON = gpx(xml);
        
        const points: TrackPoint[] = [];
        
        if (geoJSON.features) {
          geoJSON.features.forEach((feature: any) => {
            if (feature.geometry.type === 'LineString') {
              const coords = feature.geometry.coordinates;
              const times = feature.properties.coordTimes || [];
              
              coords.forEach((coord: number[], index: number) => {
                const timeStr = times[index];
                const time = timeStr ? new Date(timeStr) : new Date();
                points.push({
                  lng: coord[0],
                  lat: coord[1],
                  elevation: coord[2],
                  time,
                });
              });
            }
          });
        }
        
        points.sort((a, b) => a.time.getTime() - b.time.getTime());
        
        const startTime = points.length > 0 ? points[0].time : new Date();
        const endTime = points.length > 0 ? points[points.length - 1].time : new Date();
        
        resolve({
          id: generateId(),
          name: file.name.replace(/\.gpx$/i, ''),
          points,
          startTime,
          endTime,
        });
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

export function getTrackBounds(track: Track): [[number, number], [number, number]] | null {
  if (track.points.length === 0) return null;
  
  let minLat = Infinity, maxLat = -Infinity;
  let minLng = Infinity, maxLng = -Infinity;
  
  track.points.forEach(p => {
    minLat = Math.min(minLat, p.lat);
    maxLat = Math.max(maxLat, p.lat);
    minLng = Math.min(minLng, p.lng);
    maxLng = Math.max(maxLng, p.lng);
  });
  
  return [[minLat, minLng], [maxLat, maxLng]];
}

export function getAllTracksBounds(tracks: Track[]): [[number, number], [number, number]] | null {
  if (tracks.length === 0) return null;
  
  let minLat = Infinity, maxLat = -Infinity;
  let minLng = Infinity, maxLng = -Infinity;
  
  tracks.forEach(track => {
    const bounds = getTrackBounds(track);
    if (bounds) {
      minLat = Math.min(minLat, bounds[0][0]);
      maxLat = Math.max(maxLat, bounds[1][0]);
      minLng = Math.min(minLng, bounds[0][1]);
      maxLng = Math.max(maxLng, bounds[1][1]);
    }
  });
  
  if (minLat === Infinity) return null;
  
  return [[minLat, minLng], [maxLat, maxLng]];
}
