const express = require('express');
const router = express.Router();
const qualityController = require('../controllers/qualityController');

router.get('/', qualityController.getQualityScores);
router.get('/personal', qualityController.getPersonalQuality);
router.post('/update', qualityController.updateQualityScore);
router.get('/rankings', qualityController.getAnnotatorRankings);
router.get('/trends', qualityController.getQualityTrends);

module.exports = router;
