from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>Upload Test</h1>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*,video/*" required>
        <button type="submit">Test Upload</button>
    </form>
    """

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return "No file selected", 400

    file = request.files["file"]

    if not file.filename:
        return "No file selected", 400

    return f"File received successfully: {file.filename}"

if __name__ == "__main__":
    port = int(__import__("os").environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)