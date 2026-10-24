# SQLite Database Contract (Proposed)
Agent 2 owns the final schema.

`endpoints`: `id` (PK), `name`, `target_url`, `schema_json`, `selectors_json`, `status`, `version`, `last_verified`, `updated_at`.

`healing_logs`: `log_id` (PK), `endpoint_id` (FK), `timestamp`, `failure_reason`, `old_selectors`, `new_selectors`, `ai_reasoning`, nullable `screenshot_b64`, `heal_latency_ms`, optional `from_version`/`to_version`.

`request_telemetry`: `id` (PK), `endpoint_id` (FK), `execution_path`, `latency_ms`, nullable `tokens_used`, `http_status`, `timestamp`.

Rules: enable SQLite foreign keys; use parameterized queries and transactions; selector update and audit log are atomic; persist only verified patches; retain the most recent 50 healing records per endpoint per SRS, with screenshot retention policy documented; do not store secrets/cookies without an explicit security design.
