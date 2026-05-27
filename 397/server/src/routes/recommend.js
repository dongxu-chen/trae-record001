const express = require('express');
const router = express.Router();
const recommendController = require('../controllers/recommendController');
const auth = require('../middleware/auth');

router.get('/', auth, recommendController.getRecommendations);
router.get('/history', auth, recommendController.getViewHistory);
router.post('/view/:templateId', auth, recommendController.recordView);

module.exports = router;
