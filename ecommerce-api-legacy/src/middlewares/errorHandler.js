'use strict';

const { HttpError } = require('../utils/errors');
const logger = require('../utils/logger');

// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, _next) {
    if (err instanceof HttpError) {
        return res.status(err.status).json({ error: err.code, message: err.message });
    }
    logger.error({ err: err.message, stack: err.stack, path: req.path }, 'Unhandled error');
    res.status(500).json({ error: 'INTERNAL_ERROR', message: 'Internal Server Error' });
}

module.exports = { errorHandler };
