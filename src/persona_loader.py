from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


EMERGENCY_PROFILE_DEFAULTS = {
    "persona_name": "Claw Capone",
    "public_mode_label": "limited deterministic mode",
}

EMERGENCY_PUBLIC_DEFAULTS = {
    "default_response": [
        "Limited access: public users can use only !help, !status, and !about right now."
    ],
    "rate_limited_response": [
        "Slow down. Public access is rate limited."
    ],
    "duplicate_suppressed_response": [
        "Duplicate message ignored in limited public mode."
    ],
}

EMERGENCY_REFUSED_DEFAULTS = {
    "denial_response": [
        "Access denied. This bot is not available in this channel or DM for your account."
    ]
}

EMERGENCY_COMMAND_DEFAULTS = {
    "!help": "{persona_name} is in limited access mode. Available commands: !help, !status, !about.",
    "!status": "Status: {persona_name} is running in {public_mode_label}.",
    "!about": (
        "{persona_name} uses owner-trusted hosted routing and deterministic public responses."
    ),
}


@dataclass(frozen=True)
class PersonaBundle:
    profile: dict[str, str]
    public_responses: dict[str, list[str]]
    refused_responses: dict[str, list[str]]
    command_text: dict[str, str]


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class PersonaLoader:
    def __init__(self, root_dir: str | Path | None = None):
        repo_root = Path(root_dir) if root_dir is not None else Path(__file__).resolve().parent.parent
        self.repo_root = repo_root
        self.active_dir = repo_root / "persona" / "active"
        self.template_dir = repo_root / "persona_templates"

    def load(self) -> PersonaBundle:
        profile = self._load_section(
            active_name="profile.json",
            template_name="profile.example.json",
            fallback=EMERGENCY_PROFILE_DEFAULTS,
            required_keys={"persona_name", "public_mode_label"},
        )
        public_responses = self._format_section(
            self._load_section(
                active_name="public_responses.json",
                template_name="public_responses.example.json",
                fallback=EMERGENCY_PUBLIC_DEFAULTS,
                required_keys={
                    "default_response",
                    "rate_limited_response",
                    "duplicate_suppressed_response",
                },
            ),
            profile,
        )
        refused_responses = self._format_section(
            self._load_section(
                active_name="refused_responses.json",
                template_name="refused_responses.example.json",
                fallback=EMERGENCY_REFUSED_DEFAULTS,
                required_keys={"denial_response"},
            ),
            profile,
        )
        command_text = self._format_section(
            self._load_section(
                active_name="command_text.json",
                template_name="command_text.example.json",
                fallback=EMERGENCY_COMMAND_DEFAULTS,
                required_keys={"!help", "!status", "!about"},
            ),
            profile,
        )

        return PersonaBundle(
            profile=profile,
            public_responses=public_responses,
            refused_responses=refused_responses,
            command_text=command_text,
        )

    @staticmethod
    def choose_line(options: list[str], seed: str | None = None) -> str:
        if not options:
            return ""
        if seed is None:
            return options[0]
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % len(options)
        return options[index]

    def _load_section(
        self,
        *,
        active_name: str,
        template_name: str,
        fallback: dict[str, str] | dict[str, list[str]],
        required_keys: set[str],
    ) -> dict[str, str] | dict[str, list[str]]:
        defaults = self._read_json_file(self.template_dir / template_name)
        if not self._is_valid_section(defaults, required_keys):
            defaults = fallback

        merged = dict(defaults)
        active_data = self._read_json_file(self.active_dir / active_name)
        if isinstance(active_data, dict):
            for key, value in active_data.items():
                if isinstance(key, str) and self._is_valid_value(value):
                    merged[key] = value

        if not self._is_valid_section(merged, required_keys):
            return dict(defaults)

        return merged

    @staticmethod
    def _read_json_file(path: Path) -> dict[str, object] | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None

        return data if isinstance(data, dict) else None

    @staticmethod
    def _is_valid_section(section: dict[str, object] | None, required_keys: set[str]) -> bool:
        if not isinstance(section, dict):
            return False

        for key in required_keys:
            value = section.get(key)
            if not PersonaLoader._is_valid_value(value):
                return False

        return True

    @staticmethod
    def _is_valid_value(value: object) -> bool:
        if isinstance(value, str):
            return bool(value)
        if isinstance(value, list):
            return bool(value) and all(isinstance(item, str) and item for item in value)
        return False

    @staticmethod
    def _format_section(
        section: dict[str, object],
        profile: dict[str, str],
    ) -> dict[str, str] | dict[str, list[str]]:
        safe_profile = _SafeFormatDict(profile)
        formatted: dict[str, str] | dict[str, list[str]] = {}
        for key, value in section.items():
            if isinstance(value, str):
                formatted[key] = value.format_map(safe_profile)
            elif isinstance(value, list):
                formatted[key] = [item.format_map(safe_profile) for item in value if isinstance(item, str)]
        return formatted
