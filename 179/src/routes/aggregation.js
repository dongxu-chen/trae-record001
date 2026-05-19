const express = require('express');
const router = express.Router();
const aggregationController = require('../controllers/aggregationController');

router.get('/status', aggregationController.getStatus);
router.get('/logs', aggregationController.getLogs);
router.post('/trigger', aggregationController.triggerAggregation);
router.post('/run', aggregationController.runAggregation);
router.post('/check-urgent', aggregationController.checkUrgent);

module.exports = router;
