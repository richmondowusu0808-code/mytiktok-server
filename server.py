from flask import Flask, request, jsonify, send_from_directory
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)


def database():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )


def create_database():
    db = database()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id SERIAL PRIMARY KEY,
            username TEXT,
            filename TEXT,
            caption TEXT,
            likes INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY,
            video_id INTEGER,
            username TEXT,
            comment TEXT
        )
    """)

    db.commit()
    cursor.close()
    db.close()


# Serve the MyTikTok frontend
@app.route("/")
def home():
    return send_from_directory(app.root_path, "index.html")


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
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO users
            (username, password)
            VALUES (%s, %s)
            """,
            (username, password)
        )

        db.commit()

    except psycopg2.IntegrityError:
        db.rollback()
        cursor.close()
        db.close()

        return jsonify({
            "success": False,
            "message": "Username already exists"
        })

    cursor.close()
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
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE username = %s
        AND password = %s
        """,
        (username, password)
    )

    user = cursor.fetchone()

    cursor.close()
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

    try:
        result = cloudinary.uploader.upload(
            video,
            resource_type="video",
            folder="mytiktok/videos"
        )

        video_url = result["secure_url"]

    except Exception as error:
        return jsonify({
            "success": False,
            "message": "Video upload failed",
            "error": str(error)
        }), 500

    db = database()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO videos
        (username, filename, caption)
        VALUES (%s, %s, %s)
        """,
        (username, video_url, caption)
    )

    db.commit()

    cursor.close()
    db.close()

    return jsonify({
        "success": True,
        "message": "Video uploaded",
        "video": video_url
    })


@app.route("/videos")
def videos():
    db = database()
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM videos
        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()

    cursor.close()
    db.close()

    result = []

    for row in rows:
        video_url = row["filename"]

        if not video_url.startswith("http"):
            video_url = "/video/" + video_url

        result.append({
            "id": row["id"],
            "username": row["username"],
            "caption": row["caption"],
            "likes": row["likes"],
            "video": video_url
        })

    return jsonify(result)


@app.route("/like/<int:video_id>", methods=["POST"])
def like(video_id):
    db = database()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE videos
        SET likes = likes + 1
        WHERE id = %s
        """,
        (video_id,)
    )

    db.commit()

    cursor.execute(
        """
        SELECT likes
        FROM videos
        WHERE id = %s
        """,
        (video_id,)
    )

    row = cursor.fetchone()

    cursor.close()
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
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO comments
        (video_id, username, comment)
        VALUES (%s, %s, %s)
        """,
        (video_id, username, comment_text)
    )

    db.commit()

    cursor.close()
    db.close()

    return jsonify({
        "success": True
    })


create_database()
