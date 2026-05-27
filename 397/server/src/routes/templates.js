const express = require('express');
const router = express.Router();
const templateController = require('../controllers/templateController');
const commentController = require('../controllers/commentController');
const auth = require('../middleware/auth');
const upload = require('../middleware/upload');

router.get('/', templateController.getTemplates);
router.get('/:id', templateController.getTemplateById);
router.post('/', auth, upload.fields([
  { name: 'thumbnail', maxCount: 1 },
  { name: 'previewImages', maxCount: 5 },
  { name: 'file', maxCount: 1 }
]), templateController.createTemplate);
router.put('/:id', auth, upload.fields([
  { name: 'thumbnail', maxCount: 1 },
  { name: 'previewImages', maxCount: 5 },
  { name: 'file', maxCount: 1 }
]), templateController.updateTemplate);
router.delete('/:id', auth, templateController.deleteTemplate);
router.post('/:id/download', auth, templateController.downloadTemplate);
router.post('/:id/rate', auth, templateController.rateTemplate);
router.post('/:id/apply', auth, templateController.applyTemplate);
router.get('/:id/user-rating', auth, templateController.getUserRating);

router.get('/:templateId/comments', commentController.getComments);
router.post('/:templateId/comments', auth, commentController.createComment);
router.post('/comments/:commentId/reply', auth, commentController.replyComment);
router.delete('/comments/:commentId', auth, commentController.deleteComment);

module.exports = router;
