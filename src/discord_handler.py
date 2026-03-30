from router import TrustRouter, RequestContext
from session_manager import SessionManager
from tool_firewall import ToolFirewall
from public_responder import PublicResponder
import logging


logger = logging.getLogger(__name__)

class DiscordHandler:
    def __init__(self, router, openclaw_client):
        self.router = router
        self.openclaw_client = openclaw_client

    @staticmethod
    def _session_label(session_id: str | None) -> str:
        return session_id if session_id is not None else "no_session"

    @staticmethod
    def _admission_result(policy) -> str:
        return "refused" if not policy.model_invocation_allowed else "allowed"

    @staticmethod
    def _log_structured_event(event_name: str, **fields) -> None:
        logger.info("%s %s", event_name, fields)

    @staticmethod
    def _is_trusted_model(policy) -> bool:
        return policy.mode == "trusted" and policy.model_alias == "openai/gpt-trusted"

    def _respond_refused(self, ctx: RequestContext, policy) -> str:
        self._log_structured_event(
            "model_invocation_refused",
            author_id=ctx.author_id,
            channel_id=ctx.channel_id,
            is_dm=ctx.is_dm,
            resolved_policy=policy.mode,
            reason=policy.denial_message,
        )
        return PublicResponder.DENIAL_RESPONSE

    def _respond_untrusted(self, ctx: RequestContext, policy, message_text: str) -> str:
        self._log_structured_event(
            "local_model_invocation_skipped",
            author_id=ctx.author_id,
            channel_id=ctx.channel_id,
            is_dm=ctx.is_dm,
            reason="phase_2a_deterministic_public_responder",
        )
        response = PublicResponder.respond(message_text)
        self._log_structured_event(
            "public_response_generated",
            author_id=ctx.author_id,
            channel_id=ctx.channel_id,
            is_dm=ctx.is_dm,
            response_kind=response,
        )
        return response

    async def handle_message(self, message):
        ctx = RequestContext(
            author_id=message.author.id,
            channel_id=getattr(message.channel, "id", None),
            is_dm=getattr(message.guild, "id", None) is None,
        )

        policy = self.router.route(ctx)
        trusted_user = self.router.is_trusted_user(ctx)
        requested_tier = "trusted" if trusted_user else "untrusted"
        session_id = policy.session_namespace if policy.model_invocation_allowed else None

        self._log_structured_event(
            "discord_request",
            author_id=ctx.author_id,
            channel_id=ctx.channel_id,
            is_dm=ctx.is_dm,
            admission_result=self._admission_result(policy),
            resolved_policy=policy.mode,
            selected_model_alias=policy.model_alias,
            session_namespace=self._session_label(session_id),
        )

        if not policy.model_invocation_allowed:
            if requested_tier == "untrusted":
                self._log_structured_event(
                    "local_model_invocation_blocked",
                    author_id=ctx.author_id,
                    channel_id=ctx.channel_id,
                    is_dm=ctx.is_dm,
                    reason=policy.denial_message,
                )
            return self._respond_refused(ctx, policy)

        if policy.mode == "untrusted":
            return self._respond_untrusted(ctx, policy, message.content)

        session_id = SessionManager.get_session_id(policy)

        try:
            response = await self.openclaw_client.generate_response(
                user_text=message.content,
                model_alias=policy.model_alias,
                session_id=session_id,
                max_tokens=policy.max_tokens,
                memory_enabled=policy.memory_enabled,
                max_tool_calls=policy.max_tool_calls,
                tool_checker=lambda tool_name: ToolFirewall.enforce(policy, tool_name) is None,
            )
        except Exception as exc:
            raise

        return response
