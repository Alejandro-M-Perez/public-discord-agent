# Goal

Build a Discord + OpenClaw routing layer with two trust tiers.

## Trusted tier
Condition:
- Discord author.id == OWNER_ID

Behavior:
- Route to hosted GPT model
- Enable privileged tool set
- Enable persistent owner session
- Allow longer context and multi-step execution
- Prefer DM or allowlisted admin channel

## Untrusted tier
Condition:
- Any Discord user whose author.id != OWNER_ID

Behavior:
- Route to local LM Studio model
- No privileged tools
- No shared memory with owner
- Short responses, low token cap
- Isolated per-user or disposable session
- Never escalate to hosted model

## Security requirements
- Trust decision must happen before model invocation
- Tool permissions enforced in code, not prompt only
- Trusted and untrusted sessions must be isolated
- Public users must not be able to access prompts, secrets, or owner-only commands
- Public users must never trigger hosted-model execution

## OpenClaw integration
- Hosted provider: OpenAI
- Local provider: LM Studio at http://127.0.0.1:1234/v1
- OpenClaw config should support both providers
- Use model aliases where practical
