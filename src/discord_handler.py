from router import TrustRouter, RequestContext
from session_manager import SessionManager
from tool_firewall import ToolFirewall
from public_responder import PublicResponder
from public_rate_limiter import PublicRateLimiter
import logging


logger = logging.getLogger(__name__)

class DiscordHandler:
    def __init__(
        self,
        router,
        openclaw_client,
        public_responder: PublicResponder | None = None,
        public_rate_limiter: PublicRateLimiter | None = None,
    ):
        self.router = router
        self.openclaw_client = openclaw_client
        self.public_responder = public_responder or PublicResponder()
        self.public_rate_limiter = public_rate_limiter or PublicRateLimiter()

    @staticmethod
    def _session_label(session_id: str | None) -> str:
        return session_id if session_id is not None else "none"

    def _build_log_record(self, ctx: RequestContext, policy) -> dict[str, str | int | bool | None]:
        session_namespace = policy.session_namespace if policy.mode != "refused" else None
        return {
            "author_id": ctx.author_id,
            "channel_id": ctx.channel_id,
            "is_dm": ctx.is_dm,
            "admission_result": "refused" if policy.mode == "refused" else "admitted",
            "policy_mode": policy.mode,
            "response_mode": "refused",
            "model_alias": "none",
            "session_namespace": self._session_label(session_namespace),
            "tool_blocked": None,
        }

    @staticmethod
    def _emit_message_log(log_record: dict[str, str | int | bool | None]) -> None:
        logger.info("discord_message %s", log_record)

    @staticmethod
    def _response_seed(ctx: RequestContext, mode: str, message_text: str = "", reason: str = "") -> str:
        return f"{mode}|{ctx.author_id}|{ctx.channel_id}|{int(ctx.is_dm)}|{reason}|{message_text.strip()}"

    async def handle_message(self, message):
        ctx = RequestContext(
            author_id=message.author.id,
            channel_id=getattr(message.channel, "id", None),
            is_dm=getattr(message.guild, "id", None) is None,
        )

        policy = self.router.route(ctx)
        log_record = self._build_log_record(ctx, policy)

        if policy.mode == "refused":
            response = self.public_responder.refusal_response(
                seed=self._response_seed(ctx, "refused", reason=policy.denial_message or ""),
            )
            self._emit_message_log(log_record)
            return response

        if policy.mode == "untrusted":
            decision = self.public_rate_limiter.evaluate(ctx.author_id, message.content)
            log_record["response_mode"] = "public_deterministic"
            if not decision.allowed:
                response = self.public_responder.rate_limited_response(
                    decision.reason or "cooldown",
                    seed=self._response_seed(
                        ctx,
                        "rate_limit",
                        message_text=message.content,
                        reason=decision.reason or "cooldown",
                    ),
                )
                self._emit_message_log(log_record)
                return response

            response = self.public_responder.respond(
                message.content,
                seed=self._response_seed(ctx, "public", message_text=message.content),
            )
            self._emit_message_log(log_record)
            return response

        session_id = SessionManager.get_session_id(policy)
        log_record["response_mode"] = "trusted_model"
        log_record["model_alias"] = policy.model_alias or "none"
        log_record["session_namespace"] = self._session_label(session_id)

        tool_state = {"blocked": None}

        def tool_checker(tool_name: str) -> bool:
            try:
                ToolFirewall.enforce(policy, tool_name)
            except PermissionError:
                tool_state["blocked"] = tool_name
                raise
            return True

        try:
            return await self.openclaw_client.generate_response(
                user_text=message.content,
                model_alias=policy.model_alias,
                session_id=session_id,
                max_tokens=policy.max_tokens,
                memory_enabled=policy.memory_enabled,
                max_tool_calls=policy.max_tool_calls,
                tool_checker=tool_checker,
            )
        finally:
            log_record["tool_blocked"] = tool_state["blocked"]
            self._emit_message_log(log_record)
