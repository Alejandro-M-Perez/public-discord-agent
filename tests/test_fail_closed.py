import asyncio
import os
import sys
import unittest
from types import SimpleNamespace


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import AppConfig
from discord_handler import DiscordHandler
from public_responder import PublicResponder
from router import RequestContext, TrustRouter


def make_config(
    *,
    owner_id=42,
    admin_channel_ids=None,
    trusted_model="openai/gpt-trusted",
    untrusted_model="lmstudio/local-public",
) -> AppConfig:
    return AppConfig(
        owner_id=owner_id,
        admin_channel_ids={1001} if admin_channel_ids is None else admin_channel_ids,
        trusted_model=trusted_model,
        untrusted_model=untrusted_model,
        trusted_tools={"discord_send", "search", "planner", "memory"},
        trusted_max_tokens=4000,
        untrusted_max_tokens=300,
    )


class FakeOpenClawClient:
    def __init__(self) -> None:
        self.calls = []
        self.error = None

    async def generate_response(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return "ok"


def make_message(*, author_id, channel_id=None, is_dm=False, content="hello"):
    guild = None if is_dm else SimpleNamespace(id=999)
    channel = SimpleNamespace(id=channel_id) if channel_id is not None else SimpleNamespace()
    author = SimpleNamespace(id=author_id)
    return SimpleNamespace(author=author, channel=channel, guild=guild, content=content)


class FailClosedTests(unittest.TestCase):
    def test_owner_in_non_allowlisted_public_channel_is_refused(self) -> None:
        router = TrustRouter(make_config())
        policy = router.route(RequestContext(author_id=42, channel_id=9999, is_dm=False))

        self.assertEqual(policy.mode, "refused")
        self.assertFalse(policy.model_invocation_allowed)

    def test_non_owner_dm_is_refused(self) -> None:
        router = TrustRouter(make_config())
        policy = router.route(RequestContext(author_id=77, channel_id=None, is_dm=True))

        self.assertEqual(policy.mode, "refused")
        self.assertFalse(policy.model_invocation_allowed)

    def test_missing_owner_id_defaults_away_from_trusted(self) -> None:
        router = TrustRouter(make_config(owner_id=None))
        policy = router.route(RequestContext(author_id=42, channel_id=None, is_dm=True))

        self.assertEqual(policy.mode, "refused")
        self.assertNotEqual(policy.model_alias, "openai/gpt-trusted")

    def test_missing_public_model_does_not_escalate_to_hosted(self) -> None:
        router = TrustRouter(make_config(untrusted_model=""))
        policy = router.route(RequestContext(author_id=77, channel_id=1001, is_dm=False))

        self.assertEqual(policy.mode, "refused")
        self.assertNotEqual(policy.model_alias, "openai/gpt-trusted")
        self.assertFalse(policy.model_invocation_allowed)

    def test_missing_trusted_model_downgrades_owner_to_untrusted(self) -> None:
        router = TrustRouter(make_config(trusted_model=""))
        policy = router.route(RequestContext(author_id=42, channel_id=None, is_dm=True))

        self.assertEqual(policy.mode, "untrusted")
        self.assertEqual(policy.model_alias, "lmstudio/local-public")

    def test_handler_blocks_refused_requests_before_model_call(self) -> None:
        client = FakeOpenClawClient()
        handler = DiscordHandler(TrustRouter(make_config()), client)

        with self.assertLogs("discord_handler", level="INFO") as captured:
            response = asyncio.run(
                handler.handle_message(
                    make_message(author_id=77, channel_id=None, is_dm=True)
                )
            )

        self.assertEqual(response, PublicResponder.DENIAL_RESPONSE)
        self.assertEqual(client.calls, [])
        joined = "\n".join(captured.output)
        self.assertIn("discord_request", joined)
        self.assertIn("'admission_result': 'refused'", joined)
        self.assertIn("'session_namespace': 'no_session'", joined)
        self.assertIn("local_model_invocation_blocked", joined)
        self.assertIn("model_invocation_refused", joined)

    def test_handler_uses_deterministic_public_responder_for_untrusted_requests(self) -> None:
        client = FakeOpenClawClient()
        handler = DiscordHandler(TrustRouter(make_config()), client)

        with self.assertLogs("discord_handler", level="INFO") as captured:
            response = asyncio.run(
                handler.handle_message(
                    make_message(author_id=77, channel_id=1001, is_dm=False, content="hello")
                )
            )

        self.assertEqual(response, PublicResponder.DEFAULT_RESPONSE)
        self.assertEqual(client.calls, [])
        joined = "\n".join(captured.output)
        self.assertIn("discord_request", joined)
        self.assertIn("'admission_result': 'allowed'", joined)
        self.assertIn("'resolved_policy': 'untrusted'", joined)
        self.assertIn("'selected_model_alias': 'lmstudio/local-public'", joined)
        self.assertIn("'session_namespace': 'public:77'", joined)
        self.assertIn("local_model_invocation_skipped", joined)
        self.assertIn("public_response_generated", joined)

    def test_handler_logs_local_model_blocked_when_untrusted_model_missing(self) -> None:
        client = FakeOpenClawClient()
        handler = DiscordHandler(
            TrustRouter(make_config(untrusted_model="")),
            client,
        )

        with self.assertLogs("discord_handler", level="INFO") as captured:
            response = asyncio.run(
                handler.handle_message(
                    make_message(author_id=77, channel_id=1001, is_dm=False)
                )
            )

        self.assertEqual(response, PublicResponder.DENIAL_RESPONSE)
        self.assertEqual(client.calls, [])
        joined = "\n".join(captured.output)
        self.assertIn("local_model_invocation_blocked", joined)

    def test_trusted_requests_still_invoke_hosted_path(self) -> None:
        client = FakeOpenClawClient()
        handler = DiscordHandler(TrustRouter(make_config()), client)

        response = asyncio.run(
            handler.handle_message(
                make_message(author_id=42, channel_id=None, is_dm=True, content="owner request")
            )
        )

        self.assertEqual(response, "ok")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["model_alias"], "openai/gpt-trusted")
        self.assertEqual(client.calls[0]["session_id"], "owner:42")

    def test_public_help_command_returns_canned_response(self) -> None:
        client = FakeOpenClawClient()
        handler = DiscordHandler(TrustRouter(make_config()), client)

        response = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="!help")
            )
        )

        self.assertEqual(response, PublicResponder.HELP_RESPONSE)
        self.assertEqual(client.calls, [])

    def test_public_status_command_returns_canned_response(self) -> None:
        client = FakeOpenClawClient()
        handler = DiscordHandler(TrustRouter(make_config()), client)

        response = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="!status")
            )
        )

        self.assertEqual(response, PublicResponder.STATUS_RESPONSE)
        self.assertEqual(client.calls, [])

    def test_public_about_command_returns_canned_response(self) -> None:
        client = FakeOpenClawClient()
        handler = DiscordHandler(TrustRouter(make_config()), client)

        response = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="!about")
            )
        )

        self.assertEqual(response, PublicResponder.ABOUT_RESPONSE)
        self.assertEqual(client.calls, [])

    def test_public_unknown_message_returns_limited_access_response(self) -> None:
        client = FakeOpenClawClient()
        handler = DiscordHandler(TrustRouter(make_config()), client)

        response = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="what can you do?")
            )
        )

        self.assertEqual(response, PublicResponder.DEFAULT_RESPONSE)
        self.assertEqual(client.calls, [])

    def test_trusted_path_still_surfaces_hosted_failures(self) -> None:
        client = FakeOpenClawClient()
        client.error = RuntimeError("hosted model offline")
        handler = DiscordHandler(TrustRouter(make_config()), client)

        with self.assertRaises(RuntimeError):
            asyncio.run(
                handler.handle_message(
                    make_message(author_id=42, channel_id=None, is_dm=True)
                )
            )
