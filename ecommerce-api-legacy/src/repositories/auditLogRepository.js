'use strict';

const { getDb } = require('../db');

function create(action) {
    getDb()
        .prepare("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))")
        .run(action);
}

module.exports = { create };
