const express = require('express');
const router = express.Router();
const documentController = require('../controllers/documentController');

router.get('/task/:taskId', documentController.getDocumentsByTask);
router.get('/next/:taskId/:currentId?', documentController.getNextDocument);
router.get('/:id', documentController.getDocumentById);
router.post('/', documentController.createDocument);
router.post('/bulk', documentController.bulkCreateDocuments);
router.put('/:id', documentController.updateDocument);
router.delete('/:id', documentController.deleteDocument);

module.exports = router;
