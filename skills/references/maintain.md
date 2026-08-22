# Maintain

## Purpose

Maintain and improve the Personal LLM Wiki automatically.

## Workflow

1. Scan the entire workspace.
2. Detect missing or invalid wiki pages.
3. Detect broken links.
4. Detect duplicate knowledge.
5. Detect outdated information.
6. Detect empty pages.
7. Detect orphan pages.
8. Detect temporary or unused files.
9. Remove confirmed redundant or invalid data.
10. Merge duplicate knowledge when appropriate.
11. Repair inconsistencies when possible.
12. Update affected wiki pages.
13. Rebuild `index.md` if needed.
14. Append `log.md`.
15. Preserve all existing valid knowledge unless explicitly removed.

## Cleanup Rules

- Remove empty pages.
- Remove temporary files.
- Remove invalid metadata.
- Remove broken or obsolete references.
- Remove confirmed duplicate data.
- Merge duplicate knowledge instead of deleting when information is still valuable.
- Never delete valid knowledge.

## Continuous Storage

Any validated new knowledge produced during maintenance MUST be written into the wiki immediately.

Knowledge must persist across future sessions.

## Output

If successful, return exactly:

```
Bảo trì hệ thống hoàn tất!
```

If failed, return only the errors.