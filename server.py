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

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Media Upload</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 30px 20px;
            text-align: center;
        }

        .box {
            border: 2px dashed #999;
            border-radius: 15px;
            padding: 30px 20px;
        }

        input {
            width: 100%;
            margin: 20px 0;
        }

        button {
            padding: 12px 25px;
            border: 0;
            border-radius: 8px;
            cursor: pointer;
        }

        img, video {
            max-width: 100%;
            margin-top: 20px;
            border-radius: 10px;
        }

        .url {
            word-break: break-all;
            margin-top: 20px;
        }
    </style>
</head>

<body>

<h1>📤 Media Upload</h1>

<div class="box">

<form action="/upload" method="post" enctype="multipart/form-data">

<input
    type="file"
    name="file"
    accept="image/*,video/*"
    required
>

<button type="submit">Upload</button>

</form>

</div>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/upload", methods=["POST"])
def upload():

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

        url = result["secure_url"]
        resource_type = result["resource_type"]

        if resource_type == "video":
            preview = f'<video controls src="{url}"></video>'
        else:
            preview = f'<img src="{url}" alt="Uploaded image">'

        return f"""
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Upload Successful</title>
        </head>

        <body style="font-family:Arial;text-align:center;padding:30px">

            <h1>✅ Upload Successful!</h1>

            <p><b>File:</b> {file.filename}</p>

            {preview}

            <div class="url">
                <p><b>Cloudinary URL:</b></p>
                <a href="{url}" target="_blank">{url}</a>
            </div>

            <br>

            <a href="/">Upload another file</a>

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
    app.run(host="0.0.0.0", port=port)