import os
import cloudinary
import cloudinary.uploader
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Upload to Cloudinary</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <h2>Upload Image or Video</h2>

    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*,video/*" required>
        <br><br>
        <button type="submit">Upload</button>
    </form>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    result = cloudinary.uploader.upload(
        file,
        resource_type="auto"
    )

    return jsonify({
        "message": "Upload successful",
        "url": result["secure_url"],
        "public_id": result["public_id"],
        "resource_type": result["resource_type"]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)