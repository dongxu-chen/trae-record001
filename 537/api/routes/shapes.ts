import { Router } from 'express';
import multer from 'multer';
import type { RecognizeRequest, RecognizeResponse, UploadResponse, Shape, Shape3D, ShapeRelation } from '../../shared/types';
import { recognizeShapes, infer3DShapes, detectShapeRelations } from '../services/shapeRecognition';

const router = Router();

const storage = multer.memoryStorage();
const upload = multer({ storage, limits: { fileSize: 10 * 1024 * 1024 } });

function decodeBase64Image(base64: string): { width: number; height: number } | null {
  try {
    const matches = base64.match(/^data:image\/(png|jpeg|jpg);base64,/);
    if (!matches) return null;

    const buffer = Buffer.from(base64.split(',')[1], 'base64');
    if (buffer.length < 24) return null;

    if (matches[1] === 'png') {
      const width = buffer.readUInt32BE(16);
      const height = buffer.readUInt32BE(20);
      return { width, height };
    } else if (matches[1] === 'jpeg' || matches[1] === 'jpg') {
      let offset = 2;
      while (offset < buffer.length - 4) {
        const marker = buffer.readUInt16BE(offset);
        const segmentLength = buffer.readUInt16BE(offset + 2);

        if ((marker & 0xFFF0) === 0xFFC0 && marker !== 0xFFC4 && marker !== 0xFFC8) {
          const height = buffer.readUInt16BE(offset + 5);
          const width = buffer.readUInt16BE(offset + 7);
          return { width, height };
        }
        offset += 2 + segmentLength;
      }
    }
    return { width: 800, height: 600 };
  } catch (e) {
    console.error('Failed to parse image size:', e);
    return { width: 800, height: 600 };
  }
}

function createMockImageData(width: number, height: number): ImageData {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < data.length; i += 4) {
    data[i] = 255;
    data[i + 1] = 255;
    data[i + 2] = 255;
    data[i + 3] = 255;
  }
  return { data, width, height } as unknown as ImageData;
}

router.post('/recognize', async (req, res) => {
  const startTime = Date.now();

  try {
    const { imageData, options } = req.body as RecognizeRequest;

    if (!imageData) {
      return res.status(400).json({
        success: false,
        shapes: [],
        shapes3D: [],
        relations: [],
        processingTime: Date.now() - startTime,
        error: '缺少图像数据',
      } as RecognizeResponse);
    }

    const imgInfo = decodeBase64Image(imageData);
    const width = imgInfo?.width || 800;
    const height = imgInfo?.height || 600;

    const mockImgData = createMockImageData(width, height);

    let shapes: Shape[] = [];
    let shapes3D: Shape3D[] = [];
    let relations: ShapeRelation[] = [];

    shapes = recognizeShapes(mockImgData, width, height, {
      minContourArea: options?.minContourArea,
      epsilonFactor: options?.epsilonFactor,
      enableCorrection: options?.enableCorrection ?? true,
    });

    if (options?.enable3DInference) {
      shapes3D = infer3DShapes(shapes);
      shapes = shapes.map((s) => {
        const s3d = shapes3D.find(s3 => s3.sourceShapeId === s.id);
        return s3d ? { ...s, shape3DId: s3d.id } : s;
      });
    }

    if (options?.enableRelationDetection) {
      relations = detectShapeRelations(shapes, width, height);
    }

    res.json({
      success: true,
      shapes,
      shapes3D,
      relations,
      processingTime: Date.now() - startTime,
    } as RecognizeResponse);

  } catch (error) {
    console.error('Shape recognition error:', error);
    res.status(500).json({
      success: false,
      shapes: [],
      shapes3D: [],
      relations: [],
      processingTime: Date.now() - startTime,
      error: error instanceof Error ? error.message : '识别失败',
    } as RecognizeResponse);
  }
});

router.post('/upload', upload.single('file'), (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        imageUrl: '',
        width: 0,
        height: 0,
      } as UploadResponse);
    }
    
    const imageData = `data:${req.file.mimetype};base64,${req.file.buffer.toString('base64')}`;
    
    res.json({
      success: true,
      imageUrl: imageData,
      width: 800,
      height: 600,
    } as UploadResponse);
    
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({
      success: false,
      imageUrl: '',
      width: 0,
      height: 0,
    } as UploadResponse);
  }
});

export default router;
