const express = require('express');
const router = express.Router();
const messageEnhancedController = require('../controllers/messageEnhancedController');

router.get('/pinned', messageEnhancedController.getPinnedMessages);
router.post('/:messageId/pin', messageEnhancedController.pinMessage);
router.post('/:messageId/unpin', messageEnhancedController.unpinMessage);

router.get('/reminders', messageEnhancedController.getReminderMessages);
router.get('/reminders/stats', messageEnhancedController.getReminderStats);
router.post('/:messageId/reanalyze-reminder', messageEnhancedController.reanalyzeReminder);

router.post('/summary/generate', messageEnhancedController.generateSummary);
router.post('/summary/batch', messageEnhancedController.batchGenerateSummaries);
router.post('/:messageId/summary/regenerate', messageEnhancedController.regenerateMessageSummary);
router.post('/summary/regenerate-all', messageEnhancedController.regenerateAllSummaries);

router.post('/template/parse', messageEnhancedController.parseTemplate);
router.post('/template/batch', messageEnhancedController.batchParseTemplates);
router.get('/templates', messageEnhancedController.getTemplates);
router.get('/templates/:templateName', messageEnhancedController.getTemplateByName);
router.post('/templates', messageEnhancedController.addTemplate);
router.delete('/templates/:templateName', messageEnhancedController.removeTemplate);
router.post('/templates/reload', messageEnhancedController.reloadTemplates);
router.post('/:messageId/template/reparse', messageEnhancedController.reparseMessageTemplate);
router.post('/template/reparse-all', messageEnhancedController.reparseAllTemplates);

router.get('/by-template/:templateName', messageEnhancedController.getMessagesByTemplate);
router.get('/:messageId/card', messageEnhancedController.getMessageCard);
router.get('/:messageId/structured', messageEnhancedController.getStructuredData);

module.exports = router;
