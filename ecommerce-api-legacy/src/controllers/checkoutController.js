'use strict';

const checkoutService = require('../services/checkoutService');
const { validateCheckout } = require('../schemas/checkoutSchema');

function checkout(req, res, next) {
    try {
        const data = validateCheckout(req.body);
        const { enrollmentId } = checkoutService.checkout(data);
        res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
    } catch (err) {
        next(err);
    }
}

module.exports = { checkout };
