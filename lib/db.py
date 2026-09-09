import os
import sqlite3
from contextlib import contextmanager

from . import store

DB_PATH = os.path.join(store.DATA_DIR, "app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS facilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id INTEGER NOT NULL REFERENCES facilities(id),
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'caregiver',  -- 'owner' or 'caregiver'
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS residents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id INTEGER NOT NULL REFERENCES facilities(id),
    name TEXT NOT NULL,
    room TEXT NOT NULL DEFAULT '',
    date_of_birth TEXT NOT NULL DEFAULT '',
    allergies TEXT NOT NULL DEFAULT '',
    diagnoses TEXT NOT NULL DEFAULT '',
    emergency_contact TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER NOT NULL REFERENCES residents(id),
    name TEXT NOT NULL,
    dose TEXT NOT NULL DEFAULT '',
    route TEXT NOT NULL DEFAULT '',
    instructions TEXT NOT NULL DEFAULT '',
    times TEXT NOT NULL DEFAULT '',  -- comma-separated HH:MM, e.g. "08:00,14:00,20:00"
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mar_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medication_id INTEGER NOT NULL REFERENCES medications(id),
    scheduled_date TEXT NOT NULL,   -- YYYY-MM-DD
    scheduled_time TEXT NOT NULL,   -- HH:MM
    status TEXT NOT NULL DEFAULT 'due',  -- due, given, missed, refused, held
    logged_by_user_id INTEGER REFERENCES app_users(id),
    logged_at TEXT,
    note TEXT NOT NULL DEFAULT '',
    UNIQUE(medication_id, scheduled_date, scheduled_time)
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER NOT NULL REFERENCES residents(id),
    title TEXT NOT NULL,
    shift TEXT NOT NULL DEFAULT 'any',  -- morning, afternoon, evening, night, any
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    log_date TEXT NOT NULL,  -- YYYY-MM-DD
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, done, missed
    completed_by_user_id INTEGER REFERENCES app_users(id),
    completed_at TEXT,
    note TEXT NOT NULL DEFAULT '',
    UNIQUE(task_id, log_date)
);

CREATE TABLE IF NOT EXISTS billing_charges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER NOT NULL REFERENCES residents(id),
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'rent',  -- rent, care_level, service, other
    amount_cents INTEGER NOT NULL,
    charge_date TEXT NOT NULL,  -- YYYY-MM-DD
    voided INTEGER NOT NULL DEFAULT 0,
    logged_by_user_id INTEGER REFERENCES app_users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS billing_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER NOT NULL REFERENCES residents(id),
    amount_cents INTEGER NOT NULL,
    method TEXT NOT NULL DEFAULT 'check',  -- check, cash, card, ach, medicaid, other
    payer TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    paid_on TEXT NOT NULL,  -- YYYY-MM-DD
    voided INTEGER NOT NULL DEFAULT 0,
    logged_by_user_id INTEGER REFERENCES app_users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id INTEGER NOT NULL REFERENCES facilities(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS form_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id INTEGER NOT NULL REFERENCES forms(id),
    label TEXT NOT NULL,
    field_type TEXT NOT NULL DEFAULT 'text',  -- text, textarea, checkbox, date, select
    options TEXT NOT NULL DEFAULT '',  -- comma-separated choices, for 'select' type
    required INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS form_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id INTEGER NOT NULL REFERENCES forms(id),
    resident_id INTEGER REFERENCES residents(id),
    submitted_by_user_id INTEGER REFERENCES app_users(id),
    data_json TEXT NOT NULL,
    submitted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS signature_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id INTEGER NOT NULL REFERENCES facilities(id),
    resident_id INTEGER REFERENCES residents(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    created_by_user_id INTEGER REFERENCES app_users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS signatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES signature_documents(id),
    signer_name TEXT NOT NULL,
    signer_role TEXT NOT NULL DEFAULT '',
    signature_data TEXT NOT NULL,
    signed_by_user_id INTEGER REFERENCES app_users(id),
    signed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS faxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id INTEGER NOT NULL REFERENCES facilities(id),
    resident_id INTEGER REFERENCES residents(id),
    to_number TEXT NOT NULL,
    to_name TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'queued',  -- queued, sent, failed — see app_fax route for why it stops at 'queued'
    created_by_user_id INTEGER REFERENCES app_users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def session():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with session() as conn:
        conn.executescript(SCHEMA)
