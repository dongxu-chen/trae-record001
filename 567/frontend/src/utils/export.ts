import { saveAs } from 'file-saver';
import JSZip from 'jszip';
import { Photo, GPSPoint, PrivacyConfig } from '@/types';
import { writeGPStoJPEG } from './exif';
import { getExportGPS } from './privacy';

export function getPhotoEffectiveGPS(photo: Photo): GPSPoint | undefined {
  return photo.manualGps || photo.matchedGps || photo.originalGps;
}

export function getPhotoGPSForExport(photo: Photo, privacy?: PrivacyConfig): GPSPoint | undefined {
  if (privacy && privacy.enabled && privacy.applyToExport) {
    return getExportGPS(photo, privacy);
  }
  return getPhotoEffectiveGPS(photo);
}

export async function exportPhotoWithGPS(photo: Photo, privacy?: PrivacyConfig): Promise<Blob> {
  const gps = getPhotoGPSForExport(photo, privacy);
  if (!gps || !photo.file) {
    throw new Error('照片没有GPS信息或文件');
  }
  
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const dataUrl = e.target?.result as string;
        const modifiedDataUrl = writeGPStoJPEG(dataUrl, gps);
        const byteString = atob(modifiedDataUrl.split(',')[1]);
        const mimeString = modifiedDataUrl.split(',')[0].split(':')[1].split(';')[0];
        const ab = new ArrayBuffer(byteString.length);
        const ia = new Uint8Array(ab);
        for (let i = 0; i < byteString.length; i++) {
          ia[i] = byteString.charCodeAt(i);
        }
        resolve(new Blob([ab], { type: mimeString }));
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = reject;
    reader.readAsDataURL(photo.file!);
  });
}

export async function exportPhotosAsZip(photos: Photo[], onProgress?: (current: number, total: number) => void, privacy?: PrivacyConfig): Promise<void> {
  const zip = new JSZip();
  const photosWithGPS = photos.filter(p => getPhotoGPSForExport(p, privacy));
  
  for (let i = 0; i < photosWithGPS.length; i++) {
    const photo = photosWithGPS[i];
    try {
      const blob = await exportPhotoWithGPS(photo, privacy);
      zip.file(photo.name, blob);
    } catch (error) {
      console.error(`导出照片 ${photo.name} 失败:`, error);
    }
    if (onProgress) {
      onProgress(i + 1, photosWithGPS.length);
    }
  }
  
  const content = await zip.generateAsync({ type: 'blob' });
  saveAs(content, 'geotagged-photos.zip');
}

export function exportPhotosAsGPX(photos: Photo[], filename: string = 'photo-waypoints.gpx', privacy?: PrivacyConfig): void {
  const waypoints = photos
    .filter(p => getPhotoGPSForExport(p, privacy))
    .map(photo => {
      const gps = getPhotoGPSForExport(photo, privacy)!;
      const time = photo.exifData.dateTimeOriginal?.toISOString() || '';
      return `
    <wpt lat="${gps.lat}" lon="${gps.lng}">
      <name>${photo.name}</name>
      <time>${time}</time>
      ${gps.elevation !== undefined ? `<ele>${gps.elevation}</ele>` : ''}
    </wpt>`;
    })
    .join('');
  
  const gpxContent = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Photo GeoTagger">
  <metadata>
    <name>Photo Waypoints</name>
    <time>${new Date().toISOString()}</time>
  </metadata>
${waypoints}
</gpx>`;
  
  const blob = new Blob([gpxContent], { type: 'application/gpx+xml' });
  saveAs(blob, filename);
}

export function exportPhotosAsKML(photos: Photo[], filename: string = 'photo-waypoints.kml', privacy?: PrivacyConfig): void {
  const placemarks = photos
    .filter(p => getPhotoGPSForExport(p, privacy))
    .map(photo => {
      const gps = getPhotoGPSForExport(photo, privacy)!;
      const time = photo.exifData.dateTimeOriginal?.toISOString() || '';
      return `
    <Placemark>
      <name>${photo.name}</name>
      <TimeStamp>
        <when>${time}</when>
      </TimeStamp>
      <Point>
        <coordinates>${gps.lng},${gps.lat}${gps.elevation !== undefined ? ',' + gps.elevation : ''}</coordinates>
      </Point>
    </Placemark>`;
    })
    .join('');
  
  const kmlContent = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Photo Waypoints</name>
${placemarks}
  </Document>
</kml>`;
  
  const blob = new Blob([kmlContent], { type: 'application/vnd.google-earth.kml+xml' });
  saveAs(blob, filename);
}

export function exportPhotosAsCSV(photos: Photo[], filename: string = 'photo-geotags.csv', privacy?: PrivacyConfig): void {
  const headers = ['Filename', 'Latitude', 'Longitude', 'Elevation', 'DateTime', 'Source'];
  const rows = photos
    .filter(p => getPhotoGPSForExport(p, privacy))
    .map(photo => {
      const gps = getPhotoGPSForExport(photo, privacy)!;
      const source = photo.manualGps ? 'Manual' : photo.matchedGps ? 'Matched' : 'Original';
      return [
        photo.name,
        gps.lat.toFixed(8),
        gps.lng.toFixed(8),
        gps.elevation?.toFixed(2) || '',
        photo.exifData.dateTimeOriginal?.toISOString() || '',
        source,
      ];
    });
  
  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' });
  saveAs(blob, filename);
}
