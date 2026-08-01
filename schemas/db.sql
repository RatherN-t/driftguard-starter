PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  external_id TEXT NOT NULL,
  uri TEXT,
  title TEXT NOT NULL,
  source_version TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  normalized_content TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_spans (
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL REFERENCES artifacts(id),
  locator_type TEXT NOT NULL,
  start_locator TEXT,
  end_locator TEXT,
  excerpt TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS claims (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  claim_type TEXT NOT NULL,
  subject TEXT NOT NULL,
  statement TEXT NOT NULL,
  scope TEXT,
  status TEXT NOT NULL,
  confidence REAL NOT NULL,
  effective_from TEXT,
  effective_to TEXT,
  model_id TEXT,
  prompt_version TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_evidence (
  claim_id TEXT NOT NULL REFERENCES claims(id),
  evidence_id TEXT NOT NULL REFERENCES evidence_spans(id),
  support_type TEXT NOT NULL,
  PRIMARY KEY (claim_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS drift_alerts (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  relationship TEXT NOT NULL,
  severity TEXT NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL,
  summary TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS change_proposals (
  id TEXT PRIMARY KEY,
  alert_id TEXT NOT NULL REFERENCES drift_alerts(id),
  target_artifact_id TEXT NOT NULL REFERENCES artifacts(id),
  expected_revision TEXT NOT NULL,
  patch_json TEXT NOT NULL,
  status TEXT NOT NULL,
  approved_by TEXT,
  approved_at TEXT,
  applied_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  actor_type TEXT NOT NULL,
  actor_id TEXT,
  event_type TEXT NOT NULL,
  object_type TEXT NOT NULL,
  object_id TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);
