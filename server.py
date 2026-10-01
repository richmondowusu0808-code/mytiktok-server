import os
import cloudinary
import cloudinary.uploader
from flask import Flask, request

app = Flask(__name__)

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

@app.route("/")
def home():
    return """
    <h1>Cloudinary Upload</h1>

    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*,video/*" required>
        <br><br>
        <button type="submit">Upload</button>
    </form>
    """

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

        return f"""
        <h2>Upload successful!</h2>
        <p>File: {file.filename}</p>
        <p>Cloudinary URL:</p>
        <a href="{result['secure_url']}" target="_blank">
            {result['secure_url']}
        </a>
        """

    except Exception as e:
        return f"Upload failed: {str(e)}", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)