import os
import sqlite3

from flask import Flask, render_template, request, redirect, session
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# ================= APP =================
app = Flask(__name__)

# 🔥 СТАБИЛЬНЫЙ KEY (НЕ МЕНЯЕТСЯ НА RENDER)
app.secret_key = os.environ.get("SECRET_KEY", "super_ultra_dev_key_123")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False  # Render = True если HTTPS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "app.db")


# ================= DB =================
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


# ================= LOGIN SAFE =================
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
    try:
        conn = db()
        u = conn.execute(
            "SELECT * FROM users WHERE id=?",
            (user_id,)
        ).fetchone()
        conn.close()

        if not u:
            return None

        return User(u["id"], u["username"], u["plan"])

    except:
        return None

# ================= SAFE HOME =================
@app.route("/")
def home():
    return redirect("/login")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ================= AUTH =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        conn = db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (request.form["username"],)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], request.form["password"]):

            login_user(
                User(user["id"], user["username"], user["plan"]),
                remember=True   # 🔥 ВОТ ЭТО ГЛАВНОЕ
            )

            return redirect("/dashboard")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        conn = db()
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?,?)",
            (request.form["username"],
             generate_password_hash(request.form["password"]))
        )
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect("/login")


# ================= ERROR CATCH (ANTI-500) =================
@app.errorhandler(Exception)
def error(e):
    import traceback
    print(traceback.format_exc())
    return f"ERROR: {str(e)}", 500


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
