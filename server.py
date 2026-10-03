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

    # =========================
    # USERS TABLE
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            bio TEXT DEFAULT ''
        )
    """)

    # =========================
    # MEDIA TABLE
    # =========================

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

    # =========================
    # LIKES TABLE
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            media_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, media_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (media_id) REFERENCES media(id)
        )
    """)

    # =========================
    # FOLLOWERS TABLE
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER NOT NULL,
            following_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(follower_id, following_id),
            FOREIGN KEY (follower_id) REFERENCES users(id),
            FOREIGN KEY (following_id) REFERENCES users(id)
        )
    """)

    # =========================
    # COMMENTS TABLE
    # =========================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            media_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (media_id) REFERENCES media(id)
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
# PROFILE PAGE
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
    background: #000;
    color: #fff;
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
    gap: 40px;
    margin-bottom: 30px;
}

.stat {
    text-align: center;
}

.stat-number {
    font-size: 22px;
    font-weight: bold;
}

.stat-label {
    color: #aaa;
    font-size: 14px;
}

button {
    background: #ff0050;
    color: white;
    border: none;
    padding: 12px 25px;
    border-radius: 8px;
    font-size: 16px;
}

a {
    color: white;
    text-decoration: none;
}

</style>

</head>

<body>

<div class="profile">

    <div class="username">
        {{ user["username"] }}
    </div>

    <div class="bio">
        {{ user["bio"] }}
    </div>

    <div class="stats">

        <div class="stat">

            <div class="stat-number">
                0
            </div>

            <div class="stat-label">
                Following
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                0
            </div>

            <div class="stat-label">
                Followers
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {{ post_count }}
            </div>

            <div class="stat-label">
                Posts
            </div>

        </div>

    </div>

    <a href="/">
        <button>Back to Feed</button>
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

body {
    margin: 0;
    background: #000;
    color: #fff;
    font-family: Arial, sans-serif;
    overflow: hidden;
}

.feed {
    height: 100vh;
    overflow-y: scroll;
    scroll-snap-type: y mandatory;
}

.video {
    height: 100vh;
    position: relative;
    scroll-snap-align: start;
    background: #000;
}

.video video,
.video img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.overlay {
    position: absolute;
    bottom: 25px;
    left: 15px;
    right: 15px;
}

.username {
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 15px;
}

.actions {
    position: absolute;
    right: 10px;
    bottom: 30px;
    display: flex;
    flex-direction: column;
    gap: 15px;
}

.action-btn {
    border: none;
    background: rgba(0,0,0,0.5);
    color: white;
    width: 55px;
    height: 55px;
    border-radius: 50%;
    font-size: 22px;
}

.count {
    text-align: center;
    font-size: 13px;
    margin-top: -10px;
}

.comment-box {
    position: fixed;
    left: 0;
    right: 0;
    bottom: -100%;
    height: 55%;
    background: #111;
    z-index: 100;
    transition: bottom 0.3s;
    padding: 20px;
    overflow-y: auto;
}

.comment-box.open {
    bottom: 0;
}

.comment-header {
    display: flex;
    justify-content: space-between;
    font-size: 20px;
    margin-bottom: 20px;
}

.comment {
    padding: 10px 0;
    border-bottom: 1px solid #333;
}

.comment-user {
    font-weight: bold;
}

.comment-text {
    color: #ddd;
    margin-top: 4px;
}

.comment-input {
    position: fixed;
    bottom: 10px;
    left: 15px;
    right: 15px;
    display: flex;
    gap: 10px;
}

.comment-input input {
    flex: 1;
    padding: 12px;
    border-radius: 20px;
    border: none;
}

.comment-input button {
    border: none;
    background: #ff0050;
    color: white;
    border-radius: 20px;
    padding: 0 18px;
}

</style>

</head>

<body>


<div class="feed">

{% for item in media %}

<div class="video">

{% if item["media_type"] == "video" %}

<video
    src="{{ item["url"] }}"
    autoplay
    muted
    loop
    playsinline>
</video>

{% else %}

<img src="{{ item["url"] }}">

{% endif %}


<div class="overlay">

<div class="username">
    @{{ item["username"] }}
</div>

</div>


<div class="actions">

<button
    class="action-btn"
    onclick="toggleLike(
        {{ item["id"] }},
        this
    )">

    {% if item["user_liked"] %}
        ❤️
    {% else %}
        🤍
    {% endif %}

</button>

<div class="count">
    {{ item["like_count"] }}
</div>


<button
    class="action-btn"
    onclick="openComments(
        {{ item["id"] }}
    )">

    💬

</button>

<div class="count">
    {{ item["comment_count"] }}
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
    onclick="closeComments()">

    ✕

</button>

</div>


<div id="commentsList"></div>


<div class="comment-input">

<input
    id="commentInput"
    type="text"
    maxlength="500"
    placeholder="Add a comment...">

<button
    onclick="sendComment()">

    Send

</button>

</div>

</div>


<script>

let currentMediaId = null;


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

    button.innerText =
        data.liked ? "❤️" : "🤍";

    const countElement =
        button.nextElementSibling;

    countElement.innerText =
        data.like_count;
}


function openComments(mediaId) {

    currentMediaId = mediaId;

    document
        .getElementById("commentBox")
        .classList
        .add("open");

    loadComments(mediaId);
}


function closeComments() {

    document
        .getElementById("commentBox")
        .classList
        .remove("open");

    currentMediaId = null;
}


async function loadComments(mediaId) {

    const response = await fetch(
        "/comments/" + mediaId
    );

    if (!response.ok) {
        return;
    }

    const comments =
        await response.json();

    const list =
        document.getElementById(
            "commentsList"
        );

    list.innerHTML = "";

    comments.forEach(
        function(comment) {

            addCommentToList(
                comment.username,
                comment.text
            );

        }
    );
}


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

    div.innerHTML = `

        <div class="comment-user">
            @${username}
        </div>

        <div class="comment-text">
            ${text}
        </div>

    `;

    list.appendChild(div);
}


async function sendComment() {

    const input =
        document.getElementById(
            "commentInput"
        );

    const text =
        input.value.trim();

    if (!text) {
        return;
    }

    if (!currentMediaId) {
        return;
    }

    const response =
        await fetch(
            "/comment/" + currentMediaId,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    text: text
                })
            }
        );

    if (!response.ok) {
        return;
    }

    const data =
        await response.json();

    addCommentToList(
        data.username,
        data.text
    );

    input.value = "";
}


document
    .getElementById("commentInput")
    .addEventListener(
        "keydown",
        function(event) {

            if (event.key === "Enter") {

                event.preventDefault();

                sendComment();

            }

        }
    );

</script>

</body>

</html>

"""


# =========================
# SIGNUP HTML
# =========================

SIGNUP_HTML = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Sign Up</title>

<style>

body {
    background: #000;
    color: white;
    font-family: Arial;
    padding: 30px;
}

input {
    display: block;
    width: 100%;
    padding: 12px;
    margin: 10px 0;
}

button {
    width: 100%;
    padding: 12px;
    background: #ff0050;
    color: white;
    border: none;
}

a {
    color: white;
}

</style>

</head>

<body>

<h1>Create Account</h1>

<form method="POST">

<input
    name="username"
    placeholder="Username"
    required>

<input
    name="password"
    type="password"
    placeholder="Password"
    required>

<button type="submit">
    Sign Up
</button>

</form>

<p>
Already have an account?
<a href="/login">Login</a>
</p>

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

<title>Login</title>

<style>

body {
    background: #000;
    color: white;
    font-family: Arial;
    padding: 30px;
}

input {
    display: block;
    width: 100%;
    padding: 12px;
    margin: 10px 0;
}

button {
    width: 100%;
    padding: 12px;
    background: #ff0050;
    color: white;
    border: none;
}

a {
    color: white;
}

</style>

</head>

<body>

<h1>Login</h1>

<form method="POST">

<input
    name="username"
    placeholder="Username"
    required>

<input
    name="password"
    type="password"
    placeholder="Password"
    required>

<button type="submit">
    Login
</button>

</form>

<p>
Don't have an account?
<a href="/signup">Create account</a>
</p>

</body>

</html>

"""


# =========================
# HOME / FEED
# =========================

@app.route("/")
def home():

    conn = get_db()

    current_user_id = session.get("user_id")

    media = conn.execute("""
        SELECT
            media.id,
            media.url,
            media.media_type,
            users.username,

            (
                SELECT COUNT(*)
                FROM likes
                WHERE likes.media_id = media.id
            ) AS like_count,

            (
                SELECT COUNT(*)
                FROM comments
                WHERE comments.media_id = media.id
            ) AS comment_count,

            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM likes
                    WHERE likes.media_id = media.id
                    AND likes.user_id = ?
                )
                THEN 1
                ELSE 0
            END AS user_liked

        FROM media

        JOIN users
        ON users.id = media.user_id

        ORDER BY media.created_at DESC
    """, (current_user_id or 0,)).fetchall()

    conn.close()

    return render_template_string(
        HTML,
        media=media
    )


# =========================
# LIKE / UNLIKE
# =========================

@app.route(
    "/like/<int:media_id>",
    methods=["POST"]
)
def like(media_id):

    if "user_id" not in session:

        return {
            "error": "Login required"
        }, 401

    user_id = session["user_id"]

    conn = get_db()

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


    like_count = conn.execute("""
        SELECT COUNT(*)
        FROM likes
        WHERE media_id = ?
    """, (
        media_id,
    )).fetchone()[0]


    conn.commit()

    conn.close()

    return {
        "liked": liked,
        "like_count": like_count
    }


# =========================
# ADD COMMENT
# =========================

@app.route(
    "/comment/<int:media_id>",
    methods=["POST"]
)
def add_comment(media_id):

    if "user_id" not in session:

        return {
            "error": "Login required"
        }, 401

    data = request.get_json()

    text = (
        data.get("text", "").strip()
        if data
        else ""
    )

    if not text:

        return {
            "error": "Comment cannot be empty"
        }, 400

    if len(text) > 500:

        return {
            "error": "Comment too long"
        }, 400


    user_id = session["user_id"]

    conn = get_db()

    media_exists = conn.execute("""
        SELECT id
        FROM media
        WHERE id = ?
    """, (
        media_id,
    )).fetchone()


    if not media_exists:

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


    username = conn.execute("""
        SELECT username
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()["username"]


    conn.commit()

    conn.close()


    return {
        "username": username,
        "text": text
    }


# =========================
# LOAD COMMENTS
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

        ORDER BY comments.created_at ASC
    """, (
        media_id,
    )).fetchall()


    conn.close()


    return [
        {
            "username": comment["username"],
            "text": comment["text"]
        }

        for comment in comments
    ]


# =========================
# SIGNUP
# =========================

@app.route(
    "/signup",
    methods=["GET", "POST"]
)
def signup():

    if request.method == "POST":

        username = request.form[
            "username"
        ].strip()

        password = request.form[
            "password"
        ]


        if not username or not password:

            return "Username and password required"


        hashed_password = (
            generate_password_hash(password)
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

            session["user_id"] = user_id
            session["username"] = username

            conn.close()

            return redirect("/")

        except sqlite3.IntegrityError:

            conn.close()

            return "Username already exists"


    return render_template_string(
        SIGNUP_HTML
    )


# =========================
# LOGIN
# =========================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form[
            "username"
        ].strip()

        password = request.form[
            "password"
        ]


        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (
            username,
        )).fetchone()


        conn.close()


        if not user:

            return "Invalid username or password"


        if not check_password_hash(
            user["password"],
            password
        ):

            return "Invalid username or password"


        session["user_id"] = user["id"]

        session["username"] = user["username"]


        return redirect("/")


    return render_template_string(
        LOGIN_HTML
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# PROFILE
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
    """, (
        user_id,
    )).fetchone()


    post_count = conn.execute("""
        SELECT COUNT(*)
        FROM media
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()[0]


    conn.close()


    return render_template_string(
        PROFILE_HTML,
        user=user,
        post_count=post_count
    )


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

        file = request.files.get(
            "file"
        )


        if not file:

            return "No file selected"


        result = cloudinary.uploader.upload(
            file,
            resource_type="auto"
        )


        url = result["secure_url"]


        resource_type = result.get(
            "resource_type",
            "image"
        )


        media_type = (
            "video"
            if resource_type == "video"
            else "image"
        )


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

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Upload</title>

<style>

body {
    background: #000;
    color: white;
    font-family: Arial;
    padding: 30px;
}

input {
    margin: 20px 0;
}

button {
    padding: 12px 25px;
    background: #ff0050;
    color: white;
    border: none;
}

</style>

</head>

<body>

<h1>Upload</h1>

<form
    method="POST"
    enctype="multipart/form-data">

<input
    type="file"
    name="file"
    accept="video/*,image/*"
    required>

<br>

<button type="submit">
    Upload
</button>

</form>

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