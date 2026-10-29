"""LAN Share v2: private sessions. Everything is deleted when the session ends.
Run:  pip install flask   then   python app.py
"""
import atexit
import os
import re
import secrets
import shutil
import socket
import threading
import time

from flask import Flask, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename

PORT = 8000
IDLE_SECONDS = 10 * 60             # no open tab for 10 min -> session deleted
MAX_SESSION_SECONDS = 2 * 3600     # hard limit: 2 hours
MAX_ROOM_BYTES = 100 * 1024**2     # 100 MB per session
MAX_ROOMS = 50                     # stops one person creating endless sessions
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no I, O, 0, 1 (easy to misread)
CODE_RE = re.compile(r"[A-HJ-NP-Z2-9]{6}")

BASE = os.path.dirname(os.path.abspath(__file__))
SHARE = os.path.join(BASE, "shared")

ROOMS = {}                         # code -> {"created": t, "active": t}
LOCK = threading.Lock()            # the janitor thread and request threads share ROOMS

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_ROOM_BYTES


def wipe_all():
    shutil.rmtree(SHARE, ignore_errors=True)
    os.makedirs(SHARE, exist_ok=True)


wipe_all()                         # nothing survives a restart
atexit.register(wipe_all)          # or a normal shutdown


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))   # sends no data
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def room_dir(code):
    return os.path.join(SHARE, code)


def get_room(code):
    """Validate the code, refresh its activity time, return its folder."""
    if not CODE_RE.fullmatch(code):    # also blocks path tricks like ../
        abort(404)
    with LOCK:
        room = ROOMS.get(code)
        if not room:
            abort(404)
        room["active"] = time.time()
    return room_dir(code)


def end_room(code):
    with LOCK:
        ROOMS.pop(code, None)
    shutil.rmtree(room_dir(code), ignore_errors=True)


def janitor():
    """Every 30 s, delete sessions that are idle or too old."""
    while True:
        time.sleep(30)
        now = time.time()
        with LOCK:
            dead = [c for c, r in ROOMS.items()
                    if now - r["active"] > IDLE_SECONDS or now - r["created"] > MAX_SESSION_SECONDS]
        for c in dead:
            end_room(c)


threading.Thread(target=janitor, daemon=True).start()


def dir_size(path):
    return sum(f.stat().st_size for f in os.scandir(path) if f.is_file())


def unique_name(folder, name):
    root, ext = os.path.splitext(name)
    candidate, n = name, 1
    while os.path.exists(os.path.join(folder, candidate)):
        candidate = f"{root}_{n}{ext}"
        n += 1
    return candidate


@app.get("/")
def home():
    return send_from_directory(BASE, "index.html")


@app.get("/api/info")
def info():
    return jsonify(url=f"http://{local_ip()}:{PORT}")


@app.post("/api/room")
def create_room():
    with LOCK:
        if len(ROOMS) >= MAX_ROOMS:
            return jsonify(error="Too many active sessions. Try again in a few minutes."), 503
        code = "".join(secrets.choice(ALPHABET) for _ in range(6))
        while code in ROOMS:
            code = "".join(secrets.choice(ALPHABET) for _ in range(6))
        now = time.time()
        ROOMS[code] = {"created": now, "active": now}
    os.makedirs(room_dir(code), exist_ok=True)
    return jsonify(code=code)


@app.get("/api/<code>/files")
def list_files(code):
    d = get_room(code)
    items = [{"name": f.name, "size": f.stat().st_size, "modified": f.stat().st_mtime}
             for f in os.scandir(d) if f.is_file()]
    items.sort(key=lambda x: x["modified"], reverse=True)
    return jsonify(items)


@app.post("/api/<code>/upload")
def upload(code):
    d = get_room(code)
    if dir_size(d) + (request.content_length or 0) > MAX_ROOM_BYTES:
        return jsonify(error="This session is full (100 MB)."), 413
    saved = []
    for f in request.files.getlist("files"):
        name = secure_filename(f.filename)     # strips ../ and odd characters
        if not name:
            continue
        name = unique_name(d, name)
        f.save(os.path.join(d, name))
        saved.append(name)
    return jsonify(saved=saved)


@app.get("/api/<code>/files/<path:name>")
def download(code, name):
    return send_from_directory(get_room(code), name, as_attachment=True)


@app.delete("/api/<code>/files/<path:name>")
def delete_file(code, name):
    path = os.path.join(get_room(code), secure_filename(name))
    if not os.path.isfile(path):
        abort(404)
    os.remove(path)
    return "", 204


@app.delete("/api/<code>")
def end_session(code):
    get_room(code)
    end_room(code)
    return "", 204


if __name__ == "__main__":
    print(f"\n  Open on any device on this network:  http://{local_ip()}:{PORT}\n")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
