"""Logins for the web version.

Every page needs a signed-in user. Accounts live in a ``users`` table in
the same database as the HR records; passwords are stored only as salted
hashes. There is no public sign-up: the first account is created from the
command line (see DEPLOY.md), and signed-in users can add more.
"""

import functools
import hmac
import secrets
import sqlite3
import time

import click
from flask import flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from hr.database import get_connection

MIN_PASSWORD_LENGTH = 8

# Simple brute-force protection: after MAX_FAILURES wrong passwords for a
# username, further attempts are refused for LOCKOUT_SECONDS.
MAX_FAILURES = 5
LOCKOUT_SECONDS = 15 * 60
_failures = {}  # username -> (count, time of first failure)


def setup_users_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def create_user(username, password):
    """Add a user. Returns an error message, or ``None`` on success."""
    username = (username or "").strip()
    if not username:
        return "Username is required."
    if len(password or "") < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return "That username is already taken."
    finally:
        conn.close()
    return None


def set_password(user_id, password):
    if len(password or "") < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                 (generate_password_hash(password), user_id))
    conn.commit()
    conn.close()
    return None


def check_login(username, password):
    """Return the user row if the details are right, else ``None``.

    Raises ``PermissionError`` while the username is locked out.
    """
    key = (username or "").strip().lower()
    count, first = _failures.get(key, (0, 0))
    if count >= MAX_FAILURES and time.time() - first < LOCKOUT_SECONDS:
        raise PermissionError

    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?",
                        (key,)).fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password or ""):
        _failures.pop(key, None)
        return user

    if time.time() - first >= LOCKOUT_SECONDS:
        count, first = 0, time.time()
    _failures[key] = (count + 1, first)
    return None


def load_current_user():
    """Before each request: put the signed-in user (or None) on ``g.user``."""
    g.user = None
    user_id = session.get("user_id")
    if user_id is not None:
        conn = get_connection()
        g.user = conn.execute("SELECT id, username FROM users WHERE id = ?",
                              (user_id,)).fetchone()
        conn.close()
        if g.user is None:          # account was removed
            session.clear()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please sign in.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Protection against cross-site form posts (CSRF)
# ---------------------------------------------------------------------------


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def check_csrf():
    """Before each request: every form post must carry the session's token.

    A post without it (a stale page, or another website submitting a form)
    is not carried out; the page is simply shown again.
    """
    if request.method == "POST":
        sent = request.form.get("csrf_token", "")
        if not hmac.compare_digest(sent, session.get("csrf_token", "")):
            flash("That form had expired, so nothing was saved. Please try again.",
                  "warning")
            return redirect(request.full_path if request.query_string else request.path)


# ---------------------------------------------------------------------------
# Command line (from this folder):  flask --app app create-user
# ---------------------------------------------------------------------------


def register_commands(app):
    @app.cli.command("create-user")
    @click.option("--username", prompt=True)
    @click.password_option()
    def create_user_command(username, password):
        """Create a login for the web version."""
        setup_users_table()
        error = create_user(username, password)
        if error:
            raise click.ClickException(error)
        click.echo(f"User '{username}' created. You can now sign in.")
