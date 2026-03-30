from policies import ExecutionPolicy

class SessionManager:
    @staticmethod
    def get_session_id(policy: ExecutionPolicy) -> str:
        if policy.session_namespace is None:
            raise PermissionError(
                f"Session access is not allowed for mode '{policy.mode}'."
            )
        return policy.session_namespace
