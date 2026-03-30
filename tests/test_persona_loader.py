import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from persona_loader import PersonaLoader
from public_responder import PublicResponder


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def seed_templates(root: Path) -> None:
    write_json(
        root / "persona_templates" / "profile.example.json",
        {
            "persona_name": "Template Bot",
            "public_mode_label": "template public mode",
        },
    )
    write_json(
        root / "persona_templates" / "public_responses.example.json",
        {
            "default_response": ["{persona_name} default a", "{persona_name} default b"],
            "rate_limited_response": ["{persona_name} cooldown a", "{persona_name} cooldown b"],
            "duplicate_suppressed_response": ["{persona_name} duplicate a", "{persona_name} duplicate b"],
        },
    )
    write_json(
        root / "persona_templates" / "refused_responses.example.json",
        {
            "denial_response": ["{persona_name} denied a", "{persona_name} denied b"],
        },
    )
    write_json(
        root / "persona_templates" / "command_text.example.json",
        {
            "!help": "{persona_name} help",
            "!status": "{persona_name} status",
            "!about": "{persona_name} about",
        },
    )


class PersonaLoaderTests(unittest.TestCase):
    def test_active_persona_files_override_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            seed_templates(root)
            write_json(
                root / "persona" / "active" / "profile.json",
                {
                    "persona_name": "Custom Bot",
                    "public_mode_label": "custom public mode",
                },
            )
            write_json(
                root / "persona" / "active" / "public_responses.json",
                {
                    "default_response": ["{persona_name} custom default a", "{persona_name} custom default b"],
                    "rate_limited_response": ["{persona_name} custom cooldown a", "{persona_name} custom cooldown b"],
                    "duplicate_suppressed_response": ["{persona_name} custom duplicate a", "{persona_name} custom duplicate b"],
                },
            )
            write_json(
                root / "persona" / "active" / "refused_responses.json",
                {
                    "denial_response": ["{persona_name} custom denied a", "{persona_name} custom denied b"],
                },
            )
            write_json(
                root / "persona" / "active" / "command_text.json",
                {
                    "!help": "{persona_name} custom help",
                    "!status": "{persona_name} custom status",
                    "!about": "{persona_name} custom about",
                },
            )

            responder = PublicResponder(PersonaLoader(root))

            self.assertEqual(responder.respond("!help"), "Custom Bot custom help")
            self.assertIn(
                responder.respond("hello", seed="public-seed"),
                {"Custom Bot custom default a", "Custom Bot custom default b"},
            )
            self.assertIn(
                responder.refusal_response(seed="refused-seed"),
                {"Custom Bot custom denied a", "Custom Bot custom denied b"},
            )

    def test_missing_active_persona_files_fallback_to_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            seed_templates(root)

            responder = PublicResponder(PersonaLoader(root))

            self.assertEqual(responder.respond("!status"), "Template Bot status")
            self.assertIn(
                responder.respond("hello", seed="default-seed"),
                {"Template Bot default a", "Template Bot default b"},
            )
            self.assertIn(
                responder.rate_limited_response("cooldown", seed="cooldown-seed"),
                {"Template Bot cooldown a", "Template Bot cooldown b"},
            )

    def test_invalid_active_persona_files_fallback_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            seed_templates(root)
            broken_path = root / "persona" / "active" / "command_text.json"
            broken_path.parent.mkdir(parents=True, exist_ok=True)
            broken_path.write_text("{not-json", encoding="utf-8")

            responder = PublicResponder(PersonaLoader(root))

            self.assertEqual(responder.respond("!about"), "Template Bot about")

    def test_rotation_is_seeded_and_stays_within_phrase_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            seed_templates(root)
            responder = PublicResponder(PersonaLoader(root))

            options = {"Template Bot default a", "Template Bot default b"}
            first = responder.respond("hello", seed="seed-one")
            second = responder.respond("hello", seed="seed-two")
            repeated = responder.respond("hello", seed="seed-one")

            self.assertIn(first, options)
            self.assertIn(second, options)
            self.assertEqual(first, repeated)

    def test_missing_persona_field_falls_back_to_template_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            seed_templates(root)
            write_json(
                root / "persona" / "active" / "public_responses.json",
                {
                    "default_response": ["Custom default only"],
                },
            )

            responder = PublicResponder(PersonaLoader(root))

            self.assertEqual(responder.respond("hello", seed="x"), "Custom default only")
            self.assertIn(
                responder.rate_limited_response("cooldown", seed="y"),
                {"Template Bot cooldown a", "Template Bot cooldown b"},
            )
