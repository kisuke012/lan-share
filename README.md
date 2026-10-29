# LAN Share

A small web app for sending files between devices (phone, laptop, another computer) with no cable, pen drive, or chat app. Files live inside a **private session** and are **deleted automatically** when the session ends.

Built with Python (Flask) and plain HTML/CSS/JavaScript. Started as a Computer Networks lab experiment on file sharing over a local network, then grew into a web app.

<img width="1046" height="565" alt="lanshare1" src="https://github.com/user-attachments/assets/07cd194b-569a-478d-a2ef-9dd484e62a6e" />
<img width="1207" height="881" alt="lanshare2" src="https://github.com/user-attachments/assets/45a4999a-d657-4cb1-996f-99c7c3a508a4" />



## Live demo

**https://lan-share-arcg.onrender.com/**



The app runs on a free server that sleeps when idle, so the first visit can take up to a minute to load. Please do not upload private or sensitive files.

## How to use

1. Open the link and click **Start a session**.
2. Copy the session link (or note the 6-character code) and send it to the other device.
3. On the other device, open that link, or click **Join session** and enter the code.
4. Drop files in on either device and download them on the other.
5. Click **End session and delete everything** when you are done. Otherwise the session deletes itself after 10 idle minutes.

## Features

- **Private sessions:** start a session and get a random 6-character code. Only people with the code can see its files.
- **Join by code or link:** type the code on another device, or open the shared link.
- **Everything vanishes:** a session and all its files are deleted when any of these happens:
  - someone clicks **End session and delete everything**
  - no page has been open for 10 minutes
  - 2 hours have passed
  - the server restarts or shuts down
- **Drag and drop uploads** with a progress bar, multiple files at once.
- **Safe by design:** sanitised file names, per-session size cap, limit on active sessions, no file ever overwritten.
- **Works offline on a LAN:** no external libraries, fonts, or internet needed.

## How it works

```
Device A (browser)  ──┐                         ┌── shared/K7M2QX/report.pdf
                      ├──►  Flask server  ──────┤
Device B (browser)  ──┘   (sessions in memory)  └── shared/P3N8TW/photo.jpg
```

1. `POST /api/room` creates a session and returns a code.
2. Every other request includes that code in the URL and is rejected unless the session exists.
3. The page asks for the file list every 4 seconds. This keeps the session alive and shows new files without refreshing.
4. A background cleanup thread deletes idle or expired sessions every 30 seconds.

## Project structure

```
lan-share/
├── app.py             Flask backend (sessions, upload, download, cleanup)
├── index.html         Frontend (HTML, CSS, JavaScript in one file)
├── requirements.txt   Python dependencies
├── .gitignore         Files Git should ignore
└── README.md          This file
```

A `shared/` folder is created automatically at runtime and wiped on every start.

## Run it locally

Requirements: Python 3.9 or newer.

```
pip install flask
python app.py
```

The terminal prints an address such as `http://192.168.1.5:8000`.

- Open it on your computer, click **Start a session**, and note the code.
- On your phone (same Wi-Fi or phone hotspot), open the same address and enter the code.

If the phone cannot connect, check that both devices are on the same network, that your firewall allows Python on private networks, and that your college Wi-Fi does not block device-to-device traffic (a phone hotspot usually works).

### Running locally? You can raise the upload limit to 2 GB

The default limit is **100 MB per session**, chosen to keep the free hosted version safe. On your own computer you can raise it up to **2 GB** by editing one line in `app.py`:

MAX_ROOM_BYTES = 2 * 1024**3       # 2 GB per session

Then update the two messages in `index.html` so users see the right number: the note under the drop zone ("Up to 100 MB per session") and the "not enough space" message.

## Deploy it (Render, free tier)

1. Push the project files to a GitHub repository (files at the top level).
2. On render.com, create a **Web Service** from that repository.
3. Use these settings:

| Setting | Value |
|---|---|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT` |
| Instance Type | Free |

**Why `--workers 1`:** sessions are stored in the memory of a single process. With several workers, each would have its own separate sessions.

Free-tier services sleep after a period of inactivity and lose local files when they restart. That fits this app, since files are temporary anyway. Check Render's current documentation for exact limits.

## API reference

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/room` | Create a session, returns `{ "code": "K7M2QX" }` |
| GET | `/api/<code>/files` | List files in the session |
| POST | `/api/<code>/upload` | Upload one or more files (`multipart/form-data`, field `files`) |
| GET | `/api/<code>/files/<name>` | Download a file |
| DELETE | `/api/<code>/files/<name>` | Delete one file |
| DELETE | `/api/<code>` | End the session and delete everything |
| GET | `/api/info` | Returns the server's LAN address |

## Settings

Edit the constants at the top of `app.py`:

| Constant | Default | Meaning |
|---|---|---|
| `PORT` | 8000 | Port used when running locally |
| `IDLE_SECONDS` | 600 | Delete a session after this long with no open page |
| `MAX_SESSION_SECONDS` | 7200 | Hard lifetime limit of a session |
| `MAX_ROOM_BYTES` | 100 MB | Total upload size per session |
| `MAX_ROOMS` | 50 | Maximum active sessions at once |

## Security notes and limitations

- **The session code is the only protection.** Anyone who has or guesses it can view, add, and delete files in that session. There is currently no limit on wrong guesses.
- **Plain HTTP on a local network is not encrypted.** Other people on the same network could read the traffic. Use a hosted deployment or a tunnel (which provide HTTPS) for anything private.
- **Deleted means removed from the server.** It cannot remove copies that someone already downloaded.
- **Sessions are kept in memory.** A server restart ends every session, and the app is designed to run as a single process.
- Do not use this for sensitive or confidential files.

## Ideas for improvement

- Limit wrong code guesses per IP address
- Optional password for a session
- Delete a file automatically after its first download
- Show how much time is left before a session expires
- Store sessions in a database so the app can run on several servers
- QR code on the session screen to join from a phone

## Tech stack

Python, Flask, Gunicorn, HTML, CSS, vanilla JavaScript. No database and no external front-end libraries.

## Author

Rishabh, Computer Science (AI and Machine Learning). Built as part of a Computer Networks lab project.
