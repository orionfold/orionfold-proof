---
name: security-secrets-review
description: Use before releases and after provider changes. Checks for secrets, verifies provider key handling, reviews network access, and inspects logs, receipts, and screenshots for sensitive data.
---

# Security & secrets review

Privacy is a product promise here. The user must be able to trust what left the machine.

## Checks

1. **Secret scan** — grep code, logs, receipts, sample artifacts, and screenshots for
   API keys, tokens, and credentials. Nothing sensitive may be committed.
2. **Provider key handling** — keys are read from env/config, never logged, never
   printed in UI, never written to any receipt format. Keys are not shown after entry.
3. **Network access** — cloud calls are opt-in; default paths use mock/local providers.
   No unexpected outbound requests; no telemetry without explicit operator approval.
4. **Error paths** — provider errors are actionable and privacy-safe (e.g. report a 401
   without echoing the key). No stack traces leak secrets.
5. **Artifacts** — exported receipts and screenshots in `samples/` contain no secrets.
6. **`.env` hygiene** — `.env` is gitignored and never read/printed.

## Output

Report each finding with a file/line reference and a concrete fix. For deep passes,
delegate to the `security-reviewer` subagent so reads stay out of the main context.
