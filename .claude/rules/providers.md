---
paths:
  - "src/orionfold/providers/**"
---
- API keys are never logged, never written to receipts, never printed in UI.
- Every provider returns a `ProviderResult`, including on error (no raised exceptions across the boundary).
- Cloud calls are opt-in; default to mock/local providers in tests.
- Provider tests must skip gracefully when credentials are absent.
- The cloud/local boundary must be representable so the UI and receipt can label it.
