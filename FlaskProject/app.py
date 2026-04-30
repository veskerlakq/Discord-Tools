from flask import Flask, render_template, request, redirect, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import zipfile

app = Flask(__name__)
app.secret_key = "change_me_123"

DB = "app.db"

# ---------------- DB ----------------
def db():
    return sqlite3.connect(DB)

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
        data TEXT,
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
        return User(u[0], u[1], u[3])
    return None

# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect("/login")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

# ---------------- TOGGLES ----------------
@app.route("/toggle-theme")
def toggle_theme():
    session["theme"] = "light" if session.get("theme", "dark") == "dark" else "dark"
    return redirect(request.referrer or "/dashboard")

@app.route("/toggle-lang")
def toggle_lang():
    session["lang"] = "ru" if session.get("lang", "en") == "en" else "en"
    return redirect(request.referrer or "/dashboard")

# ---------------- MARKETPLACE ----------------
@app.route("/templates")
@login_required
def templates():

    conn = db()
    rows = conn.execute("SELECT * FROM templates").fetchall()
    conn.close()

    templates = []
    for r in rows:
        templates.append({
            "id": r[0],
            "name": r[1],
            "desc": r[2],
            "data": r[3],
            "author": r[4]
        })

    return render_template("templates.html", templates=templates)

@app.route("/create-template", methods=["GET", "POST"])
@login_required
def create_template():

    if request.method == "POST":

        name = request.form["name"]
        desc = request.form["desc"]
        data = request.form["data"]

        conn = db()
        conn.execute(
            "INSERT INTO templates (name, description, data, author) VALUES (?,?,?,?)",
            (name, desc, data, current_user.username)
        )
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
        return "Template not found"

    return render_template("use_template.html", tpl=tpl)

# ---------------- BOT GENERATOR ----------------
@app.route("/bot-generator", methods=["GET", "POST"])
@login_required
def bot_generator():

    if current_user.plan != "premium":
        return redirect("/dashboard")

    if request.method == "POST":

        name = request.form["name"]
        prefix = request.form["prefix"]

        os.makedirs("generated", exist_ok=True)

        code = f"""
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="{prefix}")

@bot.event
async def on_ready():
    print("{name} is ready")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

bot.run("TOKEN")
"""

        path = f"generated/{name}.py"

        with open(path, "w", encoding="utf-8") as f:
            f.write(code)

        zip_path = f"generated/{name}.zip"

        with zipfile.ZipFile(zip_path, "w") as z:
            z.write(path, arcname=f"{name}.py")

        return f"Bot generated: {zip_path}"

    return render_template("bot_generator.html")

# ---------------- AUTH ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        conn.close()

        if user and check_password_hash(user[2], p):
            login_user(User(user[0], user[1], user[3]))
            return redirect("/dashboard")

    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = db()
        conn.execute(
            "INSERT INTO users (username,password) VALUES (?,?)",
            (u, generate_password_hash(p))
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
