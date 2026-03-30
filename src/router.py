from dataclasses import dataclass
from policies import ExecutionPolicy, build_trusted_policy, build_untrusted_policy
from config import AppConfig

@dataclass(frozen=True)
class RequestContext:
    author_id: int | None
    channel_id: int | None
    is_dm: bool

class TrustRouter:
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config

    def is_trusted_user(self, ctx: RequestContext) -> bool:
        return ctx.author_id == self.app_config.owner_id

    def is_trusted_channel(self, ctx: RequestContext) -> bool:
        if ctx.is_dm:
            return True
        return ctx.channel_id in self.app_config.admin_channel_ids

    def route(self, ctx: RequestContext) -> ExecutionPolicy:
        if ctx.author_id is None:
            return build_untrusted_policy(
                user_id=0,
                untrusted_model=self.app_config.untrusted_model,
                max_tokens=self.app_config.untrusted_max_tokens,
            )

        if self.is_trusted_user(ctx) and self.is_trusted_channel(ctx):
            return build_trusted_policy(
                owner_id=self.app_config.owner_id,
                trusted_model=self.app_config.trusted_model,
                trusted_tools=self.app_config.trusted_tools,
                max_tokens=self.app_config.trusted_max_tokens,
            )

        return build_untrusted_policy(
            user_id=ctx.author_id,
            untrusted_model=self.app_config.untrusted_model,
            max_tokens=self.app_config.untrusted_max_tokens,
        )
