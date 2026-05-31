import Exif from 'exif-js';
import piexif from 'piexifjs';
import { ExifData, GPSPoint } from '@/types';

function convertDMSToDD(degrees: number, minutes: number, seconds: number, direction: string): number {
  let dd = degrees + minutes / 60 + seconds / 3600;
  if (direction === 'S' || direction === 'W') {
    dd = dd * -1;
  }
  return dd;
}

function parseExifGPS(tags: any): GPSPoint | undefined {
  if (!tags.GPSLatitude || !tags.GPSLongitude) return undefined;
  
  const lat = convertDMSToDD(
    tags.GPSLatitude[0],
    tags.GPSLatitude[1],
    tags.GPSLatitude[2],
    tags.GPSLatitudeRef
  );
  
  const lng = convertDMSToDD(
    tags.GPSLongitude[0],
    tags.GPSLongitude[1],
    tags.GPSLongitude[2],
    tags.GPSLongitudeRef
  );
  
  return { lat, lng };
}

export function parseExifData(file: File): Promise<ExifData> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const exifData = Exif.readFromBinaryFile(e.target?.result as ArrayBuffer);
        const tags = Exif.getAllTags(file);
        
        let dateTimeOriginal: Date | undefined;
        if (tags.DateTimeOriginal) {
          const parts = tags.DateTimeOriginal.split(' ');
          const datePart = parts[0].replace(/:/g, '-');
          dateTimeOriginal = new Date(`${datePart} ${parts[1]}`);
        }
        
        const gps = parseExifGPS(tags);
        
        resolve({
          make: tags.Make,
          model: tags.Model,
          dateTimeOriginal,
          gps,
          exposureTime: tags.ExposureTime?.toString(),
          fNumber: tags.FNumber,
          iso: tags.ISOSpeedRatings,
          focalLength: tags.FocalLength,
        });
      } catch (error) {
        resolve({});
      }
    };
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
}

export function generateThumbnail(file: File, maxSize: number = 120): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;
        
        if (width > height) {
          if (width > maxSize) {
            height = height * (maxSize / width);
            width = maxSize;
          }
        } else {
          if (height > maxSize) {
            width = width * (maxSize / height);
            height = maxSize;
          }
        }
        
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx?.drawImage(img, 0, 0, width, height);
        resolve(canvas.toDataURL('image/jpeg', 0.8));
      };
      img.onerror = reject;
      img.src = e.target?.result as string;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}

function convertDDToDMS(dd: number): [number, number, number] {
  const abs = Math.abs(dd);
  const degrees = Math.floor(abs);
  const minutes = Math.floor((abs - degrees) * 60);
  const seconds = (abs - degrees - minutes / 60) * 3600;
  return [degrees, minutes, seconds];
}

export function writeGPStoJPEG(dataUrl: string, gps: GPSPoint): string {
  const exifObj = piexif.load(dataUrl);
  
  const latDMS = convertDDToDMS(gps.lat);
  const lngDMS = convertDDToDMS(gps.lng);
  
  exifObj.GPS = {
    [piexif.GPSIFD.GPSLatitudeRef]: gps.lat >= 0 ? 'N' : 'S',
    [piexif.GPSIFD.GPSLatitude]: [[latDMS[0], 1], [latDMS[1], 1], [Math.round(latDMS[2] * 100), 100]],
    [piexif.GPSIFD.GPSLongitudeRef]: gps.lng >= 0 ? 'E' : 'W',
    [piexif.GPSIFD.GPSLongitude]: [[lngDMS[0], 1], [lngDMS[1], 1], [Math.round(lngDMS[2] * 100), 100]],
  };
  
  const exifBytes = piexif.dump(exifObj);
  return piexif.insert(exifBytes, dataUrl);
}
