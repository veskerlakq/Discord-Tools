import os
import sqlite3
import zipfile

def clean_name(name: str) -> str:
    if not name:
        return "untitled"
    return name.replace("-", "_")
    
from flask import Flask, render_template, request, redirect, send_file, session
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ================= APP =================
app = Flask(__name__)
app.secret_key = "dev_secret"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB = os.path.join(BASE_DIR, "app.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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
        author TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ================= LOGIN =================
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


# ================= ROUTES =================
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
            login_user(User(user["id"], user["username"], user["plan"]))
            return redirect("/dashboard")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        conn = db()
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?,?)",
            (request.form["username"], generate_password_hash(request.form["password"]))
        )
        conn.commit()
        conn.close()
        return redirect("/login")

    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


# ================= BOT GENERATOR =================
@app.route("/bot-generator", methods=["GET", "POST"])
@login_required
def bot_generator():

    if request.method == "POST":

        name = request.form.get("name", "bot")
        prefix = request.form.get("prefix", "!")

        os.makedirs("generated", exist_ok=True)

        code = f"""
from discord.ext import commands

bot = commands.Bot(command_prefix="{prefix}")

@bot.event
async def on_ready():
    print("{name} ready")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

bot.run("TOKEN")
"""

        py_path = f"generated/{name}.py"

        with open(py_path, "w", encoding="utf-8") as f:
            f.write(code)

        zip_path = f"generated/{name}.zip"

        with zipfile.ZipFile(zip_path, "w") as z:
            z.write(py_path, arcname=f"{name}.py")

        return send_file(zip_path, as_attachment=True)

    return render_template("bot_generator.html")


# ================= TEMPLATES =================
@app.route("/templates")
@login_required
def templates():
    conn = db()
    rows = conn.execute("SELECT * FROM templates").fetchall()
    conn.close()

    return render_template("templates.html", templates=rows)


@app.route("/create-template", methods=["GET", "POST"])
@login_required
def create_template():

    if request.method == "POST":

        name = request.form.get("name")
        desc = request.form.get("description")

        file = request.files.get("image")

        image_path = ""

        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)
            image_path = "/static/uploads/" + filename

        conn = db()
        conn.execute(
            "INSERT INTO templates (name, description, image, author) VALUES (?,?,?,?)",
            (name, desc, image_path, current_user.username)
        )
        conn.commit()
        conn.close()

        return redirect("/templates")

    return render_template("create_template.html")


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


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
