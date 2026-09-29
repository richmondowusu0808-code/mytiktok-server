from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

DATABASE = "tiktok.db"
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def database():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():

    db = database()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            filename TEXT,
            caption TEXT,
            likes INTEGER DEFAULT 0
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER,
            username TEXT,
            comment TEXT
        )
    """)

    db.commit()
    db.close()


@app.route("/")
def home():
    return "🔥 MyTikTok server is working!"


@app.route("/signup", methods=["POST"])
def signup():

    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({
            "success": False,
            "message": "Enter username and password"
        })

    db = database()

    try:

        db.execute(
            """
            INSERT INTO users
            (username, password)
            VALUES (?, ?)
            """,
            (username, password)
        )

        db.commit()

    except sqlite3.IntegrityError:

        db.close()

        return jsonify({
            "success": False,
            "message": "Username already exists"
        })

    db.close()

    return jsonify({
        "success": True,
        "message": "Account created"
    })


@app.route("/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")

    db = database()

    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE username=?
        AND password=?
        """,
        (username, password)
    ).fetchone()

    db.close()

    if user:

        return jsonify({
            "success": True,
            "username": username
        })

    return jsonify({
        "success": False,
        "message": "Invalid login"
    })


@app.route("/upload", methods=["POST"])
def upload():

    username = request.form.get("username")
    caption = request.form.get("caption", "")

    if "video" not in request.files:
        return jsonify({
            "success": False,
            "message": "No video selected"
        })

    video = request.files["video"]

    if not video.filename:
        return jsonify({
            "success": False,
            "message": "Invalid video"
        })

    filename = secure_filename(video.filename)

    path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    video.save(path)

    db = database()

    db.execute(
        """
        INSERT INTO videos
        (username, filename, caption)
        VALUES (?, ?, ?)
        """,
        (username, filename, caption)
    )

    db.commit()
    db.close()

    return jsonify({
        "success": True,
        "message": "Video uploaded"
    })


@app.route("/videos")
def videos():

    db = database()

    rows = db.execute(
        """
        SELECT *
        FROM videos
        ORDER BY id DESC
        """
    ).fetchall()

    db.close()

    result = []

    for row in rows:

        result.append({
            "id": row["id"],
            "username": row["username"],
            "caption": row["caption"],
            "likes": row["likes"],
            "video": "/video/" + row["filename"]
        })

    return jsonify(result)


@app.route("/video/<path:filename>")
def video(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


@app.route("/like/<int:video_id>", methods=["POST"])
def like(video_id):

    db = database()

    db.execute(
        """
        UPDATE videos
        SET likes = likes + 1
        WHERE id=?
        """,
        (video_id,)
    )

    db.commit()

    row = db.execute(
        """
        SELECT likes
        FROM videos
        WHERE id=?
        """,
        (video_id,)
    ).fetchone()

    db.close()

    if not row:

        return jsonify({
            "success": False,
            "message": "Video not found"
        }), 404

    return jsonify({
        "success": True,
        "likes": row["likes"]
    })


@app.route("/comment", methods=["POST"])
def comment():

    data = request.get_json(silent=True) or {}

    video_id = data.get("video_id")
    username = data.get("username")
    comment_text = data.get("comment")

    if not video_id or not username or not comment_text:

        return jsonify({
            "success": False,
            "message": "Missing information"
        })

    db = database()

    db.execute(
        """
        INSERT INTO comments
        (video_id, username, comment)
        VALUES (?, ?, ?)
        """,
        (video_id, username, comment_text)
    )

    db.commit()
    db.close()

    return jsonify({
        "success": True
    })


create_database()
