from dataclasses import dataclass
from policies import (
    ExecutionPolicy,
    build_refused_policy,
    build_trusted_policy,
    build_untrusted_policy,
)
from config import AppConfig

@dataclass(frozen=True)
class RequestContext:
    author_id: int | None
    channel_id: int | None
    is_dm: bool

class TrustRouter:
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config

    @staticmethod
    def _has_model_alias(model_alias: str | None) -> bool:
        return isinstance(model_alias, str) and bool(model_alias.strip())

    def is_trusted_user(self, ctx: RequestContext) -> bool:
        if self.app_config.owner_id is None or ctx.author_id is None:
            return False
        return ctx.author_id == self.app_config.owner_id

    def is_allowed_channel(self, ctx: RequestContext) -> bool:
        if ctx.is_dm:
            return self.is_trusted_user(ctx)
        return ctx.channel_id in self.app_config.admin_channel_ids

    def _build_untrusted_policy(self, user_id: int) -> ExecutionPolicy:
        return build_untrusted_policy(
            user_id=user_id,
            untrusted_model=self.app_config.untrusted_model,
            max_tokens=self.app_config.untrusted_max_tokens,
        )

    def route(self, ctx: RequestContext) -> ExecutionPolicy:
        if ctx.author_id is None:
            return build_refused_policy(
                "Request denied because the author identity could not be verified."
            )

        if not self.is_allowed_channel(ctx):
            return build_refused_policy(
                "Request denied because this channel is not allowed in phase 1."
            )

        if self.is_trusted_user(ctx):
            if not self._has_model_alias(self.app_config.trusted_model):
                return self._build_untrusted_policy(user_id=ctx.author_id)
            return build_trusted_policy(
                owner_id=self.app_config.owner_id,
                trusted_model=self.app_config.trusted_model,
                trusted_tools=self.app_config.trusted_tools,
                max_tokens=self.app_config.trusted_max_tokens,
            )

        if not self._has_model_alias(self.app_config.untrusted_model):
            return build_refused_policy(
                "Request denied because the untrusted model is not configured."
            )

        return self._build_untrusted_policy(user_id=ctx.author_id)
