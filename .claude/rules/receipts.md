---
paths:
  - "src/orionfold/receipts/**"
  - "src/orionfold/scoring/**"
---
- Receipts must never contain secrets, raw API keys, or full provider config.
- Every receipt includes a config hash and a timestamp.
- Markdown/HTML/JSON exports must stay schema-stable; bump a `version` field on any change.
- The receipt is the central product artifact — protect it from feature creep.
