import { Router } from 'express';
import {
  createBatchProcess,
  getBatchProgress,
  downloadBatchResults,
  processSingleImage
} from '../controllers/batchController.js';
import { uploadSingle, uploadMultiple } from '../middleware/upload.js';

const router = Router();

router.post('/process', createBatchProcess);
router.get('/progress/:taskId', getBatchProgress);
router.get('/download/:taskId', downloadBatchResults);
router.post('/process-single', uploadSingle, processSingleImage);

export default router;
