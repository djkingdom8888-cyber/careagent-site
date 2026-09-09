import os
import secrets
from functools import wraps

from flask import session, redirect, url_for, request
from werkzeug.security import generate_password_hash, check_password_hash

from . import store

CREDENTIALS_NOTICE_PATH = os.path.join(store.DATA_DIR, "ADMIN_CREDENTIALS.txt")


def bootstrap_admin():
    """Create a default admin account on first run, if none exists yet."""
    if os.path.exists(store.ADMIN_PATH):
        return
    password = secrets.token_urlsafe(9)
    admin_data = {
        "username": "admin",
        "password_hash": generate_password_hash(password, method="pbkdf2:sha256"),
    }
    store.save_admin(admin_data)
    with open(CREDENTIALS_NOTICE_PATH, "w") as f:
        f.write(
            "CareAgent admin — first-run credentials\n"
            "========================================\n"
            "Username: admin\n"
            "Password: {}\n\n"
            "Log in at /admin/login, then change your password from\n"
            "Settings inside the admin panel. This file is safe to delete\n"
            "once you've logged in and changed the password.\n".format(password)
        )


def apply_env_password_reset():
    """Escape hatch for production: set CA_ADMIN_RESET_PASSWORD in Render's env
    vars to force the admin password, then remove the env var again. Avoids
    needing shell/SSH access just to recover into the admin account."""
    new_password = os.environ.get("CA_ADMIN_RESET_PASSWORD", "").strip()
    if not new_password:
        return
    admin = store.load_admin()
    admin["password_hash"] = generate_password_hash(new_password, method="pbkdf2:sha256")
    store.save_admin(admin)


def verify_login(username, password):
    admin = store.load_admin()
    if username != admin.get("username"):
        return False
    return check_password_hash(admin.get("password_hash", ""), password)


def set_password(new_password):
    admin = store.load_admin()
    admin["password_hash"] = generate_password_hash(new_password, method="pbkdf2:sha256")
    store.save_admin(admin)


def set_username(new_username):
    admin = store.load_admin()
    admin["username"] = new_username
    store.save_admin(admin)


def get_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def verify_csrf(token):
    expected = session.get("csrf_token")
    return bool(token) and bool(expected) and secrets.compare_digest(token, expected)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped
