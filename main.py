
import os
import json
import sqlite3
import random
import string
from flask import Flask, render_template_string, request, jsonify, redirect

app = Flask(__name__)
DB_PATH = "/tmp/aether.db" if os.getenv("VERCEL") else "aether.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_invited INTEGER DEFAULT 0,
            used_code TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS invites (
            code TEXT PRIMARY KEY,
            is_used INTEGER DEFAULT 0,
            created_by TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER,
            author_name TEXT,
            title TEXT,
            content TEXT,
            is_pinned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def generate_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# HTML + CSS + JS Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>aether's</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #000000;
            --text-primary: #ffffff;
            --text-secondary: #8e8e93;
            --surface-color: #121212;
            --border-color: #333333;
            --button-bg: #ffffff;
            --button-text: #000000;
            --radius-m3: 24px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Roboto', sans-serif;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-primary);
            overflow-x: hidden;
            min-height: 100vh;
        }

        .screen {
            display: none;
            opacity: 0;
            transition: opacity 0.5s ease;
            padding: 24px 16px;
            min-height: 100vh;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }

        .screen.active {
            display: flex;
            opacity: 1;
        }

        /* Double Border Button */
        .btn-double {
            background: var(--button-bg);
            color: var(--button-text);
            border: 1px solid #000000;
            outline: 2px solid #ffffff;
            border-radius: var(--radius-m3);
            padding: 12px 28px;
            font-weight: bold;
            font-size: 14px;
            cursor: pointer;
            transition: transform 0.1s ease;
        }

        .btn-double:active {
            transform: scale(0.96);
        }

        .btn-secondary {
            background: transparent;
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-m3);
            padding: 12px 24px;
            cursor: pointer;
        }

        /* Input Style */
        .m3-input-wrapper {
            position: relative;
            width: 100%;
            max-width: 320px;
            margin: 20px 0;
        }

        .m3-input {
            width: 100%;
            background: #1a1a1a;
            border: 1px solid transparent;
            border-radius: 16px;
            padding: 16px;
            color: #fff;
            outline: none;
            font-size: 16px;
        }

        .m3-input:focus {
            background: #000;
            border: 1px solid #000;
            outline: 1px solid #fff;
        }

        .m3-label {
            position: absolute;
            left: 12px;
            top: -8px;
            background: #000;
            padding: 0 6px;
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: lowercase;
        }

        /* Captcha Box */
        .captcha-card {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-m3);
            padding: 24px;
            width: 100%;
            max-width: 320px;
            text-align: center;
        }

        .captcha-check {
            width: 24px;
            height: 24px;
            border: 2px solid var(--text-secondary);
            border-radius: 6px;
            display: inline-block;
            cursor: pointer;
            margin-top: 12px;
        }

        /* Main Dashboard */
        .header-title {
            font-size: 24px;
            font-weight: bold;
            letter-spacing: -0.5px;
            margin-bottom: 16px;
            text-align: center;
        }

        .tabs {
            display: flex;
            background: var(--surface-color);
            border-radius: 50px;
            padding: 4px;
            margin-bottom: 20px;
            width: 100%;
            max-width: 360px;
        }

        .tab {
            flex: 1;
            text-align: center;
            padding: 10px;
            border-radius: 50px;
            font-size: 14px;
            color: var(--text-secondary);
            cursor: pointer;
        }

        .tab.active {
            background: #ffffff;
            color: #000000;
            font-weight: 500;
        }

        .card {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 18px;
            padding: 16px;
            margin-bottom: 12px;
            width: 100%;
            max-width: 360px;
        }

        .badge-pinned {
            font-size: 10px;
            background: #333;
            color: #fff;
            padding: 2px 8px;
            border-radius: 12px;
            float: right;
        }

        .actions-row {
            display: flex;
            gap: 10px;
            width: 100%;
            max-width: 360px;
            margin-top: 10px;
        }
    </style>
</head>
<body>

    <!-- SCREEN 1: CAPTCHA -->
    <div id="screen-captcha" class="screen active">
        <div class="captcha-card">
            <p style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">aetheris.win Captcha</p>
            <p style="font-size: 12px; color: var(--text-secondary);">Подтвердите, что вы не робот</p>
            <div style="margin-top: 16px; display: flex; align-items: center; justify-content: center; gap: 10px;">
                <div class="captcha-check" onclick="passCaptcha()"></div>
                <span style="font-size: 13px;">Я человек</span>
            </div>
        </div>
    </div>

    <!-- SCREEN 2: WELCOME -->
    <div id="screen-welcome" class="screen">
        <h2 style="font-size: 26px; margin-bottom: 8px;" id="welcome-text">welcome, user</h2>
        <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 32px;">let's start! aether's</p>
        <div style="width: 100%; max-width: 320px; display: flex; justify-content: flex-end;">
            <button class="btn-double" onclick="navTo('screen-invite')">next -></button>
        </div>
    </div>

    <!-- SCREEN 3: INVITE CODE -->
    <div id="screen-invite" class="screen">
        <h3 style="font-size: 20px; margin-bottom: 16px;">do you have invite?</h3>
        <div class="m3-input-wrapper">
            <span class="m3-label">invite code</span>
            <input type="text" id="invite-input" class="m3-input" placeholder="...">
        </div>
        <div style="display: flex; gap: 12px; width: 100%; max-width: 320px; justify-content: flex-end;">
            <button class="btn-secondary" onclick="skipInvite()">skip</button>
            <button class="btn-double" onclick="submitInvite()">confirm</button>
        </div>
    </div>

    <!-- SCREEN 4: MAIN APP -->
    <div id="screen-main" class="screen" style="justify-content: flex-start;">
        <h1 class="header-title">aether's</h1>
        
        <div class="tabs">
            <div class="tab active" onclick="switchTab('forum')">Forum</div>
            <div class="tab" onclick="switchTab('account')">Account</div>
        </div>

        <!-- TAB: FORUM -->
        <div id="tab-forum" style="width: 100%; display: flex; flex-direction: column; align-items: center;">
            <div id="posts-container" style="width: 100%; max-width: 360px;"></div>
            
            <div class="actions-row">
                <button class="btn-secondary" style="flex:1;" onclick="loadMore()">ещё</button>
                <button class="btn-double" style="flex:1;" id="btn-create" onclick="createPost()">create post</button>
            </div>
        </div>

        <!-- TAB: ACCOUNT -->
        <div id="tab-account" style="width: 100%; display: none; flex-direction: column; align-items: center;">
            <div class="card" style="text-align: center;">
                <div id="user-avatar" style="width: 64px; height: 64px; background: #222; border-radius: 50%; margin: 0 auto 12px auto; display: flex; align-items: center; justify-content: center; font-size: 24px;">👤</div>
                <h3 id="acc-name">Name</h3>
                <p id="acc-username" style="color: var(--text-secondary); font-size: 13px;">@username</p>
                <p id="acc-id" style="color: var(--text-secondary); font-size: 11px; margin-top: 4px;">ID: -</p>
            </div>

            <div class="card">
                <p style="font-size: 12px; color: var(--text-secondary);">Invite Status</p>
                <p id="acc-invite-status" style="font-weight: bold; margin-top: 4px;">Not Activated</p>
                <p id="acc-code" style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;"></p>
            </div>
        </div>
    </div>

    <script>
        const tg = window.Telegram?.WebApp;
        if (tg) tg.expand();

        let userData = {
            id: tg?.initDataUnsafe?.user?.id || 123456,
            first_name: tg?.initDataUnsafe?.user?.first_name || 'User',
            username: tg?.initDataUnsafe?.user?.username || 'username',
            is_invited: 0,
            used_code: ''
        };

        document.getElementById('welcome-text').innerText = `welcome, ${userData.first_name.toLowerCase()}`;
        document.getElementById('acc-name').innerText = userData.first_name;
        document.getElementById('acc-username').innerText = `@${userData.username}`;
        document.getElementById('acc-id').innerText = `ID: ${userData.id}`;

        function navTo(screenId) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            setTimeout(() => {
                document.getElementById(screenId).classList.add('active');
            }, 300);
        }

        function passCaptcha() {
            navTo('screen-welcome');
            registerUser();
        }

        async function registerUser() {
            await fetch('/api/user/sync', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(userData)
            });
        }

        async function submitInvite() {
            const code = document.getElementById('invite-input').value.trim();
            if(!code) return navTo('screen-main');
            
            const res = await fetch('/api/invite/use', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userData.id, code: code })
            });
            const data = await res.json();
            if(data.success) {
                userData.is_invited = 1;
                userData.used_code = code;
            } else {
                alert(data.message || "Ошибка кода");
            }
            enterMainApp();
        }

        function skipInvite() {
            enterMainApp();
        }

        function enterMainApp() {
            navTo('screen-main');
            updateAccountUI();
            loadPosts();
        }

        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            if(tab === 'forum') {
                document.querySelectorAll('.tab')[0].classList.add('active');
                document.getElementById('tab-forum').style.display = 'flex';
                document.getElementById('tab-account').style.display = 'none';
            } else {
                document.querySelectorAll('.tab')[1].classList.add('active');
                document.getElementById('tab-forum').style.display = 'none';
                document.getElementById('tab-account').style.display = 'flex';
            }
        }

        function updateAccountUI() {
            const statusEl = document.getElementById('acc-invite-status');
            const codeEl = document.getElementById('acc-code');
            const btnCreate = document.getElementById('btn-create');

            if(userData.is_invited) {
                statusEl.innerText = "Active Access";
                statusEl.style.color = "#ffffff";
                codeEl.innerText = `Used Code: ${userData.used_code}`;
                btnCreate.style.opacity = "1";
                btnCreate.style.pointerEvents = "auto";
            } else {
                statusEl.innerText = "No Invite";
                statusEl.style.color = "var(--text-secondary)";
                btnCreate.style.opacity = "0.4";
                btnCreate.style.pointerEvents = "none";
            }
        }

        async function loadPosts() {
            const res = await fetch('/api/posts');
            const posts = await res.json();
            const container = document.getElementById('posts-container');
            container.innerHTML = '';
            
            posts.forEach(p => {
                container.innerHTML += `
                    <div class="card">
                        ${p.is_pinned ? '<span class="badge-pinned">PINNED</span>' : ''}
                        <p style="font-weight: bold; font-size: 15px;">${p.title}</p>
                        <p style="font-size: 13px; color: var(--text-secondary); margin: 6px 0;">${p.content}</p>
                        <p style="font-size: 10px; color: #555;">by ${p.author_name}</p>
                    </div>
                `;
            });
        }

        async function createPost() {
            if(!userData.is_invited) return;
            const title = prompt("Заголовок поста:");
            const content = prompt("Текст поста:");
            if(title && content) {
                await fetch('/api/posts/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        author_id: userData.id,
                        author_name: userData.first_name,
                        title, content
                    })
                });
                loadPosts();
            }
        }

        function loadMore() {
            loadPosts();
        }
    </script>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/user/sync', methods=['POST'])
def sync_user():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (data['id'], data['username'], data['first_name']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/invite/use', methods=['POST'])
def use_invite():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT is_used FROM invites WHERE code = ?", (data['code'],))
    invite = cur.fetchone()
    
    if invite and invite[0] == 0:
        cur.execute("UPDATE invites SET is_used = 1 WHERE code = ?", (data['code'],))
        cur.execute("UPDATE users SET is_invited = 1, used_code = ? WHERE user_id = ?", (data['code'], data['user_id']))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    
    conn.close()
    return jsonify({"success": False, "message": "Неверный или использованный код"})

@app.route('/api/posts', methods=['GET'])
def get_posts():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT author_name, title, content, is_pinned FROM posts ORDER BY is_pinned DESC, id DESC LIMIT 6")
    rows = cur.fetchall()
    conn.close()
    return jsonify([{"author_name": r[0], "title": r[1], "content": r[2], "is_pinned": r[3]} for r in rows])

@app.route('/api/posts/create', methods=['POST'])
def create_post():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO posts (author_id, author_name, title, content) VALUES (?, ?, ?, ?)",
                (data['author_id'], data['author_name'], data['title'], data['content']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# --- ADMIN PANEL (/invc) ---

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>aether's Admin</title>
    <style>
        body { background: #000; color: #fff; font-family: sans-serif; padding: 20px; }
        .card { background: #111; border: 1px solid #333; padding: 15px; border-radius: 12px; margin-bottom: 12px; }
        button { background: #fff; color: #000; border: none; padding: 8px 16px; border-radius: 8px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <h2>aether's Admin Panel</h2>
    <form action="/invc/generate" method="post" style="margin: 20px 0;">
        <button type="submit">Сгенерировать инвайт</button>
    </form>
    
    <h3>Инвайт коды</h3>
    {% for code in invites %}
        <div class="card">
            Код: <b>{{ code[0] }}</b> | Использован: {{ "Да" if code[1] else "Нет" }}
        </div>
    {% endfor %}

    <h3>Пользователи</h3>
    {% for u in users %}
        <div class="card">
            ID: {{ u[0] }} | Name: {{ u[2] }} (@{{ u[1] }}) | Invited: {{ "YES" if u[3] else "NO" }}
        </div>
    {% endfor %}
</body>
</html>
"""

@app.route('/invc')
def admin_panel():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT code, is_used FROM invites")
    invites = cur.fetchall()
    cur.execute("SELECT user_id, username, first_name, is_invited FROM users")
    users = cur.fetchall()
    conn.close()
    return render_template_string(ADMIN_TEMPLATE, invites=invites, users=users)

@app.route('/invc/generate', methods=['POST'])
def gen_invite():
    code = generate_code()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO invites (code) VALUES (?)", (code,))
    conn.commit()
    conn.close()
    return redirect('/invc')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
