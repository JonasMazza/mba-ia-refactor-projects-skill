'use strict';

const userService = require('../services/userService');
const { BadRequestError } = require('../utils/errors');

function remove(req, res, next) {
    try {
        const id = Number(req.params.id);
        if (!Number.isInteger(id) || id <= 0) throw new BadRequestError('invalid id');
        userService.deleteUser(id);
        res.status(200).json({ msg: 'Usuário deletado com sucesso (matrículas e pagamentos removidos atomicamente)' });
    } catch (err) {
        next(err);
    }
}

module.exports = { remove };
