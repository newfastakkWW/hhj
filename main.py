import os
import json
import sqlite3
import random
import string
import telebot
from flask import Flask, render_template_string, request, jsonify, redirect

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

DB_PATH = "/tmp/aether.db" if os.getenv("VERCEL") else "aether.db"
app = Flask(__name__)

# --- БАЗА ДАННЫХ ---
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
            is_used INTEGER DEFAULT 0
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
    return 'AETHER-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# --- HTML / M3 / CSS / JS ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>aether's</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #000000;
            --surface-color: #0d0d0d;
            --surface-variant: #161616;
            --border-color: #262626;
            --border-focus: #ffffff;
            --text-primary: #ffffff;
            --text-secondary: #737373;
            --radius-m3: 20px;
            --radius-btn: 100px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-primary);
            overflow-x: hidden;
            min-height: 100vh;
            display: flex;
            justify-content: center;
        }

        .app-viewport {
            width: 100%;
            max-width: 420px;
            min-height: 100vh;
            position: relative;
            display: flex;
            flex-direction: column;
        }

        /* Screen Transitions */
        .screen {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            min-height: 100vh;
            padding: 32px 20px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            opacity: 0;
            visibility: hidden;
            transform: scale(0.98);
            transition: opacity 0.35s cubic-bezier(0.4, 0, 0.2, 1),
                        transform 0.35s cubic-bezier(0.4, 0, 0.2, 1),
                        visibility 0.35s;
            z-index: 1;
        }

        .screen.active {
            opacity: 1;
            visibility: visible;
            transform: scale(1);
            z-index: 2;
        }

        /* Cloudflare-like Captcha Widget */
        .cf-captcha-wrapper {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 14px 18px;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: space-between;
            user-select: none;
            transition: border-color 0.2s;
        }

        .cf-checkbox-container {
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
        }

        .cf-checkbox {
            width: 22px;
            height: 22px;
            border: 2px solid #404040;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            background: #000;
        }

        .cf-checkbox.loading {
            border-color: #ffffff;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        .cf-checkbox.checked {
            background: #ffffff;
            border-color: #ffffff;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .cf-logo {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            font-size: 10px;
            color: var(--text-secondary);
        }

        /* M3 Input */
        .m3-input-group {
            position: relative;
            width: 100%;
            margin: 24px 0;
        }

        .m3-input {
            width: 100%;
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 18px 16px 10px 16px;
            color: #fff;
            font-size: 15px;
            outline: none;
            transition: all 0.2s ease;
        }

        .m3-input:focus {
            background: #000;
            border-color: #fff;
            box-shadow: 0 0 0 1px #fff;
        }

        .m3-label {
            position: absolute;
            left: 16px;
            top: 6px;
            font-size: 10px;
            color: var(--text-secondary);
            letter-spacing: 0.5px;
            text-transform: uppercase;
            font-weight: 600;
        }

        /* Buttons */
        .btn-double {
            background: #ffffff;
            color: #000000;
            border: 1px solid #000000;
            outline: 2px solid #ffffff;
            border-radius: var(--radius-btn);
            padding: 12px 28px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: transform 0.15s ease, opacity 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .btn-double:active {
            transform: scale(0.95);
        }

        .btn-secondary {
            background: transparent;
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-btn);
            padding: 12px 24px;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .btn-secondary:active {
            background: var(--surface-color);
        }

        /* Main App Tabs */
        .header-brand {
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.5px;
            text-align: center;
            margin-bottom: 20px;
        }

        .tabs-m3 {
            display: flex;
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-btn);
            padding: 4px;
            margin-bottom: 24px;
        }

        .tab-btn {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 10px;
            border-radius: var(--radius-btn);
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.25s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .tab-btn.active {
            background: #ffffff;
            color: #000000;
            font-weight: 600;
        }

        /* Cards & Forum */
        .card-m3 {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-m3);
            padding: 18px;
            margin-bottom: 12px;
            transition: border-color 0.2s;
        }

        .badge-pin {
            font-size: 9px;
            font-weight: 700;
            background: #ffffff;
            color: #000000;
            padding: 2px 6px;
            border-radius: 4px;
            float: right;
            letter-spacing: 0.5px;
        }

        .svg-icon {
            width: 16px;
            height: 16px;
            fill: currentColor;
        }
    </style>
</head>
<body>

    <div class="app-viewport">

        <!-- SCREEN 1: CAPTCHA (No wrappers, ultra-clean) -->
        <div id="screen-captcha" class="screen active">
            <h1 style="font-size: 24px; font-weight: 700; margin-bottom: 6px;">aetheris.win</h1>
            <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 28px;">Verification required to continue</p>

            <div class="cf-captcha-wrapper">
                <div class="cf-checkbox-container" onclick="triggerCaptcha()">
                    <div id="captcha-box" class="cf-checkbox">
                        <svg id="captcha-check-icon" style="display:none; width: 14px; height: 14px; fill: #000;" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                    </div>
                    <span style="font-size: 13px; font-weight: 500;">Verify you are human</span>
                </div>
                <div class="cf-logo">
                    <span style="font-weight: 600; color: #a3a3a3;">Cloudflare</span>
                    <span style="font-size: 8px;">Turnstile</span>
                </div>
            </div>
        </div>

        <!-- SCREEN 2: WELCOME -->
        <div id="screen-welcome" class="screen">
            <h2 style="font-size: 28px; font-weight: 700; margin-bottom: 8px;" id="welcome-text">welcome, user</h2>
            <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 40px;">let's start! aether's</p>
            
            <div style="display: flex; justify-content: flex-end;">
                <button class="btn-double" onclick="navTo('screen-invite')">
                    next
                    <svg class="svg-icon" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
            </div>
        </div>

        <!-- SCREEN 3: INVITE CODE -->
        <div id="screen-invite" class="screen">
            <h3 style="font-size: 22px; font-weight: 600; margin-bottom: 4px;">do you have invite?</h3>
            <p style="color: var(--text-secondary); font-size: 13px;">Enter your key to unlock posting features</p>

            <div class="m3-input-group">
                <span class="m3-label">invite code</span>
                <input type="text" id="invite-input" class="m3-input" placeholder="AETHER-XXXXXX" autocomplete="off">
            </div>

            <div style="display: flex; gap: 12px; justify-content: flex-end;">
                <button class="btn-secondary" onclick="skipInvite()">skip</button>
                <button class="btn-double" onclick="submitInvite()">confirm</button>
            </div>
        </div>

        <!-- SCREEN 4: MAIN APP -->
        <div id="screen-main" class="screen" style="justify-content: flex-start; padding-top: 24px;">
            <div class="header-brand">aether's</div>

            <div class="tabs-m3">
                <button class="tab-btn active" onclick="switchTab('forum', this)">
                    <svg class="svg-icon" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    Forum
                </button>
                <button class="tab-btn" onclick="switchTab('account', this)">
                    <svg class="svg-icon" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                    Account
                </button>
            </div>

            <!-- TAB: FORUM -->
            <div id="tab-forum" style="width: 100%;">
                <div id="posts-container"></div>
                
                <div style="display: flex; gap: 10px; margin-top: 12px;">
                    <button class="btn-secondary" style="flex: 1;" onclick="loadPosts()">ещё</button>
                    <button class="btn-double" style="flex: 1; justify-content: center;" id="btn-create" onclick="createPost()">create post</button>
                </div>
            </div>

            <!-- TAB: ACCOUNT -->
            <div id="tab-account" style="width: 100%; display: none;">
                <div class="card-m3" style="text-align: center; padding: 24px 16px;">
                    <div style="width: 56px; height: 56px; background: #1a1a1a; border: 1px solid var(--border-color); border-radius: 50%; margin: 0 auto 12px auto; display: flex; align-items: center; justify-content: center;">
                        <svg class="svg-icon" style="width:24px; height:24px; fill:var(--text-secondary)" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                    </div>
                    <h3 id="acc-name" style="font-size: 16px; font-weight: 600;">Name</h3>
                    <p id="acc-username" style="color: var(--text-secondary); font-size: 13px;">@username</p>
                    <p id="acc-id" style="color: #404040; font-size: 11px; margin-top: 4px;">ID: -</p>
                </div>

                <div class="card-m3">
                    <p style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Invite Status</p>
                    <p id="acc-invite-status" style="font-size: 15px; font-weight: 600; margin-top: 6px;">Not Activated</p>
                    <p id="acc-code" style="font-size: 12px; color: var(--text-secondary); margin-top: 6px;"></p>
                </div>
            </div>
        </div>

    </div>

    <script>
        const tg = window.Telegram?.WebApp;
        if (tg) {
            tg.expand();
            tg.ready();
        }

        let isVerified = false;
        let userData = {
            id: tg?.initDataUnsafe?.user?.id || 999999,
            first_name: tg?.initDataUnsafe?.user?.first_name || 'Guest',
            username: tg?.initDataUnsafe?.user?.username || 'guest',
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
            }, 150);
        }

        function triggerCaptcha() {
            if (isVerified) return;
            const box = document.getElementById('captcha-box');
            const icon = document.getElementById('captcha-check-icon');
            
            box.classList.add('loading');
            
            setTimeout(() => {
                box.classList.remove('loading');
                box.classList.add('checked');
                icon.style.display = 'block';
                isVerified = true;
                
                registerUser();
                setTimeout(() => navTo('screen-welcome'), 600);
            }, 1000);
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
            if(!code) return enterMainApp();
            
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
                alert(data.message || "Invalid invite code");
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

        function switchTab(tab, btn) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            if(tab === 'forum') {
                document.getElementById('tab-forum').style.display = 'block';
                document.getElementById('tab-account').style.display = 'none';
            } else {
                document.getElementById('tab-forum').style.display = 'none';
                document.getElementById('tab-account').style.display = 'block';
            }
        }

        function updateAccountUI() {
            const statusEl = document.getElementById('acc-invite-status');
            const codeEl = document.getElementById('acc-code');
            const btnCreate = document.getElementById('btn-create');

            if(userData.is_invited) {
                statusEl.innerText = "Invited Access";
                statusEl.style.color = "#ffffff";
                codeEl.innerText = `Key: ${userData.used_code}`;
                btnCreate.style.opacity = "1";
                btnCreate.style.pointerEvents = "auto";
            } else {
                statusEl.innerText = "Standard Access";
                statusEl.style.color = "var(--text-secondary)";
                btnCreate.style.opacity = "0.3";
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
                    <div class="card-m3">
                        ${p.is_pinned ? '<span class="badge-pin">PIN</span>' : ''}
                        <p style="font-weight: 600; font-size: 15px; margin-bottom: 4px;">${p.title}</p>
                        <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.4;">${p.content}</p>
                        <p style="font-size: 10px; color: #404040; margin-top: 10px;">by ${p.author_name}</p>
                    </div>
                `;
            });
        }

        async function createPost() {
            if(!userData.is_invited) return;
            const title = prompt("Заголовок:");
            const content = prompt("Текст:");
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
    </script>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>aether's Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #000; color: #fff; font-family: monospace; padding: 20px; }
        .card { background: #111; border: 1px solid #222; padding: 12px; border-radius: 8px; margin-bottom: 8px; font-size: 13px; }
        button { background: #fff; color: #000; border: none; padding: 10px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <h2>aether's Admin Panel (/inv)</h2>
    <form action="/inv/generate" method="post" style="margin: 20px 0;">
        <button type="submit">+ Create Invite Code</button>
    </form>
    
    <h3>Invites</h3>
    {% for code in invites %}
        <div class="card">
            Code: <b>{{ code[0] }}</b> | Used: {{ "YES" if code[1] else "NO" }}
        </div>
    {% endfor %}

    <h3>Users</h3>
    {% for u in users %}
        <div class="card">
            ID: {{ u[0] }} | Name: {{ u[2] }} (@{{ u[1] }}) | Invited: {{ "YES" if u[3] else "NO" }}
        </div>
    {% endfor %}
</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'ok', 200
    return 'error', 400

# Фикс команды /start и кнопки WebApp
@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = telebot.types.InlineKeyboardMarkup()
    # Берем динамический хост Vercel
    app_url = request.host_url
    web_app_info = telebot.types.WebAppInfo(url=app_url)
    btn = telebot.types.InlineKeyboardButton(text="Open aether's App", web_app=web_app_info)
    markup.add(btn)
    
    bot.send_message(
        message.chat.id, 
        "Welcome to aether's. Click below to launch:", 
        reply_markup=markup
    )

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
    return jsonify({"success": False, "message": "Invalid code"})

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

# --- АДМИНКА ПО АДРЕСУ /inv ---

@app.route('/inv')
def admin_panel():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT code, is_used FROM invites")
    invites = cur.fetchall()
    cur.execute("SELECT user_id, username, first_name, is_invited FROM users")
    users = cur.fetchall()
    conn.close()
    return render_template_string(ADMIN_TEMPLATE, invites=invites, users=users)

@app.route('/inv/generate', methods=['POST'])
def gen_invite():
    code = generate_code()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO invites (code) VALUES (?)", (code,))
    conn.commit()
    conn.close()
    return redirect('/inv')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
