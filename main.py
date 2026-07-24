import os
import json
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
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            avatar_url TEXT DEFAULT '',
            is_invited INTEGER DEFAULT 0,
            used_code TEXT DEFAULT '',
            is_banned INTEGER DEFAULT 0,
            prefix TEXT DEFAULT 'USER'
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
            author_name TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def generate_code(length=8):
    return 'AETHER-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# --- HTML TEMPLATE ---
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
            --bg: #000000;
            --surface: #0a0a0a;
            --surface-variant: #141414;
            --border: #222222;
            --border-light: #333333;
            --text: #ffffff;
            --text-sub: #737373;
            --m3-easing: cubic-bezier(0.2, 0, 0, 1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background-color: var(--bg);
            color: var(--text);
            overflow-x: hidden;
            min-height: 100vh;
            display: flex;
            justify-content: center;
        }

        .viewport {
            width: 100%;
            max-width: 440px;
            min-height: 100vh;
            position: relative;
        }

        /* Screens */
        .screen {
            position: absolute;
            inset: 0;
            padding: 24px 18px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            opacity: 0;
            visibility: hidden;
            transform: scale(0.97);
            transition: opacity 0.3s var(--m3-easing), transform 0.3s var(--m3-easing), visibility 0.3s;
            z-index: 1;
        }

        .screen.active {
            opacity: 1;
            visibility: visible;
            transform: scale(1);
            z-index: 2;
        }

        /* M3 Typography & Buttons */
        .title-large { font-size: 26px; font-weight: 700; letter-spacing: -0.5px; }
        .text-sub { color: var(--text-sub); font-size: 13px; }

        .btn-m3-primary {
            background: #ffffff;
            color: #000000;
            border: 1px solid #000000;
            outline: 2px solid #ffffff;
            border-radius: 100px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: transform 0.1s var(--m3-easing);
        }

        .btn-m3-primary:active { transform: scale(0.95); }

        .btn-m3-secondary {
            background: transparent;
            color: #ffffff;
            border: 1px solid var(--border-light);
            border-radius: 100px;
            padding: 12px 20px;
            font-size: 14px;
            cursor: pointer;
        }

        .input-m3 {
            width: 100%;
            background: var(--surface-variant);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 14px 16px;
            color: #fff;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }

        .input-m3:focus {
            border-color: #ffffff;
        }

        /* Captcha Card */
        .captcha-box {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 24px;
            text-align: center;
        }

        /* Tabs */
        .tabs {
            display: flex;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 100px;
            padding: 4px;
            margin-bottom: 20px;
        }

        .tab {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-sub);
            padding: 10px;
            border-radius: 100px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: all 0.2s var(--m3-easing);
        }

        .tab.active {
            background: #ffffff;
            color: #000000;
            font-weight: 600;
        }

        /* Cards */
        .card-post {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 12px;
            cursor: pointer;
            transition: border-color 0.2s;
        }

        .card-post:active {
            border-color: var(--border-light);
        }

        .badge-prefix {
            font-size: 9px;
            font-weight: 700;
            background: #ffffff;
            color: #000000;
            padding: 2px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }

        .badge-pin {
            font-size: 9px;
            border: 1px solid #fff;
            color: #fff;
            padding: 1px 5px;
            border-radius: 4px;
            float: right;
        }

        /* Modal */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.85);
            backdrop-filter: blur(8px);
            z-index: 100;
            display: none;
            align-items: flex-end;
            justify-content: center;
        }

        .modal-overlay.active { display: flex; }

        .modal-sheet {
            background: var(--surface);
            border: 1px solid var(--border);
            border-top-left-radius: 24px;
            border-top-right-radius: 24px;
            width: 100%;
            max-width: 440px;
            max-height: 85vh;
            overflow-y: auto;
            padding: 24px 20px;
            animation: slideUp 0.3s var(--m3-easing);
        }

        @keyframes slideUp {
            from { transform: translateY(100%); }
            to { transform: translateY(0); }
        }

        .svg-icon { width: 18px; height: 18px; fill: currentColor; }
    </style>
</head>
<body>

    <div class="viewport">

        <!-- CAPTCHA SCREEN -->
        <div id="screen-captcha" class="screen active">
            <div class="captcha-box">
                <h2 style="font-size: 20px; font-weight: 700; margin-bottom: 6px;">aetheris.win</h2>
                <p class="text-sub" style="margin-bottom: 20px;">Security Verification</p>

                <p id="captcha-question" style="font-size: 15px; font-weight: 600; margin-bottom: 16px;">Solve: 3 + 4 = ?</p>
                
                <div style="display: flex; gap: 8px; justify-content: center; margin-bottom: 16px;">
                    <input type="number" id="captcha-input" class="input-m3" style="text-align: center; width: 100px;" placeholder="Ans">
                    <button class="btn-m3-primary" onclick="verifyCaptcha()">Verify</button>
                </div>
            </div>
        </div>

        <!-- WELCOME SCREEN -->
        <div id="screen-welcome" class="screen">
            <h1 class="title-large" id="welcome-title">welcome</h1>
            <p class="text-sub" style="margin-top: 4px; margin-bottom: 32px;">let's start! aether's</p>
            
            <div style="display: flex; justify-content: flex-end;">
                <button class="btn-m3-primary" onclick="navTo('screen-invite')">
                    next
                    <svg class="svg-icon" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2"/></svg>
                </button>
            </div>
        </div>

        <!-- INVITE SCREEN -->
        <div id="screen-invite" class="screen">
            <h2 class="title-large">do you have invite?</h2>
            <p class="text-sub" style="margin-top: 4px; margin-bottom: 20px;">Unlock posting rights with access code</p>

            <input type="text" id="invite-code-input" class="input-m3" placeholder="invite code" style="margin-bottom: 24px;">

            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button class="btn-m3-secondary" onclick="enterApp()">skip</button>
                <button class="btn-m3-primary" onclick="submitInvite()">confirm</button>
            </div>
        </div>

        <!-- MAIN APP -->
        <div id="screen-main" class="screen" style="justify-content: flex-start; padding-top: 20px;">
            <div style="font-size: 22px; font-weight: 700; text-align: center; margin-bottom: 16px;">aether's</div>

            <div class="tabs">
                <button class="tab active" onclick="switchTab('forum', this)">
                    <svg class="svg-icon" viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>
                    Forum
                </button>
                <button class="tab" onclick="switchTab('account', this)">
                    <svg class="svg-icon" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                    Account
                </button>
            </div>

            <!-- FORUM TAB -->
            <div id="tab-forum">
                <div style="position: relative; margin-bottom: 16px;">
                    <input type="text" id="search-input" class="input-m3" placeholder="Search posts..." oninput="loadPosts()" style="padding-left: 40px;">
                    <svg class="svg-icon" style="position: absolute; left: 14px; top: 14px; color: var(--text-sub);" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                </div>

                <div id="posts-list"></div>

                <div style="display: flex; gap: 10px; margin-top: 16px;">
                    <button class="btn-m3-secondary" style="flex:1;" onclick="loadPosts()">Refresh</button>
                    <button class="btn-m3-primary" style="flex:1;" id="btn-open-create" onclick="openCreateModal()">Create Post</button>
                </div>
            </div>

            <!-- ACCOUNT TAB -->
            <div id="tab-account" style="display: none;">
                <div class="captcha-box" style="margin-bottom: 12px; text-align: left;">
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <div id="my-avatar" style="width: 52px; height: 52px; border-radius: 50%; background: #222; display: flex; align-items: center; justify-content: center; font-size: 20px;">👤</div>
                        <div>
                            <div style="display: flex; align-items: center; gap: 6px;">
                                <h3 id="my-name" style="font-size: 16px; font-weight: 600;">Name</h3>
                                <span id="my-prefix" class="badge-prefix">USER</span>
                            </div>
                            <p id="my-username" class="text-sub">@username</p>
                        </div>
                    </div>
                </div>

                <div class="captcha-box" style="text-align: left;">
                    <p class="text-sub">Invite Status</p>
                    <p id="my-invite-status" style="font-weight: 600; margin-top: 4px;">Standard Access</p>
                    <p id="my-used-code" class="text-sub" style="margin-top: 4px; font-size: 11px;"></p>
                </div>
            </div>

        </div>

    </div>

    <!-- POST DETAIL MODAL -->
    <div id="modal-post" class="modal-overlay">
        <div class="modal-sheet">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span id="post-detail-author" class="text-sub" style="cursor: pointer; text-decoration: underline;" onclick="viewAuthorProfile()">by Author</span>
                <button onclick="closeModal('modal-post')" style="background: none; border: none; color: #fff; font-size: 20px; cursor: pointer;">✕</button>
            </div>

            <h2 id="post-detail-title" style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">Title</h2>
            <p id="post-detail-content" style="font-size: 14px; line-height: 1.5; color: #ccc; margin-bottom: 12px; white-space: pre-wrap;"></p>
            
            <div id="post-detail-img-box" style="display: none; margin-bottom: 16px;">
                <img id="post-detail-img" src="" style="width: 100%; border-radius: 12px; border: 1px solid var(--border);">
            </div>

            <hr style="border: none; border-top: 1px solid var(--border); margin: 16px 0;">

            <h4 style="font-size: 14px; font-weight: 600; margin-bottom: 12px;">Comments</h4>
            <div id="comments-list" style="margin-bottom: 16px;"></div>

            <div id="comment-form" style="display: flex; gap: 8px;">
                <input type="text" id="comment-input" class="input-m3" placeholder="Write a comment...">
                <button class="btn-m3-primary" onclick="sendComment()">Send</button>
            </div>
        </div>
    </div>

    <!-- CREATE POST MODAL -->
    <div id="modal-create" class="modal-overlay">
        <div class="modal-sheet">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h3 style="font-size: 16px; font-weight: 600;">Create New Post</h3>
                <button onclick="closeModal('modal-create')" style="background: none; border: none; color: #fff; font-size: 20px; cursor: pointer;">✕</button>
            </div>

            <input type="text" id="new-title" class="input-m3" placeholder="Title" style="margin-bottom: 10px;">
            <textarea id="new-content" class="input-m3" placeholder="Text..." rows="4" style="margin-bottom: 10px; resize: none;"></textarea>
            <input type="text" id="new-img" class="input-m3" placeholder="Image URL (optional)" style="margin-bottom: 14px;">

            <label style="display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-sub); margin-bottom: 20px; cursor: pointer;">
                <input type="checkbox" id="new-allow-comments" checked style="accent-color: #fff;">
                Allow comments for non-invited users
            </label>

            <button class="btn-m3-primary" style="width: 100%;" onclick="submitPost()">Publish</button>
        </div>
    </div>

    <!-- USER PROFILE MODAL -->
    <div id="modal-user" class="modal-overlay">
        <div class="modal-sheet" style="text-align: center;">
            <div style="display: flex; justify-content: flex-end;">
                <button onclick="closeModal('modal-user')" style="background: none; border: none; color: #fff; font-size: 20px; cursor: pointer;">✕</button>
            </div>
            <div id="user-view-avatar" style="width: 64px; height: 64px; border-radius: 50%; background: #222; margin: 0 auto 12px auto; display: flex; align-items: center; justify-content: center; font-size: 24px;">👤</div>
            <h3 id="user-view-name" style="font-size: 18px; font-weight: 600;">Name</h3>
            <span id="user-view-prefix" class="badge-prefix" style="margin-top: 4px; inline-block;">USER</span>
            <p id="user-view-username" class="text-sub" style="margin-top: 6px;">@username</p>
            <p id="user-view-id" class="text-sub" style="font-size: 11px; margin-top: 2px;">ID: -</p>
        </div>
    </div>

    <script>
        const tg = window.Telegram?.WebApp;
        if(tg) { tg.expand(); tg.ready(); }

        let n1 = Math.floor(Math.random() * 8) + 1;
        let n2 = Math.floor(Math.random() * 8) + 1;
        let captchaAns = n1 + n2;
        document.getElementById('captcha-question').innerText = `Solve: ${n1} + ${n2} = ?`;

        let activePostId = null;
        let activeAuthorId = null;

        let currentUser = {
            id: tg?.initDataUnsafe?.user?.id || 777777,
            first_name: tg?.initDataUnsafe?.user?.first_name || 'User',
            username: tg?.initDataUnsafe?.user?.username || 'user',
            avatar_url: tg?.initDataUnsafe?.user?.photo_url || '',
            is_invited: 0,
            used_code: '',
            prefix: 'USER'
        };

        document.getElementById('welcome-title').innerText = `welcome, ${currentUser.first_name.toLowerCase()}`;

        function navTo(id) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            setTimeout(() => document.getElementById(id).classList.add('active'), 150);
        }

        function verifyCaptcha() {
            const val = parseInt(document.getElementById('captcha-input').value);
            if(val === captchaAns) {
                syncUser();
                navTo('screen-welcome');
            } else {
                alert("Wrong answer");
            }
        }

        async function syncUser() {
            const res = await fetch('/api/user/sync', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(currentUser)
            });
            const data = await res.json();
            if(data.user) {
                currentUser = data.user;
                updateAccountUI();
            }
        }

        async function submitInvite() {
            const code = document.getElementById('invite-code-input').value.trim();
            if(!code) return enterApp();

            const res = await fetch('/api/invite/use', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: currentUser.id, code })
            });
            const data = await res.json();
            if(data.success) {
                currentUser.is_invited = 1;
                currentUser.used_code = code;
            } else {
                alert(data.message || "Error");
            }
            enterApp();
        }

        function enterApp() {
            navTo('screen-main');
            updateAccountUI();
            loadPosts();
        }

        function updateAccountUI() {
            document.getElementById('my-name').innerText = currentUser.first_name;
            document.getElementById('my-username').innerText = `@${currentUser.username}`;
            document.getElementById('my-prefix').innerText = currentUser.prefix;
            
            const btnCreate = document.getElementById('btn-open-create');
            const statusEl = document.getElementById('my-invite-status');

            if(currentUser.is_invited) {
                statusEl.innerText = "Invited Access";
                document.getElementById('my-used-code').innerText = `Key: ${currentUser.used_code}`;
                btnCreate.style.opacity = "1";
                btnCreate.style.pointerEvents = "auto";
            } else {
                statusEl.innerText = "Standard Access";
                btnCreate.style.opacity = "0.3";
                btnCreate.style.pointerEvents = "none";
            }
        }

        function switchTab(tab, btn) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            if(tab === 'forum') {
                document.getElementById('tab-forum').style.display = 'block';
                document.getElementById('tab-account').style.display = 'none';
            } else {
                document.getElementById('tab-forum').style.display = 'none';
                document.getElementById('tab-account').style.display = 'block';
            }
        }

        async function loadPosts() {
            const q = document.getElementById('search-input').value.trim();
            const res = await fetch(`/api/posts?q=${encodeURIComponent(q)}`);
            const posts = await res.json();
            
            const box = document.getElementById('posts-list');
            box.innerHTML = '';
            
            posts.forEach(p => {
                box.innerHTML += `
                    <div class="card-post" onclick="openPost(${p.id})">
                        ${p.is_pinned ? '<span class="badge-pin">PIN</span>' : ''}
                        <div style="font-size: 15px; font-weight: 600; margin-bottom: 4px;">${p.title}</div>
                        <div class="text-sub" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${p.content}</div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; font-size: 11px; color: var(--text-sub);">
                            <span>by ${p.author_name}</span>
                            <span>💬 ${p.comments_count}</span>
                        </div>
                    </div>
                `;
            });
        }

        async function openPost(id) {
            activePostId = id;
            const res = await fetch(`/api/posts/${id}`);
            const data = await res.json();
            
            document.getElementById('post-detail-title').innerText = data.post.title;
            document.getElementById('post-detail-content').innerText = data.post.content;
            document.getElementById('post-detail-author').innerText = `by ${data.post.author_name}`;
            activeAuthorId = data.post.author_id;

            const imgBox = document.getElementById('post-detail-img-box');
            if(data.post.image_url) {
                document.getElementById('post-detail-img').src = data.post.image_url;
                imgBox.style.display = 'block';
            } else {
                imgBox.style.display = 'none';
            }

            // Comments list
            const cList = document.getElementById('comments-list');
            cList.innerHTML = '';
            data.comments.forEach(c => {
                cList.innerHTML += `
                    <div style="background: var(--surface-variant); padding: 10px 12px; border-radius: 10px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-sub); margin-bottom: 2px;">
                            <span style="cursor: pointer; font-weight: 600;" onclick="viewUserProfile(${c.author_id})">${c.author_name}</span>
                        </div>
                        <p style="font-size: 13px;">${c.content}</p>
                    </div>
                `;
            });

            // Comment permission check
            const cForm = document.getElementById('comment-form');
            if(currentUser.is_invited || data.post.allow_comments) {
                cForm.style.display = 'flex';
            } else {
                cForm.style.display = 'none';
            }

            document.getElementById('modal-post').classList.add('active');
        }

        async function sendComment() {
            const input = document.getElementById('comment-input');
            const val = input.value.trim();
            if(!val) return;

            await fetch(`/api/posts/${activePostId}/comment`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    author_id: currentUser.id,
                    author_name: currentUser.first_name,
                    content: val
                })
            });

            input.value = '';
            openPost(activePostId);
        }

        function openCreateModal() {
            if(!currentUser.is_invited) return;
            document.getElementById('modal-create').classList.add('active');
        }

        async function submitPost() {
            const title = document.getElementById('new-title').value.trim();
            const content = document.getElementById('new-content').value.trim();
            const image_url = document.getElementById('new-img').value.trim();
            const allow_comments = document.getElementById('new-allow-comments').checked ? 1 : 0;

            if(!title || !content) return;

            await fetch('/api/posts/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    author_id: currentUser.id,
                    author_name: currentUser.first_name,
                    title, content, image_url, allow_comments
                })
            });

            closeModal('modal-create');
            loadPosts();
        }

        function viewAuthorProfile() {
            if(activeAuthorId) viewUserProfile(activeAuthorId);
        }

        async function viewUserProfile(userId) {
            const res = await fetch(`/api/user/${userId}`);
            const data = await res.json();
            if(data.user) {
                document.getElementById('user-view-name').innerText = data.user.first_name;
                document.getElementById('user-view-username').innerText = `@${data.user.username}`;
                document.getElementById('user-view-prefix').innerText = data.user.prefix;
                document.getElementById('user-view-id').innerText = `ID: ${data.user.user_id}`;
                document.getElementById('modal-user').classList.add('active');
            }
        }

        function closeModal(id) {
            document.getElementById(id).classList.remove('active');
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
        body { background: #000; color: #fff; font-family: monospace; padding: 16px; }
        .card { background: #0f0f0f; border: 1px solid #222; padding: 14px; border-radius: 12px; margin-bottom: 12px; }
        button { background: #fff; color: #000; border: none; padding: 6px 12px; border-radius: 6px; font-weight: bold; cursor: pointer; }
        .btn-danger { background: #ff3b30; color: #fff; }
        input, select { background: #1a1a1a; color: #fff; border: 1px solid #333; padding: 6px; border-radius: 6px; }
    </style>
</head>
<body>
    <h2>aether's Admin (/inv)</h2>
    
    <div style="margin: 16px 0;">
        <form action="/inv/generate" method="post" style="display:inline;">
            <button type="submit">+ Generate Invite</button>
        </form>
    </div>

    <h3>Invites</h3>
    {% for code in invites %}
        <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <b>{{ code[0] }}</b> | Used: {{ "YES" if code[1] else "NO" }}
            </div>
            <form action="/inv/delete-invite" method="post">
                <input type="hidden" name="code" value="{{ code[0] }}">
                <button type="submit" class="btn-danger">Delete</button>
            </form>
        </div>
    {% endfor %}

    <h3>Users</h3>
    {% for u in users %}
        <div class="card">
            <div><b>{{ u[2] }}</b> (@{{ u[1] }}) | ID: {{ u[0] }}</div>
            <div>Banned: <b>{{ "YES" if u[6] else "NO" }}</b> | Prefix: <b>{{ u[7] }}</b></div>
            
            <div style="margin-top: 10px; display: flex; gap: 8px;">
                <form action="/inv/ban" method="post">
                    <input type="hidden" name="user_id" value="{{ u[0] }}">
                    <button type="submit" class="btn-danger">{{ "Unban" if u[6] else "Ban" }}</button>
                </form>

                <form action="/inv/prefix" method="post" style="display: flex; gap: 4px;">
                    <input type="hidden" name="user_id" value="{{ u[0] }}">
                    <input type="text" name="prefix" value="{{ u[7] }}" style="width: 70px;">
                    <button type="submit">Set Prefix</button>
                </form>
            </div>
        </div>
    {% endfor %}

    <h3>Posts</h3>
    {% for p in posts %}
        <div class="card">
            <div><b>{{ p[3] }}</b> (by {{ p[2] }})</div>
            <p style="font-size: 12px; color: #888;">{{ p[4] }}</p>
            <div style="margin-top: 8px; display: flex; gap: 8px;">
                <form action="/inv/toggle-pin" method="post">
                    <input type="hidden" name="post_id" value="{{ p[0] }}">
                    <button type="submit">{{ "Unpin" if p[6] else "Pin" }}</button>
                </form>
                <form action="/inv/delete-post" method="post">
                    <input type="hidden" name="post_id" value="{{ p[0] }}">
                    <button type="submit" class="btn-danger">Delete Post</button>
                </form>
            </div>
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

@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = telebot.types.InlineKeyboardMarkup()
    web_app_info = telebot.types.WebAppInfo(url=request.host_url)
    btn = telebot.types.InlineKeyboardButton(text="Open aether's App", web_app=web_app_info)
    markup.add(btn)
    bot.send_message(message.chat.id, "Welcome to aether's:", reply_markup=markup)

@app.route('/api/user/sync', methods=['POST'])
def sync_user():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, avatar_url) VALUES (?, ?, ?, ?)",
                (data['id'], data['username'], data['first_name'], data.get('avatar_url', '')))
    cur.execute("SELECT user_id, username, first_name, avatar_url, is_invited, used_code, is_banned, prefix FROM users WHERE user_id = ?", (data['id'],))
    u = cur.fetchone()
    conn.commit()
    conn.close()
    
    user_dict = {
        "id": u[0], "username": u[1], "first_name": u[2],
        "avatar_url": u[3], "is_invited": u[4], "used_code": u[5],
        "is_banned": u[6], "prefix": u[7]
    }
    return jsonify({"user": user_dict})

@app.route('/api/user/<int:user_id>')
def get_user_profile(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, first_name, avatar_url, is_invited, prefix FROM users WHERE user_id = ?", (user_id,))
    u = cur.fetchone()
    conn.close()
    if u:
        return jsonify({"user": {"user_id": u[0], "username": u[1], "first_name": u[2], "avatar_url": u[3], "is_invited": u[4], "prefix": u[5]}})
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
    return jsonify({"success": False, "message": "Invalid or used code"})

@app.route('/api/posts')
def get_posts():
    q = request.args.get('q', '').strip()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if q:
        cur.execute("""
            SELECT p.id, p.author_id, p.author_name, p.title, p.content, p.image_url, p.allow_comments, p.is_pinned,
            (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) as comments_count
            FROM posts p WHERE p.title LIKE ? OR p.content LIKE ?
            ORDER BY p.is_pinned DESC, p.id DESC
        """, (f"%{q}%", f"%{q}%"))
    else:
        cur.execute("""
            SELECT p.id, p.author_id, p.author_name, p.title, p.content, p.image_url, p.allow_comments, p.is_pinned,
            (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) as comments_count
            FROM posts p ORDER BY p.is_pinned DESC, p.id DESC LIMIT 10
        """)
    rows = cur.fetchall()
    conn.close()
    return jsonify([{
        "id": r[0], "author_id": r[1], "author_name": r[2],
        "title": r[3], "content": r[4], "image_url": r[5],
        "allow_comments": r[6], "is_pinned": r[7], "comments_count": r[8]
    } for r in rows])

@app.route('/api/posts/<int:post_id>')
def get_post_detail(post_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, author_id, author_name, title, content, image_url, allow_comments, is_pinned FROM posts WHERE id = ?", (post_id,))
    p = cur.fetchone()
    cur.execute("SELECT id, author_id, author_name, content, created_at FROM comments WHERE post_id = ? ORDER BY id ASC", (post_id,))
    comments = cur.fetchall()
    conn.close()
    
    if not p: return jsonify({"error": "Not found"}), 404
    
    post_dict = {"id": p[0], "author_id": p[1], "author_name": p[2], "title": p[3], "content": p[4], "image_url": p[5], "allow_comments": p[6], "is_pinned": p[7]}
    comments_list = [{"id": c[0], "author_id": c[1], "author_name": c[2], "content": c[3], "created_at": c[4]} for c in comments]
    return jsonify({"post": post_dict, "comments": comments_list})

@app.route('/api/posts/create', methods=['POST'])
def create_post():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO posts (author_id, author_name, title, content, image_url, allow_comments) VALUES (?, ?, ?, ?, ?, ?)",
                (data['author_id'], data['author_name'], data['title'], data['content'], data.get('image_url', ''), data.get('allow_comments', 1)))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/posts/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO comments (post_id, author_id, author_name, content) VALUES (?, ?, ?, ?)",
                (post_id, data['author_id'], data['author_name'], data['content']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# --- ADMIN ROUTES (/inv) ---

@app.route('/inv')
def admin_panel():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT code, is_used FROM invites")
    invites = cur.fetchall()
    cur.execute("SELECT user_id, username, first_name, avatar_url, is_invited, used_code, is_banned, prefix FROM users")
    users = cur.fetchall()
    cur.execute("SELECT id, author_id, author_name, title, content, image_url, is_pinned FROM posts ORDER BY id DESC")
    posts = cur.fetchall()
    conn.close()
    return render_template_string(ADMIN_TEMPLATE, invites=invites, users=users, posts=posts)

@app.route('/inv/generate', methods=['POST'])
def gen_invite():
    code = generate_code()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO invites (code) VALUES (?)", (code,))
    conn.commit()
    conn.close()
    return redirect('/inv')

@app.route('/inv/delete-invite', methods=['POST'])
def del_invite():
    code = request.form.get('code')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM invites WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    return redirect('/inv')

@app.route('/inv/ban', methods=['POST'])
def ban_user():
    user_id = request.form.get('user_id')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_banned = CASE WHEN is_banned=1 THEN 0 ELSE 1 END WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect('/inv')

@app.route('/inv/prefix', methods=['POST'])
def set_prefix():
    user_id = request.form.get('user_id')
    prefix = request.form.get('prefix', 'USER').upper()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET prefix = ? WHERE user_id = ?", (prefix, user_id))
    conn.commit()
    conn.close()
    return redirect('/inv')

@app.route('/inv/delete-post', methods=['POST'])
def del_post():
    post_id = request.form.get('post_id')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    cur.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
    conn.commit()
    conn.close()
    return redirect('/inv')

@app.route('/inv/toggle-pin', methods=['POST'])
def toggle_pin():
    post_id = request.form.get('post_id')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE posts SET is_pinned = CASE WHEN is_pinned=1 THEN 0 ELSE 1 END WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return redirect('/inv')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
