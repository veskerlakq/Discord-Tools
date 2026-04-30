import os
import sqlite3
import requests

from flask import Flask, redirect, request, session, render_template
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# ================= CONFIG =================
app = Flask(__name__)
app.secret_key = "DISCORD_ULTRA_SECRET"

CLIENT_ID = "ТВОЙ_CLIENT_ID"
CLIENT_SECRET = "ТВОЙ_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:5000/callback"

API_BASE = "https://discord.com/api"

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
        id TEXT PRIMARY KEY,
        username TEXT,
        avatar TEXT,
        plan TEXT DEFAULT 'free'
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ================= LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, id, username, avatar, plan):
        self.id = id
        self.username = username
        self.avatar = avatar
        self.plan = plan


@login_manager.user_loader
def load_user(user_id):
    conn = db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()

    if u:
        return User(u["id"], u["username"], u["avatar"], u["plan"])


# ================= ROUTES =================

@app.route("/")
def home():
    return render_template("home.html")


# ---------- LOGIN DISCORD ----------
@app.route("/login")
def login():
    return redirect(
        f"{API_BASE}/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code&scope=identify"
    )


# ---------- CALLBACK ----------
@app.route("/callback")
def callback():
    code = request.args.get("code")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    r = requests.post(f"{API_BASE}/oauth2/token", data=data, headers=headers).json()
    access_token = r.get("access_token")

    user = requests.get(
        f"{API_BASE}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    user_id = user["id"]
    username = user["username"]
    avatar = f"https://cdn.discordapp.com/avatars/{user_id}/{user['avatar']}.png"

    conn = db()

    existing = conn.execute(
        "SELECT * FROM users WHERE id=?", (user_id,)
    ).fetchone()

    if not existing:
        conn.execute(
            "INSERT INTO users (id, username, avatar) VALUES (?,?,?)",
            (user_id, username, avatar)
        )
        conn.commit()

    conn.close()

    login_user(User(user_id, username, avatar, "free"), remember=True)

    return redirect("/dashboard")


# ---------- DASHBOARD ----------
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ---------- LOGOUT ----------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect("/")


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
