import unittest
from unittest.mock import Mock, patch

import requests

from abdm import ABDMClient
from gofile import GoFileClient, WebsiteTokenRejected


class WebsiteTokenRetryRegressionTests(unittest.TestCase):
    def _payload(self):
        return {
            "data": {
                "id": "root123",
                "name": "Root",
                "type": "folder",
                "childrenCount": 0,
                "children": {},
            }
        }

    def test_timeout_retries_current_window_without_falling_back(self):
        client = GoFileClient(session=Mock())
        client.token = "guest-token"
        calls = []

        def request(content_id, **kwargs):
            calls.append(kwargs["window_offset"])
            if len(calls) == 1:
                raise requests.Timeout("temporary timeout")
            return self._payload()

        client._request_folder_page = request
        with patch("gofile.time.sleep"):
            result = client.fetch_folder("root123")

        self.assertEqual(result["name"], "Root")
        self.assertEqual(calls, [0, 0])

    def test_website_token_rejection_falls_back_once_to_previous_window(self):
        client = GoFileClient(session=Mock())
        client.token = "guest-token"
        calls = []

        def request(content_id, **kwargs):
            calls.append(kwargs["window_offset"])
            if len(calls) == 1:
                raise WebsiteTokenRejected("rejected")
            return self._payload()

        client._request_folder_page = request
        result = client.fetch_folder("root123")

        self.assertEqual(result["name"], "Root")
        self.assertEqual(calls, [0, -1])

    def test_previous_window_rejection_is_not_retried(self):
        client = GoFileClient(session=Mock())
        client.token = "guest-token"
        calls = []

        def request(content_id, **kwargs):
            calls.append(kwargs["window_offset"])
            raise WebsiteTokenRejected("rejected")

        client._request_folder_page = request
        with self.assertRaises(WebsiteTokenRejected):
            client.fetch_folder("root123")

        self.assertEqual(calls, [0, -1])


class WindowsDriveRootRegressionTests(unittest.TestCase):
    def test_drive_root_keeps_trailing_slash(self):
        self.assertEqual(ABDMClient.build_folder(r"C:\", ""), "C:/")
        self.assertEqual(ABDMClient.build_folder("D:/", ""), "D:/")

    def test_drive_root_joins_relative_folder_without_double_slash(self):
        self.assertEqual(ABDMClient.build_folder(r"C:\", "Anime/Subs"), "C:/Anime/Subs")


class SanitizedCollisionRegressionTests(unittest.TestCase):
    def test_colliding_file_names_get_unique_safe_names(self):
        client = GoFileClient(session=Mock())
        client.token = "guest-token"
        client.fetch_folder = lambda content_id, password=None: {
            "id": content_id,
            "name": "Root",
            "type": "folder",
            "childrenCount": 2,
            "children": {
                "first": {
                    "id": "file001",
                    "name": "episode:01.mkv",
                    "type": "file",
                    "size": 1,
                    "link": "https://cold.gofile.io/first",
                },
                "second": {
                    "id": "file002",
                    "name": "episode?01.mkv",
                    "type": "file",
                    "size": 1,
                    "link": "https://cold.gofile.io/second",
                },
            },
        }

        result = client.resolve("root123")
        safe_names = [item.safe_name for item in result.files.values()]

        self.assertEqual(len(set(name.casefold() for name in safe_names)), 2)
        self.assertIn("episode_01.mkv", safe_names)
        self.assertTrue(any("~" in name for name in safe_names))

    def test_colliding_folder_names_get_unique_relative_folders(self):
        client = GoFileClient(session=Mock())
        client.token = "guest-token"
        tree = {
            "root123": {
                "id": "root123",
                "name": "Root",
                "type": "folder",
                "childrenCount": 2,
                "children": {
                    "first": {"id": "folder01", "name": "A:B", "type": "folder"},
                    "second": {"id": "folder02", "name": "A?B", "type": "folder"},
                },
            },
            "folder01": {
                "id": "folder01",
                "name": "A:B",
                "type": "folder",
                "childrenCount": 1,
                "children": {
                    "file": {
                        "id": "file001",
                        "name": "one.bin",
                        "type": "file",
                        "size": 1,
                        "link": "https://cold.gofile.io/one",
                    }
                },
            },
            "folder02": {
                "id": "folder02",
                "name": "A?B",
                "type": "folder",
                "childrenCount": 1,
                "children": {
                    "file": {
                        "id": "file002",
                        "name": "two.bin",
                        "type": "file",
                        "size": 1,
                        "link": "https://cold.gofile.io/two",
                    }
                },
            },
        }
        client.fetch_folder = lambda content_id, password=None: tree[content_id]

        result = client.resolve("root123")
        relative_folders = [item.relative_folder for item in result.files.values()]

        self.assertEqual(len(set(path.casefold() for path in relative_folders)), 2)
        self.assertTrue(all(path.startswith("Root/") for path in relative_folders))
        self.assertTrue(any("~" in path for path in relative_folders))


if __name__ == "__main__":
    unittest.main()
