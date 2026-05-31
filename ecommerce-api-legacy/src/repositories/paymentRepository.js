'use strict';

const { getDb } = require('../db');

function create({ enrollmentId, amount, status }) {
    const info = getDb()
        .prepare('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)')
        .run(enrollmentId, amount, status);
    return info.lastInsertRowid;
}

module.exports = { create };
