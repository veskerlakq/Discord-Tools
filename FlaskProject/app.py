from flask import Flask, render_template, request, redirect, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "app.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


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


with app.app_context():
    init_db()


# ---------------- LOGIN ----------------
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


# ---------------- TEMPLATES ----------------
@app.route("/templates")
@login_required
def templates():
    conn = db()
    rows = conn.execute("SELECT * FROM templates").fetchall()
    conn.close()

    return render_template("templates.html", templates=rows)


# ---------------- CREATE TEMPLATE (UPLOAD FIX) ----------------
@app.route("/create-template", methods=["GET", "POST"])
@login_required
def create_template():

    if request.method == "POST":

        name = request.form.get("name", "")
        desc = request.form.get("desc", "")
        link = request.form.get("link", "")

        file = request.files.get("image")

        image_path = ""

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)

            image_path = "/static/uploads/" + filename

        conn = db()
        conn.execute("""
            INSERT INTO templates (name, description, image, link, author)
            VALUES (?,?,?,?,?)
        """, (
            name,
            desc,
            image_path,
            link,
            current_user.username
        ))
        conn.commit()
        conn.close()

        return redirect("/templates")

    return render_template("create_template.html")
