class PublicResponder:
    HELP_RESPONSE = (
        "Limited access mode. Available commands: !help, !status, !about."
    )
    STATUS_RESPONSE = (
        "Status: public access is in limited deterministic mode."
    )
    ABOUT_RESPONSE = (
        "Claw Capone is running owner-trusted hosted routing with limited public access."
    )
    DEFAULT_RESPONSE = (
        "Limited access: public users can use only !help, !status, and !about right now."
    )
    DENIAL_RESPONSE = (
        "Access denied. This bot is not available in this channel or DM for your account."
    )

    COMMAND_RESPONSES = {
        "!help": HELP_RESPONSE,
        "!status": STATUS_RESPONSE,
        "!about": ABOUT_RESPONSE,
    }

    @classmethod
    def respond(cls, message_text: str) -> str:
        command = message_text.strip().split(maxsplit=1)[0].lower() if message_text.strip() else ""
        return cls.COMMAND_RESPONSES.get(command, cls.DEFAULT_RESPONSE)
