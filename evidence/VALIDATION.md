# Validation results and limits

Validation date: 29 October 2026.

The official January 2025 Parquet source was downloaded and inspected. It contains **3,475,226 rows**, occupies 59,158,238 bytes, and has SHA-256 `9af277e4c0d3f9deb30644da822981e1e7df6af58313170fd3aa8a474485488a`. Source metadata and schema are recorded in source_verification.json.

## Completed checks

- Standard Python checks: **9 passed, 1 database integration test skipped** when no native PostgreSQL target was configured.
- Database-backed application checks: **10 passed** using the actual application functions and SQL through a PGlite QA adapter.
- Full-source application execution through that adapter: **3,328,707 accepted rows and 146,519 rejected rows**. The counts reconcile to 3,475,226.
- A full-source transformation rerun returned the same accepted and rejected counts.
- Generated file checksums, quality-rejection totals, and hourly, daily and quarterly trip totals passed reconciliation.
- January-only output correctly reports `complete_quarter: false`. The synthetic integration fixture also checked the complete-quarter path; it was not reported as three months of real TLC data.
- All Python files passed syntax inspection; both Compose files were checked as YAML.
- Revised Phase 1 DOCX: all package parts other than document text were preserved; non-text document XML matched. All five rendered pages were visually reviewed. The original architecture PNG is unchanged.
- Both portfolio-field text files contain exactly 200 whitespace-delimited words, including the repository marker in Phase 2.

The database fixture checks missing/out-of-month timestamps, invalid duration, negative distance, NaN/infinite charges, invalid locations, unknown passenger counts, retention of identical-looking trips, repeated loads, stale-source export rejection, rollback, aggregate values, checksums and quarter completeness.

## Test environment distinction

Docker and a native PostgreSQL service were unavailable in the supplied environment. The application and its SQL were therefore exercised using **PGlite 0.5.13, PostgreSQL 18.6 compiled to WebAssembly**, with a synchronous QA adapter. This adapter maps database calls to PGlite and maps COPY STDIN/STDOUT to its documented blob COPY facility. It preserves the project SQL, quality policy and application control flow, while replacing the psycopg network transport. Initial socket-based compatibility attempts were unsuitable for this test environment; they do not establish a defect in native PostgreSQL COPY, but native transport remains unverified here.

These results **do not certify Docker deployment, PostgreSQL 17.4 runtime compatibility, native psycopg connectivity, role isolation, network isolation, concurrent locking, container startup or CI execution**. The included `python scripts/run_tests.py` command is the repeatable native Docker test gate for the target machine. Run it and `python scripts/run_pipeline.py --month 2025-01`, then retain your console and container-status evidence.

Application timing is specific to this adapter and is not a production performance claim. Initial full-source loading took about 64.7 seconds; transformation took about 27.5 seconds, and its rerun about 45.1 seconds. SQL aggregates are computed on demand rather than stored as materialized aggregate tables.

## Supplied evidence

- `full_source_results.json`: actual stage metrics, source fingerprints and rejection totals.
- `adapted_validation_log.txt`: captured application test and full-source execution log.
- `test_results.txt`: concise check outcomes with environment qualifiers.
- `example_output/`: the complete aggregate output snapshot from the adapted full-source run, including its manifest. These files demonstrate application results and are not claimed as Docker-produced evidence. Runtime output on your machine is created separately under outputs/.

GitHub publication has not occurred because no authenticated GitHub account or repository was supplied. Repository_Link.txt explicitly records that status; the publishing helper replaces it only after a successful push. A live link and target-machine Docker evidence are still needed for the formal Phase 2 hand-in.
