'use strict';

const express = require('express');

const { config } = require('./config');
const { initDb } = require('./db');
const logger = require('./utils/logger');
const { errorHandler } = require('./middlewares/errorHandler');

const checkoutRoutes = require('./routes/checkoutRoutes');
const adminRoutes = require('./routes/adminRoutes');
const userRoutes = require('./routes/userRoutes');

function createApp() {
    const app = express();
    app.use(express.json());

    app.get('/health', (_req, res) => res.json({ status: 'ok' }));

    app.use('/api/checkout', checkoutRoutes);
    app.use('/api/admin', adminRoutes);
    app.use('/api/users', userRoutes);

    app.use(errorHandler);
    return app;
}

function start() {
    initDb();
    const app = createApp();
    app.listen(config.port, () => {
        logger.info(
            { port: config.port, authDisabled: config.auth.disabled },
            'LMS API listening',
        );
    });
}

if (require.main === module) {
    start();
}

module.exports = { createApp, start };
