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

media = []

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>My Media</title>

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

        .upload {
            display: inline-block;
            padding: 10px 18px;
            background: white;
            color: black;
            text-decoration: none;
            border-radius: 20px;
            font-weight: bold;
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
    <a class="upload" href="/upload">📤 Upload</a>
</div>

<div class="feed">

{% if media %}

    {% for item in media %}

        <div class="post">

            {% if item.type == "video" %}

                <video
                    controls
                    playsinline
                    loop
                    preload="metadata">
                    <source src="{{ item.url }}">
                </video>

            {% else %}

                <img src="{{ item.url }}" alt="Uploaded image">

            {% endif %}

        </div>

    {% endfor %}

{% else %}

    <div class="empty">
        <div>
            <h2>🎬 No videos yet</h2>
            <p>Tap Upload to add your first video.</p>
        </div>
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