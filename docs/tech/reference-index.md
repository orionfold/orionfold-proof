# Technical Reference Index

Last updated: 2026-06-19

Consult this before adding dependencies or using framework-specific APIs. If a reference
is stale or missing, fetch current guidance (Context7 MCP or web), then log it in
`docs-update-log.md`. Do not copy large docs into the repo.

## Claude Code

- Best practices — https://code.claude.com/docs/en/best-practices
  - Use for: CLAUDE.md, plan mode, verification loops, subagents, /clear, scaling.
- Steering methods (CLAUDE.md, rules, skills, subagents, hooks, output styles) — https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more
  - Use for: deciding where each instruction belongs and its compaction behavior.
- Overview & docs map — https://code.claude.com/docs/en/overview
- Skills — https://code.claude.com/docs/en/skills
  - Use for: SKILL.md format, invocation, disable-model-invocation.
- Subagents — https://code.claude.com/docs/en/sub-agents
- Hooks — https://code.claude.com/docs/en/hooks-guide
- Rules / memory — https://code.claude.com/docs/en/memory
- Permissions & sandboxing — https://code.claude.com/docs/en/permissions
- Claude in Chrome — https://claude.com/claude-for-chrome

## Python and backend

- uv — https://docs.astral.sh/uv/
- FastAPI — https://fastapi.tiangolo.com/
- Pydantic — https://docs.pydantic.dev/latest/
- Typer — https://typer.tiangolo.com/
- SQLite — https://www.sqlite.org/docs.html
- Python sqlite3 — https://docs.python.org/3/library/sqlite3.html
- Ruff — https://docs.astral.sh/ruff/
- pytest — https://docs.pytest.org/

## Provider HTTP APIs (Gate 6)

- Ollama REST — https://docs.ollama.com/api/chat
  - Use for: local `/api/chat` (`stream:false`); `message.content`, `prompt_eval_count`, `eval_count`.
- Gemini REST — https://ai.google.dev/gemini-api/docs/api-overview
  - Use for: `generateContent`, `x-goog-api-key` header, `candidates[].content.parts[].text`, `usageMetadata`.
- OpenAI Chat Completions — https://platform.openai.com/docs/api-reference/chat
  - Use for: OpenAI-compatible profile (OpenAI / OpenRouter / LM Studio); `choices[].message.content`, `usage`.
- Anthropic Messages — `claude-api` skill (bundled); https://platform.claude.com/docs/en/api
  - Use for: native Anthropic profile; `x-api-key` + `anthropic-version`, `content[].text`, `usage.{input,output}_tokens`; current model IDs.

## Frontend

- React — https://react.dev/learn
- Vite — https://vite.dev/guide/
- Tailwind CSS (Vite) — https://tailwindcss.com/docs/installation/using-vite
- shadcn/ui — https://ui.shadcn.com/docs
- Radix UI — https://www.radix-ui.com/primitives/docs/overview/introduction
- TanStack Query — https://tanstack.com/query/latest/docs/framework/react/overview
- React Hook Form — https://react-hook-form.com/get-started
- Zod — https://zod.dev/

## Testing

- Playwright — https://playwright.dev/docs/intro
- Vitest — https://vitest.dev/guide/

## UX, accessibility, product polish

- WCAG 2.2 quick reference — https://www.w3.org/WAI/WCAG22/quickref/
- Nielsen Norman usability heuristics — https://www.nngroup.com/articles/ten-usability-heuristics/
- Apple Human Interface Guidelines — https://developer.apple.com/design/human-interface-guidelines
- GOV.UK Design System — https://design-system.service.gov.uk/
