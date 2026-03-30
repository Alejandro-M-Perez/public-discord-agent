from dataclasses import dataclass
import time


@dataclass
class _PublicUserState:
    last_request_at: float
    last_message: str
    last_message_at: float


@dataclass(frozen=True)
class PublicRateLimitDecision:
    allowed: bool
    reason: str | None = None


class PublicRateLimiter:
    def __init__(
        self,
        *,
        cooldown_seconds: float = 2.0,
        suppress_duplicates: bool = True,
        duplicate_window_seconds: float = 10.0,
        clock=None,
    ):
        self.cooldown_seconds = cooldown_seconds
        self.suppress_duplicates = suppress_duplicates
        self.duplicate_window_seconds = duplicate_window_seconds
        self.clock = clock or time.monotonic
        self.user_state: dict[int, _PublicUserState] = {}

    def evaluate(self, user_id: int, message_text: str) -> PublicRateLimitDecision:
        now = self.clock()
        normalized = message_text.strip()
        state = self.user_state.get(user_id)

        if (
            self.suppress_duplicates
            and state is not None
            and normalized
            and normalized == state.last_message
            and now - state.last_message_at < self.duplicate_window_seconds
        ):
            return PublicRateLimitDecision(allowed=False, reason="duplicate")

        if state is not None and now - state.last_request_at < self.cooldown_seconds:
            return PublicRateLimitDecision(allowed=False, reason="cooldown")

        self.user_state[user_id] = _PublicUserState(
            last_request_at=now,
            last_message=normalized,
            last_message_at=now,
        )
        return PublicRateLimitDecision(allowed=True)
