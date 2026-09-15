# filename: abdm.py
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional

import requests

from gofile import ResolvedFile, sanitize_relative_path

ABDM_BASE_URL = "http://127.0.0.1:15151"
ABDM_TIMEOUT = 8


class ABDMError(RuntimeError):
    pass


class ABDMUncertainError(ABDMError):
    """ABDM may have accepted a POST even though no confirmation was received."""


@dataclass
class ABDMResult:
    ok: bool
    status_code: int
    message: str


class ABDMClient:
    def __init__(self, *, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()

    def queues(self) -> List[Dict[str, Any]]:
        """Return ABDM queues using the documented GET /queues endpoint."""
        try:
            response = self.session.get(f"{ABDM_BASE_URL}/queues", timeout=ABDM_TIMEOUT)
        except requests.RequestException as exc:
            raise ABDMError("Could not connect to AB Download Manager.") from exc

        if not response.ok:
            raise ABDMError(f"ABDM returned HTTP {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise ABDMError("ABDM returned an invalid queue response.") from exc

        if not isinstance(data, list):
            raise ABDMError("ABDM returned an invalid queue response.")

        queues: List[Dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            queue_id = item.get("id")
            name = item.get("name")
            if isinstance(queue_id, bool) or not isinstance(queue_id, int):
                continue
            if not isinstance(name, str):
                continue
            queues.append({"id": queue_id, "name": name})
        return queues

    def status(self) -> bool:
        """Use the documented GET /queues endpoint as the connection check."""
        try:
            self.queues()
            return True
        except ABDMError:
            return False

    @staticmethod
    def _normalize_root(root: str) -> str:
        value = (root or "").strip().replace("\\", "/")
        if value.startswith("//"):
            value = "//" + re.sub(r"/+", "/", value[2:])
        else:
            value = re.sub(r"/+", "/", value)
        # Preserve POSIX and Windows drive roots. "C:" and "C:/" have different
        # semantics on Windows, so a user-selected drive root must keep its slash.
        if value == "/" or re.fullmatch(r"[A-Za-z]:/", value):
            return value
        # Do not reinterpret, expand, or sanitize the user-selected root. Only
        # trim trailing separators so sanitized GoFile subpaths can be appended.
        while len(value) > 1 and value.endswith("/"):
            value = value[:-1]
        return value

    @classmethod
    def build_folder(cls, user_root: str, relative_folder: str) -> Optional[str]:
        root = cls._normalize_root(user_root)
        if not root:
            # Official REST-API.yml documents folder as optional. Omitting it is
            # the only documented way to preserve ABDM's own default behavior.
            return None
        relative = sanitize_relative_path(relative_folder)
        if not relative:
            return root
        if root == "/" or re.fullmatch(r"[A-Za-z]:/", root):
            return f"{root}{relative}"
        return f"{root}/{relative}"

    def send(
        self,
        item: ResolvedFile,
        *,
        save_root: str = "",
        preserve_structure: bool = True,
        queue_id: Optional[int] = None,
    ) -> ABDMResult:
        body: Dict[str, Any] = {
            "downloadSource": {
                "link": item.link,
                "headers": dict(item.headers),
                "downloadPage": item.download_page,
            },
            "name": item.safe_name,
        }
        relative_folder = item.relative_folder if preserve_structure else ""
        folder = self.build_folder(save_root, relative_folder)
        if folder is not None:
            body["folder"] = folder
        if queue_id is not None:
            body["queueId"] = queue_id

        try:
            response = self.session.post(
                f"{ABDM_BASE_URL}/start-headless-download",
                json=body,
                timeout=ABDM_TIMEOUT,
            )
        except requests.RequestException as exc:
            # With a POST, a transport failure cannot prove that ABDM did not
            # already accept the task. Keep this separate from a definite HTTP
            # failure so callers do not blindly retry and create duplicates.
            raise ABDMUncertainError(
                "ABDM did not confirm whether the download task was accepted."
            ) from exc

        if response.ok:
            return ABDMResult(True, response.status_code, "sent")

        # Do not echo arbitrary ABDM body content; keep errors concise and avoid
        # accidentally surfacing a request payload or URL.
        return ABDMResult(False, response.status_code, f"ABDM returned HTTP {response.status_code}")
