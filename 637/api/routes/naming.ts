import { Router } from 'express';
import { recommendNames, convertName, recordSelection } from '../controllers/namingController.js';

const router = Router();

router.post('/recommend', recommendNames);
router.post('/convert', convertName);
router.post('/record', recordSelection);

export default router;
