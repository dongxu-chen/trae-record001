const express = require('express');
const router = express.Router();
const classificationController = require('../controllers/classificationController');

router.post('/classify', classificationController.classify);
router.get('/keywords', classificationController.getClassificationKeywords);
router.post('/keywords', classificationController.addClassificationKeyword);
router.delete('/keywords', classificationController.removeClassificationKeyword);
router.get('/synonyms', classificationController.getSynonyms);
router.post('/synonyms', classificationController.addSynonym);
router.get('/synonyms/:word', classificationController.getWordSynonyms);
router.post('/synonyms/reload', classificationController.reloadSynonyms);
router.get('/model-info', classificationController.getModelInfo);

module.exports = router;
