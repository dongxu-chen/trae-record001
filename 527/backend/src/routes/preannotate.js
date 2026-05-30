const express = require('express');
const router = express.Router();
const preAnnotateController = require('../controllers/preAnnotateController');

router.post('/document/:documentId', preAnnotateController.preAnnotateDocument);
router.get('/consistency/:taskId', preAnnotateController.checkConsistency);
router.post('/finetune/:taskId', preAnnotateController.fineTune);
router.get('/next-uncertain/:taskId', preAnnotateController.getNextUncertainDocument);
router.get('/model-info/:taskId', preAnnotateController.getModelInfo);

module.exports = router;
