# Obsidian Synapse Blackboard

## Overview
This directory contains the append-only blackboard for Obsidian Synapse, consisting of:
- `obsidian_synapse_blackboard.jsonl`: JSON Lines file for event logging.
- `obsidian_synapse_blackboard.duckdb`: DuckDB database for structured queries.

## Append-Only Enforcement

### JSONL File (obsidian_synapse_blackboard.jsonl)
- **Writing**: Always open the file in append mode ('a') to add new lines without modifying existing content. Example in Python:
  ```
  with open('obsidian_synapse_blackboard.jsonl', 'a') as f:
      f.write(json.dumps(entry) + '\n')
  ```
- **Enforcement**:
  - **File Permissions**: After initialization, set read-only permissions using `chmod 444 obsidian_synapse_blackboard.jsonl` to prevent modifications or deletions by non-root users.
  - **Immutable Flag**: For stronger enforcement on Linux, use `chattr +a obsidian_synapse_blackboard.jsonl` to make the file append-only at the filesystem level.
  - **No Delete Hooks**: Ensure no scripts or processes include deletion logic (e.g., rm, truncate). Validate writes to confirm append-only behavior.

### DuckDB Database (obsidian_synapse_blackboard.duckdb)
- **Schema**: Table `events` with columns: `timestamp TEXT`, `event TEXT`, `role TEXT`, `summary TEXT`, `artifacts TEXT` (JSON string).
- **Writing**: Use only `INSERT` statements. Avoid `UPDATE`, `DELETE`, or `DROP`. Example:
  ```
  INSERT INTO events (timestamp, event, role, summary, artifacts)
  VALUES ('2025-10-27T12:34:00Z', 'init', 'system', 'Blackboard initialized', '{}');
  ```
- **Enforcement**:
  - **Application-Level**: Codebase enforces INSERT-only operations; no UPDATE/DELETE in any scripts or tools interacting with the DB.
  - **File Permissions**: Set the database file to read-only with `chmod 444 obsidian_synapse_blackboard.duckdb` post-initialization to prevent direct modifications.
  - **No Delete Hooks**: Implement no triggers or hooks that allow deletions. Use read-only connections where possible: `duckdb.connect(database, read_only=True)`.
  - **Verification**: Query `SELECT COUNT(*) FROM events` to confirm growth without removals.

## Usage Notes
- Initialize empty files as done.
- For queries, use DuckDB CLI or Python library with the virtual environment (`.venv`).
- Backup periodically while preserving append-only integrity.