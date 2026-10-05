# PII registry on every source-to-destination job: design (draft, 5 Oct 2026)

**Status:** design only. No code yet. Written against `ingestion-platform` branch `fix/review-findings` (commit `5d4befd`).
**Decisions it implements:**
- ADR-06 mask at write (3 Oct).
- Every PII value becomes the literal `PII MASKED`; NULL and empty stay as they are.
- Rules are `keep | mask | address`.
- Presidio auto-detection with provisional masking (PII-18).
- Each client runs its own copy of the platform (4 Oct).

## 1. Today
The platform has no PII handling. A search for `pii`, `mask`, `classif`, `sensitive` and `presidio` finds only log and
credential redaction. Presidio is not a dependency. Every job writes source values to the destination unchanged.

**Raw PII also reaches the UI:**
- `GET /connections/{id}/objects/schema` returns 20 sample rows (`connections.py` → `base_sql.get_schema` / `_sample_rows`).
- `POST /connections/{id}/profile` returns min/max values and, for files, 5 sample values per column.

## 2. Where it hooks in: one place for every job
Every SQL and file job runs through `connectors/dlt_bridge/service.py::_run`. Transforms are already applied as a dlt
per-item map:
- SQL: `sql_source.build_sql_resource` → `resource.add_map(...)`
- Files: `file_source.build_file_resource` → `resource.add_map(...)`

The masking step is a **second map, added after the transform map and filter**, in both builders. It sees the
post-rename column names, and nothing reaches the parquet writer without passing through it.

```
source → [transform map: rename/cast] → [transform filter] → [PII map] → dlt normalize → parquet on target
```

**`build_pii_map(rules)`**, in a new module `connectors/dlt_bridge/pii.py`:
- **Item shapes:** handles the same shapes as `transform.apply_transform`: Arrow `Table` and `RecordBatch` (SQL path),
  pandas `DataFrame` (CSV and Parquet files), a list of dicts (JSONL), and a single dict (row-wise file items).
- **Fails closed:** an unknown item shape raises and the task fails. Today's transform passes unknown shapes through
  (`transform.py:139`); masking must not.
- **Masking:** Arrow uses `pc.if_else(pc.is_null(col), null, "PII MASKED")`; pandas and dicts use the same rule.
  Empty string `""` stays `""`, per the "empty stays empty" rule.
- **Untyped:** the map stays unannotated, the same as `build_transform_map`, because dlt coerces items based on
  annotations.
- **Column types:** masked non-string columns become strings. The SQL resource must therefore use
  `reflection_level=None`, as it already does when a transform map is present, so dlt doesn't keep the old type hint.

## 3. Rules
| Rule | Curated output | Elsewhere |
|---|---|---|
| `keep` | value unchanged | — |
| `mask` | `PII MASKED` (NULL and empty kept) | — |
| `address` | `PII MASKED` | Clear value written to the client's **CDS-only address table** (PII-17), in the same task |

**Address write.** The map collects the key columns plus the address columns for `address`-rule rows into a side
buffer. After a successful load, the task writes that buffer to the CDS table (`pii_address.customer_address`, readable
only by `svc_cds_<client>`). This is a separate SQLAlchemy write to the client's PostgreSQL, not a dlt destination. If
the address write fails, the task fails, so curated data and the CDS table never disagree.

## 4. Registry storage
New table `pii_column_rules`, migration `0005_pii_registry`. It follows the existing idempotent convention (guarded by
`has_table`, `JSONVariant`, `ix_<table>_<col>` index names).

| Column | Notes |
|---|---|
| `id`, `tenant_id` | One value per copy, but kept for consistency |
| `connection_id`, `object_key` | The **source table or file**, not the pipeline. Two pipelines over one table share its rules |
| `column_name` | The **source** column name; the map resolves renames through the transform spec |
| `rule` | `keep` \| `mask` \| `address` |
| `status` | `approved` \| `provisional` |
| `detected_by`, `entity`, `confidence` | `presidio` / `regex` / `steward`; e.g. `EMAIL_ADDRESS`, 0.85 |
| `reviewed_by`, `reviewed_at`, `created_at`, `updated_at` | |

- **Unique key:** (`connection_id`, `object_key`, `column_name`).
- **Source of truth:** per-client rule files in Git (the one-time setup scripts decided on 4 Oct) are loaded into this
  table by an idempotent `python -m app.pii.registry apply <dir>` run from that client's Jenkins. A steward approval in
  the UI writes the same table and is exported back to Git for review.

## 5. What every job does
In `app/orchestrator/tasks.py::execute_task`, next to where `transform_spec` is built:
1. **Load the rules** for (`connection_id`, `object_key`). If the registry can't be read, the task **fails** (fail
   closed). It never loads unmasked.
2. **Schema diff.** Read `connector.get_schema(ref)` and compare it with the registry. A column with no rule is new.
3. **Classify new columns.** Run `connector._sample_rows(ref, 200)` through Presidio Analyzer (spaCy `en_core_web_lg`,
   plus the UK postcode and Indian recognizers from the PII POC), with a regex fallback. Insert a **`mask` /
   `provisional`** rule for any column that scores as PII. Columns that clearly aren't PII get `keep` / `provisional`.
   Both go to the steward.
4. **Open one review issue** per object with new columns (GitLab, PII-18). Loading continues, masked.
5. **Build the map** from the rules and pass it to `run_sql_object` / `run_file_object` (new `pii=` argument, alongside
   `transform=`).
6. **Pipeline config.** New `PiiSpec` in `PipelineConfig`:
   - `enabled: true` by default, and it cannot be turned off without platform-admin rights;
   - `detection: presidio | regex | off`;
   - `on_registry_error: fail`.

   It follows the additive, defaulted convention, so old configs still validate.

## 6. Validation changes (otherwise every masked job fails validation)
Source statistics are read from the raw source and target statistics from the written parquet:

| Check | Effect of masking | Change |
|---|---|---|
| `row_count`, `size` | none | — |
| `null_counts` | none (NULL kept) | — |
| `schema_match` | masked non-string columns show a type difference | Treat masked columns as an expected `string` |
| `checksum`, `sample_records`, `duplicate_counts` | **fail** (values differ by design) | Pass `exclude_columns` (the masked set) through `_run_validation` → `run_validation` → `stats_from_sql` / `stats_from_arrow` / DuckDB stats |
| New: `masking` | — | Every masked column in the output contains only `PII MASKED` or NULL/empty; FAIL otherwise |

The source side of `checksum` and samples still reads raw values inside the worker. They are compared in memory and
never stored: `ValidationResult` stores only counts and column names.

## 7. Close the UI leaks
`object_schema` sample rows, profile min/max and the file-profile samples go through the same rules before they are
returned. A column with no rule is shown masked until a steward approves it.

## 8. Tests
- **Shape round-trips** for the map (Arrow, RecordBatch, pandas, list, dict), mirroring `test_dlt_bridge.py:649–747`.
  An unknown shape must raise.
- **End-to-end:** a SQLite source with `email` and `phone` columns, through the API, with the parquet read back. Only
  `PII MASKED` appears, NULLs are kept, other columns are unchanged. Template: `test_transforms_e2e.py`.
- **New column:** a column added to the source between two runs is masked on the very next run, with a provisional rule
  and a review issue recorded.
- **Validation:** a masked job passes `checksum`, `sample_records` and `duplicate_counts` with exclusions; the
  `masking` check fails if a value leaks.
- **Fail closed:** registry unreachable means the task fails and no file is written.
- **Address rule:** the CDS table gets the clear value and the curated output gets `PII MASKED`.

## 9. Tickets and effort (engineer-days)
| Work | Ticket | Days |
|---|---|---|
| `pii_column_rules` model, migration, Git apply/export CLI | PII-06 | 2 |
| `build_pii_map` (all shapes, fail closed) + wiring in both resource builders and `execute_task` | PII-07 | 2.5 |
| Pre-run schema diff + Presidio/regex classification + provisional rules + review issue | PII-18 | 3 |
| Address side-write to the CDS table | PII-17 | 1.5 |
| Validation exclusions + `masking` check | PII-07 | 1.5 |
| UI leak fixes (schema samples, profile) + steward approve screen | PII-09 | 2 |
| Tests listed above | — | 2 |
| **Total** | | **≈ 14.5 days** |

**Dependencies:**
- The `pyproject.toml` lock file (ING-04) before adding `presidio-analyzer` and spaCy. Pin the
  `ghcr.io/data-privacy-stack` Presidio release.
- Each client's CDS account and `pii_address` schema (PII-17).

## 10. Open questions for Harish
1. Should masking match the column **after rename** (what the analyst sees) or the source name? The design keys rules on
   the **source** name, which survives renames.
2. Steward review in GitLab issues (as PII-18 says) or a screen in the platform UI? The design does both, with Git as
   the source of truth.
3. A job where classification itself fails (Presidio down): mask every new column (proposed), or fail the task?
