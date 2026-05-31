'use strict';

const { getDb } = require('../db');

function create({ userId, courseId }) {
    const info = getDb()
        .prepare('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)')
        .run(userId, courseId);
    return info.lastInsertRowid;
}

module.exports = { create };
