'use strict';

const reportRepository = require('../repositories/reportRepository');

/**
 * Builds the financial report using a single JOIN (replacing the legacy N+1).
 *
 * Output shape preserves the legacy contract:
 *   [ { course, revenue, students: [{ student, paid }] }, ... ]
 */
function buildFinancialReport() {
    const rows = reportRepository.getFinancialReportRows();
    const byCourse = new Map();

    for (const row of rows) {
        let entry = byCourse.get(row.course_id);
        if (!entry) {
            entry = { course: row.course_title, revenue: 0, students: [] };
            byCourse.set(row.course_id, entry);
        }
        // Course with no enrollments still produced 1 row with NULL student.
        if (row.student_name === null && row.payment_amount === null) continue;

        if (row.payment_status === 'PAID') {
            entry.revenue += row.payment_amount;
        }
        entry.students.push({
            student: row.student_name || 'Unknown',
            paid: row.payment_amount || 0,
        });
    }

    return Array.from(byCourse.values());
}

module.exports = { buildFinancialReport };
