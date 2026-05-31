'use strict';

// Load .env if present (no-op if dotenv is not configured)
try {
    require('dotenv').config();
} catch (_) {
    // dotenv optional — env vars can still come from the shell
}

function required(name, fallback) {
    const value = process.env[name];
    if (value === undefined || value === '') {
        if (fallback !== undefined) return fallback;
        throw new Error(`Missing required env var: ${name}`);
    }
    return value;
}

const config = {
    port: parseInt(process.env.PORT || '3000', 10),
    dbPath: process.env.DB_PATH || ':memory:',
    jwt: {
        secret: required('JWT_SECRET', 'dev-secret-change-me'),
        expiresIn: process.env.JWT_EXPIRES_IN || '1h',
    },
    auth: {
        disabled: String(process.env.AUTH_DISABLED || 'false').toLowerCase() === 'true',
    },
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || 'pk_test_dev_only',
    logLevel: process.env.LOG_LEVEL || 'info',
};

module.exports = { config };
