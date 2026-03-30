import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from policies import build_refused_policy, build_trusted_policy, build_untrusted_policy
from session_manager import SessionManager


class SessionIsolationTests(unittest.TestCase):
    def test_owner_namespace_uses_owner_prefix(self) -> None:
        policy = build_trusted_policy(
            owner_id=42,
            trusted_model="openai/gpt-trusted",
            trusted_tools={"memory"},
            max_tokens=4000,
        )

        self.assertEqual(SessionManager.get_session_id(policy), "owner:42")

    def test_public_namespace_uses_user_prefix(self) -> None:
        policy = build_untrusted_policy(
            user_id=77,
            untrusted_model="lmstudio/local-public",
            max_tokens=300,
        )

        self.assertEqual(SessionManager.get_session_id(policy), "public:77")

    def test_public_users_do_not_share_namespaces(self) -> None:
        first = build_untrusted_policy(
            user_id=77,
            untrusted_model="lmstudio/local-public",
            max_tokens=300,
        )
        second = build_untrusted_policy(
            user_id=88,
            untrusted_model="lmstudio/local-public",
            max_tokens=300,
        )

        self.assertNotEqual(
            SessionManager.get_session_id(first),
            SessionManager.get_session_id(second),
        )
        self.assertNotEqual(
            SessionManager.get_session_id(first),
            "owner:42",
        )

    def test_refused_requests_do_not_get_session_ids(self) -> None:
        with self.assertRaises(PermissionError):
            SessionManager.get_session_id(build_refused_policy("denied"))
