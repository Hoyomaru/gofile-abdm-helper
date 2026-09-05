# filename: app.py
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

from flask import Flask, jsonify, request

from abdm import ABDMClient, ABDMError
from gofile import (
    ContentNotFound,
    GoFileClient,
    GoFileError,
    InvalidContent,
    PasswordRequired,
    RateLimited,
    ResolveResult,
    WebsiteTokenRejected,
    WrongPassword,
)

HOST = "127.0.0.1"
PORT = 8765
API_MARKER_HEADER = "X-GoFile-ABDM"
API_MARKER_VALUE = "1"
CACHE_TTL_SECONDS = 20 * 60
MAX_SEND_ITEMS = 1000

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


@dataclass
class CacheEntry:
    created_at: float
    result: ResolveResult


_cache: Dict[str, CacheEntry] = {}
_cache_lock = threading.Lock()


def _prune_cache() -> None:
    cutoff = time.time() - CACHE_TTL_SECONDS
    with _cache_lock:
        expired = [key for key, entry in _cache.items() if entry.created_at < cutoff]
        for key in expired:
            _cache.pop(key, None)


def _cache_put(result: ResolveResult) -> str:
    _prune_cache()
    resolve_id = secrets.token_urlsafe(24)
    with _cache_lock:
        _cache[resolve_id] = CacheEntry(time.time(), result)
    return resolve_id


def _cache_get(resolve_id: str) -> Optional[ResolveResult]:
    _prune_cache()
    with _cache_lock:
        entry = _cache.get(resolve_id)
        return entry.result if entry else None


def _api_error(message: str, code: str, status: int):
    return jsonify({"ok": False, "error": {"code": code, "message": message}}), status


@app.before_request
def local_only_and_csrf_guard():
    if request.remote_addr not in {"127.0.0.1", "::1"}:
        return _api_error("Local requests only.", "local_only", 403)
    if request.path.startswith("/api/"):
        if request.headers.get(API_MARKER_HEADER) != API_MARKER_VALUE:
            return _api_error("Missing helper request marker.", "request_marker_required", 403)
        if request.method in {"POST", "PUT", "PATCH"} and not request.is_json:
            return _api_error("JSON request required.", "json_required", 415)
    return None


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "gofile-abdm-helper"})


@app.get("/api/abdm/status")
def abdm_status():
    connected = ABDMClient().status()
    return jsonify({"ok": True, "connected": connected})


@app.get("/api/abdm/queues")
def abdm_queues():
    try:
        queues = ABDMClient().queues()
        return jsonify({"ok": True, "connected": True, "queues": queues})
    except ABDMError:
        return _api_error("AB Download Manager is offline or its queue list is unavailable.", "abdm_offline", 502)


@app.post("/api/gofile/resolve")
def gofile_resolve():
    body = request.get_json(silent=True) or {}
    source = body.get("url") or body.get("content_id")
    password = body.get("password")
    if password is not None and not isinstance(password, str):
        return _api_error("Password must be a string.", "invalid_password", 400)

    try:
        result = GoFileClient().resolve(source, password=password or None)
        resolve_id = _cache_put(result)
        public_root = result.root.to_public_dict()
        return jsonify(
            {
                "ok": True,
                "resolve_id": resolve_id,
                "expires_in": CACHE_TTL_SECONDS,
                "content_id": result.content_id,
                "root_name": result.root_name,
                "root": public_root,
                "top_level": [child.to_public_dict() for child in result.root.children],
                "file_count": result.root.file_count,
                "total_size": result.root.total_size,
            }
        )
    except InvalidContent as exc:
        return _api_error(str(exc), exc.code, 400)
    except PasswordRequired as exc:
        return _api_error(str(exc), exc.code, 401)
    except WrongPassword as exc:
        return _api_error(str(exc), exc.code, 401)
    except ContentNotFound as exc:
        return _api_error(str(exc), exc.code, 404)
    except RateLimited as exc:
        return _api_error(str(exc), exc.code, 429)
    except WebsiteTokenRejected as exc:
        return _api_error(str(exc), exc.code, 502)
    except GoFileError as exc:
        return _api_error(str(exc), getattr(exc, "code", "gofile_error"), 502)
    except Exception:
        # Deliberately avoid returning/logging request bodies, tokens, cookies,
        # passwords or temporary direct URLs.
        return _api_error("Unexpected GoFile helper error.", "internal_error", 500)


@app.post("/api/abdm/send")
def abdm_send():
    body = request.get_json(silent=True) or {}
    resolve_id = body.get("resolve_id")
    file_keys = body.get("file_keys")
    save_root = body.get("save_root", "")
    preserve_structure = body.get("preserve_structure", True)
    queue_id = body.get("queue_id")

    if not isinstance(resolve_id, str) or not resolve_id:
        return _api_error("resolve_id is required.", "invalid_resolve_id", 400)
    if not isinstance(file_keys, list) or not file_keys:
        return _api_error("file_keys must be a non-empty array.", "invalid_file_keys", 400)
    if len(file_keys) > MAX_SEND_ITEMS:
        return _api_error("Too many files in one request.", "too_many_files", 400)
    if not all(isinstance(key, str) and 1 <= len(key) <= 128 for key in file_keys):
        return _api_error("Invalid file key.", "invalid_file_keys", 400)
    if not isinstance(save_root, str) or len(save_root) > 1000 or "\x00" in save_root:
        return _api_error("Invalid save root.", "invalid_save_root", 400)
    if not isinstance(preserve_structure, bool):
        return _api_error("preserve_structure must be a boolean.", "invalid_preserve_structure", 400)
    if queue_id is not None and (isinstance(queue_id, bool) or not isinstance(queue_id, int)):
        return _api_error("queue_id must be an integer or null.", "invalid_queue_id", 400)

    resolved = _cache_get(resolve_id)
    if resolved is None:
        return _api_error("Resolved GoFile session expired. Resolve the page again.", "resolve_expired", 410)

    client = ABDMClient()
    results = []
    for key in file_keys:
        item = resolved.files.get(key)
        if item is None:
            results.append({"key": key, "ok": False, "error": "Unknown or stale file key."})
            continue
        try:
            result = client.send(
                item,
                save_root=save_root,
                preserve_structure=preserve_structure,
                queue_id=queue_id,
            )
            results.append(
                {
                    "key": key,
                    "name": item.name,
                    "ok": result.ok,
                    "status": result.status_code,
                    "error": None if result.ok else result.message,
                }
            )
        except ABDMError as exc:
            results.append({"key": key, "name": item.name, "ok": False, "error": str(exc)})
        except Exception:
            results.append({"key": key, "name": item.name, "ok": False, "error": "Unexpected ABDM error."})

    success = sum(1 for item in results if item.get("ok"))
    failed = len(results) - success
    return jsonify({"ok": True, "success": success, "failed": failed, "results": results})


if __name__ == "__main__":
    # Never expose the helper to the LAN. Flask's development server is enough
    # for this single-user localhost helper.
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
