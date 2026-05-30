const express = require('express');
const router = express.Router();
const achievementController = require('../controllers/achievementController');

router.get('/', achievementController.getAllAchievements);
router.get('/user', achievementController.getUserAchievements);
router.post('/progress', achievementController.updateAchievementProgress);
router.get('/leaderboard', achievementController.getLeaderboard);
router.get('/summary', achievementController.getAnnotatorSummary);

module.exports = router;
