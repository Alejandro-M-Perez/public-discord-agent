from policies import ExecutionPolicy

class SessionManager:
    @staticmethod
    def get_session_id(policy: ExecutionPolicy) -> str:
        return policy.session_namespace
