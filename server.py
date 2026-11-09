from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import sqlite3
import hashlib
import secrets
import time
import re
import requests

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
WEB_DIR = BASE_DIR / "web"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "nova_users.db"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen3:8b"
TOKEN_DAYS = 7

app = FastAPI(title="Nova AI API")
bearer = HTTPBearer(auto_error=False)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            updated_at REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
        """)


init_db()


def make_password_hash(password):
    salt = secrets.token_bytes(16)
    hashed = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ":" + hashed.hex()


def verify_password(password, stored):
    try:
        salt_hex, hash_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def token_digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Please log in")

    digest = token_digest(credentials.credentials)
    now = time.time()

    with connect_db() as conn:
        row = conn.execute(
            "SELECT users.id, users.username FROM sessions "
            "JOIN users ON users.id = sessions.user_id "
            "WHERE sessions.token_hash = ? AND sessions.expires_at > ?",
            (digest, now)
        ).fetchone()
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))

    if row is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return {"id": row["id"], "username": row["username"]}


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=24)
    password: str = Field(min_length=10, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: int | None = None


@app.get("/")
def home():
    return FileResponse(WEB_DIR / "index.html")


@app.post("/register")
def register(data: RegisterRequest):
    username = data.username.strip().lower()

    if not re.fullmatch(r"[a-z0-9_]{3,24}", username):
        raise HTTPException(
            status_code=400,
            detail="Username: use 3-24 letters, numbers, or underscores"
        )

    if len(data.password) < 10:
        raise HTTPException(status_code=400, detail="Password must contain at least 10 characters")

    try:
        with connect_db() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, make_password_hash(data.password), time.time())
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username is already taken")

    return {"message": "Account created", "user_id": user_id, "username": username}


@app.post("/login")
def login(data: LoginRequest):
    username = data.username.strip().lower()

    with connect_db() as conn:
        user = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,)
        ).fetchone()

    if user is None or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = secrets.token_urlsafe(32)

    with connect_db() as conn:
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_digest(token), user["id"], time.time() + TOKEN_DAYS * 86400)
        )

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"]
    }


@app.get("/me")
def me(user=Depends(current_user)):
    return {"username": user["username"]}


@app.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer), user=Depends(current_user)):
    with connect_db() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (token_digest(credentials.credentials),)
        )
    return {"message": "Logged out"}


@app.get("/conversations")
def list_conversations(user=Depends(current_user)):
    with connect_db() as conn:
        rows = conn.execute(
            "SELECT id, title, updated_at FROM conversations "
            "WHERE user_id = ? ORDER BY updated_at DESC",
            (user["id"],)
        ).fetchall()

    return {"conversations": [dict(row) for row in rows]}


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int, user=Depends(current_user)):
    with connect_db() as conn:
        conversation = conn.execute(
            "SELECT id, title FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user["id"])
        ).fetchone()

        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        rows = conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY id",
            (conversation_id,)
        ).fetchall()

    return {
        "conversation": dict(conversation),
        "messages": [dict(row) for row in rows]
    }


@app.post("/chat")
def chat(data: ChatRequest, user=Depends(current_user)):
    now = time.time()

    with connect_db() as conn:
        if data.conversation_id is None:
            title = data.message.strip().replace("\n", " ")[:60] or "New chat"
            cursor = conn.execute(
                "INSERT INTO conversations (user_id, title, updated_at) VALUES (?, ?, ?)",
                (user["id"], title, now)
            )
            conversation_id = cursor.lastrowid
        else:
            row = conn.execute(
                "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
                (data.conversation_id, user["id"])
            ).fetchone()

            if row is None:
                raise HTTPException(status_code=404, detail="Conversation not found")

            conversation_id = row["id"]

        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) "
            "VALUES (?, 'user', ?, ?)",
            (conversation_id, data.message, now)
        )

        history = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? "
            "ORDER BY id DESC LIMIT 20",
            (conversation_id,)
        ).fetchall()

        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id)
        )

    messages = [{
        "role": "system",
        "content": "You are Nova, a helpful AI assistant. Your name is Nova. Reply in the user's language."
    }]
    messages.extend(
        {"role": row["role"], "content": row["content"]}
        for row in reversed(history)
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "messages": messages, "stream": False},
            timeout=180
        )
        response.raise_for_status()
        reply = response.json()["message"]["content"]
    except (requests.RequestException, KeyError, ValueError):
        raise HTTPException(status_code=503, detail="Nova AI is temporarily unavailable")

    with connect_db() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) "
            "VALUES (?, 'assistant', ?, ?)",
            (conversation_id, reply, time.time())
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (time.time(), conversation_id)
        )

    return {"reply": reply, "conversation_id": conversation_id}
