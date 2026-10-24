# MorphAPI Integration Pack
Use this as the shared contract pack for seven parallel agents. Source of truth: the uploaded SRS and System Design/UML documents. Proposed decisions must be approved by Agent 1 before implementation.

Read in order: build rules, decisions, ownership, contracts, API/MCP, database, healing/events, testing, handoff, runbook, NVIDIA NIM provider, seven-agent workflow.

Rules: one owner per module; shared contract changes require Agent 1 approval; no selector patch is persisted before live extraction and schema validation; tests use a fake model by default; never commit API keys.
