import os
import sqlite3
import random
import string
import telebot
from flask import Flask, render_template_string, request, jsonify, redirect

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

DB_PATH = "/tmp/aether.db" if os.getenv("VERCEL") else "aether.db"
app = Flask(__name__)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Таблица пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            avatar_url TEXT DEFAULT '',
            is_invited INTEGER DEFAULT 0,
            used_code TEXT DEFAULT '',
            is_banned INTEGER DEFAULT 0,
            prefix TEXT DEFAULT 'USER',
            prefix_color TEXT DEFAULT '#888888',
            aliases TEXT DEFAULT ''
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS invites (
            code TEXT PRIMARY KEY,
            is_used INTEGER DEFAULT 0
        )
    ''')
    # Таблицы постов и комментов теперь ссылаются только на author_id
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

# --- HTML TEMPLATE (Single Page App) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
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
        }

        * {
            box-sizing: border-box; margin: 0; padding: 0;
            font-family: 'Inter', sans-serif;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background-color: var(--bg); color: var(--text);
            overflow: hidden; /* Запрещаем скролл body, скроллим внутри страниц */
        }

        /* Навигация по страницам (Свайпы как в ТГ/Почте) */
        .viewport {
            position: relative; width: 100vw; height: 100vh; overflow: hidden;
        }

        .page {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: var(--bg);
            overflow-y: auto;
            transform: translateX(100%);
            transition: transform 0.35s var(--m3-easing);
            z-index: 10;
            display: flex; flex-direction: column;
        }
        
        .page.active { transform: translateX(0); z-index: 20; }
        .page.base { transform: translateX(0); z-index: 1; }
        .page.dimmed { transform: translateX(-20%); opacity: 0.5; } /* Эффект ухода на задний план */

        /* Топ-бары */
        .top-bar {
            position: sticky; top: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(12px);
            padding: 16px 20px; display: flex; align-items: center; gap: 16px; z-index: 100;
            border-bottom: 1px solid var(--border);
        }
        .top-bar .title { font-size: 20px; font-weight: 700; flex: 1; }
        .icon-btn {
            background: none; border: none; color: var(--text); cursor: pointer;
            display: flex; align-items: center; justify-content: center;
        }

        /* Лента форума */
        .feed-container { padding: 16px; padding-bottom: 80px; }
        
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
        
        .author-row { display: flex; align-items: center; gap: 10px; }
        .avatar { width: 28px; height: 28px; border-radius: 50%; background: #222; object-fit: cover; }
        .author-name { font-size: 14px; font-weight: 600; color: var(--text); }
        .badge { font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 6px; text-transform: uppercase; }

        /* Внутренности поста */
        .post-content-area { padding: 20px; flex: 1; }
        .post-content-area h1 { font-size: 32px; font-weight: 700; line-height: 1.1; margin-bottom: 16px; letter-spacing: -1px; }
        .post-text { font-size: 16px; line-height: 1.6; color: #ddd; white-space: pre-wrap; margin-bottom: 24px; }
        .post-image { width: 100%; border-radius: 16px; margin-bottom: 24px; border: 1px solid var(--border); }
        
        /* Комментарии */
        .comments-section { border-top: 1px solid var(--border); padding-top: 24px; }
        .comment-item { display: flex; gap: 12px; margin-bottom: 20px; }
        .comment-item .avatar { width: 36px; height: 36px; }
        .comment-bubble { background: var(--surface-variant); padding: 12px 16px; border-radius: 4px 16px 16px 16px; flex: 1; }
        .comment-author { font-size: 13px; font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 8px; }
        .comment-text { font-size: 14px; line-height: 1.5; color: #ccc; }

        /* M3 Input & FAB */
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

        /* M3 Switch (Чекбокс) */
        .m3-switch-container {
            display: flex; justify-content: space-between; align-items: center;
            background: var(--surface); padding: 16px; border-radius: 16px; border: 1px solid var(--border); margin-bottom: 24px;
        }
        .m3-switch {
            position: relative; width: 52px; height: 32px; appearance: none;
            background: var(--border); border-radius: 100px; outline: none; cursor: pointer;
            transition: background 0.3s;
        }
        .m3-switch::after {
            content: ''; position: absolute; top: 4px; left: 4px; width: 24px; height: 24px;
            background: #888; border-radius: 50%; transition: 0.3s var(--m3-easing);
        }
        .m3-switch:checked { background: var(--primary); }
        .m3-switch:checked::after { transform: translateX(20px); background: #000; }

        /* Профиль (Стиль ТГ) */
        .profile-header { text-align: center; padding: 40px 20px 20px; }
        .profile-avatar { width: 100px; height: 100px; border-radius: 50%; object-fit: cover; margin-bottom: 16px; background: #222; }
        .profile-name { font-size: 24px; font-weight: 700; display: flex; justify-content: center; align-items: center; gap: 8px; }
        .profile-box { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 16px; margin: 0 20px; }

        .btn-primary {
            background: var(--primary); color: #000; border: none; border-radius: 100px;
            padding: 16px; font-size: 16px; font-weight: 600; width: 100%; cursor: pointer;
        }
        
        .banned-text { color: #ff5252; font-style: italic; }
    </style>
</head>
<body>

    <div class="viewport">
        <!-- БАЗОВАЯ СТРАНИЦА (ЛЕНТА) -->
        <div id="page-feed" class="page base">
            <div class="top-bar">
                <span class="title">aether's</span>
                <div class="icon-btn" onclick="openSearch()"><span class="material-symbols-rounded">search</span></div>
                <div class="icon-btn" onclick="openMyProfile()"><span class="material-symbols-rounded">account_circle</span></div>
            </div>
            
            <div style="padding: 16px 16px 0 16px; display: none;" id="search-box">
                <input type="text" id="search-input" class="input-m3" placeholder="Search topics..." oninput="loadFeed()">
            </div>

            <div class="feed-container" id="feed-list">
                <!-- Карточки загружаются сюда -->
            </div>
            
            <div class="fab" onclick="openCreatePost()"><span class="material-symbols-rounded">edit</span></div>
        </div>

        <!-- СТРАНИЦА: ПРОСМОТР ПОСТА -->
        <div id="page-post" class="page">
            <div class="top-bar">
                <div class="icon-btn" onclick="closePage('page-post')"><span class="material-symbols-rounded">arrow_back</span></div>
                <span class="title">Thread</span>
            </div>
            <div class="post-content-area">
                <h1 id="view-title">Loading...</h1>
                <div class="author-row" style="margin-bottom: 24px; cursor: pointer;" id="view-author-trigger">
                    <img id="view-avatar" class="avatar" src="">
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

        <!-- СТРАНИЦА: СОЗДАНИЕ ПОСТА -->
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

        <!-- СТРАНИЦА: ПРОФИЛЬ (ТГ СТИЛЬ) -->
        <div id="page-profile" class="page">
            <div class="top-bar">
                <div class="icon-btn" onclick="closePage('page-profile')"><span class="material-symbols-rounded">arrow_back</span></div>
                <span class="title">Profile</span>
            </div>
            <div class="profile-header">
                <img id="prof-avatar" class="profile-avatar" src="">
                <div class="profile-name">
                    <span id="prof-name">Name</span>
                    <span id="prof-badge" class="badge"></span>
                </div>
                <div style="color: var(--text-sub); margin-top: 8px;" id="prof-username">@username</div>
            </div>
            
            <div class="profile-box">
                <div style="font-size: 12px; color: var(--text-sub); margin-bottom: 4px;">User ID</div>
                <div id="prof-id" style="font-size: 15px; font-family: monospace; margin-bottom: 16px;">-</div>
                
                <div style="font-size: 12px; color: var(--text-sub); margin-bottom: 4px;">Also known as</div>
                <div id="prof-aliases" style="font-size: 15px; color: #fff;">None</div>
            </div>
            
            <div id="invite-section" class="profile-box" style="margin-top: 16px; display: none;">
                <div style="font-size: 12px; color: var(--text-sub); margin-bottom: 8px;">Enter Invite Code</div>
                <input type="text" id="invite-code-input" class="input-m3" style="padding: 10px; margin-bottom: 10px;" placeholder="AETHER-XXXXX">
                <button class="btn-primary" style="padding: 10px;" onclick="useInvite()">Activate</button>
            </div>
        </div>
    </div>

    <script>
        const tg = window.Telegram?.WebApp;
        if(tg) { tg.expand(); tg.ready(); }

        let currentUser = {
            id: tg?.initDataUnsafe?.user?.id || 123456,
            first_name: tg?.initDataUnsafe?.user?.first_name || 'Guest',
            username: tg?.initDataUnsafe?.user?.username || 'guest',
            avatar_url: tg?.initDataUnsafe?.user?.photo_url || '',
            is_invited: 0
        };

        let currentActivePostId = null;

        // --- Управление страницами ---
        function openPage(pageId) {
            document.getElementById('page-feed').classList.add('dimmed');
            const page = document.getElementById(pageId);
            page.style.display = 'flex';
            // Force reflow
            void page.offsetWidth;
            page.classList.add('active');
        }

        function closePage(pageId) {
            document.getElementById('page-feed').classList.remove('dimmed');
            const page = document.getElementById(pageId);
            page.classList.remove('active');
            setTimeout(() => { if(!page.classList.contains('active')) page.style.display = ''; }, 350);
        }
        
        function openSearch() {
            const sb = document.getElementById('search-box');
            sb.style.display = sb.style.display === 'none' ? 'block' : 'none';
        }

        // --- API Вызовы ---
        async function initApp() {
            // Синхронизация юзера с БД
            const res = await fetch('/api/user/sync', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(currentUser)
            });
            const data = await res.json();
            currentUser = data.user;
            loadFeed();
        }

        async function loadFeed() {
            const q = document.getElementById('search-input').value.trim();
            const res = await fetch(`/api/posts?q=${encodeURIComponent(q)}`);
            const posts = await res.json();
            
            const list = document.getElementById('feed-list');
            list.innerHTML = '';
            
            posts.forEach(p => {
                // Если забанен
                const authorName = p.is_banned ? '<span class="banned-text">Account not found</span>' : p.author_name;
                const avatar = p.is_banned || !p.avatar_url ? 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" fill="%23555" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>' : p.avatar_url;
                const badge = (!p.is_banned && p.prefix) ? `<span class="badge" style="background: ${p.prefix_color}; color: #000;">${p.prefix}</span>` : '';
                const pin = p.is_pinned ? `<span class="material-symbols-rounded" style="font-size: 16px; float: right; color: var(--text-sub);">push_pin</span>` : '';

                list.innerHTML += `
                    <div class="post-card" onclick="viewPost(${p.id})">
                        ${pin}
                        <h2>${p.title}</h2>
                        <p>${p.content}</p>
                        <div class="author-row">
                            <img class="avatar" src="${avatar}">
                            <span class="author-name">${authorName}</span>
                            ${badge}
                        </div>
                    </div>
                `;
            });
        }

        async function viewPost(id) {
            currentActivePostId = id;
            const res = await fetch(`/api/posts/${id}`);
            const data = await res.json();
            const p = data.post;
            
            document.getElementById('view-title').innerText = p.title;
            document.getElementById('view-content').innerText = p.content;
            
            const img = document.getElementById('view-image');
            if(p.image_url) { img.src = p.image_url; img.style.display = 'block'; }
            else { img.style.display = 'none'; }

            const aName = p.is_banned ? 'Account not found' : p.author_name;
            const aAva = p.is_banned || !p.avatar_url ? 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" fill="%23555" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>' : p.avatar_url;
            
            document.getElementById('view-author').innerText = aName;
            if(p.is_banned) document.getElementById('view-author').classList.add('banned-text');
            else document.getElementById('view-author').classList.remove('banned-text');

            document.getElementById('view-avatar').src = aAva;
            
            const badgeEl = document.getElementById('view-badge');
            if(!p.is_banned && p.prefix) {
                badgeEl.innerText = p.prefix;
                badgeEl.style.background = p.prefix_color;
                badgeEl.style.color = '#000';
                badgeEl.style.display = 'inline-block';
            } else {
                badgeEl.style.display = 'none';
            }

            // Обработчик профиля
            document.getElementById('view-author-trigger').onclick = () => {
                if(!p.is_banned) openProfile(p.author_id);
            };

            // Комменты
            const cList = document.getElementById('comments-list');
            cList.innerHTML = '';
            data.comments.forEach(c => {
                const cName = c.is_banned ? '<span class="banned-text">Account not found</span>' : c.author_name;
                const cAva = c.is_banned || !c.avatar_url ? 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" fill="%23555" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>' : c.avatar_url;
                const cBadge = (!c.is_banned && c.prefix) ? `<span class="badge" style="background: ${c.prefix_color}; color: #000; font-size: 8px;">${c.prefix}</span>` : '';

                cList.innerHTML += `
                    <div class="comment-item">
                        <img class="avatar" src="${cAva}" style="cursor:pointer;" onclick="${c.is_banned ? '' : `openProfile(${c.author_id})`}">
                        <div class="comment-bubble">
                            <div class="comment-author" style="cursor:pointer;" onclick="${c.is_banned ? '' : `openProfile(${c.author_id})`}">
                                ${cName} ${cBadge}
                            </div>
                            <div class="comment-text">${c.content}</div>
                        </div>
                    </div>
                `;
            });

            // Форма комментов
            if(currentUser.is_invited || p.allow_comments) {
                document.getElementById('comment-input-area').style.display = 'flex';
            } else {
                document.getElementById('comment-input-area').style.display = 'none';
            }

            openPage('page-post');
        }

        function openCreatePost() {
            if(!currentUser.is_invited) {
                tg.showAlert("Posting is limited to verified/invited users.");
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
                    author_id: currentUser.id,
                    title: title, content: content, image_url: img, allow_comments: allow_comments
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
            viewPost(currentActivePostId); // refresh
        }

        function openMyProfile() {
            openProfile(currentUser.id, true);
        }

        async function openProfile(userId, isMe = false) {
            const res = await fetch(`/api/user/${userId}`);
            const data = await res.json();
            if(data.error) return;
            const u = data.user;

            document.getElementById('prof-name').innerText = u.first_name;
            document.getElementById('prof-username').innerText = `@${u.username}`;
            document.getElementById('prof-id').innerText = u.user_id;
            
            const ava = u.avatar_url || 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" fill="%23555" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>';
            document.getElementById('prof-avatar').src = ava;

            const badgeEl = document.getElementById('prof-badge');
            if(u.prefix) {
                badgeEl.innerText = u.prefix;
                badgeEl.style.background = u.prefix_color;
                badgeEl.style.color = '#000';
                badgeEl.style.display = 'inline-block';
            } else {
                badgeEl.style.display = 'none';
            }

            document.getElementById('prof-aliases').innerText = u.aliases ? u.aliases.split(',').map(a => `@${a.trim()}`).join(', ') : 'None';

            if(isMe && !currentUser.is_invited) {
                document.getElementById('invite-section').style.display = 'block';
            } else {
                document.getElementById('invite-section').style.display = 'none';
            }

            openPage('page-profile');
        }

        async function useInvite() {
            const code = document.getElementById('invite-code-input').value.trim();
            const res = await fetch('/api/invite/use', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: currentUser.id, code })
            });
            const data = await res.json();
            if(data.success) {
                currentUser.is_invited = 1;
                tg.showAlert("Access granted!");
                openMyProfile();
            } else {
                tg.showAlert("Invalid code.");
            }
        }

        initApp();
    </script>
</body>
</html>
"""

# --- ADMIN PANEL HTML ---
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #000; color: #fff; font-family: sans-serif; padding: 20px; }
        h1 { font-size: 24px; border-bottom: 1px solid #333; padding-bottom: 10px; }
        .card { background: #111; border: 1px solid #333; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
        input, select { background: #000; color: #fff; border: 1px solid #444; padding: 8px; border-radius: 6px; width: 100%; margin-top: 4px; box-sizing: border-box; }
        button { background: #fff; color: #000; border: none; padding: 10px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .btn-danger { background: #ff3b30; color: #fff; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #333; }
        details { cursor: pointer; }
    </style>
</head>
<body>
    <h1>Administration</h1>
    
    <div class="card">
        <h3>Create Invite</h3>
        <form action="/inv/generate" method="post">
            <button type="submit">Generate Code</button>
        </form>
    </div>

    <div class="card">
        <h3>Users Control</h3>
        <table>
            <tr><th>ID</th><th>Username</th><th>Prefix</th><th>Banned</th><th>Action</th></tr>
            {% for u in users %}
            <tr>
                <td>{{ u[0] }}</td>
                <td>{{ u[1] }}</td>
                <td><span style="color:{{ u[8] }}">{{ u[7] }}</span></td>
                <td>{{ "YES" if u[6] else "NO" }}</td>
                <td>
                    <details>
                        <summary>Edit</summary>
                        <div style="background: #000; padding: 10px; margin-top: 5px; border-radius: 6px; border: 1px solid #333;">
                            <form action="/inv/edit_user" method="post">
                                <input type="hidden" name="user_id" value="{{ u[0] }}">
                                <label>Prefix:</label>
                                <input type="text" name="prefix" value="{{ u[7] }}">
                                <label>Prefix Color (HEX):</label>
                                <input type="text" name="prefix_color" value="{{ u[8] }}">
                                <label>Aliases (comma separated):</label>
                                <input type="text" name="aliases" value="{{ u[9] }}">
                                
                                <div style="display:flex; gap:10px; margin-top:10px;">
                                    <button type="submit">Save</button>
                                </div>
                            </form>
                            <form action="/inv/ban" method="post" style="margin-top: 5px;">
                                <input type="hidden" name="user_id" value="{{ u[0] }}">
                                <button type="submit" class="btn-danger">{{ "Unban User" if u[6] else "Ban User" }}</button>
                            </form>
                        </div>
                    </details>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
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
    # Обновляем инфу при заходе
    cur.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, avatar_url) VALUES (?, ?, ?, ?)",
                (data['id'], data['username'], data['first_name'], data.get('avatar_url', '')))
    cur.execute("UPDATE users SET avatar_url = ?, username = ?, first_name = ? WHERE user_id = ?", 
                (data.get('avatar_url', ''), data['username'], data['first_name'], data['id']))
    
    cur.execute("SELECT user_id, username, first_name, avatar_url, is_invited, used_code, is_banned, prefix, prefix_color, aliases FROM users WHERE user_id = ?", (data['id'],))
    u = cur.fetchone()
    conn.commit()
    conn.close()
    
    return jsonify({"user": {
        "id": u[0], "username": u[1], "first_name": u[2], "avatar_url": u[3],
        "is_invited": u[4], "used_code": u[5], "is_banned": u[6],
        "prefix": u[7], "prefix_color": u[8], "aliases": u[9]
    }})

@app.route('/api/user/<int:user_id>')
def get_user_profile(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, first_name, avatar_url, prefix, prefix_color, aliases, is_banned FROM users WHERE user_id = ?", (user_id,))
    u = cur.fetchone()
    conn.close()
    if u and not u[7]: # Если не забанен
        return jsonify({"user": {"user_id": u[0], "username": u[1], "first_name": u[2], "avatar_url": u[3], "prefix": u[4], "prefix_color": u[5], "aliases": u[6]}})
    return jsonify({"error": "Not found"}), 404

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
    return jsonify({"success": False})

@app.route('/api/posts')
def get_posts():
    q = request.args.get('q', '').strip()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    query = """
        SELECT p.id, p.author_id, p.title, p.content, p.image_url, p.allow_comments, p.is_pinned,
               u.first_name, u.avatar_url, u.prefix, u.prefix_color, u.is_banned
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
        "prefix": r[9], "prefix_color": r[10], "is_banned": r[11]
    } for r in rows])

@app.route('/api/posts/<int:post_id>')
def get_post_detail(post_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Пост
    cur.execute("""
        SELECT p.id, p.author_id, p.title, p.content, p.image_url, p.allow_comments,
               u.first_name, u.avatar_url, u.prefix, u.prefix_color, u.is_banned
        FROM posts p LEFT JOIN users u ON p.author_id = u.user_id WHERE p.id = ?
    """, (post_id,))
    p = cur.fetchone()
    
    # Комменты
    cur.execute("""
        SELECT c.id, c.author_id, c.content, u.first_name, u.avatar_url, u.prefix, u.prefix_color, u.is_banned
        FROM comments c LEFT JOIN users u ON c.author_id = u.user_id WHERE c.post_id = ? ORDER BY c.id ASC
    """, (post_id,))
    comments = cur.fetchall()
    conn.close()
    
    if not p: return jsonify({"error": "Not found"}), 404
    
    post_dict = {
        "id": p[0], "author_id": p[1], "title": p[2], "content": p[3], "image_url": p[4], "allow_comments": p[5],
        "author_name": p[6], "avatar_url": p[7], "prefix": p[8], "prefix_color": p[9], "is_banned": p[10]
    }
    comments_list = [{
        "id": c[0], "author_id": c[1], "content": c[2], "author_name": c[3], 
        "avatar_url": c[4], "prefix": c[5], "prefix_color": c[6], "is_banned": c[7]
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

# --- ADMIN ROUTES (/inv) ---
@app.route('/inv')
def admin_panel():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    conn.close()
    return render_template_string(ADMIN_TEMPLATE, users=users)

@app.route('/inv/generate', methods=['POST'])
def admin_gen_invite():
    code = generate_code()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO invites (code) VALUES (?)", (code,))
    conn.commit()
    conn.close()
    return redirect('/inv')

@app.route('/inv/edit_user', methods=['POST'])
def admin_edit_user():
    user_id = request.form.get('user_id')
    prefix = request.form.get('prefix', '').upper()
    prefix_color = request.form.get('prefix_color', '#ffffff')
    aliases = request.form.get('aliases', '')
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET prefix = ?, prefix_color = ?, aliases = ? WHERE user_id = ?", 
                (prefix, prefix_color, aliases, user_id))
    conn.commit()
    conn.close()
    return redirect('/inv')

@app.route('/inv/ban', methods=['POST'])
def admin_ban_user():
    user_id = request.form.get('user_id')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_banned = CASE WHEN is_banned=1 THEN 0 ELSE 1 END WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect('/inv')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
