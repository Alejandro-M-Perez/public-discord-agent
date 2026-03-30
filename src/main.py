import asyncio
import json
import logging
import os
from pathlib import Path
from urllib import error, request

import discord

from config import load_config
from discord_handler import DiscordHandler
from router import TrustRouter


logger = logging.getLogger(__name__)
OPENCLAW_RESPONSES_URL = "http://127.0.0.1:18789/v1/responses"
OPENCLAW_AGENT_TARGET = "openclaw/default"
TRUSTED_FAILURE_RESPONSE = "Trusted path is temporarily unavailable. Please try again shortly."


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]

        os.environ.setdefault(key, value)


class OpenClawGatewayClient:
    def __init__(self, gateway_token: str):
        self.responses_url = OPENCLAW_RESPONSES_URL
        self.gateway_token = gateway_token

    async def generate_response(
        self,
        *,
        user_text: str,
        model_alias: str,
        session_id: str,
        max_tokens: int,
        memory_enabled: bool,
        max_tool_calls: int,
        tool_checker,
    ) -> str | None:
        payload = {
            "model": OPENCLAW_AGENT_TARGET,
            "input": user_text,
            "max_output_tokens": max_tokens,
        }
        return await asyncio.to_thread(
            self._post_response,
            payload,
            model_alias,
            session_id,
        )

    def _post_response(
        self,
        payload: dict[str, object],
        backend_model_alias: str,
        session_id: str,
    ) -> str | None:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=self.responses_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.gateway_token}",
                "x-openclaw-model": backend_model_alias,
                "x-openclaw-session-key": session_id,
            },
            method="POST",
        )

        logger.info(
            "openclaw_request {'url': '%s', 'agent_target': '%s', 'backend_model_override': '%s', 'session_key': '%s'}",
            self.responses_url,
            OPENCLAW_AGENT_TARGET,
            backend_model_alias,
            session_id,
        )

        try:
            with request.urlopen(req, timeout=60) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.exception(
                "openclaw_request_failed {'url': '%s', 'agent_target': '%s', 'backend_model_override': '%s', 'session_key': '%s', 'status': %s}",
                self.responses_url,
                OPENCLAW_AGENT_TARGET,
                backend_model_alias,
                session_id,
                exc.code,
            )
            raise RuntimeError(f"OpenClaw gateway error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            logger.exception(
                "openclaw_request_failed {'url': '%s', 'agent_target': '%s', 'backend_model_override': '%s', 'session_key': '%s', 'reason': '%s'}",
                self.responses_url,
                OPENCLAW_AGENT_TARGET,
                backend_model_alias,
                session_id,
                exc.reason,
            )
            raise RuntimeError(f"OpenClaw gateway unavailable: {exc.reason}") from exc

        logger.info(
            "openclaw_request_succeeded {'url': '%s', 'agent_target': '%s', 'backend_model_override': '%s', 'session_key': '%s'}",
            self.responses_url,
            OPENCLAW_AGENT_TARGET,
            backend_model_alias,
            session_id,
        )

        output_text = response_data.get("output_text")
        if isinstance(output_text, str) and output_text:
            return output_text

        output = response_data.get("output")
        if isinstance(output, list):
            fragments: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                for content in item.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "output_text":
                        text = content.get("text")
                        if isinstance(text, str):
                            fragments.append(text)
            joined = "".join(fragments).strip()
            return joined or None

        return None


class DiscordBridgeClient(discord.Client):
    def __init__(self, discord_handler: DiscordHandler):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.discord_handler = discord_handler

    async def on_ready(self) -> None:
        if self.user is not None:
            logger.info("discord_bot_ready {'bot_user_id': %s}", self.user.id)

    async def on_message(self, message: discord.Message) -> None:
        if self.user is not None and message.author.id == self.user.id:
            return

        if getattr(message.author, "bot", False):
            return

        try:
            response = await self.discord_handler.handle_message(message)
        except Exception:
            logger.exception(
                "discord_handler_failed {'channel_id': %s, 'author_id': %s}",
                getattr(message.channel, "id", None),
                getattr(message.author, "id", None),
            )
            response = TRUSTED_FAILURE_RESPONSE

        if response:
            await message.channel.send(response)


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    bot_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required.")
    gateway_token = os.getenv("OPENCLAW_GATEWAY_TOKEN", "").strip()
    if not gateway_token:
        raise RuntimeError("OPENCLAW_GATEWAY_TOKEN is required.")

    app_config = load_config()
    router = TrustRouter(app_config)
    openclaw_client = OpenClawGatewayClient(gateway_token=gateway_token)
    discord_handler = DiscordHandler(router, openclaw_client)
    client = DiscordBridgeClient(discord_handler)
    client.run(bot_token)


if __name__ == "__main__":
    main()
