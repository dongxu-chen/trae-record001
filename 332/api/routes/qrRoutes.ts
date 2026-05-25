import { Router } from 'express';
import { saveQRCode, getQRCodes, deleteQRCode } from '../controllers/qrCodeController.js';
import { authMiddleware } from '../middleware/auth.js';

const router = Router();

router.post('/', authMiddleware, saveQRCode);
router.get('/', authMiddleware, getQRCodes);
router.delete('/:id', authMiddleware, deleteQRCode);

export default router;
