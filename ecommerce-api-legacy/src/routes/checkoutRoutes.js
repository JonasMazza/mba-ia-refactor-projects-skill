'use strict';

const express = require('express');
const checkoutController = require('../controllers/checkoutController');

const router = express.Router();

// Checkout is intentionally NOT behind auth — it creates the user account
// on first call (legacy contract preserved).
router.post('/', checkoutController.checkout);

module.exports = router;
