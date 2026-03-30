import asyncio
import os
import sys
import unittest
from types import SimpleNamespace


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import AppConfig
from discord_handler import DiscordHandler
from public_rate_limiter import PublicRateLimiter
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
    def __init__(self, *, error=None, blocked_tool=None) -> None:
        self.calls = []
        self.error = error
        self.blocked_tool = blocked_tool

    async def generate_response(self, **kwargs):
        self.calls.append(kwargs)
        if self.blocked_tool is not None:
            kwargs["tool_checker"](self.blocked_tool)
        if self.error is not None:
            raise self.error
        return "ok"


def make_message(*, author_id, channel_id=None, is_dm=False, content="hello"):
    guild = None if is_dm else SimpleNamespace(id=999)
    channel = SimpleNamespace(id=channel_id) if channel_id is not None else SimpleNamespace()
    author = SimpleNamespace(id=author_id)
    return SimpleNamespace(author=author, channel=channel, guild=guild, content=content)


class Phase2BBehaviorTests(unittest.TestCase):
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

    def test_missing_owner_id_defaults_to_refused(self) -> None:
        router = TrustRouter(make_config(owner_id=None))
        policy = router.route(RequestContext(author_id=42, channel_id=None, is_dm=True))

        self.assertEqual(policy.mode, "refused")
        self.assertNotEqual(policy.model_alias, "openai/gpt-trusted")

    def test_missing_untrusted_model_does_not_refuse_public_access(self) -> None:
        router = TrustRouter(make_config(untrusted_model=""))
        policy = router.route(RequestContext(author_id=77, channel_id=1001, is_dm=False))

        self.assertEqual(policy.mode, "untrusted")
        self.assertEqual(policy.session_namespace, "public:77")

    def test_missing_trusted_model_refuses_owner_request(self) -> None:
        router = TrustRouter(make_config(trusted_model=""))
        policy = router.route(RequestContext(author_id=42, channel_id=None, is_dm=True))

        self.assertEqual(policy.mode, "refused")
        self.assertFalse(policy.model_invocation_allowed)

    def test_refused_requests_return_canned_denial_and_zero_model_calls(self) -> None:
        client = FakeOpenClawClient()
        responder = PublicResponder()
        handler = DiscordHandler(TrustRouter(make_config()), client, public_responder=responder)

        with self.assertLogs("discord_handler", level="INFO") as captured:
            response = asyncio.run(
                handler.handle_message(
                    make_message(author_id=77, channel_id=None, is_dm=True)
                )
            )

        self.assertIn(
            response,
            set(responder.persona().refused_responses["denial_response"]),
        )
        self.assertEqual(client.calls, [])
        self.assertEqual(len(captured.output), 1)
        joined = "\n".join(captured.output)
        self.assertIn("'admission_result': 'refused'", joined)
        self.assertIn("'policy_mode': 'refused'", joined)
        self.assertIn("'response_mode': 'refused'", joined)
        self.assertIn("'model_alias': 'none'", joined)
        self.assertIn("'session_namespace': 'none'", joined)

    def test_untrusted_requests_use_deterministic_public_response_and_zero_model_calls(self) -> None:
        client = FakeOpenClawClient()
        responder = PublicResponder()
        handler = DiscordHandler(TrustRouter(make_config()), client, public_responder=responder)

        with self.assertLogs("discord_handler", level="INFO") as captured:
            response = asyncio.run(
                handler.handle_message(
                    make_message(author_id=77, channel_id=1001, is_dm=False, content="hello")
                )
            )

        self.assertIn(
            response,
            set(responder.persona().public_responses["default_response"]),
        )
        self.assertEqual(client.calls, [])
        self.assertEqual(len(captured.output), 1)
        joined = "\n".join(captured.output)
        self.assertIn("'admission_result': 'admitted'", joined)
        self.assertIn("'policy_mode': 'untrusted'", joined)
        self.assertIn("'response_mode': 'public_deterministic'", joined)
        self.assertIn("'model_alias': 'none'", joined)
        self.assertIn("'session_namespace': 'public:77'", joined)

    def test_trusted_requests_still_invoke_hosted_path(self) -> None:
        client = FakeOpenClawClient()
        handler = DiscordHandler(TrustRouter(make_config()), client)

        with self.assertLogs("discord_handler", level="INFO") as captured:
            response = asyncio.run(
                handler.handle_message(
                    make_message(author_id=42, channel_id=None, is_dm=True, content="owner request")
                )
            )

        self.assertEqual(response, "ok")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["model_alias"], "openai/gpt-trusted")
        self.assertEqual(client.calls[0]["session_id"], "owner:42")
        self.assertEqual(len(captured.output), 1)
        joined = "\n".join(captured.output)
        self.assertIn("'response_mode': 'trusted_model'", joined)
        self.assertIn("'model_alias': 'openai/gpt-trusted'", joined)

    def test_public_help_command_returns_exact_persona_response(self) -> None:
        responder = PublicResponder()
        handler = DiscordHandler(TrustRouter(make_config()), FakeOpenClawClient(), public_responder=responder)

        response = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="!help")
            )
        )

        self.assertEqual(response, responder.respond("!help"))

    def test_public_status_command_returns_exact_persona_response(self) -> None:
        responder = PublicResponder()
        handler = DiscordHandler(TrustRouter(make_config()), FakeOpenClawClient(), public_responder=responder)

        response = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="!status")
            )
        )

        self.assertEqual(response, responder.respond("!status"))

    def test_public_about_command_returns_exact_persona_response(self) -> None:
        responder = PublicResponder()
        handler = DiscordHandler(TrustRouter(make_config()), FakeOpenClawClient(), public_responder=responder)

        response = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="!about")
            )
        )

        self.assertEqual(response, responder.respond("!about"))

    def test_public_commands_do_not_use_fuzzy_matching(self) -> None:
        responder = PublicResponder()
        handler = DiscordHandler(TrustRouter(make_config()), FakeOpenClawClient(), public_responder=responder)

        response = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="!help now")
            )
        )

        self.assertEqual(response, responder.respond("something else"))

    def test_public_rate_limiting_returns_short_deterministic_response(self) -> None:
        responder = PublicResponder()
        rate_limiter = PublicRateLimiter(cooldown_seconds=60.0)
        handler = DiscordHandler(
            TrustRouter(make_config()),
            FakeOpenClawClient(),
            public_responder=responder,
            public_rate_limiter=rate_limiter,
        )

        first = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="!help")
            )
        )
        second = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="!status")
            )
        )

        self.assertEqual(first, responder.respond("!help"))
        self.assertIn(
            second,
            set(responder.persona().public_responses["rate_limited_response"]),
        )

    def test_public_duplicate_suppression_is_deterministic(self) -> None:
        responder = PublicResponder()
        rate_limiter = PublicRateLimiter(cooldown_seconds=0.0, suppress_duplicates=True, duplicate_window_seconds=60.0)
        handler = DiscordHandler(
            TrustRouter(make_config()),
            FakeOpenClawClient(),
            public_responder=responder,
            public_rate_limiter=rate_limiter,
        )

        first = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="hello")
            )
        )
        second = asyncio.run(
            handler.handle_message(
                make_message(author_id=77, channel_id=1001, is_dm=False, content="hello")
            )
        )

        self.assertIn(
            first,
            set(responder.persona().public_responses["default_response"]),
        )
        self.assertIn(
            second,
            set(responder.persona().public_responses["duplicate_suppressed_response"]),
        )

    def test_trusted_users_are_not_rate_limited(self) -> None:
        client = FakeOpenClawClient()
        rate_limiter = PublicRateLimiter(cooldown_seconds=60.0)
        handler = DiscordHandler(
            TrustRouter(make_config()),
            client,
            public_rate_limiter=rate_limiter,
        )

        asyncio.run(handler.handle_message(make_message(author_id=42, channel_id=None, is_dm=True, content="one")))
        asyncio.run(handler.handle_message(make_message(author_id=42, channel_id=None, is_dm=True, content="two")))

        self.assertEqual(len(client.calls), 2)

    def test_trusted_tool_block_is_reflected_in_message_log(self) -> None:
        client = FakeOpenClawClient(blocked_tool="admin_delete")
        handler = DiscordHandler(TrustRouter(make_config()), client)

        with self.assertLogs("discord_handler", level="INFO") as captured:
            with self.assertRaises(PermissionError):
                asyncio.run(
                    handler.handle_message(
                        make_message(author_id=42, channel_id=None, is_dm=True, content="owner request")
                    )
                )

        self.assertEqual(len(captured.output), 1)
        self.assertIn("'tool_blocked': 'admin_delete'", "\n".join(captured.output))
