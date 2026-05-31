'use strict';

const { getDb } = require('../db');

function findByEmail(email) {
    return getDb().prepare('SELECT id, name, email, pass, role FROM users WHERE email = ?').get(email);
}

function findById(id) {
    return getDb().prepare('SELECT id, name, email, role FROM users WHERE id = ?').get(id);
}

function create({ name, email, passwordHash, role = 'user' }) {
    const info = getDb()
        .prepare('INSERT INTO users (name, email, pass, role) VALUES (?, ?, ?, ?)')
        .run(name, email, passwordHash, role);
    return info.lastInsertRowid;
}

function remove(id) {
    const info = getDb().prepare('DELETE FROM users WHERE id = ?').run(id);
    return info.changes;
}

module.exports = { findByEmail, findById, create, remove };
