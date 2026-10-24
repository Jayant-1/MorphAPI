# Build Rules
1. Shared request/response models live in `backend/app/models/contracts.py`.
2. One owner per module, as listed in `03_MODULE_OWNERSHIP.md`.
3. Do not invent alternate route names or payload fields; raise conflicts to Agent 1.
4. Fast path must never call the model.
5. A selector patch is only persisted after Playwright extraction and Pydantic validation pass.
6. Healing is bounded to one retry after error feedback.
7. Use one async healing lock per endpoint; re-read selectors after lock acquisition.
8. Keep secrets in environment variables; `.env` is ignored by Git.
9. Unit/integration tests use local HTML fixtures and a fake model adapter.
10. Contract changes update docs, tests, and affected agents before merge.
11. Every agent supplies tests, known limitations, and handoff notes.
12. Keep the app runnable and merge small changes frequently.

Definition of done: tests pass, interface matches contract, errors are controlled, handoff template is completed, and shared smoke test passes.
