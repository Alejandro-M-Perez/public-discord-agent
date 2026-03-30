from dataclasses import dataclass
import os

@dataclass(frozen=True)
class AppConfig:
    owner_id: int | None
    admin_channel_ids: set[int]
    trusted_model: str
    untrusted_model: str
    trusted_tools: set[str]
    trusted_max_tokens: int
    untrusted_max_tokens: int

def _parse_optional_int(raw_value: str | None) -> int | None:
    if raw_value is None:
        return None

    value = raw_value.strip()
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def _parse_admin_channel_ids(raw_value: str) -> set[int]:
    admin_channel_ids: set[int] = set()

    for item in raw_value.split(","):
        value = item.strip()
        if not value:
            continue

        try:
            admin_channel_ids.add(int(value))
        except ValueError:
            continue

    return admin_channel_ids


def load_config() -> AppConfig:
    owner_id = _parse_optional_int(os.getenv("OWNER_ID"))
    admin_channels_raw = os.getenv("ADMIN_CHANNEL_IDS", "")
    admin_channel_ids = _parse_admin_channel_ids(admin_channels_raw)

    return AppConfig(
        owner_id=owner_id,
        admin_channel_ids=admin_channel_ids,
        trusted_model="openai/gpt-trusted",
        untrusted_model="lmstudio/local-public",
        trusted_tools={"discord_send", "search", "planner", "memory"},
        trusted_max_tokens=4000,
        untrusted_max_tokens=300,
    )
