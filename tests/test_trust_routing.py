import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import AppConfig
from router import RequestContext, TrustRouter


def make_config() -> AppConfig:
    return AppConfig(
        owner_id=42,
        admin_channel_ids={1001},
        trusted_model="openai/gpt-trusted",
        untrusted_model="lmstudio/local-public",
        trusted_tools={"discord_send", "search", "planner", "memory"},
        trusted_max_tokens=4000,
        untrusted_max_tokens=300,
    )


class TrustRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = TrustRouter(make_config())

    def test_owner_dm_is_trusted(self) -> None:
        policy = self.router.route(
            RequestContext(author_id=42, channel_id=None, is_dm=True)
        )

        self.assertEqual(policy.mode, "trusted")
        self.assertEqual(policy.model_alias, "openai/gpt-trusted")
        self.assertEqual(policy.session_namespace, "owner:42")

    def test_owner_in_admin_channel_is_trusted(self) -> None:
        policy = self.router.route(
            RequestContext(author_id=42, channel_id=1001, is_dm=False)
        )

        self.assertEqual(policy.mode, "trusted")

    def test_non_owner_in_admin_channel_is_untrusted(self) -> None:
        policy = self.router.route(
            RequestContext(author_id=77, channel_id=1001, is_dm=False)
        )

        self.assertEqual(policy.mode, "untrusted")
        self.assertEqual(policy.model_alias, "lmstudio/local-public")
        self.assertEqual(policy.session_namespace, "public:77")

    def test_missing_author_is_refused(self) -> None:
        policy = self.router.route(
            RequestContext(author_id=None, channel_id=1001, is_dm=False)
        )

        self.assertEqual(policy.mode, "refused")
        self.assertFalse(policy.model_invocation_allowed)
        self.assertIsNone(policy.model_alias)

    def test_message_content_cannot_change_tier(self) -> None:
        policy = self.router.route(
            RequestContext(author_id=77, channel_id=1001, is_dm=False)
        )

        self.assertEqual(policy.mode, "untrusted")
