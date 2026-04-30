from flask import Flask, render_template, request, redirect, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import traceback

app = Flask(__name__)

# ---------------- CONFIG ----------------
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# FIX: Render-safe DB path
DB = os.path.join(BASE_DIR, "app.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------------- GLOBAL ERROR CATCH ----------------
@app.errorhandler(Exception)
def handle_error(e):
    print("🔥 GLOBAL ERROR:")
    print(traceback.format_exc())
    return f"SERVER ERROR: {str(e)}", 500


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


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return redirect("/login")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/toggle-theme")
def toggle_theme():
    session["theme"] = "light" if session.get("theme", "dark") == "dark" else "dark"
    return redirect(request.referrer or "/dashboard")


# ---------------- TEMPLATES ----------------
@app.route("/templates")
@login_required
def templates():
    conn = db()
    rows = conn.execute("SELECT * FROM templates").fetchall()
    conn.close()
    return render_template("templates.html", templates=rows)


# ---------------- CREATE TEMPLATE (FIXED 100%) ----------------
@app.route("/create-template", methods=["GET", "POST"])
@login_required
def create_template():

    if request.method == "POST":

        try:
            name = request.form.get("name", "").strip()
            desc = request.form.get("desc", "").strip()
            link = request.form.get("link", "").strip()

            if not name:
                return "Name required", 400

            file = request.files.get("image")

            image_path = ""

            if file and file.filename:
                filename = secure_filename(file.filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(save_path)
                image_path = "/static/uploads/" + filename

            author = getattr(current_user, "username", "unknown")

            conn = db()
            conn.execute("""
                INSERT INTO templates (name, description, image, link, author)
                VALUES (?,?,?,?,?)
            """, (
                name,
                desc,
                image_path,
                link,
                author
            ))
            conn.commit()
            conn.close()

            return redirect("/templates")

        except Exception as e:
            print(traceback.format_exc())
            return f"CREATE ERROR: {str(e)}", 500

    return render_template("create-template.html")


# ---------------- USE TEMPLATE ----------------
@app.route("/use-template/<int:template_id>")
@login_required
def use_template(template_id):

    conn = db()
    tpl = conn.execute(
        "SELECT * FROM templates WHERE id=?",
        (template_id,)
    ).fetchone()
    conn.close()

    if not tpl:
        return "Not found", 404

    return render_template("use_template.html", tpl=tpl)


# ---------------- AUTH ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        conn = db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (request.form.get("username"),)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], request.form.get("password")):
            login_user(User(user["id"], user["username"], user["plan"]))
            return redirect("/dashboard")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        conn = db()
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?,?)",
            (
                request.form.get("username"),
                generate_password_hash(request.form.get("password"))
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
    return redirect("/login")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
