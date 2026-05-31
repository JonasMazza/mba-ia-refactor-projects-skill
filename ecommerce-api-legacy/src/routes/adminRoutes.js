'use strict';

const express = require('express');
const reportController = require('../controllers/reportController');
const { authRequired, requireRole } = require('../middlewares/auth');

const router = express.Router();

// All /api/admin/* routes require an authenticated admin user.
// Dev override: set AUTH_DISABLED=true in .env to bypass for local testing.
router.use(authRequired, requireRole('admin'));

router.get('/financial-report', reportController.financialReport);

module.exports = router;
