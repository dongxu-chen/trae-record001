const express = require('express');
const router = express.Router();
const userController = require('../controllers/userController');
const auth = require('../middleware/auth');

router.get('/templates', auth, userController.getMyTemplates);
router.get('/favorites', auth, userController.getFavorites);
router.post('/favorites/:id', auth, userController.addFavorite);
router.delete('/favorites/:id', auth, userController.removeFavorite);
router.get('/downloads', auth, userController.getDownloadHistory);
router.get('/statistics', auth, userController.getStatistics);

module.exports = router;
