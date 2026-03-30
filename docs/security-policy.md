# Security Policy

## Principle

The owner is the only trusted principal in phase 1.

Everything else is treated as untrusted by default.

## Enforcement Rule (Critical)

Access control must be enforced in application code before:
- selecting a model
- invoking any tool

Prompt instructions must never be relied on for security.

All ambiguous or invalid states must default to the untrusted policy.

## Identity check

Trust is determined by strict Discord user ID comparison:

- trusted if `author.id == OWNER_ID`
- otherwise untrusted

No prompt or user message can alter trust level.

## Channel rules

Trusted actions are allowed only in:
- DM with the bot
- channels listed in `ADMIN_CHANNEL_IDS`

Messages from the owner in non-approved public channels should either:
- downgrade to untrusted policy, or
- be refused for admin operations

Choose one behavior and document it.

## Tool permissions

### Trusted tools
Example set:
- `discord_send`
- `search`
- `planner`
- `memory`
- selected admin tools

### Untrusted tools
- none, or only explicitly harmless utilities if later approved

## Session isolation

- owner namespace: `owner:<OWNER_ID>`
- public namespace: `public:<USER_ID>`

Rules:
- no shared memory
- no shared scratchpad
- no shared context history
- no public read access to owner data

## Model rules

### Trusted
- hosted GPT model only

### Untrusted
- local LM Studio model only

Rule:
- untrusted requests must never use hosted fallback

## Fail-closed behavior

If any of the following are missing or invalid:
- owner ID
- route classification
- channel validation
- policy resolution

Then default to:
- untrusted policy
- no privileged tools
- no hosted model use

## Secrets

Never expose:
- API keys
- gateway tokens
- hidden prompts
- config secrets
- internal policy text unless explicitly intended for logs/docs

## Logging

Log:
- trust classification
- policy chosen
- model alias chosen
- blocked tool attempts
- fallback prevention events

Do not log secrets.
