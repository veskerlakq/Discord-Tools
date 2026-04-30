import os
import sqlite3
import zipfile
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, redirect, session, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "ULTRA_SECRET_500_FIX"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "app.db")

UPLOAD = os.path.join(BASE_DIR, "static/uploads")
GEN = os.path.join(BASE_DIR, "generated")

os.makedirs(UPLOAD, exist_ok=True)
os.makedirs(GEN, exist_ok=True)


# ---------- DB ----------
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


# ---------- AUTH ----------
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


# ---------- ROUTES ----------

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ---------- AUTH ----------

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
            login_user(User(user["id"], user["username"], user["plan"]), remember=True)
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
    session.clear()
    return redirect("/")


# ---------- TEMPLATES ----------

@app.route("/templates")
@login_required
def templates():
    conn = db()
    data = conn.execute("SELECT * FROM templates").fetchall()
    conn.close()
    return render_template("templates.html", templates=data)


@app.route("/create-template", methods=["GET", "POST"])
@login_required
def create_template():
    if request.method == "POST":
        file = request.files.get("image")

        img = ""
        if file and file.filename:
            filename = secure_filename(file.filename)
            path = os.path.join(UPLOAD, filename)
            file.save(path)
            img = "/static/uploads/" + filename

        conn = db()
        conn.execute("""
        INSERT INTO templates (name, description, image, link, author)
        VALUES (?,?,?,?,?)
        """, (
            request.form["name"],
            request.form["desc"],
            img,
            request.form["link"],
            current_user.username
        ))
        conn.commit()
        conn.close()

        return redirect("/templates")

    return render_template("create_template.html")


@app.route("/use-template/<int:id>")
@login_required
def use_template(id):
    conn = db()
    tpl = conn.execute("SELECT * FROM templates WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("use_template.html", tpl=tpl)


# ---------- BOT GENERATOR ----------

@app.route("/bot-generator", methods=["GET", "POST"])
@login_required
def bot_generator():

    if request.method == "POST":
        name = request.form["name"]
        prefix = request.form["prefix"]

        code = f"""
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="{prefix}")

@bot.event
async def on_ready():
    print("{name} ready")

@bot.command()
async def ping(ctx):
    await ctx.send("pong")

bot.run("TOKEN")
"""

        path = os.path.join(GEN, f"{name}.py")
        with open(path, "w") as f:
            f.write(code)

        zip_path = os.path.join(GEN, f"{name}.zip")
        with zipfile.ZipFile(zip_path, "w") as z:
            z.write(path, arcname=f"{name}.py")

        return send_file(zip_path, as_attachment=True)

    return render_template("bot_generator.html")


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
