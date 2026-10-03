import os
import cloudinary
import cloudinary.uploader
from flask import Flask, request, render_template_string

app = Flask(__name__)

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

# Temporary in-memory media list
media = []

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>My Media App</title>

    <style>
        body {
            margin: 0;
            background: #111;
            color: white;
            font-family: Arial, sans-serif;
        }

        header {
            padding: 18px;
            text-align: center;
            position: sticky;
            top: 0;
            background: #111;
            z-index: 10;
        }

        .upload {
            display: block;
            width: fit-content;
            margin: 10px auto 20px;
            padding: 12px 20px;
            background: white;
            color: black;
            text-decoration: none;
            border-radius: 8px;
        }

        .feed {
            max-width: 600px;
            margin: auto;
        }

        .post {
            margin-bottom: 25px;
            background: #000;
        }

        video, img {
            width: 100%;
            max-height: 80vh;
            object-fit: contain;
            display: block;
        }

        .empty {
            text-align: center;
            padding: 50px 20px;
            color: #aaa;
        }
    </style>
</head>

<body>

<header>
    <h2>🎬 My Media Feed</h2>
    <a class="upload" href="/upload">📤 Upload</a>
</header>

<div class="feed">

{% if media %}

    {% for item in media %}

        <div class="post">

        {% if item.type == "video" %}

            <video controls playsinline preload="metadata">
                <source src="{{ item.url }}">
            </video>

        {% else %}

            <img src="{{ item.url }}" alt="Uploaded image">

        {% endif %}

        </div>

    {% endfor %}

{% else %}

    <div class="empty">
        <h3>No uploads yet</h3>
        <p>Upload your first image or video.</p>
    </div>

{% endif %}

</div>

</body>
</html>
"""

UPLOAD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Upload</title>
</head>

<body style="font-family:Arial;text-align:center;padding:30px">

<h1>📤 Upload</h1>

<form action="/upload" method="post" enctype="multipart/form-data">

<input
    type="file"
    name="file"
    accept="image/*,video/*"
    required
>

<br><br>

<button type="submit">Upload</button>

</form>

<br>

<a href="/">← Back to Feed</a>

</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(
        HTML,
        media=media
    )


@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "GET":
        return render_template_string(UPLOAD_HTML)

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

        media.insert(0, {
            "url": result["secure_url"],
            "type": result["resource_type"]
        })

        return """
        <html>
        <body style="font-family:Arial;text-align:center;padding:30px">
            <h2>✅ Upload successful!</h2>
            <a href="/">🎬 View Feed</a>
        </body>
        </html>
        """

    except Exception as e:

        return f"""
        <h2>Upload failed</h2>
        <p>{str(e)}</p>
        """, 500


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )