const express = require('express');
const router = express.Router();
const annotationController = require('../controllers/annotationController');

router.get('/document/:documentId', annotationController.getAnnotationByDocument);
router.get('/task/:taskId', annotationController.getAnnotationsByTask);
router.post('/document/:documentId', annotationController.saveAnnotation);
router.delete('/document/:documentId', annotationController.deleteAnnotation);

module.exports = router;
