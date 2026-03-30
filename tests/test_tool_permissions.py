import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from policies import build_trusted_policy, build_untrusted_policy
from tool_firewall import ToolFirewall


class ToolPermissionTests(unittest.TestCase):
    def test_trusted_can_use_approved_tool(self) -> None:
        policy = build_trusted_policy(
            owner_id=42,
            trusted_model="openai/gpt-trusted",
            trusted_tools={"memory", "search"},
            max_tokens=4000,
        )

        self.assertTrue(ToolFirewall.can_use_tool(policy, "memory"))
        ToolFirewall.enforce(policy, "search")

    def test_trusted_cannot_use_unapproved_tool(self) -> None:
        policy = build_trusted_policy(
            owner_id=42,
            trusted_model="openai/gpt-trusted",
            trusted_tools={"memory"},
            max_tokens=4000,
        )

        with self.assertLogs("tool_firewall", level="INFO") as captured:
            with self.assertRaises(PermissionError):
                ToolFirewall.enforce(policy, "admin_delete")

        self.assertIn("Blocked tool attempt", "\n".join(captured.output))

    def test_untrusted_cannot_use_privileged_tool(self) -> None:
        policy = build_untrusted_policy(
            user_id=77,
            untrusted_model="lmstudio/local-public",
            max_tokens=300,
        )

        self.assertFalse(ToolFirewall.can_use_tool(policy, "memory"))
        with self.assertLogs("tool_firewall", level="INFO") as captured:
            with self.assertRaises(PermissionError):
                ToolFirewall.enforce(policy, "memory")

        joined = "\n".join(captured.output)
        self.assertIn("Blocked tool attempt", joined)
        self.assertIn("tool=memory", joined)
