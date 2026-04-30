import os
import sqlite3
import traceback

from flask import Flask, render_template, request, redirect, session
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ================= CONFIG =================
app.secret_key = os.environ.get("SECRET_KEY", "saas_ultra_key_999")

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

    conn.execute("""
    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        image TEXT,
        link TEXT,
        author TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ================= AUTH =================
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
        u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        if u:
            return User(u["id"], u["username"], u["plan"])
    except:
        return None


# ================= ERROR SAFETY =================
@app.errorhandler(Exception)
def error(e):
    print(traceback.format_exc())
    return f"ERROR: {e}", 500


# ================= ROUTES =================

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect("/dashboard")
    return render_template("home.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ================= AUTH =================

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


@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect("/")


# ================= TEMPLATES =================

@app.route("/templates")
@login_required
def templates():
    conn = db()
    rows = conn.execute("SELECT * FROM templates ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("templates.html", templates=rows)


@app.route("/create-template", methods=["GET", "POST"])
@login_required
def create_template():

    if request.method == "POST":
        name = request.form["name"]
        desc = request.form["desc"]
        link = request.form["link"]

        conn = db()
        conn.execute("""
            INSERT INTO templates (name, description, image, link, author)
            VALUES (?,?,?,?,?)
        """, (name, desc, "", link, current_user.username))
        conn.commit()
        conn.close()

        return redirect("/templates")

    return render_template("create_template.html")


@app.route("/use-template/<int:template_id>")
@login_required
def use_template(template_id):

    conn = db()
    tpl = conn.execute("SELECT * FROM templates WHERE id=?", (template_id,)).fetchone()
    conn.close()

    if not tpl:
        return "Not found", 404

    return render_template("use_template.html", tpl=tpl)


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
