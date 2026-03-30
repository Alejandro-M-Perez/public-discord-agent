from persona_loader import PersonaBundle, PersonaLoader


class PublicResponder:
    def __init__(self, persona_loader: PersonaLoader | None = None):
        self.persona_loader = persona_loader or PersonaLoader()

    def persona(self) -> PersonaBundle:
        return self.persona_loader.load()

    def refusal_response(self, seed: str | None = None) -> str:
        persona = self.persona()
        return self.persona_loader.choose_line(
            persona.refused_responses["denial_response"],
            seed=seed,
        )

    def rate_limited_response(self, reason: str, seed: str | None = None) -> str:
        persona = self.persona()
        if reason == "duplicate":
            return self.persona_loader.choose_line(
                persona.public_responses["duplicate_suppressed_response"],
                seed=seed,
            )
        return self.persona_loader.choose_line(
            persona.public_responses["rate_limited_response"],
            seed=seed,
        )

    def respond(self, message_text: str, seed: str | None = None) -> str:
        persona = self.persona()
        command = message_text.strip()
        if command in persona.command_text:
            return persona.command_text[command]
        return self.persona_loader.choose_line(
            persona.public_responses["default_response"],
            seed=seed,
        )
