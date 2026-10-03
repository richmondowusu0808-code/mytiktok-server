import os
import cloudinary
import cloudinary.uploader
from flask import Flask, request, render_template_string, redirect

app = Flask(__name__)

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

media = []

profile = {
    "username": "user",
    "bio": "Welcome to my profile 🎬"
}


HTML = """
<!DOCTYPE html>
<html>

<head>

<meta name="viewport" content="width=device-width, initial-scale=1">

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
@{{ profile.username }}
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
        "@{{ profile.username }}: " + text;

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
<div class="number">0</div>
<div class="label">Likes</div>
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

</div>

</body>

</html>
"""


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


@app.route("/")
def home():

    return render_template_string(
        HTML,
        media=media,
        profile=profile
    )


@app.route("/profile", methods=["GET", "POST"])
def profile_page():

    if request.method == "POST":

        username = request.form.get(
            "username",
            "user"
        ).strip()

        bio = request.form.get(
            "bio",
            ""
        ).strip()

        if username:

            profile["username"] = username

        profile["bio"] = bio

        return redirect("/profile")

    return render_template_string(
        PROFILE_HTML,
        profile=profile
    )


@app.route("/upload", methods=["GET", "POST"])
def upload():

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

        media.insert(0, {
            "url": result["secure_url"],
            "type": result["resource_type"]
        })

        return """
        <html>

        <body
        style="font-family:Arial;text-align:center;padding:30px">

        <h2>✅ Upload successful!</h2>

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


if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )