from functools import wraps

from flask import session, redirect, url_for, request, abort
from werkzeug.security import generate_password_hash, check_password_hash

from . import db


def create_facility(name):
    with db.session() as conn:
        cur = conn.execute("INSERT INTO facilities (name) VALUES (?)", (name,))
        return cur.lastrowid


def create_user(facility_id, username, password, full_name, role="caregiver"):
    with db.session() as conn:
        cur = conn.execute(
            "INSERT INTO app_users (facility_id, username, password_hash, full_name, role) VALUES (?,?,?,?,?)",
            (facility_id, username, generate_password_hash(password, method="pbkdf2:sha256"), full_name, role),
        )
        return cur.lastrowid


def verify_app_login(username, password):
    with db.session() as conn:
        row = conn.execute("SELECT * FROM app_users WHERE username = ?", (username,)).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return row
    return None


def get_current_user():
    user_id = session.get("app_user_id")
    if not user_id:
        return None
    with db.session() as conn:
        return conn.execute("SELECT * FROM app_users WHERE id = ?", (user_id,)).fetchone()


def get_current_facility():
    with db.session() as conn:
        fid = session.get("app_facility_id")
        if not fid:
            return None
        return conn.execute("SELECT * FROM facilities WHERE id = ?", (fid,)).fetchone()


def app_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("app_user_id"):
            return redirect(url_for("app_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("app_user_id"):
            return redirect(url_for("app_login", next=request.path))
        if session.get("app_role") != "owner":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def username_exists(username):
    with db.session() as conn:
        row = conn.execute("SELECT id FROM app_users WHERE username = ?", (username,)).fetchone()
    return row is not None


def set_password(user_id, new_password):
    with db.session() as conn:
        conn.execute(
            "UPDATE app_users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password, method="pbkdf2:sha256"), user_id),
        )
