import asyncio
import io
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from urllib import error


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from discord_handler import DiscordHandler
from main import (
    DiscordBridgeClient,
    OPENCLAW_AGENT_TARGET,
    OPENCLAW_RESPONSES_URL,
    OpenClawGatewayClient,
    TRUSTED_FAILURE_RESPONSE,
)
from router import TrustRouter

from test_fail_closed import FakeOpenClawClient, make_config, make_message


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class OpenClawGatewayClientTests(unittest.TestCase):
    def test_trusted_transport_posts_to_documented_responses_endpoint(self) -> None:
        client = OpenClawGatewayClient(gateway_token="secret-token")
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout=0):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            captured["headers"] = dict(req.header_items())
            captured["body"] = json.loads(req.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeHTTPResponse({"output_text": "owner reply"})

        with patch("main.request.urlopen", side_effect=fake_urlopen):
            response = client._post_response(
                {"model": OPENCLAW_AGENT_TARGET, "input": "owner request", "max_output_tokens": 4000},
                "openai/gpt-trusted",
                "owner:42",
            )

        self.assertEqual(response, "owner reply")
        self.assertEqual(captured["url"], OPENCLAW_RESPONSES_URL)
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["body"]["model"], "openclaw/default")
        self.assertEqual(captured["headers"]["Content-type"], "application/json")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer secret-token")
        self.assertEqual(captured["headers"]["X-openclaw-model"], "openai/gpt-trusted")
        self.assertEqual(captured["headers"]["X-openclaw-session-key"], "owner:42")

    def test_trusted_transport_logs_session_key_without_secrets(self) -> None:
        client = OpenClawGatewayClient(gateway_token="super-secret")

        with self.assertLogs("main", level="INFO") as captured:
            with patch("main.request.urlopen", return_value=FakeHTTPResponse({"output_text": "ok"})):
                response = client._post_response(
                    {"model": OPENCLAW_AGENT_TARGET, "input": "owner request", "max_output_tokens": 4000},
                    "openai/gpt-trusted",
                    "owner:42",
                )

        self.assertEqual(response, "ok")
        joined = "\n".join(captured.output)
        self.assertIn(OPENCLAW_RESPONSES_URL, joined)
        self.assertIn("openclaw/default", joined)
        self.assertIn("openai/gpt-trusted", joined)
        self.assertIn("owner:42", joined)
        self.assertNotIn("super-secret", joined)


class DiscordBridgeClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_trusted_http_404_returns_fallback_without_crashing(self) -> None:
        handler = DiscordHandler(
            TrustRouter(make_config()),
            FakeOpenClawClient(error=RuntimeError("OpenClaw gateway error 404: Not Found")),
        )
        client = DiscordBridgeClient(handler)
        client._connection.user = SimpleNamespace(id=5000)
        sent_messages: list[str] = []

        async def fake_send(content: str) -> None:
            sent_messages.append(content)

        message = make_message(author_id=42, channel_id=None, is_dm=True, content="owner request")
        message.author.bot = False
        message.channel.send = fake_send

        with self.assertLogs("main", level="ERROR") as captured:
            await client.on_message(message)

        self.assertEqual(sent_messages, [TRUSTED_FAILURE_RESPONSE])
        self.assertIn("discord_handler_failed", "\n".join(captured.output))

    async def test_bot_ignores_its_own_messages(self) -> None:
        handler = DiscordHandler(TrustRouter(make_config()), FakeOpenClawClient())
        client = DiscordBridgeClient(handler)
        client._connection.user = SimpleNamespace(id=42)
        sent_messages: list[str] = []

        async def fake_send(content: str) -> None:
            sent_messages.append(content)

        message = make_message(author_id=42, channel_id=None, is_dm=True, content="owner request")
        message.author.bot = False
        message.channel.send = fake_send

        await client.on_message(message)

        self.assertEqual(sent_messages, [])


class DocumentationContractTests(unittest.TestCase):
    def test_readme_documents_backend_only_openclaw_contract(self) -> None:
        readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
        with open(readme_path, "r", encoding="utf-8") as handle:
            readme_text = handle.read()

        self.assertIn("src/main.py", readme_text)
        self.assertIn("http://127.0.0.1:18789/v1/responses", readme_text)
        self.assertIn("built-in Discord provider disabled", readme_text)
        self.assertIn("enable the HTTP responses endpoint", readme_text)

    def test_example_config_documents_http_responses_and_disables_discord_provider(self) -> None:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "openclaw.example.json")
        with open(config_path, "r", encoding="utf-8") as handle:
            config_text = handle.read()

        self.assertIn('"mode": "local"', config_text)
        self.assertIn('"responses": {', config_text)
        self.assertIn('"enabled": true', config_text)
        self.assertIn('"auth": {', config_text)
        self.assertIn('"mode": "token"', config_text)
        self.assertIn('"discord": {', config_text)
        self.assertIn('"enabled": false', config_text)


class TransportErrorTests(unittest.TestCase):
    def test_http_404_raises_runtime_error_with_status_detail(self) -> None:
        client = OpenClawGatewayClient(gateway_token="secret-token")

        def fake_urlopen(req, timeout=0):
            raise error.HTTPError(
                req.full_url,
                404,
                "Not Found",
                hdrs=None,
                fp=io.BytesIO(b"Not Found"),
            )

        with self.assertLogs("main", level="ERROR") as captured_logs:
            with patch("main.request.urlopen", side_effect=fake_urlopen):
                with self.assertRaises(RuntimeError) as captured:
                    client._post_response(
                        {"model": OPENCLAW_AGENT_TARGET, "input": "owner request", "max_output_tokens": 4000},
                        "openai/gpt-trusted",
                        "owner:42",
                    )

        self.assertIn("404", str(captured.exception))
        self.assertIn("Not Found", str(captured.exception))
        self.assertIn("openclaw_request_failed", "\n".join(captured_logs.output))
