const express = require('express');
const router = express.Router();
const { createShortLink } = require('../controllers/shortlinkController');

router.post('/create', createShortLink);

module.exports = router;