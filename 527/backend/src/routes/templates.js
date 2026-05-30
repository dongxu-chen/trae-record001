const express = require('express');
const router = express.Router();
const templateController = require('../controllers/templateController');

router.get('/', templateController.getAllTemplates);
router.get('/:id', templateController.getTemplateById);
router.post('/', templateController.createTemplate);
router.put('/:id', templateController.updateTemplate);
router.delete('/:id', templateController.deleteTemplate);
router.post('/apply/:templateId/:taskId', templateController.applyTemplateToTask);
router.post('/rate/:id', templateController.rateTemplate);
router.get('/suggestions/:taskId', templateController.getTemplateSuggestions);

module.exports = router;
