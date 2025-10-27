# Instructions for AI Chat Copilot (Non-HFO)

## Task Overview
Search the entire repository for blackboard-related files. Focus on files such as:
- `index.md` or similar markdown indexes mentioning blackboard.
- JSONL files, especially those related to blackboards (e.g., `obsidian_synapse_blackboard.jsonl`).
- Schemas (e.g., JSON schemas defining blackboard structures).
- Scripts in directories like `HFO_molt_shell_*` or similar (e.g., Python scripts handling blackboard operations, such as `sync_blackboard.py`).

Compile all relevant content from these files into a single append-only JSONL file named `obsidian_synapse_blackboard.jsonl`. This file should be placed in the root or blackboard directory as appropriate. Each entry in the JSONL must be a valid JSON object on a single line.

## JSONL Format
Use an append-only structure. For each extracted piece of content or merged artifact, create an entry with the following fields:
- `timestamp`: ISO 8601 UTC timestamp (e.g., "2025-10-27T12:52:21Z") for when the entry was created.
- `event`: A brief description of the event (e.g., "blackboard_file_extraction", "schema_merge", "script_summary").
- `role`: The role performing the action (e.g., "extractor", "compiler", "verifier").
- `summary`: A concise summary of the extracted/merged content (e.g., "Extracted blackboard schema from config.json").
- `artifacts`: The merged or raw content from the files as a string (e.g., JSON stringified if applicable, or markdown/text content). Preserve original formatting where possible.

Example entry:
```
{"timestamp": "2025-10-27T12:52:21Z", "event": "blackboard_file_extraction", "role": "extractor", "summary": "Merged content from blackboard/README.md", "artifacts": "Full content of README.md here..."}
```

## Steps to Execute
1. **Search the Repo**: Use tools like `grep`, `find`, or equivalent to locate files containing "blackboard" or related terms (e.g., "obsidian_synapse", "jsonl", "schema"). Include directories like `blackboard/`, `hfo_molt_shell_*`, `scripts/`.
2. **Extract Content**: Read and extract relevant sections from each file. Merge similar content (e.g., combine schemas into one artifact).
3. **Compile JSONL**: Append new entries to `obsidian_synapse_blackboard.jsonl` without overwriting existing content. Ensure each line is valid JSON.
4. **Output the File**: Produce the complete `obsidian_synapse_blackboard.jsonl` file ready for direct use or movement (e.g., copy-paste or save as file).
5. **Verification**: After compilation, run `ls -la obsidian_synapse_blackboard.jsonl` to confirm creation. Use `head -5 obsidian_synapse_blackboard.jsonl` and `tail -5 obsidian_synapse_blackboard.jsonl` to inspect the first and last entries for validity.

## Constraints
- No deviations from this format or process.
- Handle only blackboard-related content; ignore unrelated files.
- Ensure the JSONL is append-only: Do not modify or delete existing entries.
- If no new content is found, add a single entry noting "no updates".
- Output the full JSONL content at the end for easy copying.

Follow these instructions precisely to generate the JSONL file.