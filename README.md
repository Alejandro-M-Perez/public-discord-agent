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
- should be used only in DM or in an allowlisted admin channel

### Untrusted path
- uses a local LM Studio model
- has no privileged tools
- has no access to owner memory or shared context
- should be short-response, low-capability, and isolated per user
- must never fall back to the hosted model

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
