import express from 'express';
import cors from 'cors';
import multer from 'multer';
import JSZip from 'jszip';
import piexif from 'piexifjs';

const app = express();
const port = 3001;

app.use(cors());
app.use(express.json({ limit: '50mb' }));

const storage = multer.memoryStorage();
const upload = multer({ storage, limits: { fileSize: 50 * 1024 * 1024 } });

interface GPSPoint {
  lat: number;
  lng: number;
  elevation?: number;
}

function convertDDToDMS(dd: number): [number, number, number] {
  const abs = Math.abs(dd);
  const degrees = Math.floor(abs);
  const minutes = Math.floor((abs - degrees) * 60);
  const seconds = (abs - degrees - minutes / 60) * 3600;
  return [degrees, minutes, seconds];
}

function writeGPStoJPEG(buffer: Buffer, gps: GPSPoint): Buffer {
  try {
    const dataUrl = `data:image/jpeg;base64,${buffer.toString('base64')}`;
    const exifObj = piexif.load(dataUrl);
    
    const latDMS = convertDDToDMS(gps.lat);
    const lngDMS = convertDDToDMS(gps.lng);
    
    exifObj.GPS = {
      [piexif.GPSIFD.GPSLatitudeRef]: gps.lat >= 0 ? 'N' : 'S',
      [piexif.GPSIFD.GPSLatitude]: [[latDMS[0], 1], [latDMS[1], 1], [Math.round(latDMS[2] * 100), 100]],
      [piexif.GPSIFD.GPSLongitudeRef]: gps.lng >= 0 ? 'E' : 'W',
      [piexif.GPSIFD.GPSLongitude]: [[lngDMS[0], 1], [lngDMS[1], 1], [Math.round(lngDMS[2] * 100), 100]],
    };
    
    const exifBytes = piexif.dump(exifObj as any);
    const newDataUrl = piexif.insert(exifBytes, dataUrl);
    const base64Data = newDataUrl.split(',')[1];
    
    return Buffer.from(base64Data, 'base64');
  } catch (error) {
    console.error('写入GPS信息失败:', error);
    return buffer;
  }
}

app.post('/api/export/photos', upload.array('photos', 100), async (req, res) => {
  try {
    const files = req.files as Express.Multer.File[];
    const gpsData = JSON.parse(req.body.gpsData || '{}');
    
    const zip = new JSZip();
    
    for (const file of files) {
      const gps = gpsData[file.originalname];
      if (gps) {
        const modifiedBuffer = writeGPStoJPEG(file.buffer, gps);
        zip.file(file.originalname, modifiedBuffer);
      } else {
        zip.file(file.originalname, file.buffer);
      }
    }
    
    const zipBuffer = await zip.generateAsync({ type: 'nodebuffer' });
    
    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', 'attachment; filename=geotagged-photos.zip');
    res.send(zipBuffer);
  } catch (error) {
    console.error('导出照片失败:', error);
    res.status(500).json({ error: '导出失败' });
  }
});

app.post('/api/export/gpx', (req, res) => {
  try {
    const { photos } = req.body;
    
    const waypoints = photos
      .filter((p: any) => p.gps)
      .map((photo: any) => {
        const time = photo.dateTimeOriginal ? new Date(photo.dateTimeOriginal).toISOString() : '';
        return `
    <wpt lat="${photo.gps.lat}" lon="${photo.gps.lng}">
      <name>${photo.name}</name>
      <time>${time}</time>
      ${photo.gps.elevation !== undefined ? `<ele>${photo.gps.elevation}</ele>` : ''}
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
    
    res.setHeader('Content-Type', 'application/gpx+xml');
    res.setHeader('Content-Disposition', 'attachment; filename=photo-waypoints.gpx');
    res.send(gpxContent);
  } catch (error) {
    console.error('导出GPX失败:', error);
    res.status(500).json({ error: '导出失败' });
  }
});

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.listen(port, () => {
  console.log(`后端服务运行在 http://localhost:${port}`);
});
