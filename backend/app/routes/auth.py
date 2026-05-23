# =============================================
# app/routes/auth.py  —  Authentication
#
# POST /auth/login        — verify credentials, return session token
# GET  /auth/verify       — validate token (called by protected pages)
# POST /auth/logout       — invalidate token
# POST /auth/setup        — create first admin user (locked after first use)
# =============================================

import datetime
import hashlib
import secrets

from fastapi import APIRouter, HTTPException, Request

from app import db

router = APIRouter(tags=["Auth"])

# In-memory sessions {token: username}.
# Resets on server restart — acceptable for a personal IoT project.
# For production: store in MongoDB sessions collection or Redis.
_sessions: dict[str, str] = {}


def _hash(password: str) -> str:
    """SHA-256 hash. Sufficient security for a personal IoT project."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_token(token: str) -> str | None:
    """Return username if token valid, else None."""
    return _sessions.get(token)


@router.post("/auth/login")
async def login(request: Request):
    """Verify credentials against MongoDB users collection."""
    body = await request.json()
    username = body.get("username", "").strip().lower()
    password = body.get("password", "")

    if not username or not password:
        raise HTTPException(400, "Username and password required")

    if not db.is_connected():
        raise HTTPException(503, "Database unavailable — cannot authenticate")

    user = await db.get_db().users.find_one({"username": username})
    if not user or user.get("password_hash") != _hash(password):
        raise HTTPException(401, "Invalid credentials")

    token = secrets.token_urlsafe(32)
    _sessions[token] = username
    print(f"[AUTH] ✓ Login: {username}")
    return {
        "token":    token,
        "username": username,
        "role":     user.get("role", "user"),
    }


@router.get("/auth/verify")
async def verify(request: Request):
    """Validate session token. Called by protected pages on every load."""
    token = request.headers.get("X-Auth-Token", "")
    username = verify_token(token)
    if not username:
        raise HTTPException(401, "Not authenticated")
    return {"valid": True, "username": username}


@router.post("/auth/logout")
async def logout(request: Request):
    """Invalidate session token."""
    token = request.headers.get("X-Auth-Token", "")
    _sessions.pop(token, None)
    return {"success": True}


@router.post("/auth/setup")
async def setup_first_admin(request: Request):
    """
    One-time setup: creates the first admin user.
    Only works when the users collection is completely empty.
    After the first user is created this endpoint returns 403.

    Usage:
        POST /auth/setup
        {"username": "admin", "password": "admin"}
    """
    if not db.is_connected():
        raise HTTPException(503, "Database unavailable")

    count = await db.get_db().users.count_documents({})
    if count > 0:
        raise HTTPException(
            403,
            "Setup already complete — users exist. "
            "Use MongoDB Atlas UI or mongosh to manage users."
        )

    body = await request.json()
    username = body.get("username", "").strip().lower()
    password = body.get("password", "")

    if not username or not password:
        raise HTTPException(400, "Username and password required")

    await db.get_db().users.insert_one({
        "username":      username,
        "password_hash": _hash(password),
        "role":          "admin",
        "created_at":    datetime.datetime.now(datetime.timezone.utc),
    })
    print(f"[AUTH] First admin user '{username}' created via /auth/setup")
    return {
        "success": True,
        "message": f"Admin user '{username}' created. Endpoint is now locked.",
        "sha256_note": f"SHA-256('{password}') = {_hash(password)}"
    }
