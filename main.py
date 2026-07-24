import os
import sqlite3
import random
import string
import telebot
import threading
from flask import Flask, render_template_string, request, jsonify

# Укажи здесь токен своего бота!
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

DB_PATH = "aether.db"
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
            avatar_url TEXT DEFAULT '',
            is_invited INTEGER DEFAULT 0,
            used_code TEXT DEFAULT '',
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT DEFAULT '',
            ban_until TEXT DEFAULT '',
            prefix TEXT DEFAULT 'USER',
            prefix_color TEXT DEFAULT '#888888',
            aliases TEXT DEFAULT '',
            bg_color TEXT DEFAULT '#0a0a0a',
            bg_emoji TEXT DEFAULT '',
            bg_emoji_speed TEXT DEFAULT 'normal',
            avatar_frame TEXT DEFAULT 'none',
            nickname_color TEXT DEFAULT '#ffffff',
            status_badge TEXT DEFAULT '',
            status_type TEXT DEFAULT 'emoji'
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
            title TEXT,
            content TEXT,
            image_url TEXT DEFAULT '',
            allow_comments INTEGER DEFAULT 1,
            is_pinned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            author_id INTEGER,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def generate_code(length=8):
    return 'AETHER-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# --- TELEGRAM BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "Welcome to aether's! Open the Web App to join the forum.")

@bot.message_handler(commands=['inv'])
def inv_cmd(message):
    # Команда для генерации инвайт-кода
    code = generate_code()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO invites (code) VALUES (?)", (code,))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"Новый инвайт-код сгенерирован:\n`{code}`\n\nОтправьте его пользователю для доступа.", parse_mode="Markdown")

# Запуск бота в отдельном потоке
def run_bot():
    print("Bot is polling...")
    bot.polling(none_stop=True)

threading.Thread(target=run_bot, daemon=True).start()


# --- HTML / CSS / JS ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>aether's</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,1,0" />
    <style>
        :root {
            --bg: #000000;
            --surface: #0a0a0a;
            --surface-variant: #141414;
            --border: #222222;
            --text: #ffffff;
            --text-sub: #888888;
            --primary: #ffffff;
            --m3-easing: cubic-bezier(0.2, 0, 0, 1);
            /* Учитываем отступы Telegram Mini App сверху, чтобы не перекрывалось шапкой */
            --tg-top-inset: var(--tg-content-safe-area-inset-top, env(safe-area-inset-top, 24px));
        }

        * {
            box-sizing: border-box; margin: 0; padding: 0;
            font-family: 'Inter', sans-serif;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background-color: var(--bg); color: var(--text);
            overflow: hidden;
        }

        /* --- АНИМАЦИИ --- */
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes fadeOut { from { opacity: 1; } to { opacity: 0; } }
        @keyframes slideInUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        
        .anim-fade { animation: fadeIn 0.3s var(--m3-easing) forwards; }
        .anim-slide-up { animation: slideInUp 0.4s var(--m3-easing) forwards; }

        /* --- СТАРТОВЫЕ ЭКРАНЫ (ONBOARDING) --- */
        #onboarding-screen {
            position: fixed; inset: 0; background: #000; z-index: 9999;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            transition: opacity 0.4s ease; padding: 24px; text-align: left;
        }
        #onboarding-screen.hidden { opacity: 0; pointer-events: none; }
        
        .onboarding-step {
            display: none; flex-direction: column; align-items: flex-start; justify-content: center;
            width: 100%; max-width: 400px;
        }
        .onboarding-step.active { display: flex; animation: fadeIn 0.4s ease forwards; }

        .btn-outline {
            background: transparent; color: var(--text); border: 1px solid var(--text);
            border-radius: 100px; padding: 12px 24px; font-size: 16px; font-weight: 500;
            cursor: pointer; transition: 0.2s; align-self: flex-end;
        }
        .btn-outline:active { background: #222; }

        /* Экран блокировки (Бан) */
        #banned-screen {
            position: fixed; inset: 0; background: #000; z-index: 9998; display: none;
            flex-direction: column; align-items: center; justify-content: center; padding: 24px; text-align: center;
        }

        /* Viewport */
        .viewport {
            position: relative; width: 100vw; height: 100vh; overflow: hidden;
        }

        .page {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: var(--bg); overflow-y: auto;
            transform: translateX(100%); transition: transform 0.35s var(--m3-easing);
            z-index: 10; display: flex; flex-direction: column;
        }
        
        .page.active { transform: translateX(0); z-index: 20; }
        .page.base { transform: translateX(0); z-index: 1; }
        .page.dimmed { transform: translateX(-20%); opacity: 0.5; filter: blur(4px); transition: 0.35s; }

        /* Top Bar с учетом Safe Area */
        .top-bar {
            position: sticky; top: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(16px);
            padding: calc(16px + var(--tg-top-inset)) 20px 16px 20px; 
            display: flex; align-items: center; gap: 16px; z-index: 100;
            border-bottom: 1px solid var(--border);
        }
        .top-bar .title { font-size: 20px; font-weight: 700; flex: 1; }
        .icon-btn {
            background: none; border: none; color: var(--text); cursor: pointer;
            display: flex; align-items: center; justify-content: center;
        }

        /* Feed */
        .feed-container { padding: 16px; padding-bottom: 90px; }
        .post-card {
            background: var(--surface); border: 1px solid var(--border); border-radius: 20px;
            padding: 20px; margin-bottom: 16px; cursor: pointer;
            transition: transform 0.1s var(--m3-easing), border-color 0.2s;
        }
        .post-card:active { transform: scale(0.98); border-color: #444; }
        .post-card h2 { font-size: 24px; font-weight: 700; line-height: 1.2; margin-bottom: 8px; letter-spacing: -0.5px; }
        .post-card p {
            color: var(--text-sub); font-size: 15px; line-height: 1.4;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
            margin-bottom: 16px;
        }
        
        .author-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .avatar-container { position: relative; width: 32px; height: 32px; }
        .avatar { width: 100%; height: 100%; border-radius: 50%; background: #222; object-fit: cover; }
        
        .frame-neon { box-shadow: 0 0 10px #fff, inset 0 0 5px #fff; border: 2px solid #fff; }
        .frame-gold { box-shadow: 0 0 12px #ffd700; border: 2px solid #ffd700; }
        .frame-fire { box-shadow: 0 0 12px #ff4500; border: 2px solid #ff4500; }

        .author-name { font-size: 14px; font-weight: 600; color: var(--text); display: flex; align-items: center; gap: 4px; }
        .badge { font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 6px; text-transform: uppercase; }

        /* Post Content */
        .post-content-area { padding: 20px; flex: 1; }
        .post-content-area h1 { font-size: 32px; font-weight: 700; line-height: 1.1; margin-bottom: 16px; letter-spacing: -1px; }
        .post-text { font-size: 16px; line-height: 1.6; color: #ddd; white-space: pre-wrap; margin-bottom: 24px; }
        .post-image { width: 100%; border-radius: 16px; margin-bottom: 24px; border: 1px solid var(--border); }
        
        /* Comments */
        .comments-section { border-top: 1px solid var(--border); padding-top: 24px; }
        .comment-item { display: flex; gap: 12px; margin-bottom: 20px; }
        .comment-bubble { background: var(--surface-variant); padding: 12px 16px; border-radius: 4px 16px 16px 16px; flex: 1; }
        .comment-author { font-size: 13px; font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 8px; }
        .comment-text { font-size: 14px; line-height: 1.5; color: #ccc; }

        /* Inputs & FAB */
        .input-m3 {
            width: 100%; background: var(--surface-variant); border: 1px solid var(--border);
            border-radius: 16px; padding: 16px; color: #fff; font-size: 15px; outline: none; margin-bottom: 16px;
        }
        .input-m3:focus { border-color: var(--primary); }
        
        .fab {
            position: fixed; bottom: 24px; right: 24px; width: 60px; height: 60px;
            background: var(--primary); color: #000; border-radius: 16px;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 8px 24px rgba(255,255,255,0.15); z-index: 50; cursor: pointer;
        }

        .m3-switch-container {
            display: flex; justify-content: space-between; align-items: center;
            background: var(--surface); padding: 16px; border-radius: 16px; border: 1px solid var(--border); margin-bottom: 24px;
        }
        .m3-switch {
            position: relative; width: 52px; height: 32px; appearance: none;
            background: var(--border); border-radius: 100px; outline: none; cursor: pointer; transition: background 0.3s;
        }
        .m3-switch::after {
            content: ''; position: absolute; top: 4px; left: 4px; width: 24px; height: 24px;
            background: #888; border-radius: 50%; transition: 0.3s var(--m3-easing);
        }
        .m3-switch:checked { background: var(--primary); }
        .m3-switch:checked::after { transform: translateX(20px); background: #000; }

        /* Profile Styles */
        .profile-header { text-align: center; padding: 30px 20px 20px; position: relative; }
        .profile-avatar-large { width: 90px; height: 90px; border-radius: 50%; object-fit: cover; margin-bottom: 12px; background: #222; }
        .profile-name { font-size: 24px; font-weight: 700; display: flex; justify-content: center; align-items: center; gap: 8px; }
        .profile-box { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 16px; margin: 0 20px 16px; }

        .btn-primary {
            background: var(--primary); color: #000; border: none; border-radius: 100px;
            padding: 16px; font-size: 16px; font-weight: 600; width: 100%; cursor: pointer;
        }
        .banned-text { color: #ff5252; font-style: italic; }

        .bg-emoji-layer {
            position: fixed; inset: 0; pointer-events: none; z-index: -1; overflow: hidden; opacity: 0.15;
        }
        .floating-emoji {
            position: absolute; font-size: 24px; animation: floatUp linear infinite;
        }
        @keyframes floatUp {
            0% { transform: translateY(110vh) rotate(0deg); }
            100% { transform: translateY(-10vh) rotate(360deg); }
        }
    </style>
</head>
<body>

    <div id="onboarding-screen">
        
        <div id="step-welcome" class="onboarding-step active">
            <h1 style="font-size: 32px; font-weight: 700; margin-bottom: 8px;">welcome, <span id="welcome-name">guest</span></h1>
            <p style="color: var(--text-sub); margin-bottom: 32px;">let's start! aether's</p>
            <button class="btn-outline" onclick="goToStep('step-captcha')">next ➔</button>
        </div>

        <div id="step-captcha" class="onboarding-step">
            <h2 style="font-size: 24px; font-weight: 700; margin-bottom: 8px;">Human check</h2>
            <p style="color: var(--text-sub); margin-bottom: 24px;">Solve: <span id="captcha-expression" style="color:#fff; font-weight:bold;"></span></p>
            <input type="number" id="captcha-input" class="input-m3" placeholder="Answer..." style="margin-bottom: 24px;">
            <button class="btn-outline" onclick="verifyCaptcha()">verify ➔</button>
        </div>

        <div id="step-invite" class="onboarding-step">
            <h2 style="font-size: 24px; font-weight: 700; margin-bottom: 8px;">Got an invite?</h2>
            <p style="color: var(--text-sub); margin-bottom: 24px;">Enter your code to unlock all features.</p>
            <input type="text" id="start-invite-input" class="input-m3" placeholder="AETHER-XXXXX" style="margin-bottom: 24px;">
            <div style="display: flex; gap: 12px; width: 100%;">
                <button class="btn-outline" style="flex: 1; text-align: center; padding: 12px;" onclick="finishOnboarding()">skip</button>
                <button class="btn-primary" style="flex: 1; padding: 12px;" onclick="confirmStartInvite()">confirm</button>
            </div>
        </div>

    </div>

    <div id="banned-screen">
        <span class="material-symbols-rounded" style="font-size: 64px; color: #ff5252; margin-bottom: 16px;">block</span>
        <h2 style="font-size: 24px; font-weight: 700; margin-bottom: 8px;">Access Restricted</h2>
        <p id="ban-reason-text" style="color: var(--text-sub); margin-bottom: 8px; font-size: 15px;"></p>
        <p id="ban-until-text" style="color: #ff5252; font-size: 13px;"></p>
    </div>

    <div class="bg-emoji-layer" id="bg-emoji-layer"></div>

    <div class="viewport">
        <div id="page-feed" class="page base">
            <div class="top-bar">
                <span class="title">aether's</span>
                <div class="icon-btn" onclick="openSearch()"><span class="material-symbols-rounded">search</span></div>
                <div class="icon-btn" onclick="openMyProfile()"><span class="material-symbols-rounded">account_circle</span></div>
            </div>
            
            <div style="padding: 16px 16px 0 16px; display: none;" id="search-box">
                <input type="text" id="search-input" class="input-m3" placeholder="Search topics..." oninput="loadFeed()">
            </div>

            <div class="feed-container" id="feed-list"></div>
            
            <div class="fab" onclick="openCreatePost()"><span class="material-symbols-rounded">edit</span></div>
        </div>

        <div id="page-post" class="page">
            <div class="top-bar">
                <div class="icon-btn" onclick="closePage('page-post')"><span class="material-symbols-rounded">arrow_back</span></div>
                <span class="title">Thread</span>
            </div>
            <div class="post-content-area">
                <h1 id="view-title">Loading...</h1>
                <div class="author-row" style="margin-bottom: 24px; cursor: pointer;" id="view-author-trigger">
                    <div class="avatar-container" id="view-avatar-wrap"><img id="view-avatar" class="avatar" src=""></div>
                    <span id="view-author" class="author-name">...</span>
                    <span id="view-badge" class="badge"></span>
                </div>
                
                <img id="view-image" class="post-image" src="" style="display: none;">
                <div id="view-content" class="post-text"></div>
                
                <div class="comments-section">
                    <h3 style="margin-bottom: 16px; font-size: 18px;">Comments</h3>
                    <div id="comments-list"></div>
                    
                    <div id="comment-input-area" style="display: flex; gap: 8px; margin-top: 16px;">
                        <input type="text" id="comment-input" class="input-m3" style="margin-bottom: 0;" placeholder="Add a comment...">
                        <button class="btn-primary" style="width: auto; padding: 0 20px;" onclick="sendComment()">
                            <span class="material-symbols-rounded">send</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <div id="page-create" class="page">
            <div class="top-bar">
                <div class="icon-btn" onclick="closePage('page-create')"><span class="material-symbols-rounded">close</span></div>
                <span class="title">New Post</span>
            </div>
            <div class="post-content-area">
                <input type="text" id="create-title" class="input-m3" placeholder="Title (Huge)">
                <textarea id="create-content" class="input-m3" placeholder="Write your text here..." rows="6" style="resize: none;"></textarea>
                <input type="text" id="create-img" class="input-m3" placeholder="Image URL (optional)">
                
                <div class="m3-switch-container">
                    <div>
                        <div style="font-size: 15px; font-weight: 600;">Allow Comments</div>
                        <div style="font-size: 12px; color: var(--text-sub);">For all users</div>
                    </div>
                    <input type="checkbox" id="create-allow-comments" class="m3-switch" checked>
                </div>
                
                <button class="btn-primary" onclick="submitPost()">Publish Thread</button>
            </div>
        </div>

        <div id="page-profile" class="page">
            <div class="top-bar">
                <div class="icon-btn" onclick="closePage('page-profile')"><span class="material-symbols-rounded">arrow_back</span></div>
                <span class="title">Profile</span>
                <div class="icon-btn" id="edit-profile-btn" style="display: none;" onclick="openEditProfile()"><span class="material-symbols-rounded">edit</span></div>
            </div>
            
            <div class="profile-header">
                <div class="avatar-container" style="width: 90px; height: 90px; margin: 0 auto 12px;" id="prof-avatar-wrap">
                    <img id="prof-avatar" class="profile-avatar-large" src="" style="width:100%; height:100%;">
                </div>
                <div class="profile-name">
                    <span id="prof-name">Name</span>
                    <span id="prof-badge" class="badge"></span>
                    <span id="prof-status-view"></span>
                </div>
                <div style="color: var(--text-sub); margin-top: 8px;" id="prof-username">@username</div>
            </div>
            
            <div class="profile-box">
                <div style="font-size: 12px; color: var(--text-sub); margin-bottom: 4px;">User ID</div>
                <div id="prof-id" style="font-size: 15px; font-family: monospace; margin-bottom: 16px;">-</div>
                
                <div style="font-size: 12px; color: var(--text-sub); margin-bottom: 4px;">Also known as</div>
                <div id="prof-aliases" style="font-size: 15px; color: #fff;">None</div>
            </div>
            
            <div id="invite-section" class="profile-box" style="display: none;">
                <div style="font-size: 12px; color: var(--text-sub); margin-bottom: 8px;">Activate Invite Code</div>
                <input type="text" id="invite-code-input" class="input-m3" style="padding: 10px; margin-bottom: 10px;" placeholder="AETHER-XXXXX">
                <button class="btn-primary" style="padding: 10px;" onclick="useInvite('invite-code-input')">Activate</button>
            </div>
        </div>

        <div id="page-edit-profile" class="page">
            <div class="top-bar">
                <div class="icon-btn" onclick="closePage('page-edit-profile')"><span class="material-symbols-rounded">arrow_back</span></div>
                <span class="title">Customize</span>
            </div>
            <div class="post-content-area">
                <label style="font-size: 13px; color: var(--text-sub);">Background Color (HEX)</label>
                <input type="text" id="edit-bg-color" class="input-m3" placeholder="#0a0a0a">
                
                <label style="font-size: 13px; color: var(--text-sub);">Background Emoji</label>
                <input type="text" id="edit-bg-emoji" class="input-m3" placeholder="🔥">
                
                <label style="font-size: 13px; color: var(--text-sub);">Avatar Frame</label>
                <select id="edit-avatar-frame" class="input-m3">
                    <option value="none">None</option>
                    <option value="neon">Neon White</option>
                    <option value="gold">Gold</option>
                    <option value="fire">Fire</option>
                </select>

                <label style="font-size: 13px; color: var(--text-sub);">Nickname Color (HEX)</label>
                <input type="text" id="edit-nick-color" class="input-m3" placeholder="#ffffff">

                <label style="font-size: 13px; color: var(--text-sub);">Status Icon / GIF (URL or Emoji)</label>
                <input type="text" id="edit-status" class="input-m3" placeholder="⚡ or https://...">

                <button class="btn-primary" onclick="saveCustomization()">Save Changes</button>
            </div>
        </div>
    </div>

    <script>
        const tg = window.Telegram?.WebApp;
        if(tg) { tg.expand(); tg.ready(); }

        let currentUser = {
            id: tg?.initDataUnsafe?.user?.id || Math.floor(Math.random()*1000000),
            first_name: tg?.initDataUnsafe?.user?.first_name || 'Guest',
            username: tg?.initDataUnsafe?.user?.username || 'guest',
            avatar_url: tg?.initDataUnsafe?.user?.photo_url || '',
            is_invited: 0
        };

        // Устанавливаем имя в приветствии
        document.getElementById('welcome-name').innerText = currentUser.first_name.toLowerCase();

        // --- ЛОКАЛЬНАЯ БАЗА (LocalStorage) ---
        function getLocalCache(key, defaultVal) {
            const val = localStorage.getItem('aether_' + key);
            return val ? JSON.parse(val) : defaultVal;
        }
        function setLocalCache(key, val) {
            localStorage.setItem('aether_' + key, JSON.stringify(val));
        }

        // --- ONBOARDING ЛОГИКА ---
        let captchaAnswer = 0;
        function generateCaptcha() {
            const num1 = Math.floor(Math.random() * 10) + 1;
            const num2 = Math.floor(Math.random() * 10) + 1;
            captchaAnswer = num1 + num2;
            document.getElementById('captcha-expression').innerText = `${num1} + ${num2} = ?`;
        }

        function goToStep(stepId) {
            document.querySelectorAll('.onboarding-step').forEach(el => {
                el.classList.remove('active');
            });
            if(stepId === 'step-captcha') generateCaptcha();
            document.getElementById(stepId).classList.add('active');
        }

        function verifyCaptcha() {
            const val = parseInt(document.getElementById('captcha-input').value);
            if (val === captchaAnswer) {
                // Если пользователь уже был зареган и инвайтнут (проверяем кэш), можно сразу пропустить
                const cached = getLocalCache('user', null);
                if(cached && cached.is_invited) {
                    finishOnboarding();
                } else {
                    goToStep('step-invite');
                }
            } else {
                tg?.showAlert("Wrong answer, try again.");
                generateCaptcha();
                document.getElementById('captcha-input').value = '';
            }
        }

        async function confirmStartInvite() {
            const code = document.getElementById('start-invite-input').value.trim();
            if(!code) return;
            const success = await processInviteCode(code);
            if (success) {
                finishOnboarding();
            }
        }

        function finishOnboarding() {
            document.getElementById('onboarding-screen').classList.add('hidden');
            initApp();
        }


        // --- ОСНОВНОЕ ПРИЛОЖЕНИЕ ---
        let currentActivePostId = null;

        function openPage(pageId, anim = 'anim-slide-up') {
            document.getElementById('page-feed').classList.add('dimmed');
            const page = document.getElementById(pageId);
            page.style.display = 'flex';
            page.className = 'page active ' + anim;
        }

        function closePage(pageId) {
            document.getElementById('page-feed').classList.remove('dimmed');
            const page = document.getElementById(pageId);
            page.classList.remove('active');
            setTimeout(() => { if(!page.classList.contains('active')) page.style.display = 'none'; }, 350);
        }
        
        function openSearch() {
            const sb = document.getElementById('search-box');
            sb.style.display = sb.style.display === 'none' ? 'block' : 'none';
        }

        async function initApp() {
            try {
                const res = await fetch('/api/user/sync', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(currentUser)
                });
                const data = await res.json();
                currentUser = data.user;
                setLocalCache('user', currentUser);
            } catch(e) {
                currentUser = getLocalCache('user', currentUser);
            }

            if(currentUser.is_banned) {
                document.getElementById('banned-screen').style.display = 'flex';
                document.getElementById('ban-reason-text').innerText = "Reason: " + (currentUser.ban_reason || "Violation of rules");
                document.getElementById('ban-until-text').innerText = currentUser.ban_until ? ("Until: " + currentUser.ban_until) : "Permanent Ban";
                return;
            }

            applyUserTheme(currentUser);
            loadFeed();
        }

        function applyUserTheme(u) {
            if(u.bg_color) document.documentElement.style.setProperty('--bg', u.bg_color);
            if(u.bg_emoji) {
                const layer = document.getElementById('bg-emoji-layer');
                layer.innerHTML = '';
                for(let i=0; i<15; i++) {
                    const span = document.createElement('span');
                    span.className = 'floating-emoji';
                    span.innerText = u.bg_emoji;
                    span.style.left = Math.random() * 100 + '%';
                    span.style.top = Math.random() * 100 + '%';
                    span.style.animationDuration = (5 + Math.random() * 10) + 's';
                    layer.appendChild(span);
                }
            }
        }

        function getAvatarHTML(u, customClass = '') {
            const ava = u.avatar_url || 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" fill="%23555" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>';
            let frameClass = '';
            if(u.avatar_frame === 'neon') frameClass = 'frame-neon';
            if(u.avatar_frame === 'gold') frameClass = 'frame-gold';
            if(u.avatar_frame === 'fire') frameClass = 'frame-fire';

            return `<div class="avatar-container"><img class="avatar ${frameClass} ${customClass}" src="${ava}"></div>`;
        }

        function getStatusHTML(u) {
            if(!u.status_badge) return '';
            if(u.status_badge.startsWith('http')) {
                return `<img src="${u.status_badge}" style="width: 16px; height: 16px; object-fit: contain; vertical-align: middle;">`;
            }
            return `<span style="font-size: 14px;">${u.status_badge}</span>`;
        }

        async function loadFeed() {
            const q = document.getElementById('search-input')?.value.trim() || '';
            let posts = [];
            try {
                const res = await fetch(`/api/posts?q=${encodeURIComponent(q)}`);
                posts = await res.json();
                setLocalCache('posts', posts);
            } catch(e) {
                posts = getLocalCache('posts', []);
            }
            
            const list = document.getElementById('feed-list');
            list.innerHTML = '';
            
            posts.forEach(p => {
                const authorName = p.is_banned ? '<span class="banned-text">Account not found</span>' : p.author_name;
                const nickColor = p.nickname_color || '#fff';
                const badge = (!p.is_banned && p.prefix) ? `<span class="badge" style="background: ${p.prefix_color}; color: #000;">${p.prefix}</span>` : '';
                const pin = p.is_pinned ? `<span class="material-symbols-rounded" style="font-size: 16px; float: right; color: var(--text-sub);">push_pin</span>` : '';
                const status = (!p.is_banned) ? getStatusHTML(p) : '';

                list.innerHTML += `
                    <div class="post-card anim-fade" onclick="viewPost(${p.id})">
                        ${pin}
                        <h2>${p.title}</h2>
                        <p>${p.content}</p>
                        <div class="author-row">
                            ${getAvatarHTML(p)}
                            <span class="author-name" style="color: ${nickColor};">${authorName} ${status}</span>
                            ${badge}
                        </div>
                    </div>
                `;
            });
        }

        async function viewPost(id) {
            currentActivePostId = id;
            let data = {};
            try {
                const res = await fetch(`/api/posts/${id}`);
                data = await res.json();
            } catch(e) {
                return;
            }
            const p = data.post;
            
            document.getElementById('view-title').innerText = p.title;
            document.getElementById('view-content').innerText = p.content;
            
            const img = document.getElementById('view-image');
            if(p.image_url) { img.src = p.image_url; img.style.display = 'block'; }
            else { img.style.display = 'none'; }

            const aName = p.is_banned ? 'Account not found' : p.author_name;
            document.getElementById('view-author').innerText = aName;
            document.getElementById('view-author').style.color = p.nickname_color || '#fff';
            if(p.is_banned) document.getElementById('view-author').classList.add('banned-text');
            else document.getElementById('view-author').classList.remove('banned-text');

            document.getElementById('view-avatar-wrap').innerHTML = getAvatarHTML(p);
            
            const badgeEl = document.getElementById('view-badge');
            if(!p.is_banned && p.prefix) {
                badgeEl.innerText = p.prefix + ' ' + getStatusHTML(p);
                badgeEl.style.background = p.prefix_color;
                badgeEl.style.color = '#000';
                badgeEl.style.display = 'inline-block';
            } else {
                badgeEl.style.display = 'none';
            }

            document.getElementById('view-author-trigger').onclick = () => {
                if(!p.is_banned) openProfile(p.author_id);
            };

            const cList = document.getElementById('comments-list');
            cList.innerHTML = '';
            data.comments.forEach(c => {
                const cName = c.is_banned ? '<span class="banned-text">Account not found</span>' : c.author_name;
                const cBadge = (!c.is_banned && c.prefix) ? `<span class="badge" style="background: ${c.prefix_color}; color: #000; font-size: 8px;">${c.prefix}</span>` : '';
                const cStatus = (!c.is_banned) ? getStatusHTML(c) : '';

                cList.innerHTML += `
                    <div class="comment-item">
                        <div onclick="${c.is_banned ? '' : `openProfile(${c.author_id})`}" style="cursor:pointer;">${getAvatarHTML(c)}</div>
                        <div class="comment-bubble">
                            <div class="comment-author" style="cursor:pointer; color:${c.nickname_color || '#fff'};" onclick="${c.is_banned ? '' : `openProfile(${c.author_id})`}">
                                ${cName} ${cStatus} ${cBadge}
                            </div>
                            <div class="comment-text">${c.content}</div>
                        </div>
                    </div>
                `;
            });

            document.getElementById('comment-input-area').style.display = (currentUser.is_invited || p.allow_comments) ? 'flex' : 'none';

            openPage('page-post');
        }

        function openCreatePost() {
            if(!currentUser.is_invited) {
                tg?.showAlert("Posting is limited to verified/invited users.");
                return;
            }
            openPage('page-create');
        }

        async function submitPost() {
            const title = document.getElementById('create-title').value.trim();
            const content = document.getElementById('create-content').value.trim();
            const img = document.getElementById('create-img').value.trim();
            const allow_comments = document.getElementById('create-allow-comments').checked ? 1 : 0;

            if(!title || !content) return;

            await fetch('/api/posts/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    author_id: currentUser.id, title, content, image_url: img, allow_comments
                })
            });

            document.getElementById('create-title').value = '';
            document.getElementById('create-content').value = '';
            document.getElementById('create-img').value = '';
            closePage('page-create');
            loadFeed();
        }

        async function sendComment() {
            const inp = document.getElementById('comment-input');
            const val = inp.value.trim();
            if(!val) return;

            await fetch(`/api/posts/${currentActivePostId}/comment`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ author_id: currentUser.id, content: val })
            });

            inp.value = '';
            viewPost(currentActivePostId);
        }

        function openMyProfile() {
            openProfile(currentUser.id, true);
        }

        async function openProfile(userId, isMe = false) {
            let u = currentUser;
            if(!isMe) {
                const res = await fetch(`/api/user/${userId}`);
                const data = await res.json();
                if(data.error) return;
                u = data.user;
            }

            document.getElementById('prof-name').innerText = u.first_name;
            document.getElementById('prof-name').style.color = u.nickname_color || '#fff';
            document.getElementById('prof-username').innerText = u.aliases ? u.aliases.split(',').map(a => `@${a.trim()}`).join(', ') : `@${u.username}`;
            document.getElementById('prof-id').innerText = u.user_id;
            
            document.getElementById('prof-avatar-wrap').innerHTML = getAvatarHTML(u, 'profile-avatar-large');
            document.getElementById('prof-status-view').innerHTML = getStatusHTML(u);

            const badgeEl = document.getElementById('prof-badge');
            if(u.prefix) {
                badgeEl.innerText = u.prefix;
                badgeEl.style.background = u.prefix_color;
                badgeEl.style.color = '#000';
                badgeEl.style.display = 'inline-block';
            } else {
                badgeEl.style.display = 'none';
            }

            document.getElementById('edit-profile-btn').style.display = (isMe && u.is_invited) ? 'flex' : 'none';
            document.getElementById('invite-section').style.display = (isMe && !u.is_invited) ? 'block' : 'none';

            openPage('page-profile');
        }

        function openEditProfile() {
            document.getElementById('edit-bg-color').value = currentUser.bg_color || '#0a0a0a';
            document.getElementById('edit-bg-emoji').value = currentUser.bg_emoji || '';
            document.getElementById('edit-avatar-frame').value = currentUser.avatar_frame || 'none';
            document.getElementById('edit-nick-color').value = currentUser.nickname_color || '#ffffff';
            document.getElementById('edit-status').value = currentUser.status_badge || '';
            openPage('page-edit-profile');
        }

        async function saveCustomization() {
            currentUser.bg_color = document.getElementById('edit-bg-color').value.trim();
            currentUser.bg_emoji = document.getElementById('edit-bg-emoji').value.trim();
            currentUser.avatar_frame = document.getElementById('edit-avatar-frame').value;
            currentUser.nickname_color = document.getElementById('edit-nick-color').value.trim();
            currentUser.status_badge = document.getElementById('edit-status').value.trim();

            await fetch('/api/user/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(currentUser)
            });

            setLocalCache('user', currentUser);
            applyUserTheme(currentUser);
            closePage('page-edit-profile');
            openMyProfile();
        }

        async function processInviteCode(code) {
            try {
                const res = await fetch('/api/invite/use', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ user_id: currentUser.id, code })
                });
                const data = await res.json();
                if(data.success) {
                    currentUser.is_invited = 1;
                    setLocalCache('user', currentUser);
                    tg?.showAlert("Access granted!");
                    return true;
                } else {
                    tg?.showAlert("Invalid code.");
                    return false;
                }
            } catch (e) {
                tg?.showAlert("Connection error.");
                return false;
            }
        }

        async function useInvite(inputId) {
            const code = document.getElementById(inputId).value.trim();
            if(!code) return;
            const success = await processInviteCode(code);
            if (success) {
                openMyProfile();
            }
        }
    </script>
</body>
</html>
"""

# --- PYTHON API ROUTES ---
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/user/sync', methods=['POST'])
def sync_user():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, avatar_url) VALUES (?, ?, ?, ?)",
                (data['id'], data['username'], data['first_name'], data.get('avatar_url', '')))
    cur.execute("UPDATE users SET avatar_url = ?, username = ?, first_name = ? WHERE user_id = ?", 
                (data.get('avatar_url', ''), data['username'], data['first_name'], data['id']))
    
    cur.execute("SELECT user_id, username, first_name, avatar_url, is_invited, used_code, is_banned, ban_reason, ban_until, prefix, prefix_color, aliases, bg_color, bg_emoji, avatar_frame, nickname_color, status_badge FROM users WHERE user_id = ?", (data['id'],))
    u = cur.fetchone()
    conn.commit()
    conn.close()
    
    return jsonify({"user": {
        "id": u[0], "username": u[1], "first_name": u[2], "avatar_url": u[3],
        "is_invited": u[4], "used_code": u[5], "is_banned": u[6], "ban_reason": u[7], "ban_until": u[8],
        "prefix": u[9], "prefix_color": u[10], "aliases": u[11], "bg_color": u[12], "bg_emoji": u[13],
        "avatar_frame": u[14], "nickname_color": u[15], "status_badge": u[16]
    }})

@app.route('/api/user/update', methods=['POST'])
def update_user():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE users SET bg_color = ?, bg_emoji = ?, avatar_frame = ?, nickname_color = ?, status_badge = ?
        WHERE user_id = ?
    """, (data.get('bg_color'), data.get('bg_emoji'), data.get('avatar_frame'), data.get('nickname_color'), data.get('status_badge'), data['id']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/user/<int:user_id>')
def get_user_profile(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, first_name, avatar_url, prefix, prefix_color, aliases, is_banned, bg_color, bg_emoji, avatar_frame, nickname_color, status_badge FROM users WHERE user_id = ?", (user_id,))
    u = cur.fetchone()
    conn.close()
    if u and not u[7]:
        return jsonify({"user": {
            "user_id": u[0], "username": u[1], "first_name": u[2], "avatar_url": u[3],
            "prefix": u[4], "prefix_color": u[5], "aliases": u[6], "bg_color": u[8],
            "bg_emoji": u[9], "avatar_frame": u[10], "nickname_color": u[11], "status_badge": u[12]
        }})
    return jsonify({"error": "Not found"}), 404

@app.route('/api/invite/use', methods=['POST'])
def use_invite():
    data = request.json
    code = data.get('code', '').strip()
    user_id = data.get('user_id')
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT is_used FROM invites WHERE code = ?", (code,))
    invite = cur.fetchone()
    
    if invite and invite[0] == 0:
        cur.execute("UPDATE invites SET is_used = 1 WHERE code = ?", (code,))
        cur.execute("UPDATE users SET is_invited = 1, used_code = ? WHERE user_id = ?", (code, user_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    
    conn.close()
    return jsonify({"success": False})

@app.route('/api/posts')
def get_posts():
    q = request.args.get('q', '').strip()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    query = """
        SELECT p.id, p.author_id, p.title, p.content, p.image_url, p.allow_comments, p.is_pinned,
               u.first_name, u.avatar_url, u.prefix, u.prefix_color, u.is_banned,
               u.avatar_frame, u.nickname_color, u.status_badge
        FROM posts p LEFT JOIN users u ON p.author_id = u.user_id
    """
    
    if q:
        query += " WHERE p.title LIKE ? OR p.content LIKE ? ORDER BY p.is_pinned DESC, p.id DESC"
        cur.execute(query, (f"%{q}%", f"%{q}%"))
    else:
        query += " ORDER BY p.is_pinned DESC, p.id DESC LIMIT 20"
        cur.execute(query)
        
    rows = cur.fetchall()
    conn.close()
    
    return jsonify([{
        "id": r[0], "author_id": r[1], "title": r[2], "content": r[3], "image_url": r[4], 
        "allow_comments": r[5], "is_pinned": r[6], "author_name": r[7], "avatar_url": r[8],
        "prefix": r[9], "prefix_color": r[10], "is_banned": r[11], "avatar_frame": r[12],
        "nickname_color": r[13], "status_badge": r[14]
    } for r in rows])

@app.route('/api/posts/<int:post_id>')
def get_post_detail(post_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT p.id, p.author_id, p.title, p.content, p.image_url, p.allow_comments,
               u.first_name, u.avatar_url, u.prefix, u.prefix_color, u.is_banned,
               u.avatar_frame, u.nickname_color, u.status_badge
        FROM posts p LEFT JOIN users u ON p.author_id = u.user_id WHERE p.id = ?
    """, (post_id,))
    p = cur.fetchone()
    
    cur.execute("""
        SELECT c.id, c.author_id, c.content, u.first_name, u.avatar_url, u.prefix, u.prefix_color, u.is_banned,
               u.avatar_frame, u.nickname_color, u.status_badge
        FROM comments c LEFT JOIN users u ON c.author_id = u.user_id WHERE c.post_id = ? ORDER BY c.id ASC
    """, (post_id,))
    comments = cur.fetchall()
    conn.close()
    
    if not p: return jsonify({"error": "Not found"}), 404
    
    post_dict = {
        "id": p[0], "author_id": p[1], "title": p[2], "content": p[3], "image_url": p[4], "allow_comments": p[5],
        "author_name": p[6], "avatar_url": p[7], "prefix": p[8], "prefix_color": p[9], "is_banned": p[10],
        "avatar_frame": p[11], "nickname_color": p[12], "status_badge": p[13]
    }
    comments_list = [{
        "id": c[0], "author_id": c[1], "content": c[2], "author_name": c[3], 
        "avatar_url": c[4], "prefix": c[5], "prefix_color": c[6], "is_banned": c[7],
        "avatar_frame": c[8], "nickname_color": c[9], "status_badge": c[10]
    } for c in comments]
    
    return jsonify({"post": post_dict, "comments": comments_list})

@app.route('/api/posts/create', methods=['POST'])
def create_post():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO posts (author_id, title, content, image_url, allow_comments) VALUES (?, ?, ?, ?, ?)",
                (data['author_id'], data['title'], data['content'], data.get('image_url', ''), data.get('allow_comments', 1)))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/posts/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO comments (post_id, author_id, content) VALUES (?, ?, ?)",
                (post_id, data['author_id'], data['content']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
