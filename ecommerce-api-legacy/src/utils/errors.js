'use strict';

class HttpError extends Error {
    constructor(status, message, code) {
        super(message);
        this.status = status;
        this.code = code || message;
    }
}

class BadRequestError extends HttpError {
    constructor(message = 'Bad Request') { super(400, message, 'BAD_REQUEST'); }
}
class UnauthorizedError extends HttpError {
    constructor(message = 'Unauthorized') { super(401, message, 'UNAUTHORIZED'); }
}
class ForbiddenError extends HttpError {
    constructor(message = 'Forbidden') { super(403, message, 'FORBIDDEN'); }
}
class NotFoundError extends HttpError {
    constructor(message = 'Not Found') { super(404, message, 'NOT_FOUND'); }
}
class PaymentDeclinedError extends HttpError {
    constructor(message = 'Pagamento recusado') { super(400, message, 'PAYMENT_DECLINED'); }
}

module.exports = {
    HttpError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    PaymentDeclinedError,
};
