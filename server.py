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


@app.route("/videos", methods=["GET"])
def videos():
    db = database()
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            SELECT id, username, filename, caption, likes
            FROM videos
            ORDER BY id DESC
            """
        )

        rows = cursor.fetchall()

        result = []

        for row in rows:
            # This assumes database() uses RealDictCursor.
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

    finally:
        cursor.close()
        db.close()


@app.route("/like/<int:video_id>", methods=["POST"])
def like(video_id):
    db = database()
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            UPDATE videos
            SET likes = likes + 1
            WHERE id = %s
            """,
            (video_id,)
        )

        if cursor.rowcount == 0:
            db.rollback()

            return jsonify({
                "success": False,
                "message": "Video not found"
            }), 404

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

        return jsonify({
            "success": True,
            "likes": row["likes"]
        })

    finally:
        cursor.close()
        db.close()


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
        }), 400

    db = database()
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO comments
            (video_id, username, comment)
            VALUES (%s, %s, %s)
            """,
            (video_id, username, comment_text)
        )

        db.commit()

        return jsonify({
            "success": True,
            "message": "Comment added"
        })

    finally:
        cursor.close()
        db.close()


# IMPORTANT:
# Do NOT call create_database() here.
#
# create_database()
#
# Calling it while Gunicorn imports server.py can cause
# the Render deployment to fail if the database connection
# is unavailable during startup.
