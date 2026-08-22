# Update Skill

## Purpose

Reload the active `SKILL.md` and synchronize the running skill with its latest definition.

This operation updates the active behavior of the agent without modifying the user's knowledge base (`wiki/`) or raw sources (`raw/`).

---

## Workflow

### 1. Locate the skill

Locate the active `SKILL.md` in the current workspace.

If no `SKILL.md` exists:

```
Failed.

Reason:
No SKILL.md was found in the current workspace.
```

Stop.

---

### 2. Reload

Read the entire `SKILL.md`.

Reload:

- metadata
- operation dispatch
- built-in commands
- retrieval policy
- merge policy
- knowledge evaluation policy
- invariants
- all referenced workflows

---

### 3. Validate

Validate the skill definition.

Check for:

- duplicate commands
- duplicate operations
- duplicate policies
- broken reference paths
- missing reference files
- invalid command mappings
- invalid markdown tables
- invalid workflow definitions
- conflicting rules

---

### 4. Verify references

Verify every referenced file exists.

Example:

```
references/bootstrap.md
references/ingest.md
references/query.md
references/lint.md
references/update.md
references/update-skill.md
references/page-templates.md
```

If any reference is missing, report it.

---

### 5. Validate dispatch table

Ensure every operation can be dispatched.

Verify:

- bootstrap
- ingest
- query
- lint
- update
- update-skill

Every operation must map to exactly one workflow.

---

### 6. Reload command aliases

Reload every built-in command.

Examples:

- ingest
- update
- update-skill
- query
- repair
- stats
- rebuild
- check-ingest
- check-status

Update the dispatcher immediately.

---

### 7. Apply new policies

Replace the current policies with the latest version found in `SKILL.md`.

Policies include (but are not limited to):

- Retrieval Policy
- Semantic Knowledge Merge Policy
- Knowledge Quality Evaluation
- Incremental Ingest
- Key Invariants

Never merge old and new policy text.

Always use the newest definition.

---

### 8. Consistency check

Ensure:

- no command points to a missing workflow
- every workflow is reachable
- every operation has exactly one implementation
- no circular reference exists

---

### 9. Activate

Replace the currently loaded skill with the validated version.

From this point onward, every request MUST follow the updated skill.

---

### 10. Report

If successful, return exactly:

```
Update kỹ năng thành công!
```

If validation fails, return only the validation errors.

Do not append explanations, summaries, or suggestions.