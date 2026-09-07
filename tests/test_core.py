# filename: tests/test_core.py
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
    GoFileClient,
    InvalidContent,
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
        from gofile import GoFileError
        with self.assertRaises(GoFileError):
            client.resolve("root123")


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
        self.assertIn("password_digest = hashlib.sha256", self.source)



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
        self.assertIn("if (!state.root) injectCheckboxes();", resolve_block)

    def test_recursive_resolve_has_no_userscript_deadline(self):
        start = self.source.index("  async function resolveContent(")
        end = self.source.index("  function discoverVisibleDomItems()", start)
        resolve_block = self.source[start:end]
        self.assertIn("}, 0);", resolve_block)
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
