import { Router } from 'express';
import { getOverview, getCodeStats, exportStats, getLandingAnalysis, getManagementOverview } from '../controllers/statsController.js';
import { authMiddleware } from '../middleware/auth.js';

const router = Router();

router.get('/overview', authMiddleware, getOverview);
router.get('/export', authMiddleware, exportStats);
router.get('/landing/:codeId', authMiddleware, getLandingAnalysis);
router.get('/management', authMiddleware, getManagementOverview);
router.get('/:codeId', authMiddleware, getCodeStats);

export default router;
