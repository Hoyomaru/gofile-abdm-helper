import unittest
from unittest.mock import Mock, patch

import requests

import app as app_module
from abdm import ABDMClient, ABDMUncertainError
from gofile import ResolvedFile, ResolvedNode, ResolveResult


class ABDMSendOutcomeTests(unittest.TestCase):
    def _item(self):
        return ResolvedFile(
            key="key1",
            id="file001",
            name="Episode01.mkv",
            safe_name="Episode01.mkv",
            size=100,
            relative_folder="Root",
            relative_path="Root/Episode01.mkv",
            link="https://cold.gofile.io/file1",
            headers={"Cookie": "accountToken=test"},
            download_page="https://gofile.io/d/root123",
        )

    def test_transport_failure_is_uncertain_not_definite_failure(self):
        session = Mock()
        session.post.side_effect = requests.Timeout("response timeout")
        client = ABDMClient(session=session)

        with self.assertRaises(ABDMUncertainError):
            client.send(self._item())

    def test_http_failure_remains_definite(self):
        session = Mock()
        session.post.return_value = Mock(ok=False, status_code=503)
        result = ABDMClient(session=session).send(self._item())

        self.assertFalse(result.ok)
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.message, "ABDM returned HTTP 503")


class HelperSendRegressionTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()
        with app_module._cache_lock:
            app_module._cache.clear()
            app_module._source_cache.clear()

    @property
    def headers(self):
        return {"X-GoFile-ABDM": "1", "Content-Type": "application/json"}

    def test_send_requires_json_object(self):
        for body in ("[]", '"text"', "7", "null"):
            with self.subTest(body=body):
                response = self.client.post("/api/abdm/send", headers=self.headers, data=body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"]["code"], "invalid_body")

    def test_uncertain_abdm_result_is_not_counted_as_failed(self):
        item = ResolvedFile(
            key="key1",
            id="file001",
            name="Episode01.mkv",
            safe_name="Episode01.mkv",
            size=100,
            relative_folder="Root",
            relative_path="Root/Episode01.mkv",
            link="https://cold.gofile.io/file1",
            headers={"Cookie": "accountToken=test"},
            download_page="https://gofile.io/d/root123",
        )
        root = ResolvedNode(
            key="root-key",
            id="root123",
            type="folder",
            name="Root",
            children=[ResolvedNode(
                key=item.key,
                id=item.id,
                type="file",
                name=item.name,
                size=item.size,
                relative_path=item.relative_path,
                file_keys=[item.key],
            )],
            file_keys=[item.key],
        )
        resolved = ResolveResult(
            content_id="root123",
            root_name="Root",
            root=root,
            files={item.key: item},
        )
        resolve_id = app_module._cache_put(resolved)
        mock_client = Mock()
        mock_client.send.side_effect = ABDMUncertainError(
            "ABDM did not confirm whether the download task was accepted."
        )

        with patch.object(app_module, "ABDMClient", return_value=mock_client):
            response = self.client.post(
                "/api/abdm/send",
                headers={"X-GoFile-ABDM": "1"},
                json={
                    "resolve_id": resolve_id,
                    "file_keys": [item.key],
                    "save_root": "",
                    "preserve_structure": True,
                    "queue_id": None,
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["success"], 0)
        self.assertEqual(payload["failed"], 0)
        self.assertEqual(payload["uncertain"], 1)
        self.assertFalse(payload["results"][0]["ok"])
        self.assertTrue(payload["results"][0]["uncertain"])


if __name__ == "__main__":
    unittest.main()
