# Claw Capone Architecture Handoff

This repo contains the phase-1 architecture handoff for a Discord + OpenClaw agent with trust-based routing.

## Implementation Rule (Critical)

Access control must be enforced in code before:
- model invocation
- tool execution

Prompts are NOT the security boundary.

If anything is ambiguous, fail closed to the untrusted path.

## Objective

Implement a Discord/OpenClaw routing layer with two trust tiers:

- trusted: only the owner
- untrusted: everyone else

### Trusted path
- uses hosted GPT model
- can access approved tools
- has persistent owner session state
- supports longer context and multi-step execution
- should be used only in the owner DM or in an allowlisted admin channel

### Untrusted path
- uses a local LM Studio model
- has no privileged tools
- has no access to owner memory or shared context
- should be short-response, low-capability, and isolated per user
- must never fall back to the hosted model

### Refused path
- blocks all model invocation outside the phase-1 channel policy
- blocks all non-owner DMs
- blocks owner messages in non-allowlisted public channels
- blocks session allocation and tool execution

## Environment

- OS: WSL2 Ubuntu
- Discord bot already exists
- OpenClaw already installed
- OpenAI API key available as `OPENAI_API_KEY`
- LM Studio runs on the host machine and exposes an OpenAI-compatible endpoint
- Expected local endpoint: `http://127.0.0.1:1234/v1`
- If WSL cannot reach `127.0.0.1:1234`, use the Windows host IP instead

## OpenClaw notes

Useful commands during setup:

```bash
openclaw onboard
openclaw gateway status
openclaw dashboard
```

## WSL Runbook

Phase-1 channel policy:

- only the owner may DM the bot
- server traffic is allowed only in `ADMIN_CHANNEL_IDS`
- all other channels are denied before model invocation

Recommended environment in WSL:

```bash
export OWNER_ID=123456789012345678
export ADMIN_CHANNEL_IDS=111111111111111111,222222222222222222
export OPENAI_API_KEY=your_openai_key
```

LM Studio endpoint from WSL:

- default local endpoint: `http://127.0.0.1:1234/v1`
- if WSL cannot reach that loopback address, use the Windows host IP in your OpenClaw config instead

Run tests from WSL:

```bash
python3 -m unittest discover -s tests -v
```
