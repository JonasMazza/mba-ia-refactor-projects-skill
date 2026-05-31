'use strict';

const reportService = require('../services/reportService');

function financialReport(_req, res, next) {
    try {
        const report = reportService.buildFinancialReport();
        res.status(200).json(report);
    } catch (err) {
        next(err);
    }
}

module.exports = { financialReport };
