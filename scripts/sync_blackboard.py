import json
import duckdb

def append_event(timestamp, event, role, summary, artifacts, jsonl_path='blackboard/obsidian_synapse_blackboard.jsonl', db_path='blackboard/obsidian_synapse_blackboard.duckdb'):
    """
    Append event to JSONL file and mirror to DuckDB table 'events'.
    Schema: timestamp TEXT, event TEXT, role TEXT, summary TEXT, artifacts TEXT
    Ensures append-only operation.
    """
    event_data = {
        "timestamp": timestamp,
        "event": event,
        "role": role,
        "summary": summary,
        "artifacts": artifacts
    }
    
    # Append to JSONL in append mode
    with open(jsonl_path, 'a') as f:
        json.dump(event_data, f)
        f.write('\n')
    
    # Connect to DuckDB and create table if not exists
    con = duckdb.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS events (
            timestamp TEXT,
            event TEXT,
            role TEXT,
            summary TEXT,
            artifacts TEXT
        )
    """)
    
    # Insert into DuckDB (append-only, no UPDATE/DELETE)
    con.execute("""
        INSERT INTO events (timestamp, event, role, summary, artifacts)
        VALUES (?, ?, ?, ?, ?)
    """, [timestamp, event, role, summary, artifacts])
    
    con.close()

if __name__ == "__main__":
    # Test with sample event
    append_event(
        "2025-10-27T12:00:00Z",
        "setup_complete",
        "swarmlord",
        "Blackboard initialized",
        "[]"
    )
    print("Sample event appended successfully.")