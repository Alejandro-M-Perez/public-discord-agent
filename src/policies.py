from dataclasses import dataclass

@dataclass(frozen=True)
class ExecutionPolicy:
    mode: str
    model_alias: str
    allowed_tools: set[str]
    memory_enabled: bool
    max_tokens: int
    max_tool_calls: int
    session_namespace: str

def build_trusted_policy(owner_id: int, trusted_model: str, trusted_tools: set[str], max_tokens: int) -> ExecutionPolicy:
    return ExecutionPolicy(
        mode="trusted",
        model_alias=trusted_model,
        allowed_tools=trusted_tools,
        memory_enabled=True,
        max_tokens=max_tokens,
        max_tool_calls=8,
        session_namespace=f"owner:{owner_id}",
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
    )
