# Docs Update Log

Append a short entry whenever you fetch current guidance for a library or framework.
Keep notes repo-relevant; do not paste large docs.

| Date checked | Library | Version | URL | Repo-relevant notes |
| --- | --- | --- | --- | --- |
| 2026-06-19 | (seed) | — | — | Reference index created; no external docs fetched yet. |
| 2026-06-19 | Ollama API | v1 (docs.ollama.com) | https://docs.ollama.com/api/chat | Gate 6. `POST /api/chat` with `stream:false`. Req `{model, messages:[{role,content}], stream:false}`. Resp `message.content`, token counts `prompt_eval_count` (prompt) + `eval_count` (output), `done_reason`. Default host `http://localhost:11434`. |
| 2026-06-19 | Gemini API | v1beta | https://ai.google.dev/gemini-api/docs/api-overview | Gate 6. `POST /v1beta/models/{model}:generateContent`, auth via `x-goog-api-key` header (avoid `?key=` URL param — redaction). Req `{contents:[{parts:[{text}]}], generationConfig:{maxOutputTokens}}`. Resp `candidates[0].content.parts[0].text`, tokens `usageMetadata.{promptTokenCount,candidatesTokenCount}`, `finishReason`. Current flash: `gemini-2.5-flash` (default, broad availability) / newer `gemini-3.5-flash`. |
| 2026-06-19 | OpenAI Chat Completions | v1 | https://platform.openai.com/docs/api-reference/chat | Gate 6 (shared by openai/openrouter/lmstudio). `POST {base}/chat/completions`, `Authorization: Bearer`. Resp `choices[0].message.content`, tokens `usage.{prompt_tokens,completion_tokens}`. Bases: OpenAI `https://api.openai.com/v1`, OpenRouter `https://openrouter.ai/api/v1`, LM Studio `http://localhost:1234/v1` (keyless). |
| 2026-06-19 | Anthropic Messages API | 2023-06-01 | claude-api skill (bundled) | Gate 6. `POST https://api.anthropic.com/v1/messages`, headers `x-api-key` + `anthropic-version: 2023-06-01`. Req `{model, max_tokens, messages:[{role:"user",content}]}`. Resp `content[].text`, tokens `usage.{input_tokens,output_tokens}`. Default `claude-haiku-4-5` (cheap test-harness default; current model IDs per skill). |
| 2026-06-20 | lucide-react | 1.21.0 | https://lucide.dev/guide/packages/lucide-react | Icon library (operator-approved prod dep). shadcn/ui default; calm uniform line icons matching the instrument-panel aesthetic. Tree-shakeable (named imports only), MIT. Used for functional iconography: rail nav, provider boundary tags (Mock/Local/Cloud), failure status (error/fail), Recommended verdict, download/open affordances. Import icons by name; render with `aria-hidden` (decorative — labels stay text). |
