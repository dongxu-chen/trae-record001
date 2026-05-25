import { Router } from 'express';
import { 
  createDynamicCode, 
  getDynamicCodes, 
  updateDynamicCode, 
  deleteDynamicCode,
  redirectShortCode 
} from '../controllers/dynamicController.js';
import { authMiddleware } from '../middleware/auth.js';

const router = Router();

router.get('/r/:shortCode', redirectShortCode);
router.post('/', authMiddleware, createDynamicCode);
router.get('/', authMiddleware, getDynamicCodes);
router.put('/:id', authMiddleware, updateDynamicCode);
router.delete('/:id', authMiddleware, deleteDynamicCode);

export default router;
