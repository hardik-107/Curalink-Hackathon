const express = require('express');
const router = express.Router();
const { processChatMessage } = require('../controllers/chatController');

router.post('/message', processChatMessage);

module.exports = router;