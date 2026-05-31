'use strict';

const { config } = require('../config');

/**
 * Tiny JSON logger. Pino-shaped API (info/warn/error/debug) without
 * adding a dependency. Strips obvious PII keys from the bound object.
 */

const LEVELS = { debug: 10, info: 20, warn: 30, error: 40 };
const PII_KEYS = new Set(['pass', 'password', 'card', 'cardNumber', 'cvv', 'token']);

function sanitize(obj) {
    if (!obj || typeof obj !== 'object') return obj;
    const out = {};
    for (const [k, v] of Object.entries(obj)) {
        if (PII_KEYS.has(k)) {
            out[k] = '[REDACTED]';
        } else {
            out[k] = v;
        }
    }
    return out;
}

function emit(level, bindings, msg) {
    if (LEVELS[level] < LEVELS[config.logLevel || 'info']) return;
    const entry = {
        level,
        time: new Date().toISOString(),
        ...sanitize(bindings),
        msg,
    };
    const line = JSON.stringify(entry);
    if (level === 'error') process.stderr.write(line + '\n');
    else process.stdout.write(line + '\n');
}

function makeLogger() {
    return {
        debug: (bindings, msg) => emit('debug', bindings, msg),
        info: (bindings, msg) => emit('info', bindings, msg),
        warn: (bindings, msg) => emit('warn', bindings, msg),
        error: (bindings, msg) => emit('error', bindings, msg),
    };
}

module.exports = makeLogger();
