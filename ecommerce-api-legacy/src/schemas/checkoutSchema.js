'use strict';

const { BadRequestError } = require('../utils/errors');

/**
 * Tiny dependency-free schema validator for the checkout payload.
 * Accepts both the legacy short names (usr/eml/pwd/c_id/card) and the
 * clear names (name/email/password/courseId/cardNumber) for backward
 * compatibility, but returns a normalized object with clear names.
 */
function validateCheckout(body = {}) {
    const name = body.name ?? body.usr;
    const email = body.email ?? body.eml;
    const password = body.password ?? body.pwd;
    const courseId = body.courseId ?? body.c_id;
    const cardNumber = body.cardNumber ?? body.card;

    if (!name || typeof name !== 'string') throw new BadRequestError('name is required');
    if (!email || typeof email !== 'string' || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        throw new BadRequestError('valid email is required');
    }
    if (!courseId || !Number.isFinite(Number(courseId))) {
        throw new BadRequestError('courseId is required');
    }
    if (!cardNumber || !/^\d{13,19}$/.test(String(cardNumber))) {
        throw new BadRequestError('cardNumber must be 13-19 digits');
    }
    // password is optional on first checkout (legacy behavior). If provided, enforce minimum length.
    const pwd = password ? String(password) : '123456';
    if (pwd.length < 4) throw new BadRequestError('password too short');

    return {
        name: String(name),
        email: String(email),
        password: pwd,
        courseId: Number(courseId),
        cardNumber: String(cardNumber),
    };
}

module.exports = { validateCheckout };
