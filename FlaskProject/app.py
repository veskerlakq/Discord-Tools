import os
import sqlite3

from flask import Flask, render_template, request, redirect
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "saas_2_0_secret"

DB = "app.db"


# ---------------- DB ----------------
def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        plan TEXT DEFAULT 'free'
    )
    """)
    conn.commit()
    conn.close()


init_db()


# ---------------- AUTH ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(self, id, username, plan):
        self.id = str(id)
        self.username = username
        self.plan = plan


@login_manager.user_loader
def load_user(user_id):
    conn = db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()

    if u:
        return User(u["id"], u["username"], u["plan"])
    return None


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect("/dashboard")
    return render_template("home.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect("/dashboard")

    if request.method == "POST":

        conn = db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (request.form["username"],)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], request.form["password"]):
            login_user(User(user["id"], user["username"], user["plan"]), remember=True)
            return redirect("/dashboard")

    return render_template("login.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        conn = db()
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?,?)",
            (
                request.form["username"],
                generate_password_hash(request.form["password"])
            )
        )
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)

import traceback

@app.errorhandler(Exception)
def error_handler(e):
    print("\n🔥 FULL ERROR TRACEBACK:")
    print(traceback.format_exc())
    return f"ERROR: {e}", 500
