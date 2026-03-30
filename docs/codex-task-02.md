Harden the phase-1 implementation.

Add negative tests proving that untrusted users cannot:
- access trusted tools
- reuse owner session state
- trigger hosted model fallback
- execute owner-only commands in public channels
- alter trust tier through message content

Refactor only as needed to improve clarity and testability.
Do not change the intended behavior.
