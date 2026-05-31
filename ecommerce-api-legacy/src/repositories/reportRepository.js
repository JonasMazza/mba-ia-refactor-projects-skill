'use strict';

const { getDb } = require('../db');

/**
 * Single JOIN replacing the N+1 in the legacy report.
 * Returns one row per (course, enrollment) pair; courses with zero enrollments
 * still appear once with NULL columns.
 */
function getFinancialReportRows() {
    return getDb().prepare(`
        SELECT
            c.id            AS course_id,
            c.title         AS course_title,
            u.name          AS student_name,
            p.amount        AS payment_amount,
            p.status        AS payment_status
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.id
        LEFT JOIN users u       ON u.id        = e.user_id
        LEFT JOIN payments p    ON p.enrollment_id = e.id
        ORDER BY c.id
    `).all();
}

module.exports = { getFinancialReportRows };
