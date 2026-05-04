<!--
  schema-manager output template.
  Append (or replace, when hash mismatch) into:
    docs/CHECKPOINT.md → ## Big-File Summaries section.

  Do NOT include this comment block in the final output — it's a
  guide for the agent emitting the block.
-->

### `{migrations_dir}`

```yaml
path:         {migrations_dir}
size_bytes:   {total_bytes}
hash:         {12-char sha256 prefix}
recorded_at:  {YYYY-MM-DDTHH:mm:ssZ}
recorded_by:  schema-manager (orquestrum skill)
```

**Summary:**

| Table | Latest migration | Columns | Notable constraints / indexes |
|---|---|---|---|
| `{table_1}` | `{filename}` | {col_1}, {col_2}, {col_3}, … | UNIQUE({...}), idx_{...} |
| `{table_2}` | `{filename}` | {col_1}, {col_2}, … | RLS on {column}, FK→{ref} |
| ... | ... | ... | ... |

**Conventions detected:** {framework}, {tenant pattern?}, {soft-delete?}, {RLS scope?}.

**Stale flags:** {none | "table X dropped in {migration} but still referenced in views"}.

<!--
  Truncate column lists at 6 + ellipsis when longer.
  Add "**+N more tables**" footer if total tables > 30.
  Keep the entire block under ~50 lines.
-->
