const express = require('express');
const router = express.Router();
const channelController = require('../controllers/channelController');

router.get('/', channelController.getChannels);
router.post('/', channelController.createChannel);
router.get('/:id', channelController.getChannel);
router.put('/:id', channelController.updateChannel);
router.delete('/:id', channelController.deleteChannel);
router.post('/:id/test', channelController.testChannel);
router.post('/:id/sync', channelController.syncChannel);

module.exports = router;
