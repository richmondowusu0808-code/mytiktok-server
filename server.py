import os
import sqlite3

import cloudinary
import cloudinary.uploader

from flask import Flask, request, render_template_string, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "temporary-secret-key-change-later"
)

DATABASE = "app.db"


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            bio TEXT DEFAULT ''
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            media_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            media_id INTEGER NOT NULL,
            UNIQUE(user_id, media_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER NOT NULL,
            following_id INTEGER NOT NULL,
            UNIQUE(follower_id, following_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            media_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            notification_type TEXT NOT NULL,
            media_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================
# CLOUDINARY
# =========================

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)


# =========================
# NOTIFICATION HELPER
# =========================

def create_notification(
    conn,
    user_id,
    sender_id,
    notification_type,
    media_id=None
):
    if user_id == sender_id:
        return

    conn.execute("""
        INSERT INTO notifications (
            user_id,
            sender_id,
            notification_type,
            media_id
        )
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        sender_id,
        notification_type,
        media_id
    ))


# =========================
# NOTIFICATIONS PAGE
# =========================

NOTIFICATIONS_HTML = """
<!DOCTYPE html>
<html>

<head>

<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>Notifications</title>

<style>

body {
    margin: 0;
    background: #000;
    color: white;
    font-family: Arial, sans-serif;
}

.header {
    padding: 20px;
    text-align: center;
    border-bottom: 1px solid #333;
    font-size: 24px;
    font-weight: bold;
}

.notification {
    padding: 18px;
    border-bottom: 1px solid #333;
}

.unread {
    background: #181818;
}

.username {
    color: #ff0050;
    font-weight: bold;
}

.time {
    color: #888;
    font-size: 13px;
    margin-top: 5px;
}

.empty {
    text-align: center;
    color: #aaa;
    padding: 50px 20px;
}

.back {
    display: block;
    margin: 25px auto;
    width: fit-content;
    color: white;
    text-decoration: none;
    background: #ff0050;
    padding: 12px 22px;
    border-radius: 8px;
}

</style>

</head>

<body>

<div class="header">
    🔔 Notifications
</div>

{% if notifications %}

{% for item in notifications %}

<div class="notification {% if not item['is_read'] %}unread{% endif %}">

    <div>

        <span class="username">
            @{{ item["username"] }}
        </span>

        {% if item["notification_type"] == "like" %}

            liked your video ❤️

        {% elif item["notification_type"] == "comment" %}

            commented on your video 💬

        {% elif item["notification_type"] == "follow" %}

            started following you 👤

        {% endif %}

    </div>

    <div class="time">
        {{ item["created_at"] }}
    </div>

</div>

{% endfor %}

{% else %}

<div class="empty">
    No notifications yet.
</div>

{% endif %}

<a class="back" href="/">
    ← Back to Feed
</a>

</body>

</html>
"""


# =========================
# PUBLIC PROFILE
# =========================

PUBLIC_PROFILE_HTML = """
<!DOCTYPE html>
<html>

<head>

<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>{{ user["username"] }}</title>

<style>

body {
    margin: 0;
    background: #000;
    color: white;
    font-family: Arial, sans-serif;
}

.profile {
    padding: 30px 20px;
    text-align: center;
}

.username {
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 10px;
}

.bio {
    color: #ccc;
    margin-bottom: 25px;
}

.stats {
    display: flex;
    justify-content: center;
    gap: 35px;
    margin-bottom: 25px;
}

.stat-number {
    font-size: 22px;
    font-weight: bold;
}

.stat-label {
    color: #aaa;
    font-size: 14px;
}

.follow-button {
    background: #ff0050;
    color: white;
    border: none;
    padding: 12px 30px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: bold;
}

.following {
    background: #333;
}

.back-button {
    display: inline-block;
    margin-top: 20px;
    color: white;
}

</style>

</head>

<body>

<div class="profile">

    <div class="username">
        @{{ user["username"] }}
    </div>

    <div class="bio">
        {{ user["bio"] }}
    </div>

    <div class="stats">

        <div>
            <div class="stat-number">
                {{ following_count }}
            </div>

            <div class="stat-label">
                Following
            </div>
        </div>

        <div>
            <div class="stat-number" id="followerCount">
                {{ follower_count }}
            </div>

            <div class="stat-label">
                Followers
            </div>
        </div>

        <div>
            <div class="stat-number">
                {{ post_count }}
            </div>

            <div class="stat-label">
                Posts
            </div>
        </div>

    </div>


    {% if current_user_id and current_user_id != user["id"] %}

    <button
        id="followButton"
        class="follow-button {% if is_following %}following{% endif %}"
        onclick="toggleFollow()">

        {% if is_following %}
        Following
        {% else %}
        Follow
        {% endif %}

    </button>

    {% elif not current_user_id %}

    <a href="/login">

        <button class="follow-button">
            Login to Follow
        </button>

    </a>

    {% endif %}

    <br>

    <a class="back-button" href="/">
        ← Back to Feed
    </a>

</div>


<script>

async function toggleFollow() {

    const response = await fetch(
        "/follow/{{ user['id'] }}",
        {
            method: "POST"
        }
    );

    if (!response.ok) {
        return;
    }

    const data = await response.json();

    const button =
        document.getElementById("followButton");

    const count =
        document.getElementById("followerCount");

    button.innerText =
        data.following
        ? "Following"
        : "Follow";

    button.classList.toggle(
        "following",
        data.following
    );

    count.innerText =
        data.follower_count;
}

</script>

</body>
</html>
"""


# =========================
# MY PROFILE
# =========================

PROFILE_HTML = """
<!DOCTYPE html>
<html>

<head>

<meta name="viewport"
content="width=device-width, initial-scale=1">

<style>

body {
    margin: 0;
    background: #000;
    color: white;
    font-family: Arial, sans-serif;
    text-align: center;
}

.profile {
    padding: 30px 20px;
}

.username {
    font-size: 28px;
    font-weight: bold;
}

.bio {
    color: #ccc;
    margin: 15px 0 25px;
}

.stats {
    display: flex;
    justify-content: center;
    gap: 35px;
    margin-bottom: 25px;
}

.number {
    font-size: 22px;
    font-weight: bold;
}

.label {
    color: #aaa;
    font-size: 14px;
}

.button {
    display: inline-block;
    padding: 12px 20px;
    margin: 5px;
    background: #ff0050;
    color: white;
    text-decoration: none;
    border-radius: 8px;
}

.notification-button {
    display: inline-block;
    padding: 12px 20px;
    margin: 5px;
    background: #333;
    color: white;
    text-decoration: none;
    border-radius: 8px;
}

.badge {
    background: #ff0050;
    border-radius: 50%;
    padding: 3px 7px;
    font-size: 12px;
}

</style>

</head>

<body>

<div class="profile">

    <div class="username">
        @{{ user["username"] }}
    </div>

    <div class="bio">
        {{ user["bio"] }}
    </div>

    <div class="stats">

        <div>
            <div class="number">
                {{ following_count }}
            </div>

            <div class="label">
                Following
            </div>
        </div>

        <div>
            <div class="number">
                {{ follower_count }}
            </div>

            <div class="label">
                Followers
            </div>
        </div>

        <div>
            <div class="number">
                {{ post_count }}
            </div>

            <div class="label">
                Posts
            </div>
        </div>

    </div>


    <a class="notification-button"
       href="/notifications">

        🔔 Notifications

        {% if notification_count > 0 %}

        <span class="badge">
            {{ notification_count }}
        </span>

        {% endif %}

    </a>


    <br>

    <a class="button" href="/">
        Feed
    </a>

    <a class="button" href="/upload">
        Upload
    </a>

    <a class="button" href="/logout">
        Logout
    </a>

</div>

</body>

</html>
"""


# =========================
# FEED
# =========================

HTML = """
<!DOCTYPE html>
<html>

<head>

<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>MyTikTok</title>

<style>

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    padding: 0;
    background: #000;
    color: white;
    font-family: Arial, sans-serif;
}

.feed {
    height: 100vh;
    overflow-y: scroll;
    scroll-snap-type: y mandatory;
}

.video-card {
    position: relative;
    height: 100vh;
    scroll-snap-align: start;
    background: #000;
}

.media {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.overlay {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 25px 20px 40px;
    background: linear-gradient(
        transparent,
        rgba(0, 0, 0, 0.85)
    );
}

.username {
    display: inline-block;
    color: white;
    text-decoration: none;
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 15px;
}

.actions {
    display: flex;
    align-items: center;
    gap: 12px;
}

.action-button {
    width: 55px;
    height: 55px;
    border: none;
    border-radius: 50%;
    background: rgba(0, 0, 0, 0.6);
    color: white;
    font-size: 24px;
}

.liked {
    color: #ff0050;
}

.like-count {
    margin-right: 10px;
}

.top-buttons {
    position: fixed;
    top: 15px;
    right: 15px;
    z-index: 500;
}

.top-button {
    display: inline-block;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 10px 14px;
    margin-left: 5px;
    border-radius: 8px;
    text-decoration: none;
}

.notification-link {
    position: fixed;
    top: 15px;
    left: 15px;
    z-index: 500;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 10px 14px;
    border-radius: 8px;
    text-decoration: none;
}

.badge {
    background: #ff0050;
    border-radius: 50%;
    padding: 3px 7px;
    font-size: 12px;
}

.comment-box {
    position: fixed;
    left: 0;
    right: 0;
    bottom: -100%;
    height: 55%;
    background: #111;
    z-index: 1000;
    transition: bottom 0.3s;
    padding: 20px;
    overflow-y: auto;
}

.comment-box.open {
    bottom: 0;
}

.comment-header {
    position: sticky;
    top: 0;
    z-index: 1001;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #111;
    font-size: 20px;
    padding-bottom: 10px;
}

.close-button {
    width: 45px;
    height: 45px;
    border: none;
    border-radius: 50%;
    background: #ff0050;
    color: white;
    font-size: 24px;
    font-weight: bold;
}

.comment {
    padding: 12px 0;
    border-bottom: 1px solid #333;
}

.comment-user {
    font-weight: bold;
    margin-bottom: 5px;
}

.comment-text {
    color: #ddd;
}

.comment-form {
    display: flex;
    gap: 10px;
    position: sticky;
    bottom: 0;
    background: #111;
    padding-top: 10px;
}

.comment-input {
    flex: 1;
    padding: 12px;
    border-radius: 8px;
    border: none;
}

.comment-submit {
    background: #ff0050;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 18px;
}

</style>

</head>

<body>


{% if session.get("user_id") %}

<a class="notification-link"
   href="/notifications">

    🔔

    {% if notification_count > 0 %}

    <span class="badge">
        {{ notification_count }}
    </span>

    {% endif %}

</a>

{% endif %}


<div class="top-buttons">

{% if session.get("user_id") %}

<a class="top-button" href="/profile">
Profile
</a>

<a class="top-button" href="/upload">
Upload
</a>

{% else %}

<a class="top-button" href="/login">
Login
</a>

{% endif %}

</div>


<div class="feed">

{% for item in media %}

<div class="video-card">


{% if item["media_type"] == "video" %}

<video
    class="media"
    src="{{ item['url'] }}"
    autoplay
    muted
    loop
    playsinline>
</video>

{% else %}

<img
    class="media"
    src="{{ item['url'] }}">

{% endif %}


<div class="overlay">

<a
    class="username"
    href="/user/{{ item['username'] }}">

    @{{ item["username"] }}

</a>


<div class="actions">

<button
    class="action-button {% if item['liked'] %}liked{% endif %}"
    onclick="toggleLike(
        {{ item['id'] }},
        this
    )">

    ♥

</button>

<span
    class="like-count"
    id="like-count-{{ item['id'] }}">

    {{ item["like_count"] }}

</span>


<button
    class="action-button"
    onclick="openComments(
        {{ item['id'] }}
    )">

    💬

</button>

</div>

</div>

</div>

{% endfor %}

</div>


<div
    id="commentBox"
    class="comment-box">

    <div class="comment-header">

        <span>
            Comments
        </span>

        <button
            type="button"
            class="close-button"
            onclick="closeComments()">

            ✕

        </button>

    </div>

    <div id="commentsList"></div>


{% if session.get("user_id") %}

<form
    class="comment-form"
    onsubmit="submitComment(event)">

    <input
        id="commentInput"
        class="comment-input"
        type="text"
        maxlength="500"
        placeholder="Add a comment..."
        required>

    <button
        class="comment-submit"
        type="submit">

        Post

    </button>

</form>

{% else %}

<p>

    <a href="/login"
       style="color:#ff0050;">

        Login to comment

    </a>

</p>

{% endif %}

</div>


<script>

let currentCommentMediaId = null;


async function toggleLike(mediaId, button) {

    const response = await fetch(
        "/like/" + mediaId,
        {
            method: "POST"
        }
    );

    if (!response.ok) {
        return;
    }

    const data = await response.json();

    document.getElementById(
        "like-count-" + mediaId
    ).innerText = data.like_count;

    button.classList.toggle(
        "liked",
        data.liked
    );
}


async function openComments(mediaId) {

    currentCommentMediaId = mediaId;

    document.getElementById(
        "commentBox"
    ).classList.add("open");

    const list = document.getElementById(
        "commentsList"
    );

    list.innerHTML =
        "<p>Loading...</p>";

    const response = await fetch(
        "/comments/" + mediaId
    );

    if (!response.ok) {

        list.innerHTML =
            "<p>Could not load comments.</p>";

        return;
    }

    const comments =
        await response.json();

    list.innerHTML = "";

    if (comments.length === 0) {

        list.innerHTML =
            "<p>No comments yet.</p>";

        return;
    }

    comments.forEach(function(comment) {

        addCommentToList(
            comment.username,
            comment.text
        );

    });
}


function closeComments() {

    document.getElementById(
        "commentBox"
    ).classList.remove("open");

    currentCommentMediaId = null;
}


document.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Escape") {
            closeComments();
        }

    }
);


function addCommentToList(
    username,
    text
) {

    const list =
        document.getElementById(
            "commentsList"
        );

    const div =
        document.createElement("div");

    div.className = "comment";


    const userDiv =
        document.createElement("div");

    userDiv.className =
        "comment-user";

    userDiv.innerText =
        "@" + username;


    const textDiv =
        document.createElement("div");

    textDiv.className =
        "comment-text";

    textDiv.innerText =
        text;


    div.appendChild(userDiv);
    div.appendChild(textDiv);

    list.appendChild(div);
}


async function submitComment(event) {

    event.preventDefault();

    if (!currentCommentMediaId) {
        return;
    }

    const input =
        document.getElementById(
            "commentInput"
        );

    const text =
        input.value.trim();

    if (!text) {
        return;
    }

    const formData =
        new FormData();

    formData.append(
        "text",
        text
    );

    const response =
        await fetch(
            "/comment/" +
            currentCommentMediaId,
            {
                method: "POST",
                body: formData
            }
        );

    if (!response.ok) {
        return;
    }

    const data =
        await response.json();

    input.value = "";

    addCommentToList(
        data.username,
        data.text
    );
}

</script>

</body>

</html>
"""


# =========================
# HOME
# =========================

@app.route("/")
def home():

    conn = get_db()

    current_user_id = session.get("user_id")

    rows = conn.execute("""
        SELECT
            media.id,
            media.url,
            media.media_type,
            users.username
        FROM media
        JOIN users
            ON users.id = media.user_id
        ORDER BY media.id DESC
    """).fetchall()

    media = []

    for item in rows:

        like_count = conn.execute("""
            SELECT COUNT(*)
            FROM likes
            WHERE media_id = ?
        """, (item["id"],)).fetchone()[0]

        liked = False

        if current_user_id:

            existing = conn.execute("""
                SELECT id
                FROM likes
                WHERE user_id = ?
                AND media_id = ?
            """, (
                current_user_id,
                item["id"]
            )).fetchone()

            liked = existing is not None

        media.append({
            "id": item["id"],
            "url": item["url"],
            "media_type": item["media_type"],
            "username": item["username"],
            "like_count": like_count,
            "liked": liked
        })

    notification_count = 0

    if current_user_id:

        notification_count = conn.execute("""
            SELECT COUNT(*)
            FROM notifications
            WHERE user_id = ?
            AND is_read = 0
        """, (current_user_id,)).fetchone()[0]

    conn.close()

    return render_template_string(
        HTML,
        media=media,
        notification_count=notification_count
    )


# =========================
# LIKE
# =========================

@app.route(
    "/like/<int:media_id>",
    methods=["POST"]
)
def like_media(media_id):

    if "user_id" not in session:
        return {
            "error": "Login required"
        }, 401

    user_id = session["user_id"]

    conn = get_db()

    media = conn.execute("""
        SELECT user_id
        FROM media
        WHERE id = ?
    """, (media_id,)).fetchone()

    if not media:

        conn.close()

        return {
            "error": "Media not found"
        }, 404

    existing = conn.execute("""
        SELECT id
        FROM likes
        WHERE user_id = ?
        AND media_id = ?
    """, (
        user_id,
        media_id
    )).fetchone()

    if existing:

        conn.execute("""
            DELETE FROM likes
            WHERE user_id = ?
            AND media_id = ?
        """, (
            user_id,
            media_id
        ))

        liked = False

    else:

        conn.execute("""
            INSERT INTO likes (
                user_id,
                media_id
            )
            VALUES (?, ?)
        """, (
            user_id,
            media_id
        ))

        liked = True

        create_notification(
            conn,
            media["user_id"],
            user_id,
            "like",
            media_id
        )

    like_count = conn.execute("""
        SELECT COUNT(*)
        FROM likes
        WHERE media_id = ?
    """, (media_id,)).fetchone()[0]

    conn.commit()
    conn.close()

    return {
        "liked": liked,
        "like_count": like_count
    }


# =========================
# COMMENTS
# =========================

@app.route(
    "/comments/<int:media_id>"
)
def get_comments(media_id):

    conn = get_db()

    comments = conn.execute("""
        SELECT
            comments.text,
            users.username
        FROM comments
        JOIN users
            ON users.id = comments.user_id
        WHERE comments.media_id = ?
        ORDER BY comments.id ASC
    """, (media_id,)).fetchall()

    result = []

    for comment in comments:

        result.append({
            "username": comment["username"],
            "text": comment["text"]
        })

    conn.close()

    return result


@app.route(
    "/comment/<int:media_id>",
    methods=["POST"]
)
def add_comment(media_id):

    if "user_id" not in session:
        return {
            "error": "Login required"
        }, 401

    text = request.form.get(
        "text",
        ""
    ).strip()

    if not text:

        return {
            "error": "Comment cannot be empty"
        }, 400

    if len(text) > 500:

        return {
            "error": "Comment is too long"
        }, 400

    user_id = session["user_id"]

    conn = get_db()

    media = conn.execute("""
        SELECT id, user_id
        FROM media
        WHERE id = ?
    """, (media_id,)).fetchone()

    if not media:

        conn.close()

        return {
            "error": "Media not found"
        }, 404

    conn.execute("""
        INSERT INTO comments (
            user_id,
            media_id,
            text
        )
        VALUES (?, ?, ?)
    """, (
        user_id,
        media_id,
        text
    ))

    create_notification(
        conn,
        media["user_id"],
        user_id,
        "comment",
        media_id
    )

    user = conn.execute("""
        SELECT username
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    conn.commit()
    conn.close()

    return {
        "username": user["username"],
        "text": text
    }


# =========================
# SIGN UP
# =========================

@app.route(
    "/signup",
    methods=["GET", "POST"]
)
def signup():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not password:
            return "Username and password required."

        hashed_password = generate_password_hash(
            password
        )

        conn = get_db()

        try:

            cursor = conn.execute("""
                INSERT INTO users (
                    username,
                    password
                )
                VALUES (?, ?)
            """, (
                username,
                hashed_password
            ))

            conn.commit()

            user_id = cursor.lastrowid

        except sqlite3.IntegrityError:

            conn.close()

            return "Username already exists."

        conn.close()

        session["user_id"] = user_id

        return redirect("/")

    return """
    <html>
    <body style="background:#000;color:#fff;font-family:Arial;padding:30px">

    <h1>Sign Up</h1>

    <form method="POST">

    <input
        name="username"
        placeholder="Username"
        required
        style="padding:12px">

    <br><br>

    <input
        name="password"
        type="password"
        placeholder="Password"
        required
        style="padding:12px">

    <br><br>

    <button type="submit">
        Sign Up
    </button>

    </form>

    <br>

    <a href="/login" style="color:white">
        Already have an account? Login
    </a>

    </body>
    </html>
    """


# =========================
# LOGIN
# =========================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            return redirect("/")

        return "Invalid username or password."

    return """
    <html>
    <body style="background:#000;color:#fff;font-family:Arial;padding:30px">

    <h1>Login</h1>

    <form method="POST">

    <input
        name="username"
        placeholder="Username"
        required
        style="padding:12px">

    <br><br>

    <input
        name="password"
        type="password"
        placeholder="Password"
        required
        style="padding:12px">

    <br><br>

    <button type="submit">
        Login
    </button>

    </form>

    <br>

    <a href="/signup" style="color:white">
        Create account
    </a>

    </body>
    </html>
    """


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# MY PROFILE
# =========================

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    post_count = conn.execute("""
        SELECT COUNT(*)
        FROM media
        WHERE user_id = ?
    """, (user_id,)).fetchone()[0]

    follower_count = conn.execute("""
        SELECT COUNT(*)
        FROM followers
        WHERE following_id = ?
    """, (user_id,)).fetchone()[0]

    following_count = conn.execute("""
        SELECT COUNT(*)
        FROM followers
        WHERE follower_id = ?
    """, (user_id,)).fetchone()[0]

    notification_count = conn.execute("""
        SELECT COUNT(*)
        FROM notifications
        WHERE user_id = ?
        AND is_read = 0
    """, (user_id,)).fetchone()[0]

    conn.close()

    return render_template_string(
        PROFILE_HTML,
        user=user,
        post_count=post_count,
        follower_count=follower_count,
        following_count=following_count,
        notification_count=notification_count
    )


# =========================
# NOTIFICATIONS
# =========================

@app.route("/notifications")
def notifications():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_db()

    notifications = conn.execute("""
        SELECT
            notifications.id,
            notifications.notification_type,
            notifications.created_at,
            notifications.is_read,
            users.username
        FROM notifications
        JOIN users
            ON users.id = notifications.sender_id
        WHERE notifications.user_id = ?
        ORDER BY notifications.id DESC
    """, (user_id,)).fetchall()

    conn.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

    return render_template_string(
        NOTIFICATIONS_HTML,
        notifications=notifications
    )


# =========================
# PUBLIC PROFILE
# =========================

@app.route("/user/<username>")
def public_profile(username):

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE username = ?
    """, (username,)).fetchone()

    if not user:

        conn.close()

        return "User not found", 404

    user_id = user["id"]

    post_count = conn.execute("""
        SELECT COUNT(*)
        FROM media
        WHERE user_id = ?
    """, (user_id,)).fetchone()[0]

    follower_count = conn.execute("""
        SELECT COUNT(*)
        FROM followers
        WHERE following_id = ?
    """, (user_id,)).fetchone()[0]

    following_count = conn.execute("""
        SELECT COUNT(*)
        FROM followers
        WHERE follower_id = ?
    """, (user_id,)).fetchone()[0]

    current_user_id = session.get("user_id")

    is_following = False

    if current_user_id and current_user_id != user_id:

        existing = conn.execute("""
            SELECT id
            FROM followers
            WHERE follower_id = ?
            AND following_id = ?
        """, (
            current_user_id,
            user_id
        )).fetchone()

        is_following = existing is not None

    conn.close()

    return render_template_string(
        PUBLIC_PROFILE_HTML,
        user=user,
        post_count=post_count,
        follower_count=follower_count,
        following_count=following_count,
        is_following=is_following,
        current_user_id=current_user_id
    )


# =========================
# FOLLOW / UNFOLLOW
# =========================

@app.route(
    "/follow/<int:user_id>",
    methods=["POST"]
)
def follow_user(user_id):

    if "user_id" not in session:
        return {
            "error": "Login required"
        }, 401

    follower_id = session["user_id"]

    if follower_id == user_id:

        return {
            "error": "You cannot follow yourself"
        }, 400

    conn = get_db()

    target = conn.execute("""
        SELECT id
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    if not target:

        conn.close()

        return {
            "error": "User not found"
        }, 404

    existing = conn.execute("""
        SELECT id
        FROM followers
        WHERE follower_id = ?
        AND following_id = ?
    """, (
        follower_id,
        user_id
    )).fetchone()

    if existing:

        conn.execute("""
            DELETE FROM followers
            WHERE follower_id = ?
            AND following_id = ?
        """, (
            follower_id,
            user_id
        ))

        following = False

    else:

        conn.execute("""
            INSERT INTO followers (
                follower_id,
                following_id
            )
            VALUES (?, ?)
        """, (
            follower_id,
            user_id
        ))

        following = True

        create_notification(
            conn,
            user_id,
            follower_id,
            "follow"
        )

    follower_count = conn.execute("""
        SELECT COUNT(*)
        FROM followers
        WHERE following_id = ?
    """, (user_id,)).fetchone()[0]

    conn.commit()
    conn.close()

    return {
        "following": following,
        "follower_count": follower_count
    }


# =========================
# UPLOAD
# =========================

@app.route(
    "/upload",
    methods=["GET", "POST"]
)
def upload():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        file = request.files.get("file")

        if not file:
            return "No file selected."

        result = cloudinary.uploader.upload(
            file,
            resource_type="auto"
        )

        url = result.get("secure_url")

        resource_type = result.get(
            "resource_type"
        )

        if resource_type == "video":
            media_type = "video"
        else:
            media_type = "image"

        conn = get_db()

        conn.execute("""
            INSERT INTO media (
                user_id,
                url,
                media_type
            )
            VALUES (?, ?, ?)
        """, (
            session["user_id"],
            url,
            media_type
        ))

        conn.commit()
        conn.close()

        return redirect("/")

    return """
    <html>
    <body style="background:#000;color:#fff;font-family:Arial;padding:30px">

    <h1>Upload</h1>

    <form method="POST" enctype="multipart/form-data">

        <input
            type="file"
            name="file"
            accept="image/*,video/*"
            required>

        <br><br>

        <button type="submit">
            Upload
        </button>

    </form>

    <br>

    <a href="/" style="color:white">
        ← Back to Feed
    </a>

    </body>
    </html>
    """


# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
    )     