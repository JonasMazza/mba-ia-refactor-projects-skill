'use strict';

const { config } = require('../config');
const logger = require('../utils/logger');

/**
 * Fake payment gateway. Same business rule as the legacy code
 * (cards starting with "4" succeed) but:
 *  - never logs the full PAN (only BIN + last4)
 *  - never logs the gateway key
 */
function charge(cardNumber, amount) {
    const masked = mask(cardNumber);
    logger.info({ event: 'payment.charge.attempt', card: masked, amount }, 'Processing payment');

    // Sanity check: we expect the config to be loaded from env, not source.
    if (!config.paymentGatewayKey) {
        throw new Error('Payment gateway key not configured');
    }

    const status = String(cardNumber).startsWith('4') ? 'PAID' : 'DENIED';
    logger.info({ event: 'payment.charge.result', card: masked, status }, 'Payment processed');
    return status;
}

function mask(cardNumber) {
    const s = String(cardNumber || '');
    if (s.length < 10) return '****';
    return `${s.slice(0, 6)}******${s.slice(-4)}`;
}

module.exports = { charge };
