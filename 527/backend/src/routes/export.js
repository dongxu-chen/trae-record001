const express = require('express');
const router = express.Router();
const exportController = require('../controllers/exportController');

router.get('/json/:taskId', exportController.exportJSON);
router.get('/conll/:taskId', exportController.exportCoNLL);
router.get('/stats/:taskId', exportController.getStats);

module.exports = router;
