"""Internal notes API.

Seed code for a harness eval scenario. Endpoints below are intentionally
insecure — no auth, string-built SQL, unbounded input, and a debug server.
The task prompt (see ../PROMPT.md) asks an agent to harden this before it's
exposed to a partner integration.
"""
import sqlite3

from flask import Flask, g, jsonify, request

from config import DATABASE_PATH, SECRET_KEY

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute(
            "CREATE TABLE IF NOT EXISTS notes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "owner TEXT, title TEXT, body TEXT)"
        )
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/notes", methods=["GET"])
def list_notes():
    owner = request.args.get("owner", "")
    db = get_db()
    # Vulnerable: owner is concatenated directly into the query.
    query = f"SELECT id, owner, title, body FROM notes WHERE owner = '{owner}'"
    rows = db.execute(query).fetchall()
    return jsonify([dict(row) for row in rows])


@app.route("/notes", methods=["POST"])
def create_note():
    data = request.get_json(force=True, silent=True) or {}
    owner = data.get("owner")
    title = data.get("title")
    body = data.get("body")
    # No validation: owner/title/body could be missing, wrong type, or huge.
    db = get_db()
    cur = db.execute(
        "INSERT INTO notes (owner, title, body) VALUES (?, ?, ?)",
        (owner, title, body),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid}), 201


@app.route("/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    # No auth check: any caller can delete any note.
    db = get_db()
    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    return "", 204


@app.route("/admin/users", methods=["GET"])
def list_users():
    # No auth check at all on an admin-labeled route.
    return jsonify({"users": ["alice", "bob"], "admin_token_hint": "starts with sk-"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
