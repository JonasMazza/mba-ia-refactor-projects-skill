'use strict';

const { getDb } = require('../db');

function findActiveById(id) {
    return getDb()
        .prepare('SELECT id, title, price, active FROM courses WHERE id = ? AND active = 1')
        .get(id);
}

module.exports = { findActiveById };
