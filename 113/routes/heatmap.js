const express = require('express');
const router = express.Router();
const {
  trackHeatmap,
  getHeatmapData,
  getUVMStats,
  generateHeatmapOverlay
} = require('../controllers/heatmapController');

router.post('/track', trackHeatmap);
router.get('/data', getHeatmapData);
router.get('/uvm-stats', getUVMStats);
router.post('/overlay', generateHeatmapOverlay);

module.exports = router;