# filename: tests/test_core.py
import unittest
from pathlib import Path
from unittest.mock import Mock

from abdm import ABDMClient
try:
    from app import app
except ModuleNotFoundError as exc:
    if exc.name == 'flask':
        app = None
    else:
        raise
from gofile import GoFileClient, InvalidContent, ResolvedFile, parse_content_id, sanitize_relative_path, sanitize_segment


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


@unittest.skipIf(app is None, 'Flask is not installed in this execution environment')
class FlaskGuardTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

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


if __name__ == "__main__":
    unittest.main()
