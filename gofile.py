# filename: gofile.py
from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse

import requests

API_ORIGIN = "https://api.gofile.io"
SITE_ORIGIN = "https://gofile.io"
DEFAULT_TIMEOUT = 30
CONTENT_TIMEOUT = 45
PAGE_SIZE = 1000
WT_WINDOW_SECONDS = 14_400

# This is not a fixed Website Token. It is the current salt used to derive a
# per-account, per-time-window X-Website-Token. The value was verified against
# martadams89/gofile-dl on 2026-09-05; GOFILE_WT_SALT can override it without
# changing code when GoFile rotates the salt again.
DEFAULT_WT_SALT = "12af056dacea0b"
DEFAULT_LANGUAGE = "en-US"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

CONTENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{5,127}$")


class GoFileError(RuntimeError):
    code = "gofile_error"


class InvalidContent(GoFileError):
    code = "invalid_content"


class PasswordRequired(GoFileError):
    code = "password_required"


class WrongPassword(GoFileError):
    code = "wrong_password"


class RateLimited(GoFileError):
    code = "rate_limited"


class WebsiteTokenRejected(GoFileError):
    code = "website_token_rejected"


class ContentNotFound(GoFileError):
    code = "not_found"


@dataclass
class ResolvedFile:
    key: str
    id: str
    name: str
    safe_name: str
    size: int
    relative_folder: str
    relative_path: str
    link: str
    headers: Dict[str, str]
    download_page: str


@dataclass
class ResolvedNode:
    key: str
    id: str
    type: str
    name: str
    size: int = 0
    relative_path: str = ""
    children: list["ResolvedNode"] = field(default_factory=list)
    file_keys: list[str] = field(default_factory=list)

    @property
    def total_size(self) -> int:
        if self.type == "file":
            return self.size
        return sum(child.total_size for child in self.children)

    @property
    def file_count(self) -> int:
        if self.type == "file":
            return 1
        return sum(child.file_count for child in self.children)

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "size": self.size,
            "total_size": self.total_size,
            "file_count": self.file_count,
            "relative_path": self.relative_path,
            "file_keys": list(self.file_keys),
            "children": [child.to_public_dict() for child in self.children],
        }


@dataclass
class ResolveResult:
    content_id: str
    root_name: str
    root: ResolvedNode
    files: Dict[str, ResolvedFile]


def parse_content_id(value: str) -> str:
    """Accept a GoFile /d/<id> URL or a bare content ID and reject all else."""
    if not isinstance(value, str) or not value.strip():
        raise InvalidContent("A GoFile URL or content ID is required.")

    candidate = value.strip()
    if CONTENT_ID_RE.fullmatch(candidate):
        return candidate

    parsed = urlparse(candidate)
    if parsed.scheme != "https" or parsed.hostname not in {"gofile.io", "www.gofile.io"}:
        raise InvalidContent("Only https://gofile.io/d/<content-id> URLs are accepted.")

    match = re.fullmatch(r"/d/([^/?#]+)", parsed.path.rstrip("/"))
    if not match:
        raise InvalidContent("Unsupported GoFile URL format.")

    content_id = match.group(1)
    if not CONTENT_ID_RE.fullmatch(content_id):
        raise InvalidContent("Invalid GoFile content ID.")
    return content_id


def _safe_error_status(status: Any) -> str:
    return str(status or "unknown")[:100]


class GoFileClient:
    def __init__(self, *, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()
        self.user_agent = os.getenv("GOFILE_USER_AGENT", DEFAULT_USER_AGENT).strip() or DEFAULT_USER_AGENT
        self.language = os.getenv("GOFILE_LANGUAGE", DEFAULT_LANGUAGE).strip() or DEFAULT_LANGUAGE
        self.wt_salt = os.getenv("GOFILE_WT_SALT", DEFAULT_WT_SALT).strip() or DEFAULT_WT_SALT
        self.token = ""

    def _guest_token(self) -> str:
        if self.token:
            return self.token

        headers = {
            "User-Agent": self.user_agent,
            "Origin": SITE_ORIGIN,
            "Referer": SITE_ORIGIN + "/",
            "Accept": "application/json, text/plain, */*",
        }
        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                response = self.session.post(
                    f"{API_ORIGIN}/accounts",
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT,
                )
                if response.status_code == 429:
                    raise RateLimited("GoFile rate limit reached while creating a guest session.")
                response.raise_for_status()
                payload = response.json()
                status = str(payload.get("status") or "")
                status_lower = status.lower()
                if "ratelimit" in status_lower or "rate_limit" in status_lower:
                    raise RateLimited("GoFile rate limit reached while creating a guest session.")
                if status == "ok" and payload.get("data", {}).get("token"):
                    self.token = str(payload["data"]["token"])
                    return self.token
                raise GoFileError("GoFile did not issue a guest token.")
            except RateLimited:
                # A device/IP rate limit should stop the operation immediately.
                # Retrying here only adds more requests while GoFile is throttling us.
                raise
            except (requests.RequestException, ValueError, GoFileError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
        raise GoFileError("Could not create a GoFile guest session.") from last_error

    def _website_token(self, window_offset: int = 0) -> str:
        token = self._guest_token()
        window = int(time.time() // WT_WINDOW_SECONDS) + window_offset
        raw = f"{self.user_agent}::{self.language}::{token}::{window}::{self.wt_salt}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _content_headers(self, window_offset: int = 0) -> Dict[str, str]:
        token = self._guest_token()
        return {
            "Authorization": f"Bearer {token}",
            "X-Website-Token": self._website_token(window_offset),
            "X-BL": self.language,
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Origin": SITE_ORIGIN,
            "Referer": SITE_ORIGIN + "/",
        }

    @staticmethod
    def _password_hash(password: Optional[str]) -> Optional[str]:
        if not password:
            return None
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _request_folder_page(
        self,
        content_id: str,
        *,
        password: Optional[str],
        page: int,
        window_offset: int,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "contentFilter": "",
            "page": page,
            "pageSize": PAGE_SIZE,
            "sortField": "createTime",
            "sortDirection": -1,
        }
        password_hash = self._password_hash(password)
        if password_hash:
            params["password"] = password_hash

        response = self.session.get(
            f"{API_ORIGIN}/contents/{content_id}",
            headers=self._content_headers(window_offset),
            params=params,
            timeout=CONTENT_TIMEOUT,
        )

        if response.status_code == 429:
            # Some throttling responses may be HTML rather than JSON, so check
            # the HTTP status before attempting to decode the response body.
            raise RateLimited("GoFile rate limit reached.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise GoFileError(f"GoFile returned HTTP {response.status_code} with a non-JSON response.") from exc

        status = str(payload.get("status") or "")
        status_lower = status.lower()
        if status == "ok":
            return payload
        if "ratelimit" in status_lower or "rate_limit" in status_lower:
            raise RateLimited("GoFile rate limit reached.")
        if "password" in status_lower:
            if password:
                raise WrongPassword("The GoFile password was rejected.")
            raise PasswordRequired("This GoFile content requires a password.")
        if status in {"error-notFound", "error-notfound"} or "notfound" in status_lower:
            raise ContentNotFound("GoFile content was not found.")
        if status == "error-notPremium":
            raise WebsiteTokenRejected(
                "GoFile rejected the website token. The website-token salt may have rotated; "
                "set GOFILE_WT_SALT to the current value."
            )
        raise GoFileError(f"GoFile API error: {_safe_error_status(status)}")

    def fetch_folder(self, content_id: str, password: Optional[str] = None) -> Dict[str, Any]:
        """Fetch one folder with pagination; never retry a GoFile rate limit."""
        content_id = parse_content_id(content_id)
        merged: Optional[Dict[str, Any]] = None
        page = 1
        window_offsets = (0, -1)

        while True:
            payload: Optional[Dict[str, Any]] = None
            last_error: Optional[Exception] = None
            for attempt in range(4):
                window_offset = window_offsets[min(attempt, len(window_offsets) - 1)]
                try:
                    payload = self._request_folder_page(
                        content_id,
                        password=password,
                        page=page,
                        window_offset=window_offset,
                    )
                    break
                except RateLimited:
                    # Stop the entire recursive resolve on the first 429/rate-limit
                    # response instead of multiplying requests with retries.
                    raise
                except WebsiteTokenRejected:
                    if attempt == 0:
                        continue
                    raise
                except requests.Timeout as exc:
                    last_error = exc
                    if attempt < 3:
                        time.sleep(2.0 * (attempt + 1))
                        continue
                    raise GoFileError("GoFile content request timed out.") from exc
                except requests.RequestException as exc:
                    raise GoFileError("Could not reach the GoFile content API.") from exc

            if payload is None:
                raise GoFileError("Could not fetch GoFile content.") from last_error

            data = payload.get("data")
            if not isinstance(data, dict):
                raise GoFileError("GoFile returned an unexpected content payload.")

            children = data.get("children") or {}
            if isinstance(children, list):
                children = {str(item.get("id") or index): item for index, item in enumerate(children)}
            if not isinstance(children, dict):
                children = {}

            if merged is None:
                merged = dict(data)
                merged["children"] = dict(children)
            else:
                merged_children = merged.setdefault("children", {})
                if isinstance(merged_children, dict):
                    merged_children.update(children)

            children_count = int(data.get("childrenCount") or len(merged.get("children", {})))
            current_count = len(merged.get("children", {}))
            if current_count >= children_count or len(children) < PAGE_SIZE:
                return merged
            page += 1

    @staticmethod
    def _node_key(content_id: str, relative_path: str) -> str:
        raw = f"{content_id}\0{relative_path}".encode("utf-8", errors="replace")
        return hashlib.sha256(raw).hexdigest()[:24]

    def resolve(self, value: str, password: Optional[str] = None) -> ResolveResult:
        content_id = parse_content_id(value)
        self._guest_token()
        files: Dict[str, ResolvedFile] = {}
        visited: set[str] = set()
        download_page = f"{SITE_ORIGIN}/d/{content_id}"

        def walk(folder_id: str, parent_rel: str, is_root: bool = False) -> ResolvedNode:
            if folder_id in visited:
                raise GoFileError("Recursive folder loop detected in GoFile content.")
            visited.add(folder_id)
            try:
                data = self.fetch_folder(folder_id, password=password)
                folder_name = str(data.get("name") or folder_id)
                folder_rel = folder_name if is_root else f"{parent_rel}/{folder_name}" if parent_rel else folder_name
                folder_key = self._node_key(folder_id, folder_rel)
                node = ResolvedNode(
                    key=folder_key,
                    id=folder_id,
                    type="folder",
                    name=folder_name,
                    relative_path=folder_rel,
                )

                children = data.get("children") or {}
                iterable: Iterable[Dict[str, Any]]
                if isinstance(children, dict):
                    iterable = [v for v in children.values() if isinstance(v, dict)]
                elif isinstance(children, list):
                    iterable = [v for v in children if isinstance(v, dict)]
                else:
                    iterable = []

                for child in iterable:
                    child_id = str(child.get("id") or "")
                    child_type = str(child.get("type") or "")
                    child_name = str(child.get("name") or child_id or "unnamed")
                    if not child_id:
                        continue

                    if child_type == "folder":
                        child_node = walk(child_id, folder_rel, False)
                        node.children.append(child_node)
                        node.file_keys.extend(child_node.file_keys)
                        continue

                    if child_type != "file":
                        continue

                    relative_path = f"{folder_rel}/{child_name}" if folder_rel else child_name
                    file_key = self._node_key(child_id, relative_path)
                    size = int(child.get("size") or 0)
                    link = str(child.get("link") or "")
                    parsed_link = urlparse(link)
                    link_host = (parsed_link.hostname or "").lower()
                    if (
                        parsed_link.scheme != "https"
                        or not link_host
                        or not (link_host == "gofile.io" or link_host.endswith(".gofile.io"))
                    ):
                        raise GoFileError(f"GoFile did not provide a valid download link for {child_name!r}.")
                    safe_name = sanitize_segment(child_name)
                    headers = {
                        "Cookie": f"accountToken={self.token}",
                        "User-Agent": self.user_agent,
                        "Referer": download_page,
                    }
                    files[file_key] = ResolvedFile(
                        key=file_key,
                        id=child_id,
                        name=child_name,
                        safe_name=safe_name,
                        size=size,
                        relative_folder=folder_rel,
                        relative_path=relative_path,
                        link=link,
                        headers=headers,
                        download_page=download_page,
                    )
                    file_node = ResolvedNode(
                        key=file_key,
                        id=child_id,
                        type="file",
                        name=child_name,
                        size=size,
                        relative_path=relative_path,
                        file_keys=[file_key],
                    )
                    node.children.append(file_node)
                    node.file_keys.append(file_key)
                return node
            finally:
                visited.discard(folder_id)

        root = walk(content_id, "", True)
        return ResolveResult(
            content_id=content_id,
            root_name=root.name,
            root=root,
            files=files,
        )


_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_segment(value: str) -> str:
    """Sanitize a GoFile-derived path segment for Windows and Unix targets."""
    if not isinstance(value, str):
        value = str(value)
    value = value.replace("\x00", "")
    value = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", value)
    value = value.strip().rstrip(". ")
    value = value.lstrip(". ")
    if value in {"", ".", ".."}:
        value = "_"
    stem = value.split(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED:
        value = "_" + value
    return value[:240]


def sanitize_relative_path(relative_path: str) -> str:
    if not relative_path:
        return ""
    raw_parts = re.split(r"[\\/]+", relative_path)
    parts = [sanitize_segment(part) for part in raw_parts if part not in {"", ".", ".."}]
    return "/".join(parts)
