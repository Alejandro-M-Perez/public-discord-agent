# Claw Capone

Claw Capone is a Discord bot framework that keeps trust and security enforcement in application code, uses OpenClaw only as a trusted backend, and serves public users with deterministic responses instead of model output.

The current system is designed around three modes:

- `trusted`: owner-only, hosted model path through OpenClaw
- `untrusted`: admitted public users, deterministic command responses only
- `refused`: denied before any model or tool execution

## Features

- Strict trust routing based on Discord `author.id`
- Fail-closed admission policy enforced before model selection or tool execution
- Trusted path isolated to `owner:<OWNER_ID>` sessions
- Public path isolated to `public:<USER_ID>` sessions
- Deterministic public behavior with exact commands only: `!help`, `!status`, `!about`
- Public cooldown and duplicate-message suppression
- Centralized persona files for all non-security text
- Structured request logging without logging secrets or prompts
- OpenClaw used as backend-only HTTP transport for trusted requests
- Test coverage for routing, isolation, persona loading, deterministic public behavior, and trusted transport

## Current Behavior

### Trusted

Trusted requests are allowed only when both conditions are true:

- `author.id == OWNER_ID`
- the message is in an allowed location

Allowed locations:

- DM with the bot from the owner
- channels listed in `ADMIN_CHANNEL_IDS`

Trusted requests:

- use backend alias `openai/gpt-trusted`
- go through the OpenClaw HTTP responses endpoint
- can use only the trusted tool allowlist
- keep the owner session namespace `owner:<OWNER_ID>`

### Untrusted

Untrusted requests are non-owner messages in allowed public channels.

Untrusted requests:

- do not invoke any model
- do not invoke trusted tools
- use deterministic public responses only
- keep the per-user session namespace `public:<USER_ID>`
- are subject to public rate limiting and duplicate suppression

### Refused

Everything else is refused.

Refused requests:

- do not invoke any model
- do not invoke any tool
- do not create a session
- return a deterministic refusal response from the Discord layer

## Security Model

Critical rules:

- access control is enforced in code before model invocation
- access control is enforced in code before tool execution
- prompts are not a security boundary
- ambiguous or invalid states fail closed
- untrusted users never reach the hosted model
- OpenClaw does not own Discord and does not decide trust

This separation is intentional:

- `src/main.py` owns Discord I/O
- `src/router.py` decides trust and policy
- `src/discord_handler.py` applies the policy
- OpenClaw is only the trusted backend transport

## Architecture

### Request Flow

1. `src/main.py` receives a Discord message.
2. Bot-authored messages are ignored.
3. `src/discord_handler.py` builds a request context and asks `src/router.py` for a policy.
4. If the policy is `refused`, the handler returns a refusal response immediately.
5. If the policy is `untrusted`, the handler uses the deterministic public responder and optional rate limiting.
6. If the policy is `trusted`, the handler allocates the owner session namespace, enforces the tool firewall, and calls the OpenClaw gateway.
7. `src/main.py` sends any non-empty reply back to the same Discord channel.

### Key Modules

- [src/main.py](/home/loopk/projects/ClawCapone/src/main.py): Discord entrypoint and trusted OpenClaw HTTP client
- [src/router.py](/home/loopk/projects/ClawCapone/src/router.py): trust classification and admission policy
- [src/policies.py](/home/loopk/projects/ClawCapone/src/policies.py): execution policy definitions
- [src/discord_handler.py](/home/loopk/projects/ClawCapone/src/discord_handler.py): central request execution path
- [src/tool_firewall.py](/home/loopk/projects/ClawCapone/src/tool_firewall.py): trusted tool allowlist enforcement
- [src/session_manager.py](/home/loopk/projects/ClawCapone/src/session_manager.py): session namespace enforcement
- [src/public_responder.py](/home/loopk/projects/ClawCapone/src/public_responder.py): deterministic public command/default responses
- [src/public_rate_limiter.py](/home/loopk/projects/ClawCapone/src/public_rate_limiter.py): public cooldown and duplicate suppression
- [src/persona_loader.py](/home/loopk/projects/ClawCapone/src/persona_loader.py): persona loading, validation, and safe fallback

## Getting Started

### Requirements

- Python 3.11+
- WSL2 Ubuntu or Linux shell
- a Discord bot token
- a running OpenClaw gateway
- OpenClaw configured with access to the hosted backend alias `openai/gpt-trusted`

### Install Python dependency

```bash
python3 -m pip install discord.py
```

### Create `.env`

Create a `.env` file in the repo root with:

```dotenv
DISCORD_BOT_TOKEN=your_discord_bot_token
OPENCLAW_GATEWAY_TOKEN=your_openclaw_gateway_token
OWNER_ID=123456789012345678
ADMIN_CHANNEL_IDS=111111111111111111,222222222222222222
LOG_LEVEL=INFO
```

Notes:

- `OWNER_ID` is the only trusted principal
- `ADMIN_CHANNEL_IDS` controls which server channels are admitted
- `.env` is ignored by git

### Configure OpenClaw

Use [config/openclaw.example.json](/home/loopk/projects/ClawCapone/config/openclaw.example.json) as the starting point for your active OpenClaw config.

The active OpenClaw config must reflect the current integration:

- `gateway.mode` must be `"local"`
- `gateway.auth.mode` must be `"token"`
- `gateway.http.endpoints.responses.enabled` must be `true`
- the built-in Discord provider must be disabled
- built-in Discord provider disabled is a required part of the active config

Important:

- Discord is handled only by [src/main.py](/home/loopk/projects/ClawCapone/src/main.py)
- OpenClaw is backend-only in this project
- do not enable OpenClaw’s Discord channel provider for this bot
- enable the HTTP responses endpoint in the active OpenClaw config
- do not use prompt text for routing or security

### OpenClaw HTTP contract

Trusted requests are sent as:

- `POST http://127.0.0.1:18789/v1/responses`
- `Authorization: Bearer <OPENCLAW_GATEWAY_TOKEN>`
- `Content-Type: application/json`
- request body `model: "openclaw/default"`
- header `x-openclaw-model: openai/gpt-trusted`
- header `x-openclaw-session-key: owner:<OWNER_ID>`

If the trusted backend fails, the Discord loop keeps running and returns a short fallback response.

### Run the bot

```bash
python3 src/main.py
```

## Persona Customization

All non-security response text is loaded from persona files.

Tracked examples live in `persona_templates/`:

- `profile.example.json`
- `public_responses.example.json`
- `refused_responses.example.json`
- `command_text.example.json`

Local overrides live in `persona/active/` and are ignored by git.

To customize:

1. Copy the example files into `persona/active/`.
2. Edit the text values.
3. Restart the bot.

Persona can change:

- refusal lines
- default public lines
- rate-limit lines
- duplicate-suppression lines
- exact command text for `!help`, `!status`, and `!about`

Persona cannot change:

- trust routing
- model access
- tool permissions
- session isolation
- rate-limit enforcement rules
- any other security behavior

## Public Command System

Public deterministic mode supports exact commands only:

- `!help`
- `!status`
- `!about`

Everything else returns the default limited-access response.

There is no fuzzy matching and no natural-language command interpretation on the public path.

## Observability

The handler emits one structured log per Discord message with fields including:

- `author_id`
- `channel_id`
- `is_dm`
- `admission_result`
- `policy_mode`
- `response_mode`
- `model_alias`
- `session_namespace`
- `tool_blocked`

Trusted transport logging also records:

- request URL
- OpenClaw target
- backend model override
- session key
- success or failure

Secrets, tokens, and prompts are not logged.

## Testing

Run the full test suite with:

```bash
python3 -m unittest discover -s tests -v
```

Current test coverage includes:

- trust routing and fail-closed behavior
- refused and public model isolation
- trusted hosted-path isolation
- tool firewall enforcement
- session isolation
- persona loading and fallback behavior
- deterministic phrase rotation
- public rate limiting
- trusted OpenClaw transport contract
- trusted-path HTTP error fallback behavior

## WSL Notes

- If OpenClaw or other local services are hosted on Windows, confirm WSL can reach the configured endpoints.
- The default trusted OpenClaw endpoint in this project is `http://127.0.0.1:18789/v1/responses`.
- If your OpenClaw or LM Studio setup is bound elsewhere, update the active backend config accordingly.

## Project Status

The project currently provides a secure owner-trusted Discord bot shell with:

- trusted hosted execution through OpenClaw
- deterministic public handling
- centralized persona-driven text
- structured observability
- test-backed security boundaries

It is intentionally conservative on the public path. Public users do not get model access in the current implementation.
