-- These tables were added to the original schema after production had already
-- applied migration 0001.  Keep this additive migration idempotent so existing
-- learning events and learner state are never reset.

CREATE TABLE IF NOT EXISTS learner_diagnostics (
  diagnostic_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL,
  item_id TEXT,
  section_key TEXT,
  error_type TEXT NOT NULL,
  error_direction TEXT,
  evidence_text TEXT NOT NULL,
  user_correction TEXT,
  final_status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_diagnostics_user_section_created
  ON learner_diagnostics(user_id, section_key, created_at DESC);

CREATE TABLE IF NOT EXISTS memory_items (
  memory_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL,
  item_id TEXT,
  section_key TEXT,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  reason TEXT NOT NULL,
  priority TEXT NOT NULL DEFAULT 'normal',
  user_requested INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_user_section_created
  ON memory_items(user_id, section_key, created_at DESC);

CREATE TABLE IF NOT EXISTS type_classifications (
  classification_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL,
  item_id TEXT,
  section_key TEXT,
  cluster_title TEXT NOT NULL,
  basis TEXT NOT NULL,
  confidence TEXT NOT NULL DEFAULT 'medium',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_types_user_section_created
  ON type_classifications(user_id, section_key, created_at DESC);

CREATE TABLE IF NOT EXISTS wrong_question_exports (
  export_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  section_key TEXT,
  format TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL
);
