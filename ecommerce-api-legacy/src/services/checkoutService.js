'use strict';

const bcrypt = require('bcryptjs');
const { getDb } = require('../db');
const courseRepository = require('../repositories/courseRepository');
const userRepository = require('../repositories/userRepository');
const enrollmentRepository = require('../repositories/enrollmentRepository');
const paymentRepository = require('../repositories/paymentRepository');
const auditLogRepository = require('../repositories/auditLogRepository');
const paymentGateway = require('./paymentGateway');
const { NotFoundError, PaymentDeclinedError } = require('../utils/errors');

const BCRYPT_ROUNDS = 10;

/**
 * Executes the checkout flow atomically:
 *   1. Validate course exists and is active
 *   2. Find or create the user (with bcrypt password)
 *   3. Charge the card via the payment gateway
 *   4. In a single transaction: insert enrollment, payment, audit log
 *
 * No callback hell, no manual pending counters, no PAN logging.
 */
function checkout({ name, email, password, courseId, cardNumber }) {
    const course = courseRepository.findActiveById(courseId);
    if (!course) throw new NotFoundError('Curso não encontrado');

    // Resolve or create user (outside the financial transaction — user creation
    // is independently useful and doesn't roll back if payment fails).
    let user = userRepository.findByEmail(email);
    if (!user) {
        const passwordHash = bcrypt.hashSync(password, BCRYPT_ROUNDS);
        const userId = userRepository.create({ name, email, passwordHash });
        user = { id: userId, name, email };
    }

    // Charge the card BEFORE writing financial state.
    const status = paymentGateway.charge(cardNumber, course.price);
    if (status !== 'PAID') throw new PaymentDeclinedError();

    // Atomic write of enrollment + payment + audit log.
    const tx = getDb().transaction(() => {
        const enrollmentId = enrollmentRepository.create({
            userId: user.id,
            courseId: course.id,
        });
        paymentRepository.create({
            enrollmentId,
            amount: course.price,
            status,
        });
        auditLogRepository.create(`Checkout curso ${course.id} por ${user.id}`);
        return enrollmentId;
    });

    const enrollmentId = tx();
    return { enrollmentId };
}

module.exports = { checkout };
