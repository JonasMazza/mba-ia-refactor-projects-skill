'use strict';

const { getDb } = require('../db');
const userRepository = require('../repositories/userRepository');
const { NotFoundError } = require('../utils/errors');

/**
 * Deletes a user and (atomically) any dependent rows. The original code
 * confessed "matrículas e pagamentos ficaram sujos no banco" — we fix it by
 * deleting in a transaction. ON DELETE CASCADE on enrollments/payments would
 * also work, but doing it explicitly keeps the intent visible.
 */
function deleteUser(id) {
    const db = getDb();
    const tx = db.transaction(() => {
        // delete dependent rows first
        db.prepare(`
            DELETE FROM payments
            WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)
        `).run(id);
        db.prepare('DELETE FROM enrollments WHERE user_id = ?').run(id);
        const info = db.prepare('DELETE FROM users WHERE id = ?').run(id);
        if (info.changes === 0) throw new NotFoundError('Usuário não encontrado');
    });
    tx();
}

module.exports = { deleteUser, ...userRepository };
