import os
import uuid

from flask import Flask, jsonify, render_template, request

from chatbot.engine import Session

app = Flask(__name__)

# In-memory session store. Fine for a single-process demo deployment;
# sessions reset if the process restarts.
SESSIONS = {}


def get_session(session_id):
    if session_id not in SESSIONS:
        SESSIONS[session_id] = Session()
    return SESSIONS[session_id]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = (data.get("message") or "").strip()

    session_id = request.cookies.get("session_id") or str(uuid.uuid4())

    if not message:
        reply = "Say something and I'll do my best to help! \U0001F319\U0001F3AC"
    else:
        session = get_session(session_id)
        try:
            reply = session.reply(message)
        except Exception as e:
            reply = f"Sorry, something went wrong on my end ({e}). Let's start over -- what would you like to know?"
            SESSIONS.pop(session_id, None)

    resp = jsonify({"reply": reply})
    resp.set_cookie("session_id", session_id, httponly=True, samesite="Lax")
    return resp


@app.route("/api/reset", methods=["POST"])
def reset():
    session_id = request.cookies.get("session_id")
    SESSIONS.pop(session_id, None)
    return jsonify({"status": "ok"})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
