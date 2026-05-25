import { Router } from 'express';
import {
  getAllRules,
  getRule,
  createRule,
  updateRule,
  toggleRule,
  deleteRule,
  processTasksWithRules,
} from '../controllers/automationController';

const router = Router();

router.get('/', getAllRules);
router.get('/:id', getRule);
router.post('/', createRule);
router.put('/:id', updateRule);
router.patch('/:id/toggle', toggleRule);
router.delete('/:id', deleteRule);
router.post('/process', processTasksWithRules);

export default router;
