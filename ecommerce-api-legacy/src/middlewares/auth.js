'use strict';

const jwt = require('jsonwebtoken');
const { config } = require('../config');
const { UnauthorizedError, ForbiddenError } = require('../utils/errors');

/**
 * Auth middleware factory. Reads a Bearer token from Authorization header,
 * verifies it with the JWT secret, and attaches `req.user`.
 *
 * Escape hatch for local dev: when `AUTH_DISABLED=true`, the middleware
 * fabricates an admin user. Documented in .env.example.
 */
function authRequired(req, _res, next) {
    if (config.auth.disabled) {
        req.user = { id: 0, role: 'admin', name: 'dev-bypass' };
        return next();
    }
    const header = req.headers.authorization || '';
    const match = header.match(/^Bearer\s+(.+)$/i);
    if (!match) return next(new UnauthorizedError('Missing or malformed Authorization header'));
    try {
        const payload = jwt.verify(match[1], config.jwt.secret);
        req.user = payload;
        next();
    } catch (_err) {
        next(new UnauthorizedError('Invalid token'));
    }
}

function requireRole(...roles) {
    return (req, _res, next) => {
        if (!req.user) return next(new UnauthorizedError());
        if (!roles.includes(req.user.role)) return next(new ForbiddenError('Insufficient role'));
        next();
    };
}

module.exports = { authRequired, requireRole };
