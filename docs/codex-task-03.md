Refactor the trust-policy layer so it can support future trust tiers.

Requirements:
- preserve phase-1 behavior exactly
- introduce clean extension points for future collaborator mode
- keep owner-only and public tiers working as-is
- document where future per-user allowlists or collaborator roles will be added
