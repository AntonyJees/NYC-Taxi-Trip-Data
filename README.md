# NYC Taxi Phase 2 Development Package

This is the development and reflection phase for Task 1 of DLMDSEDE02. It implements the Phase 1 NYC Yellow Taxi batch-processing design using local Python services, PostgreSQL, Docker Compose and version-controlled source. There is no website or model-training component.

**Start here:** submission/ contains the revised Phase 1 DOCX, its original architecture PNG, the two 200-word portfolio texts, and the GitHub-link hand-in file. A genuine GitHub URL must still be published by the account owner. Do not submit an unpublished placeholder.

## Requirements

- Docker Desktop with Linux containers, or Docker Engine with Compose v2. The machine needs outbound access to Docker Hub, PyPI and the official TLC source.
- Python 3.12 to run the portable helper scripts; Docker installs application dependencies itself.
- Git for restoring source history and publishing. A GitHub account is needed for the formal hand-in link.
- Approximately 8 GB RAM available and 6 GB free disk for the January demonstration; actual usage varies. Source download is approximately 59 MB. Runtime data are not bundled in this ZIP.

## Run January 2025

Extract the ZIP, open a terminal in this directory, start Docker, then run:

```bash
python scripts/run_pipeline.py --month 2025-01
python scripts/verify_outputs.py
```

On Windows use `py -3` in place of `python` if required. The helpers work from PowerShell and a Unix shell. The runner creates private random credentials, starts the database, builds the application image, and executes ingestion, transformation, export and reconciliation in sequence. Do not interrupt the initial bulk load if the console is quiet. Job services are one-shot containers and normally exit with code zero.

To run the same steps manually:

```bash
python scripts/setup.py
docker compose up -d --wait db
docker compose --profile pipeline build
docker compose run --rm --no-deps ingest ingest --month 2025-01
docker compose run --rm --no-deps transform transform --month 2025-01
docker compose run --rm --no-deps export export --month 2025-01
docker compose run --rm --no-deps test selfcheck
docker compose ps -a
```

After success, `outputs/latest.json` points to a UUID directory containing `hourly_features.csv`, `daily_summary.csv`, `quarterly_features.csv`, `quality_report.csv` and `manifest.json`. Monthly aggregate trip totals must equal the accepted row count. The quarter manifest explicitly lists available and expected months; January alone is not a complete Q1 dataset.

The full official Parquet file and ingestion manifest are retained in `data/raw/`. The loader selects eight source fields for typed raw database tables. Python processes 100,000-row batches instead of reading the complete source into a dataframe. The raw source has 3,475,226 rows. The one-million-record minimum applies to the source, rather than the smaller aggregate output.

## Repeated runs and recovery

The same command can run again. It replaces the source month within a transaction and regenerates its clean data. Do not delete the database to rerun. Source rows use month and row number as keys; identical-looking rides remain because the source has no unique trip ID.

Database transactions roll back failed operations. Ingestion retries downloads three times and checks the source schema and SHA-256. A new load invalidates previous transformation provenance until transformation succeeds. Export uses a read-only consistent snapshot and only moves `latest.json` after publishing all files.

`docker compose down` stops the system while retaining the database volume. `docker compose logs db` helps diagnose startup. Database initialization scripts run only on the first creation of its volume. Do not change `.env` passwords after initialization unless you also rotate the database roles; restore the existing `.env` instead. Never publish `.env` or raw trip data.

## Additional months and quarterly delivery

Run February and March using their named months:

```bash
python scripts/run_pipeline.py --month 2025-02
python scripts/run_pipeline.py --month 2025-03 --require-complete-quarter
```

The complete-quarter option fails if any of the three months is missing or a loaded source is not transformed. Quarterly means are computed directly from clean trips, avoiding unweighted averages of monthly means. This is an analytical feature store, not a trained machine learning model or complete training pipeline.

## Scheduling

The helpers provide scheduled execution; the operator must enable the host schedule. `scripts/scheduled_batch.py` selects the month three months before the current date, allowing for TLC's usual publication delay. It runs the same monthly pipeline and produces an explicitly partial quarter until all months are available.

Example cron entry, after replacing the paths with your actual installation:

```cron
0 8 15 * * /usr/bin/python3 /absolute/path/NYC_Taxi_Phase2/scripts/scheduled_batch.py >> /absolute/path/taxi-schedule.log 2>&1
```

On Windows Task Scheduler, create a monthly task for the 15th with your Python executable as the program, the absolute path to `scripts/scheduled_batch.py` as its argument, and this project directory as “Start in”. Docker Desktop must be running. A separate quarterly task can call `run_pipeline.py --month YYYY-03 --require-complete-quarter` or the corresponding June, September or December month after its three source files are available. No task is registered automatically.

## Tests

The simplest complete test command is:

```bash
python scripts/run_tests.py
```

It builds a separate test container and starts a disposable PostgreSQL test database. Its project name differs from the pipeline stack, and the test database uses temporary storage. The test stack is stopped after the checks; your pipeline data are retained. The included GitHub Actions workflow runs this command after publication, but no CI run is claimed before publication.

For local unit tests, use a Python virtual environment:

```bash
python -m venv .venv
```

Activate `.venv` using `source .venv/bin/activate` on Unix or `.venv\Scripts\Activate.ps1` on Windows, then:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The integration test requires **a disposable, empty PostgreSQL test database** with `sql/01_schema.sql` applied and the required roles/schema created. It is skipped by default because it intentionally inserts and replaces source partitions. Set PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE, and TEST_PG=1 only for that isolated test database; do not point it at your project results. See evidence/VALIDATION.md for checks actually completed in the supplied environment.

## Restore Git history and publish

The ZIP omits a working `.git` directory for portability and includes `source_history.bundle` instead. In the extracted project root:

```bash
git clone source_history.bundle ../nyc-taxi-phase2-repository
```

Open that cloned directory. Git initially sets the local bundle as origin; remove that local remote before publishing:

```bash
git remote remove origin
```

Create an empty repository in your GitHub account, then run the command below using its actual URL:

```bash
python scripts/publish_github.py https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY
```

The URL above is an example, not an existing project repository. Configure your own Git user.name and user.email if Git requests them for the publication commit. Authenticate through your normal Git credential manager. The helper does not accept or embed tokens. Only after a successful push does it write the real URL to `submission/Repository_Link.txt` and substitute it into the 200-word explanation. A URL is one whitespace-delimited token, so this preserves that text's word count. Open the repository in GitHub and verify assessor access before handing in.

If you prefer the GitHub website, upload the extracted source files, excluding `.env`, `data/`, `outputs/`, caches and `source_history.bundle`, then enter that actual repository URL in the two submission text files. This route does not preserve the bundled Git history.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Docker command not found | Install/start Docker and confirm `docker compose version` works. |
| Database authentication fails | Restore the `.env` used when the volume was first initialized. |
| Permission denied writing output | Run setup as your normal desktop user and check ownership of data/raw and outputs. Linux uses the current UID/GID. |
| TLS or download failure | Check local internet/proxy access to the official TLC download. Retry the command. |
| Cache checksum mismatch | Restore the original file, or explicitly re-ingest a fresh official copy using the documented Python API after investigating the change. |
| Complete-quarter export fails | Process all three months and rerun with the final month. |
| Pipeline exits nonzero | Read the structured error stage, database logs and source manifest; rerun the failed stage after correcting its input. |

## Submission

Follow docs/submission_checklist.md. The required formal Phase 2 submission is the 200-word PebblePad explanation and a TXT linking to your published GitHub repository. The revised Phase 1 DOCX is supplied with its original formatting preserved. Its original figure is also supplied separately as PNG. No student identity or matriculation number has been invented.

Primary sources and access dates are recorded in docs/sources.md. See docs/architecture.md for quality rules, security, provenance, tradeoffs and operational limits.
