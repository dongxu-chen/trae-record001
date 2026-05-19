const express = require('express');
const router = express.Router();
const messageController = require('../controllers/messageController');

router.get('/', messageController.getMessages);
router.get('/stats', messageController.getStats);
router.get('/unread-count', messageController.getUnreadCount);
router.get('/fetch', messageController.fetchMessages);
router.get('/:messageId', messageController.getMessage);
router.post('/:messageId/read', messageController.markAsRead);
router.post('/:messageId/unread', messageController.markAsUnread);
router.post('/mark-all-read', messageController.markAllAsRead);
router.post('/:messageId/archive', messageController.archiveMessage);
router.delete('/:messageId', messageController.deleteMessage);

module.exports = router;
