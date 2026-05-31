'use strict';

const express = require('express');
const userController = require('../controllers/userController');
const { authRequired } = require('../middlewares/auth');

const router = express.Router();

// DELETE /api/users/:id requires authentication (admin or future ownership check).
// Dev override: AUTH_DISABLED=true.
router.delete('/:id', authRequired, userController.remove);

module.exports = router;
