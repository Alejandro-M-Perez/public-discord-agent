from router import TrustRouter, RequestContext
from session_manager import SessionManager
from tool_firewall import ToolFirewall

class DiscordHandler:
    def __init__(self, router, openclaw_client):
        self.router = router
        self.openclaw_client = openclaw_client

    async def handle_message(self, message):
        ctx = RequestContext(
            author_id=message.author.id,
            channel_id=getattr(message.channel, "id", None),
            is_dm=getattr(message.guild, "id", None) is None,
        )

        policy = self.router.route(ctx)
        session_id = SessionManager.get_session_id(policy)

        response = await self.openclaw_client.generate_response(
            user_text=message.content,
            model_alias=policy.model_alias,
            session_id=session_id,
            max_tokens=policy.max_tokens,
            memory_enabled=policy.memory_enabled,
            max_tool_calls=policy.max_tool_calls,
            tool_checker=lambda tool_name: ToolFirewall.can_use_tool(policy, tool_name),
        )

        return response
