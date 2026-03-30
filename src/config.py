from dataclasses import dataclass
import os

@dataclass(frozen=True)
class AppConfig:
    owner_id: int
    admin_channel_ids: set[int]
    trusted_model: str
    untrusted_model: str
    trusted_tools: set[str]
    trusted_max_tokens: int
    untrusted_max_tokens: int

def load_config() -> AppConfig:
    owner_id = int(os.environ["OWNER_ID"])
    admin_channels_raw = os.getenv("ADMIN_CHANNEL_IDS", "")
    admin_channel_ids = {
        int(x.strip()) for x in admin_channels_raw.split(",") if x.strip()
    }

    return AppConfig(
        owner_id=owner_id,
        admin_channel_ids=admin_channel_ids,
        trusted_model="openai/gpt-trusted",
        untrusted_model="lmstudio/local-public",
        trusted_tools={"discord_send", "search", "planner", "memory"},
        trusted_max_tokens=4000,
        untrusted_max_tokens=300,
    )
