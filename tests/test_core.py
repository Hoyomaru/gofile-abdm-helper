# filename: tests/test_core.py
import hashlib
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from abdm import ABDMClient
try:
    import app as app_module
    app = app_module.app
except ModuleNotFoundError as exc:
    if exc.name == 'flask':
        app_module = None
        app = None
    else:
        raise
from gofile import (
    ContentAccessDenied,
    GoFileClient,
    GoFileError,
    InvalidContent,
    PasswordRequired,
    RateLimited,
    ResolvedFile,
    ResolvedNode,
    ResolveResult,
    parse_content_id,
    sanitize_relative_path,
    sanitize_segment,
)


class ParseContentIdTests(unittest.TestCase):
    def test_short_id(self):
        self.assertEqual(parse_content_id("Abc123XY"), "Abc123XY")

    def test_uuid_id(self):
        value = "aafd8041-8823-4037-b0a4-6ad0de43fa65"
        self.assertEqual(parse_content_id(f"https://gofile.io/d/{value}"), value)

    def test_rejects_other_host(self):
        with self.assertRaises(InvalidContent):
            parse_content_id("https://example.com/d/Abc123XY")

    def test_rejects_generic_url(self):
        with self.assertRaises(InvalidContent):
            parse_content_id("https://gofile.io/api")


class PathSafetyTests(unittest.TestCase):
    def test_sanitize_segment(self):
        self.assertEqual(sanitize_segment("../CON"), "_CON")
        self.assertEqual(sanitize_segment("bad:name?.mkv"), "bad_name_.mkv")
        self.assertEqual(sanitize_segment("NUL.txt"), "_NUL.txt")

    def test_relative_path(self):
        result = sanitize_relative_path(r"Anime/../Subs\\Episode:01")
        self.assertEqual(result, "Anime/Subs/Episode_01")

    def test_abdm_folder_custom_root(self):
        self.assertEqual(ABDMClient.build_folder(r"D:\\Downloads\\", r"Anime\\Subs"), "D:/Downloads/Anime/Subs")

    def test_abdm_folder_default_is_omitted(self):
        self.assertIsNone(ABDMClient.build_folder("", "Anime/Subs"))

    def test_abdm_linux_root(self):
        self.assertEqual(ABDMClient.build_folder("/", "Anime/Subs"), "/Anime/Subs")

    def test_abdm_send_preserves_structure_by_default(self):
        session = Mock()
        response = Mock(ok=True, status_code=200)
        session.post.return_value = response
        client = ABDMClient(session=session)
        item = ResolvedFile(
            key="key1",
            id="file1",
            name="Episode01.mkv",
            safe_name="Episode01.mkv",
            size=100,
            relative_folder="Anime/Subs",
            relative_path="Anime/Subs/Episode01.mkv",
            link="https://cold.gofile.io/file1",
            headers={"Cookie": "accountToken=test"},
            download_page="https://gofile.io/d/root123",
        )
        client.send(item, save_root="D:/Downloads")
        body = session.post.call_args.kwargs["json"]
        self.assertEqual(body["folder"], "D:/Downloads/Anime/Subs")


    def test_abdm_queues_uses_documented_endpoint(self):
        session = Mock()
        response = Mock(ok=True, status_code=200)
        response.json.return_value = [{"id": 7, "name": "Anime"}, {"id": 9, "name": "Archive"}]
        session.get.return_value = response
        client = ABDMClient(session=session)
        queues = client.queues()
        self.assertEqual(queues, [{"id": 7, "name": "Anime"}, {"id": 9, "name": "Archive"}])
        self.assertTrue(session.get.call_args.args[0].endswith("/queues"))

    def test_abdm_send_with_queue_id(self):
        session = Mock()
        response = Mock(ok=True, status_code=200)
        session.post.return_value = response
        client = ABDMClient(session=session)
        item = ResolvedFile(
            key="key1",
            id="file1",
            name="Episode01.mkv",
            safe_name="Episode01.mkv",
            size=100,
            relative_folder="Anime/Subs",
            relative_path="Anime/Subs/Episode01.mkv",
            link="https://cold.gofile.io/file1",
            headers={"Cookie": "accountToken=test"},
            download_page="https://gofile.io/d/root123",
        )
        client.send(item, save_root="D:/Downloads", queue_id=7)
        body = session.post.call_args.kwargs["json"]
        self.assertEqual(body["queueId"], 7)

    def test_abdm_default_queue_is_omitted(self):
        session = Mock()
        response = Mock(ok=True, status_code=200)
        session.post.return_value = response
        client = ABDMClient(session=session)
        item = ResolvedFile(
            key="key1",
            id="file1",
            name="Episode01.mkv",
            safe_name="Episode01.mkv",
            size=100,
            relative_folder="Anime/Subs",
            relative_path="Anime/Subs/Episode01.mkv",
            link="https://cold.gofile.io/file1",
            headers={"Cookie": "accountToken=test"},
            download_page="https://gofile.io/d/root123",
        )
        client.send(item, save_root="D:/Downloads")
        body = session.post.call_args.kwargs["json"]
        self.assertNotIn("queueId", body)

    def test_abdm_send_flat_uses_only_save_root(self):
        session = Mock()
        response = Mock(ok=True, status_code=200)
        session.post.return_value = response
        client = ABDMClient(session=session)
        item = ResolvedFile(
            key="key1",
            id="file1",
            name="Episode01.mkv",
            safe_name="Episode01.mkv",
            size=100,
            relative_folder="Anime/Subs",
            relative_path="Anime/Subs/Episode01.mkv",
            link="https://cold.gofile.io/file1",
            headers={"Cookie": "accountToken=test"},
            download_page="https://gofile.io/d/root123",
        )
        client.send(item, save_root="D:/Downloads", preserve_structure=False)
        body = session.post.call_args.kwargs["json"]
        self.assertEqual(body["folder"], "D:/Downloads")


class ResolveTests(unittest.TestCase):
    def test_recursive_resolve_without_network(self):
        client = GoFileClient(session=Mock())
        client.token = "guest-token"
        tree = {
            "root123": {
                "id": "root123",
                "name": "Anime",
                "type": "folder",
                "childrenCount": 2,
                "children": {
                    "f1": {"id": "file001", "name": "Episode01.mkv", "type": "file", "size": 100, "link": "https://cold.gofile.io/file1"},
                    "sub": {"id": "folder02", "name": "Subs", "type": "folder", "childrenCount": 1},
                },
            },
            "folder02": {
                "id": "folder02",
                "name": "Subs",
                "type": "folder",
                "childrenCount": 1,
                "children": {
                    "f2": {"id": "file002", "name": "Episode01.ass", "type": "file", "size": 20, "link": "https://cold.gofile.io/file2"},
                },
            },
        }
        client.fetch_folder = lambda content_id, password=None: tree[content_id]
        result = client.resolve("root123")
        self.assertEqual(result.root.file_count, 2)
        self.assertEqual(result.root.total_size, 120)
        paths = sorted(item.relative_path for item in result.files.values())
        self.assertEqual(paths, ["Anime/Episode01.mkv", "Anime/Subs/Episode01.ass"])
        for item in result.files.values():
            self.assertIn("accountToken=guest-token", item.headers["Cookie"])

    def test_rejects_non_gofile_direct_link(self):
        client = GoFileClient(session=Mock())
        client.token = "guest-token"
        client.fetch_folder = lambda content_id, password=None: {
            "id": content_id,
            "name": "Folder",
            "type": "folder",
            "childrenCount": 1,
            "children": {
                "f": {
                    "id": "file001",
                    "name": "bad.bin",
                    "type": "file",
                    "size": 1,
                    "link": "https://example.com/not-gofile",
                }
            },
        }
        with self.assertRaises(GoFileError):
            client.resolve("root123")

    def test_folder_credentials_are_explicit_and_inherited_per_branch(self):
        client = GoFileClient(session=Mock())
        client.token = "guest-token"
        root_digest = "a" * 64
        child_digest = "b" * 64
        calls = []
        tree = {
            "root123": {
                "id": "root123", "name": "Root", "type": "folder", "childrenCount": 2,
                "children": {
                    "b": {"id": "folder01", "name": "B", "type": "folder"},
                    "c": {"id": "folder02", "name": "C", "type": "folder"},
                },
            },
            "folder01": {
                "id": "folder01", "name": "B", "type": "folder", "childrenCount": 1,
                "children": {"nested": {"id": "folder03", "name": "Nested", "type": "folder"}},
            },
            "folder02": {
                "id": "folder02", "name": "C", "type": "folder", "childrenCount": 1,
                "children": {"file": {"id": "file002", "name": "c.bin", "type": "file", "size": 2, "link": "https://cold.gofile.io/c"}},
            },
            "folder03": {
                "id": "folder03", "name": "Nested", "type": "folder", "childrenCount": 1,
                "children": {"file": {"id": "file003", "name": "nested.bin", "type": "file", "size": 3, "link": "https://cold.gofile.io/n"}},
            },
        }

        def fetch(content_id, password=None, *, password_hash=None):
            calls.append((content_id, password, password_hash))
            return tree[content_id]

        client.fetch_folder = fetch
        result = client.resolve(
            "root123",
            password_hashes={"root123": root_digest, "folder01": child_digest},
        )

        self.assertEqual(result.root.file_count, 2)
        self.assertEqual(calls, [
            ("root123", None, root_digest),
            ("folder01", None, child_digest),
            ("folder03", None, child_digest),
            ("folder02", None, root_digest),
        ])

    def test_password_challenge_adds_child_display_context(self):
        client = GoFileClient(session=Mock())
        client.token = "guest-token"
        client.fetch_folder = lambda content_id, password=None: (
            {"id": "root123", "name": "Root", "type": "folder", "childrenCount": 1,
             "children": {"sub": {"id": "folder01", "name": "Subs", "type": "folder"}}}
            if content_id == "root123"
            else (_ for _ in ()).throw(PasswordRequired("required", content_id=content_id))
        )

        with self.assertRaises(PasswordRequired) as caught:
            client.resolve("root123")
        self.assertEqual(caught.exception.content_id, "folder01")
        self.assertEqual(caught.exception.folder_name, "Subs")
        self.assertEqual(caught.exception.relative_path, "Root/Subs")


class FolderAccessEnvelopeTests(unittest.TestCase):
    def _client_for_payload(self, payloads):
        session = Mock()
        response = Mock(status_code=200)
        response.json.side_effect = payloads
        session.get.return_value = response
        client = GoFileClient(session=session)
        client.token = "guest-token"
        client.request_interval = 0
        return client, session

    def test_ok_envelope_password_required_is_not_empty_success(self):
        client, session = self._client_for_payload([{
            "status": "ok",
            "data": {"id": "folder01", "name": "Locked", "canAccess": False, "password": True, "passwordStatus": "passwordRequired"},
        }])
        with self.assertRaises(PasswordRequired) as caught:
            client.fetch_folder("folder01")
        self.assertEqual(caught.exception.content_id, "folder01")
        self.assertEqual(session.get.call_count, 1)

    def test_ok_envelope_wrong_password_is_distinguished(self):
        client, _ = self._client_for_payload([{
            "status": "ok",
            "data": {"id": "folder01", "canAccess": False, "password": True, "passwordStatus": "passwordWrong"},
        }])
        from gofile import WrongPassword
        with self.assertRaises(WrongPassword):
            client.fetch_folder("folder01", password_hash="c" * 64)

    def test_ok_envelope_non_password_denial_is_not_a_challenge(self):
        client, _ = self._client_for_payload([{
            "status": "ok",
            "data": {"id": "folder01", "canAccess": False, "password": False},
        }])
        with self.assertRaises(ContentAccessDenied):
            client.fetch_folder("folder01")

    def test_accessible_payload_with_protection_metadata_is_success(self):
        client, _ = self._client_for_payload([{
            "status": "ok",
            "data": {"id": "folder01", "name": "Unlocked", "canAccess": True, "password": True,
                     "passwordStatus": "passwordRequired", "children": {}},
        }])
        data = client.fetch_folder("folder01", password_hash="d" * 64)
        self.assertEqual(data["name"], "Unlocked")
        self.assertEqual(data["children"], {})

    def test_second_page_access_denial_discards_partial_folder(self):
        client = GoFileClient(session=Mock())
        client.token = "guest-token"
        client.request_interval = 0
        first = {
            "status": "ok",
            "data": {"id": "folder01", "name": "Paged", "canAccess": True, "childrenCount": 1001,
                     "children": {str(i): {"id": f"file{i:06d}", "type": "file", "name": f"f{i}", "link": "https://cold.gofile.io/x"} for i in range(1000)}},
        }
        second_error = PasswordRequired("required", content_id="folder01")
        client._request_folder_page = Mock(side_effect=[first, second_error])
        with self.assertRaises(PasswordRequired):
            client.fetch_folder("folder01")
        self.assertEqual(client._request_folder_page.call_count, 2)


class RateLimitSafetyTests(unittest.TestCase):
    def test_guest_token_is_reused(self):
        session = Mock()
        response = Mock(status_code=200)
        response.json.return_value = {"status": "ok", "data": {"token": "guest-token"}}
        session.post.return_value = response
        client = GoFileClient(session=session)

        self.assertEqual(client._guest_token(), "guest-token")
        self.assertEqual(client._guest_token(), "guest-token")
        self.assertEqual(session.post.call_count, 1)

    def test_guest_token_http_429_is_not_retried(self):
        session = Mock()
        response = Mock(status_code=429)
        session.post.return_value = response
        client = GoFileClient(session=session)

        with self.assertRaises(RateLimited):
            client._guest_token()
        self.assertEqual(session.post.call_count, 1)

    def test_guest_token_api_rate_limit_is_not_retried(self):
        session = Mock()
        response = Mock(status_code=200)
        response.json.return_value = {"status": "error-rateLimit"}
        session.post.return_value = response
        client = GoFileClient(session=session)

        with self.assertRaises(RateLimited):
            client._guest_token()
        self.assertEqual(session.post.call_count, 1)

    def test_content_http_429_is_detected_before_json_decode(self):
        session = Mock()
        response = Mock(status_code=429)
        response.json.side_effect = ValueError("HTML rate-limit page")
        session.get.return_value = response
        client = GoFileClient(session=session)
        client.token = "guest-token"

        with self.assertRaises(RateLimited):
            client._request_folder_page("root123", password=None, page=1, window_offset=0)
        response.json.assert_not_called()
        self.assertEqual(session.get.call_count, 1)

    def test_folder_rate_limit_is_not_retried(self):
        client = GoFileClient(session=Mock())
        client.token = "guest-token"
        client._request_folder_page = Mock(side_effect=RateLimited("rate limited"))

        with self.assertRaises(RateLimited):
            client.fetch_folder("root123")
        self.assertEqual(client._request_folder_page.call_count, 1)

    def test_content_request_pacing_spaces_bursts(self):
        client = GoFileClient(session=Mock())
        client.request_interval = 0.75
        with patch("gofile.time.monotonic", side_effect=[10.0, 10.0, 10.2, 10.95]), \
             patch("gofile.time.sleep") as sleep_mock:
            client._pace_content_request()
            client._pace_content_request()
        sleep_mock.assert_called_once()
        self.assertAlmostEqual(sleep_mock.call_args.args[0], 0.55, places=2)

    def test_242_content_requests_accumulate_180_75_seconds_of_pacing(self):
        client = GoFileClient(session=Mock())
        client.request_interval = 0.75
        now = [100.0]

        def monotonic():
            return now[0]

        def sleep(seconds):
            now[0] += seconds

        with patch("gofile.time.monotonic", side_effect=monotonic), \
             patch("gofile.time.sleep", side_effect=sleep):
            for _ in range(242):
                client._pace_content_request()

        self.assertAlmostEqual(now[0] - 100.0, 180.75, places=6)


class HelperRateLimitStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

    def test_helper_reuses_one_gofile_client(self):
        self.assertIn("_gofile_client = GoFileClient()", self.source)
        self.assertNotIn("result = GoFileClient().resolve", self.source)

    def test_helper_serializes_resolves(self):
        self.assertIn("_resolve_lock = threading.Lock()", self.source)
        self.assertIn("with _resolve_lock:", self.source)

    def test_helper_has_source_cache(self):
        self.assertIn("_source_cache", self.source)
        self.assertIn("_password_digest", self.source)
        self.assertIn("password_hashes", self.source)



class UserscriptStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / "gofile-abdm.user.js").read_text(encoding="utf-8")

    def test_minimal_userscript_permissions(self):
        self.assertIn("@match        https://gofile.io/*", self.source)
        self.assertIn("@grant        GM_xmlhttpRequest", self.source)
        self.assertIn("@connect      127.0.0.1", self.source)
        self.assertIn("@connect      localhost", self.source)
        self.assertNotIn("@connect      *", self.source)
        self.assertNotIn("unsafeWindow", self.source)

    def test_helper_only_abdm_flow(self):
        self.assertIn("http://127.0.0.1:8765", self.source)
        self.assertNotIn("localhost:15151", self.source)
        self.assertIn("Send Flat", self.source)
        self.assertIn("preserve_structure: preserveStructure", self.source)
        self.assertIn("/api/abdm/queues", self.source)
        self.assertIn("queue_id: queueId", self.source)
        self.assertIn("Default (ABDM)", self.source)

    def test_selection_fallback_supports_current_and_legacy_row_ids(self):
        self.assertIn("data-content-id", self.source)
        self.assertIn("data-id", self.source)
        self.assertIn("data-item-id", self.source)
        self.assertIn("data-uuid", self.source)
        self.assertIn("visibleContentIds", self.source)

    def test_items_selector_is_always_available(self):
        self.assertIn("items.classList.remove('gab-hidden')", self.source)

    def test_select_all_has_resolved_tree_fallback(self):
        self.assertIn("if (!nodes.length && state.root) nodes = state.root.children || []", self.source)

    def test_selection_works_before_helper_resolve(self):
        self.assertIn("provisionalSelectedIds", self.source)
        self.assertIn("discoverVisibleDomItems", self.source)
        self.assertIn("checkbox.dataset.gabContentId", self.source)
        self.assertIn("await resolveContent(true)", self.source)

    def test_resolve_failure_restores_provisional_checkboxes(self):
        start = self.source.index("  async function resolveContent(")
        end = self.source.index("  function discoverVisibleDomItems()", start)
        resolve_block = self.source[start:end]
        self.assertIn("if (!state.root)", resolve_block)
        self.assertIn("injectCheckboxes();", resolve_block)

    def test_recursive_resolve_has_no_userscript_deadline(self):
        start = self.source.index("  async function resolveContent(")
        end = self.source.index("  function discoverVisibleDomItems()", start)
        resolve_block = self.source[start:end]
        self.assertIn("gmRequest('POST', '/api/gofile/resolve', body, 0)", resolve_block)
        self.assertNotIn("180000", resolve_block)
        self.assertIn("...(timeout > 0 ? { timeout } : {}),", self.source)


@unittest.skipIf(app is None, 'Flask is not installed in this execution environment')
class FlaskGuardTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        with app_module._cache_lock:
            app_module._cache.clear()
            app_module._source_cache.clear()

    def test_health_available(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_api_requires_marker(self):
        response = self.client.get("/api/abdm/status")
        self.assertEqual(response.status_code, 403)

    def test_post_requires_json(self):
        response = self.client.post("/api/gofile/resolve", headers={"X-GoFile-ABDM": "1"}, data="x")
        self.assertEqual(response.status_code, 415)

    def test_invalid_gofile_url_is_rejected(self):
        response = self.client.post(
            "/api/gofile/resolve",
            headers={"X-GoFile-ABDM": "1"},
            json={"url": "https://example.com/d/notallowed"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_content")

    def test_resolve_requires_json_object(self):
        response = self.client.post(
            "/api/gofile/resolve",
            headers={"X-GoFile-ABDM": "1", "Content-Type": "application/json"},
            data="[]",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_body")

    def test_invalid_password_hashes_are_rejected_before_resolve(self):
        invalid_values = [None, [], 7, {"folder01": "not-a-digest"}]
        for invalid in invalid_values:
            with self.subTest(invalid=invalid), patch.object(app_module._gofile_client, "resolve") as resolve_mock:
                response = self.client.post(
                    "/api/gofile/resolve",
                    headers={"X-GoFile-ABDM": "1"},
                    json={"content_id": "root123", "password_hashes": invalid},
                )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.get_json()["error"]["code"], "invalid_password_hashes")
            resolve_mock.assert_not_called()

        too_many = {f"id{index:04d}": "a" * 64 for index in range(1001)}
        response = self.client.post(
            "/api/gofile/resolve",
            headers={"X-GoFile-ABDM": "1"},
            json={"content_id": "root123", "password_hashes": too_many},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_password_hashes")

    def test_password_challenge_returns_safe_target_context_and_no_source_cache(self):
        from gofile import PasswordRequired

        error = PasswordRequired(
            "This GoFile content requires a password.",
            content_id="folder01",
            folder_name="Subs",
            relative_path="Root/Subs",
        )
        with patch.object(app_module._gofile_client, "resolve", side_effect=error):
            response = self.client.post(
                "/api/gofile/resolve",
                headers={"X-GoFile-ABDM": "1"},
                json={"content_id": "root123", "password_hashes": {"root123": "A" * 64}},
            )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], {
            "code": "password_required",
            "message": "This GoFile content requires a password.",
            "content_id": "folder01",
            "folder_name": "Subs",
            "relative_path": "Root/Subs",
        })
        self.assertEqual(len(app_module._source_cache), 0)

    def test_content_access_denied_returns_403_without_password_prompt_code(self):
        with patch.object(app_module._gofile_client, "resolve") as resolve_mock:
            from gofile import ContentAccessDenied
            resolve_mock.side_effect = ContentAccessDenied("GoFile content access was denied.", content_id="folder01")
            response = self.client.post(
                "/api/gofile/resolve",
                headers={"X-GoFile-ABDM": "1"},
                json={"content_id": "root123"},
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"]["code"], "content_access_denied")
        self.assertEqual(response.get_json()["error"]["content_id"], "folder01")

    def test_password_map_normalization_and_root_legacy_precedence(self):
        root_digest = "a" * 64
        child_digest = "b" * 64
        root = ResolvedNode(key="root-key", id="root123", type="folder", name="Root")
        result = ResolveResult(content_id="root123", root_name="Root", root=root, files={})
        observed = []

        def resolve(content_id, *, password_hashes):
            observed.append((content_id, password_hashes))
            return result

        with patch.object(app_module._gofile_client, "resolve", side_effect=resolve):
            response = self.client.post(
                "/api/gofile/resolve",
                headers={"X-GoFile-ABDM": "1"},
                json={
                    "content_id": "root123",
                    "password": "legacy plaintext",
                    "password_hashes": {"folder01": child_digest, "root123": root_digest.upper()},
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed, [("root123", {"folder01": child_digest, "root123": root_digest})])

    def test_legacy_password_is_hashed_once_even_when_it_looks_like_a_digest(self):
        root = ResolvedNode(key="root-key", id="root123", type="folder", name="Root")
        result = ResolveResult(content_id="root123", root_name="Root", root=root, files={})
        observed = []

        def resolve(content_id, *, password_hashes):
            observed.append(password_hashes)
            return result

        plaintext = "A" * 64
        with patch.object(app_module._gofile_client, "resolve", side_effect=resolve):
            response = self.client.post(
                "/api/gofile/resolve",
                headers={"X-GoFile-ABDM": "1"},
                json={"content_id": "root123", "password": plaintext},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed, [{"root123": hashlib.sha256(plaintext.encode("utf-8")).hexdigest()}])

    def test_source_cache_key_is_order_case_invariant_but_child_sensitive(self):
        first = app_module._source_cache_key("root123", password_hashes={"folder01": "A" * 64, "root123": "B" * 64})
        same = app_module._source_cache_key("root123", password_hashes={"root123": "b" * 64, "folder01": "a" * 64})
        different = app_module._source_cache_key("root123", password_hashes={"folder01": "C" * 64, "root123": "B" * 64})
        self.assertEqual(first, same)
        self.assertNotEqual(first, different)

    def test_send_rejects_non_integer_queue_id(self):
        response = self.client.post(
            "/api/abdm/send",
            headers={"X-GoFile-ABDM": "1"},
            json={
                "resolve_id": "dummy",
                "file_keys": ["key1"],
                "save_root": "",
                "preserve_structure": True,
                "queue_id": "7",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_queue_id")


    def test_second_identical_resolve_uses_local_cache(self):
        root = ResolvedNode(key="root-key", id="root123", type="folder", name="Root")
        result = ResolveResult(content_id="root123", root_name="Root", root=root, files={})
        headers = {"X-GoFile-ABDM": "1"}

        with patch.object(app_module._gofile_client, "resolve", return_value=result) as resolve_mock:
            first = self.client.post("/api/gofile/resolve", headers=headers, json={"content_id": "root123"})
            second = self.client.post("/api/gofile/resolve", headers=headers, json={"content_id": "root123"})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(first.get_json()["cached"])
        self.assertTrue(second.get_json()["cached"])
        self.assertNotEqual(first.get_json()["resolve_id"], second.get_json()["resolve_id"])
        self.assertEqual(resolve_mock.call_count, 1)

    def test_password_cache_key_does_not_store_plaintext_password(self):
        key = app_module._source_cache_key("root123", "very-secret-password")
        self.assertEqual(key[0], "root123")
        self.assertNotEqual(key[1], "very-secret-password")
        self.assertEqual(len(key[1]), 64)


if __name__ == "__main__":
    unittest.main()
