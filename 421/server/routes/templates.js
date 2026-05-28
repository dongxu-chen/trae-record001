const express = require('express');
const { auth } = require('../middleware/auth');
const reviewTemplateService = require('../services/reviewTemplateService');

const router = express.Router();

router.get('/', auth, async (req, res) => {
  try {
    const { category } = req.query;
    const templates = await reviewTemplateService.getTemplates(req.user.id, { category });
    res.json(templates);
  } catch (error) {
    console.error('Get templates error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/defaults', auth, async (req, res) => {
  try {
    const templates = await reviewTemplateService.getDefaultTemplates();
    res.json(templates);
  } catch (error) {
    console.error('Get default templates error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/:templateId', auth, async (req, res) => {
  try {
    const template = await reviewTemplateService.getTemplate(
      req.params.templateId,
      req.user.id
    );
    res.json(template);
  } catch (error) {
    console.error('Get template error:', error);
    if (error.message === 'Template not found') {
      return res.status(404).json({ message: error.message });
    }
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/', auth, async (req, res) => {
  try {
    const template = await reviewTemplateService.createTemplate(
      req.user.id,
      req.body
    );
    res.status(201).json(template);
  } catch (error) {
    console.error('Create template error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.put('/:templateId', auth, async (req, res) => {
  try {
    const template = await reviewTemplateService.updateTemplate(
      req.params.templateId,
      req.user.id,
      req.body
    );
    res.json(template);
  } catch (error) {
    console.error('Update template error:', error);
    if (error.message.includes('not found')) {
      return res.status(404).json({ message: error.message });
    }
    res.status(500).json({ message: 'Server error' });
  }
});

router.delete('/:templateId', auth, async (req, res) => {
  try {
    await reviewTemplateService.deleteTemplate(
      req.params.templateId,
      req.user.id
    );
    res.json({ message: 'Template deleted' });
  } catch (error) {
    console.error('Delete template error:', error);
    if (error.message.includes('not found')) {
      return res.status(404).json({ message: error.message });
    }
    if (error.message.includes('default')) {
      return res.status(400).json({ message: error.message });
    }
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/:templateId/duplicate', auth, async (req, res) => {
  try {
    const template = await reviewTemplateService.duplicateTemplate(
      req.params.templateId,
      req.user.id
    );
    res.status(201).json(template);
  } catch (error) {
    console.error('Duplicate template error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/:templateId/apply', auth, async (req, res) => {
  try {
    const { documentId, content } = req.body;
    const result = await reviewTemplateService.applyTemplate(
      req.params.templateId,
      documentId,
      content,
      req.user.id
    );
    res.json(result);
  } catch (error) {
    console.error('Apply template error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

router.post('/init-defaults', auth, async (req, res) => {
  try {
    const templates = await reviewTemplateService.createDefaultTemplates(req.user.id);
    res.json({ created: templates.length, templates });
  } catch (error) {
    console.error('Init defaults error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

module.exports = router;
