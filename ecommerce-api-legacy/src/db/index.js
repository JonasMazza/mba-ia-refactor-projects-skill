'use strict';

const Database = require('better-sqlite3');
const { config } = require('../config');

let db;

function getDb() {
    if (!db) {
        db = new Database(config.dbPath);
        db.pragma('journal_mode = WAL');
        db.pragma('foreign_keys = ON');
    }
    return db;
}

function initDb() {
    const database = getDb();

    database.exec(`
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            pass TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT (datetime('now'))
        );
    `);

    seed(database);
}

function seed(database) {
    const existing = database.prepare('SELECT COUNT(*) AS c FROM users').get().c;
    if (existing > 0) return;

    // Seed user has a pre-hashed password ("123") via bcrypt at runtime to avoid hardcoded hash.
    const bcrypt = require('bcryptjs');
    const seedHash = bcrypt.hashSync('123', 10);

    const insertUser = database.prepare(
        "INSERT INTO users (name, email, pass, role) VALUES (?, ?, ?, ?)"
    );
    insertUser.run('Leonan', 'leonan@fullcycle.com.br', seedHash, 'user');
    // Admin user for protected endpoints (only seeded in dev — credentials from env)
    const adminPass = process.env.SEED_ADMIN_PASS || 'admin123';
    insertUser.run('Admin', 'admin@fullcycle.com.br', bcrypt.hashSync(adminPass, 10), 'admin');

    const insertCourse = database.prepare(
        "INSERT INTO courses (title, price, active) VALUES (?, ?, ?)"
    );
    insertCourse.run('Clean Architecture', 997.0, 1);
    insertCourse.run('Docker', 497.0, 1);

    database.prepare(
        "INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)"
    ).run(1, 1);
    database.prepare(
        "INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)"
    ).run(1, 997.0, 'PAID');
}

module.exports = { getDb, initDb };
