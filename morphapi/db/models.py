"""
MorphAPI Database Schemas (DDL)
Implements SQLite schema supporting endpoints, versions, candidate separation,
atomic promotion, jobs, approvals, and append-only audit events.
"""

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    policy_settings TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS endpoints (
    endpoint_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default_tenant',
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    target_url TEXT NOT NULL,
    allowed_url_scope TEXT NOT NULL DEFAULT '[]',
    schema_definition TEXT NOT NULL,
    field_descriptions TEXT NOT NULL DEFAULT '{}',
    extraction_hints TEXT NOT NULL DEFAULT '{}',
    freshness_seconds INTEGER NOT NULL DEFAULT 300,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    active_version_id TEXT,
    last_known_good_version_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_endpoints_tenant ON endpoints(tenant_id);
CREATE INDEX IF NOT EXISTS idx_endpoints_slug ON endpoints(slug);

CREATE TABLE IF NOT EXISTS endpoint_versions (
    version_id TEXT PRIMARY KEY,
    endpoint_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    schema_definition TEXT NOT NULL,
    selector_map TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'DRAFT',
    is_active INTEGER NOT NULL DEFAULT 0,
    is_last_known_good INTEGER NOT NULL DEFAULT 0,
    verification_result TEXT,
    rationale TEXT,
    evidence_refs TEXT NOT NULL DEFAULT '[]',
    created_by TEXT NOT NULL DEFAULT 'system',
    verified_at TEXT,
    activated_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id) ON DELETE CASCADE,
    UNIQUE(endpoint_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_versions_endpoint ON endpoint_versions(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_versions_status ON endpoint_versions(status);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    endpoint_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'default_tenant',
    job_type TEXT NOT NULL,
    workflow_thread_id TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    deadline TEXT,
    failure_reason TEXT,
    result_summary TEXT NOT NULL DEFAULT '{}',
    clarification TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_jobs_endpoint ON jobs(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    endpoint_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    pending_decision TEXT NOT NULL,
    sanitized_evidence TEXT NOT NULL DEFAULT '{}',
    approver TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    decided_at TEXT,
    FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id) ON DELETE CASCADE,
    FOREIGN KEY (version_id) REFERENCES endpoint_versions(version_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_events (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    correlation_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'default_tenant',
    actor TEXT NOT NULL DEFAULT 'system',
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_events(target_id);
CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_events(correlation_id);
"""
