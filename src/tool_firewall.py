from policies import ExecutionPolicy

class ToolFirewall:
    @staticmethod
    def can_use_tool(policy: ExecutionPolicy, tool_name: str) -> bool:
        return tool_name in policy.allowed_tools

    @staticmethod
    def enforce(policy: ExecutionPolicy, tool_name: str) -> None:
        if not ToolFirewall.can_use_tool(policy, tool_name):
            raise PermissionError(
                f"Tool '{tool_name}' is not allowed for mode '{policy.mode}'."
            )
