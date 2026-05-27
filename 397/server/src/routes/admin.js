const express = require('express');
const router = express.Router();
const adminController = require('../controllers/adminController');
const auth = require('../middleware/auth');

router.get('/templates/pending', auth, adminController.getPendingTemplates);
router.post('/templates/:id/approve', auth, adminController.approveTemplate);
router.post('/templates/:id/reject', auth, adminController.rejectTemplate);
router.get('/templates/:id/review-status', auth, adminController.getTemplateReviewStatus);
router.get('/statistics', auth, adminController.getStatistics);

module.exports = router;
