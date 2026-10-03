import os
import sqlite3
import cloudinary
import cloudinary.uploader

from flask import (
    Flask,
    request,
    render_template_string,
    redirect,
    session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

app = Flask(__name__)

# =========================
# SESSION SECURITY
# =========================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "temporary-secret-key-change-later"
)


# =========================
# DATABASE
# =========================

def get_db():

    conn = sqlite3.connect("app.db")

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    # USERS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            bio TEXT DEFAULT ''
        )
    """)

    # MEDIA TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            media_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
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
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)


# =========================
# PROFILE HTML
# =========================

PROFILE_HTML = """
<!DOCTYPE html>
<html>

<head>

<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>Profile</title>

<style>

body {
    margin: 0;
    background: #111;
    color: white;
    font-family: Arial, sans-serif;
    text-align: center;
}

.profile {
    padding: 35px 20px;
}

.avatar {
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: #333;
    margin: 30px auto 15px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 50px;
}

.name {
    font-size: 25px;
    font-weight: bold;
}

.bio {
    color: #ccc;
    margin: 10px 0 25px;
}

.stats {
    display: flex;
    justify-content: center;
    gap: 35px;
    margin-bottom: 30px;
}

.number {
    font-size: 20px;
    font-weight: bold;
}

.label {
    color: #aaa;
    font-size: 13px;
}

.button {
    display: inline-block;
    padding: 12px 22px;
    margin: 5px;
    background: white;
    color: black;
    text-decoration: none;
    border-radius: 22px;
    font-weight: bold;
}

.edit {
    max-width: 400px;
    margin: 30px auto;
    padding: 20px;
    background: #222;
    border-radius: 15px;
}

.input {
    width: 100%;
    padding: 12px;
    margin: 8px 0 15px;
    border: none;
    border-radius: 10px;
    box-sizing: border-box;
}

textarea.input {
    height: 90px;
    resize: none;
}

.save {
    width: 100%;
    padding: 12px;
    border: none;
    border-radius: 20px;
    background: white;
    color: black;
    font-weight: bold;
    cursor: pointer;
}

</style>

</head>

<body>

<div class="profile">

<div class="avatar">
👤
</div>

<div class="name">
@{{ profile.username }}
</div>

<div class="bio">
{{ profile.bio }}
</div>

<div class="stats">

<div>
<div class="number">0</div>
<div class="label">Following</div>
</div>

<div>
<div class="number">0</div>
<div class="label">Followers</div>
</div>

<div>
<div class="number">{{ post_count }}</div>
<div class="label">Posts</div>
</div>

</div>

<div class="edit">

<h2>✏️ Edit Profile</h2>

<form action="/profile" method="post">

<label>
Username
</label>

<input
class="input"
type="text"
name="username"
value="{{ profile.username }}"
maxlength="30"
required>

<label>
Bio
</label>

<textarea
class="input"
name="bio"
maxlength="150"
placeholder="Tell people about yourself..."
>{{ profile.bio }}</textarea>

<button
class="save"
type="submit">

Save Profile

</button>

</form>

</div>

<a class="button" href="/">
🎬 Feed
</a>

<a class="button" href="/upload">
📤 Upload
</a>

<a class="button" href="/logout">
🚪 Logout
</a>

</div>

</body>

</html>
"""


# =========================
# FEED HTML
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

html, body {
    margin: 0;
    padding: 0;
    background: black;
    color: white;
    font-family: Arial, sans-serif;
}

.feed {
    height: 100vh;
    overflow-y: scroll;
    scroll-snap-type: y mandatory;
}

.post {
    height: 100vh;
    width: 100%;
    position: relative;
    scroll-snap-align: start;
    display: flex;
    align-items: center;
    justify-content: center;
    background: black;
}

video, img {
    width: 100%;
    height: 100%;
    object-fit: contain;
}

.top {
    position: fixed;
    top: 15px;
    left: 0;
    right: 0;
    z-index: 20;
    text-align: center;
}

.nav-button {
    display: inline-block;
    padding: 10px 16px;
    margin: 3px;
    background: white;
    color: black;
    text-decoration: none;
    border-radius: 20px;
    font-weight: bold;
}

.side-buttons {
    position: absolute;
    right: 15px;
    bottom: 120px;
    z-index: 10;
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: center;
}

.action {
    background: rgba(0, 0, 0, 0.45);
    border: none;
    color: white;
    font-size: 30px;
    width: 55px;
    height: 55px;
    border-radius: 50%;
    cursor: pointer;
}

.liked {
    color: red;
}

.count {
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 10px;
}

.info {
    position: absolute;
    left: 15px;
    bottom: 35px;
    right: 90px;
    z-index: 10;
    text-align: left;
    text-shadow: 0 1px 4px black;
}

.username {
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 8px;
}

.caption {
    font-size: 15px;
}

.comments-box {
    display: none;
    position: absolute;
    left: 10px;
    right: 10px;
    bottom: 10px;
    background: white;
    color: black;
    padding: 15px;
    border-radius: 15px;
    z-index: 30;
}

.comments-list {
    max-height: 180px;
    overflow-y: auto;
    margin-bottom: 10px;
}

.comment-item {
    padding: 8px 0;
    border-bottom: 1px solid #ddd;
}

.comment-input {
    width: 75%;
    padding: 10px;
    border: 1px solid #ccc;
    border-radius: 20px;
}

.comment-send {
    width: 20%;
    padding: 10px;
    border: none;
    border-radius: 20px;
    background: black;
    color: white;
}

.close-comments {
    float: right;
    border: none;
    background: none;
    font-size: 20px;
}

.empty {
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
}

</style>

</head>

<body>

<div class="top">

<a class="nav-button" href="/">
🎬 Feed
</a>

<a class="nav-button" href="/upload">
📤 Upload
</a>

<a class="nav-button" href="/profile">
👤 Profile
</a>

<a class="nav-button" href="/login">
🔐 Login
</a>

<a class="nav-button" href="/signup">
📝 Sign Up
</a>

</div>

<div class="feed">

{% if media %}

{% for item in media %}

<div class="post">

{% if item.media_type == "video" %}

<video
controls
playsinline
loop
preload="metadata">

<source src="{{ item.url }}">

</video>

{% else %}

<img
src="{{ item.url }}"
alt="Uploaded image">

{% endif %}

<div class="side-buttons">

<button
class="action"
onclick="likePost(this)">
❤️
</button>

<div class="count">
0
</div>

<button
class="action"
onclick="openComments(this)">
💬
</button>

<div class="count comment-count">
0
</div>

<button
class="action"
onclick="sharePost('{{ item.url }}')">
↗️
</button>

<div class="count">
Share
</div>

</div>

<div class="info">

<div class="username">
@{{ item.username }}
</div>

<div class="caption">
My new video 🎬
</div>

</div>

<div class="comments-box">

<button
class="close-comments"
onclick="closeComments(this)">
✕
</button>

<h3>Comments</h3>

<div class="comments-list">
</div>

<input
class="comment-input"
type="text"
placeholder="Write a comment...">

<button
class="comment-send"
onclick="sendComment(this)">
Send
</button>

</div>

</div>

{% endfor %}

{% else %}

<div class="empty">

<div>

<h2>🎬 No videos yet</h2>

<p>
Tap Upload to add your first video.
</p>

</div>

</div>

{% endif %}

</div>

<script>

function likePost(button) {

    const count = button.nextElementSibling;

    let number = parseInt(count.innerText);

    if (button.classList.contains("liked")) {

        number--;

        button.classList.remove("liked");

    } else {

        number++;

        button.classList.add("liked");

    }

    count.innerText = number;
}


function openComments(button) {

    const post = button.closest(".post");

    const box = post.querySelector(".comments-box");

    box.style.display = "block";
}


function closeComments(button) {

    const box = button.closest(".comments-box");

    box.style.display = "none";
}


function sendComment(button) {

    const box = button.closest(".comments-box");

    const input =
        box.querySelector(".comment-input");

    const list =
        box.querySelector(".comments-list");

    const post =
        button.closest(".post");

    const count =
        post.querySelector(".comment-count");

    const text =
        input.value.trim();

    if (!text) {
        return;
    }

    const comment =
        document.createElement("div");

    comment.className = "comment-item";

    comment.innerText =
        text;

    list.appendChild(comment);

    input.value = "";

    count.innerText =
        list.children.length;
}


function sharePost(url) {

    if (navigator.share) {

        navigator.share({
            title: "MyTikTok",
            text: "Check out this video!",
            url: url
        });

    } else {

        navigator.clipboard.writeText(url);

        alert("Video link copied!");

    }
}

</script>

</body>

</html>
"""


# =========================
# SIGN UP HTML
# =========================

SIGNUP_HTML = """
<!DOCTYPE html>
<html>

<head>

<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>Sign Up - MyTikTok</title>

<style>

body {
    margin: 0;
    background: #111;
    color: white;
    font-family: Arial, sans-serif;
}

.container {
    max-width: 400px;
    margin: 60px auto;
    padding: 25px;
}

h1 {
    text-align: center;
}

.input {
    width: 100%;
    padding: 14px;
    margin: 8px 0 15px;
    border: none;
    border-radius: 10px;
    box-sizing: border-box;
}

.button {
    width: 100%;
    padding: 14px;
    border: none;
    border-radius: 25px;
    background: white;
    color: black;
    font-weight: bold;
    cursor: pointer;
}

.error {
    background: #500;
    padding: 12px;
    border-radius: 10px;
    margin-bottom: 15px;
    text-align: center;
}

.login {
    text-align: center;
    margin-top: 20px;
}

.login a {
    color: white;
}

</style>

</head>

<body>

<div class="container">

<h1>🎬 Create Account</h1>

{% if error %}

<div class="error">
{{ error }}
</div>

{% endif %}

<form action="/signup" method="post">

<label>
Username
</label>

<input
class="input"
type="text"
name="username"
maxlength="30"
required>

<label>
Password
</label>

<input
class="input"
type="password"
name="password"
required>

<button
class="button"
type="submit">

Create Account

</button>

</form>

<div class="login">

<a href="/login">
Already have an account? Login
</a>

<br><br>

<a href="/">
← Back to Feed
</a>

</div>

</div>

</body>

</html>
"""


# =========================
# LOGIN HTML
# =========================

LOGIN_HTML = """
<!DOCTYPE html>
<html>

<head>

<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>Login - MyTikTok</title>

<style>

body {
    margin: 0;
    background: #111;
    color: white;
    font-family: Arial, sans-serif;
}

.container {
    max-width: 400px;
    margin: 60px auto;
    padding: 25px;
}

h1 {
    text-align: center;
}

.input {
    width: 100%;
    padding: 14px;
    margin: 8px 0 15px;
    border: none;
    border-radius: 10px;
    box-sizing: border-box;
}

.button {
    width: 100%;
    padding: 14px;
    border: none;
    border-radius: 25px;
    background: white;
    color: black;
    font-weight: bold;
    cursor: pointer;
}

.error {
    background: #500;
    padding: 12px;
    border-radius: 10px;
    margin-bottom: 15px;
    text-align: center;
}

.signup {
    text-align: center;
    margin-top: 20px;
}

.signup a {
    color: white;
}

</style>

</head>

<body>

<div class="container">

<h1>🔐 Login</h1>

{% if error %}

<div class="error">
{{ error }}
</div>

{% endif %}

<form action="/login" method="post">

<label>
Username
</label>

<input
class="input"
type="text"
name="username"
required>

<label>
Password
</label>

<input
class="input"
type="password"
name="password"
required>

<button
class="button"
type="submit">

Login

</button>

</form>

<div class="signup">

<a href="/signup">
Create a new account
</a>

<br><br>

<a href="/">
← Back to Feed
</a>

</div>

</div>

</body>

</html>
"""


# =========================
# UPLOAD HTML
# =========================

UPLOAD_HTML = """
<!DOCTYPE html>
<html>

<head>

<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>Upload</title>

</head>

<body style="font-family:Arial;text-align:center;padding:30px">

<h1>📤 Upload</h1>

<form
action="/upload"
method="post"
enctype="multipart/form-data">

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

<a href="/">
← Back to Feed
</a>

</body>

</html>
"""


# =========================
# HOME ROUTE
# =========================

@app.route("/")
def home():

    conn = get_db()

    media = conn.execute("""
        SELECT
            media.id,
            media.url,
            media.media_type,
            users.username
        FROM media
        JOIN users
        ON media.user_id = users.id
        ORDER BY media.id DESC
    """).fetchall()

    conn.close()

    return render_template_string(
        HTML,
        media=media
    )


# =========================
# SIGN UP ROUTE
# =========================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "GET":

        return render_template_string(
            SIGNUP_HTML,
            error=""
        )

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    if not username or not password:

        return render_template_string(
            SIGNUP_HTML,
            error="Please enter a username and password."
        )

    if len(username) < 3:

        return render_template_string(
            SIGNUP_HTML,
            error="Username must be at least 3 characters."
        )

    if len(password) < 6:

        return render_template_string(
            SIGNUP_HTML,
            error="Password must be at least 6 characters."
        )

    password_hash = generate_password_hash(
        password
    )

    try:

        conn = get_db()

        cursor = conn.execute(
            """
            INSERT INTO users
            (username, password, bio)
            VALUES (?, ?, ?)
            """,
            (
                username,
                password_hash,
                "Welcome to my profile 🎬"
            )
        )

        conn.commit()

        user_id = cursor.lastrowid

        conn.close()

        session["user_id"] = user_id
        session["username"] = username

        return redirect("/profile")

    except sqlite3.IntegrityError:

        return render_template_string(
            SIGNUP_HTML,
            error="That username is already taken."
        )


# =========================
# LOGIN ROUTE
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":

        return render_template_string(
            LOGIN_HTML,
            error=""
        )

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    if not username or not password:

        return render_template_string(
            LOGIN_HTML,
            error="Please enter your username and password."
        )

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    conn.close()

    if user is None:

        return render_template_string(
            LOGIN_HTML,
            error="Invalid username or password."
        )

    if not check_password_hash(
        user["password"],
        password
    ):

        return render_template_string(
            LOGIN_HTML,
            error="Invalid username or password."
        )

    session["user_id"] = user["id"]
    session["username"] = user["username"]

    return redirect("/profile")


# =========================
# LOGOUT ROUTE
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# PROFILE ROUTE
# =========================

@app.route("/profile", methods=["GET", "POST"])
def profile_page():

    if "user_id" not in session:

        return redirect("/login")

    user_id = session["user_id"]

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    post_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM media
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    conn.close()

    if user is None:

        session.clear()

        return redirect("/login")

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        bio = request.form.get(
            "bio",
            ""
        ).strip()

        if not username:

            username = user["username"]

        try:

            conn = get_db()

            conn.execute(
                """
                UPDATE users
                SET username = ?, bio = ?
                WHERE id = ?
                """,
                (
                    username,
                    bio,
                    user_id
                )
            )

            conn.commit()
            conn.close()

            session["username"] = username

            return redirect("/profile")

        except sqlite3.IntegrityError:

            return "That username is already taken.", 400

    profile = {
        "username": user["username"],
        "bio": user["bio"]
    }

    return render_template_string(
        PROFILE_HTML,
        profile=profile,
        post_count=post_count
    )


# =========================
# UPLOAD ROUTE
# =========================

@app.route("/upload", methods=["GET", "POST"])
def upload():

    if "user_id" not in session:

        return redirect("/login")

    if request.method == "GET":

        return render_template_string(
            UPLOAD_HTML
        )

    if "file" not in request.files:

        return "No file selected", 400

    file = request.files["file"]

    if not file.filename:

        return "No file selected", 400

    try:

        result = cloudinary.uploader.upload(
            file,
            resource_type="auto"
        )

        conn = get_db()

        conn.execute(
            """
            INSERT INTO media
            (user_id, url, media_type)
            VALUES (?, ?, ?)
            """,
            (
                session["user_id"],
                result["secure_url"],
                result["resource_type"]
            )
        )

        conn.commit()
        conn.close()

        return """
        <html>

        <body
        style="font-family:Arial;text-align:center;padding:30px">

        <h2>✅ Upload successful!</h2>

        <p>Your upload is now connected to your account.</p>

        <br>

        <a href="/">
        🎬 View Feed
        </a>

        </body>

        </html>
        """

    except Exception as e:

        return f"""
        <h2>Upload failed</h2>
        <p>{str(e)}</p>
        """, 500


# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )