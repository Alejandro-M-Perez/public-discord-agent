# Persona Customization

Local persona overrides live in `persona/active/`.

Expected files:

- `profile.json`
- `public_responses.json`
- `refused_responses.json`
- `command_text.json`

These files are ignored by git. Copy the tracked examples from `persona_templates/` and edit them locally.

Persona changes affect only deterministic response text. They do not change trust routing, model access, tool permissions, or any other security behavior.
