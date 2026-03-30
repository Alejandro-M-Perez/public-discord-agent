from dataclasses import dataclass

@dataclass(frozen=True)
class ExecutionPolicy:
    mode: str
    model_alias: str | None
    allowed_tools: set[str]
    memory_enabled: bool
    max_tokens: int
    max_tool_calls: int
    session_namespace: str | None
    model_invocation_allowed: bool
    denial_message: str | None = None

def build_trusted_policy(owner_id: int, trusted_model: str, trusted_tools: set[str], max_tokens: int) -> ExecutionPolicy:
    return ExecutionPolicy(
        mode="trusted",
        model_alias=trusted_model,
        allowed_tools=trusted_tools,
        memory_enabled=True,
        max_tokens=max_tokens,
        max_tool_calls=8,
        session_namespace=f"owner:{owner_id}",
        model_invocation_allowed=True,
    )

def build_untrusted_policy(user_id: int, untrusted_model: str, max_tokens: int) -> ExecutionPolicy:
    return ExecutionPolicy(
        mode="untrusted",
        model_alias=untrusted_model,
        allowed_tools=set(),
        memory_enabled=False,
        max_tokens=max_tokens,
        max_tool_calls=0,
        session_namespace=f"public:{user_id}",
        model_invocation_allowed=True,
    )

def build_refused_policy(message: str) -> ExecutionPolicy:
    return ExecutionPolicy(
        mode="refused",
        model_alias=None,
        allowed_tools=set(),
        memory_enabled=False,
        max_tokens=0,
        max_tool_calls=0,
        session_namespace=None,
        model_invocation_allowed=False,
        denial_message=message,
    )
