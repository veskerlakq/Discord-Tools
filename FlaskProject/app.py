from flask import Flask, render_template, request, redirect, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import zipfile
import os

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
    conn.commit()
    conn.close()

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

# ---------------- TOGGLES ----------------
@app.route("/toggle-theme")
def toggle_theme():
    session["theme"] = "light" if session.get("theme", "dark") == "dark" else "dark"
    return redirect(request.referrer or "/dashboard")

@app.route("/toggle-lang")
def toggle_lang():
    session["lang"] = "ru" if session.get("lang", "en") == "en" else "en"
    return redirect(request.referrer or "/dashboard")

# ---------------- ADMIN PREMIUM ----------------
@app.route("/admin/grant-premium/<username>")
def grant_premium(username):

    if username != "ble1zx":
        return "no access"

    conn = db()
    conn.execute("UPDATE users SET plan='premium' WHERE username=?", (username,))
    conn.commit()
    conn.close()

    return f"{username} is now premium"

# ---------------- I18N ----------------
translations = {
    "en": {
        "dashboard": "Dashboard",
        "welcome": "Welcome",
        "bot": "Bot Generator",
        "templates": "Server Templates",
        "buy": "Buy Premium"
    },
    "ru": {
        "dashboard": "Панель",
        "welcome": "Добро пожаловать",
        "bot": "Генератор ботов",
        "templates": "Шаблоны серверов",
        "buy": "Купить Premium"
    }
}

@app.context_processor
def inject_lang():
    lang = session.get("lang", "en")
    return dict(t=translations[lang])

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

# ---------------- PREMIUM ----------------
@app.route("/buy-premium")
@login_required
def buy_premium():
    conn = db()
    conn.execute("UPDATE users SET plan='premium' WHERE id=?", (current_user.id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ---------------- BOT GENERATOR V2 ----------------
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

# ---------------- TEMPLATES V2 ----------------
@app.route("/templates")
@login_required
def templates():

    templates = [
        {
            "name": "Gaming Server",
            "desc": "Channels + roles setup",
            "icon": "fa-gamepad"
        },
        {
            "name": "Community Hub",
            "desc": "Social + moderation layout",
            "icon": "fa-users"
        },
        {
            "name": "Support Server",
            "desc": "Tickets + help system",
            "icon": "fa-headset"
        }
    ]

    return render_template("templates.html", templates=templates)

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