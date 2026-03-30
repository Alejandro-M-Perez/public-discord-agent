Read the files in:
- docs/architecture.md
- docs/security-policy.md
- docs/test-plan.md
- config/openclaw.example.json

Implement phase-1 trust routing for my Discord + OpenClaw bot.

Requirements:
1. Add a trust gate that classifies requests as trusted or untrusted using Discord `author.id`.
2. Trusted means `author.id == OWNER_ID`.
3. Route trusted requests to hosted model alias `openai/gpt-trusted`.
4. Route untrusted requests to local model alias `lmstudio/local-public`.
5. Enforce tool permissions in code:
   - trusted users may use only an explicit allowlist of approved tools
   - untrusted users may not use privileged tools
6. Add session isolation:
   - trusted namespace: `owner:<OWNER_ID>`
   - untrusted namespace: `public:<USER_ID>`
7. If anything is ambiguous or invalid, fail closed to the untrusted path.
8. Untrusted requests must never invoke the hosted model, even if the local model is unavailable.
9. Add tests for:
   - trust routing
   - model routing
   - tool firewall
   - session isolation
   - fail-closed behavior
10. Update README with WSL run and test instructions.

Constraints:
- Do not add personality or character behavior yet.
- Do not use prompt text as the security boundary.
- Access control must be enforced before model invocation and before tool execution.
- Keep the implementation easy to extend for future collaborator tiers.
