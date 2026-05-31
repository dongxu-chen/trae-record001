import { Router } from 'express';
import {
  getHistory,
  toggleHistoryFavorite,
  deleteHistory,
  clearAllHistory,
  submitHistoryFeedback,
  getLearningSuggestions,
  getUserPreferredStyle
} from '../controllers/learningController.js';

const router = Router();

router.get('/history', getHistory);
router.patch('/history/:id/favorite', toggleHistoryFavorite);
router.delete('/history/:id', deleteHistory);
router.delete('/history', clearAllHistory);
router.post('/history/:id/feedback', submitHistoryFeedback);
router.get('/suggestions', getLearningSuggestions);
router.get('/preferred-style', getUserPreferredStyle);

export default router;
