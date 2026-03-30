from policies import ExecutionPolicy
import logging


logger = logging.getLogger(__name__)

class ToolFirewall:
    @staticmethod
    def can_use_tool(policy: ExecutionPolicy, tool_name: str) -> bool:
        return tool_name in policy.allowed_tools

    @staticmethod
    def enforce(policy: ExecutionPolicy, tool_name: str) -> None:
        if not ToolFirewall.can_use_tool(policy, tool_name):
            logger.info(
                "Blocked tool attempt mode=%s tool=%s",
                policy.mode,
                tool_name,
            )
            raise PermissionError(
                f"Tool '{tool_name}' is not allowed for mode '{policy.mode}'."
            )
