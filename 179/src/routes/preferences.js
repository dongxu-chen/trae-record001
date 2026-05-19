const express = require('express');
const router = express.Router();
const preferenceController = require('../controllers/preferenceController');

router.get('/:userId?', preferenceController.getPreference);
router.put('/:userId?', preferenceController.updatePreference);
router.post('/:userId?/reset', preferenceController.resetPreference);

module.exports = router;
