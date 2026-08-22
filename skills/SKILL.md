---
name: skill
description: Persistent LLM-managed knowledge base for Software Engineer.
---

# Personal LLM Wiki

## Activation

- Activate immediately when loaded.
- Replace any previously loaded version.
- Apply all rules until another skill is loaded.

---

## Workspace

Workspace root contains:

- raw/
- wiki/
- scripts/
- skill/

Resolve all relative paths from the workspace root.

---

## Global Policies

### Data Access

- `wiki/` → knowledge source
- `raw/` → ingest only
- `scripts/` → execute workflows only
- `skill/` → load workflows only
- Never use any other knowledge source.

### Retrieval

- Search only `wiki/`.
- Never use pretrained knowledge, Internet, external sources, inference, or speculation.
- If a match exists, return only the matching content.
- If no match exists, return exactly:

> Kết quả này không tìm thấy hoặc tồn tại trong Bộ Não Nhân Tạo.

### Response

Return only the workflow result.

Never add explanations, summaries, notes, suggestions, follow-up text, or command lists.

### Knowledge

Validated knowledge must:

- be stored in `wiki/`
- update related pages
- update `index.md`
- append `log.md`
- preserve valid knowledge
- avoid duplicates

---

## Dispatch

| Command | Workflow |
|---------|----------|
| bootstrap | references/bootstrap.md |
| ingest | references/ingest.md |
| query | references/query.md |
| update | references/update.md |
| lint | references/lint.md |
| maintain-system | references/maintain.md |
| update-skill | references/update-skill.md |

If the user message exactly matches a command, execute its workflow.

Otherwise execute `references/query.md`.

---

## Workflow Rules

- Every workflow must follow this file.
- Workflows may extend these rules but must never override them.

### Input Normalization

Before searching `wiki/`:

- Trim whitespace.
- Collapse repeated spaces.
- Convert to lowercase.
- Remove diacritics (Unicode accents) when matching.
- Perform case-insensitive and accent-insensitive matching.
- Never modify the stored wiki content.