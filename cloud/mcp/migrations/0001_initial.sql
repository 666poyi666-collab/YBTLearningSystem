CREATE TABLE IF NOT EXISTS source_versions (
  id TEXT PRIMARY KEY,
  git_commit TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chapters (
  chapter_key TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  source_version_id TEXT NOT NULL REFERENCES source_versions(id),
  sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sections (
  section_key TEXT PRIMARY KEY,
  chapter_key TEXT NOT NULL REFERENCES chapters(chapter_key),
  title TEXT NOT NULL,
  manifest_r2_key TEXT NOT NULL,
  sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
  item_id TEXT PRIMARY KEY,
  section_key TEXT NOT NULL REFERENCES sections(section_key),
  label TEXT NOT NULL,
  item_type TEXT NOT NULL,
  concept_key TEXT,
  content_r2_key TEXT NOT NULL,
  source_sha256 TEXT NOT NULL,
  sort_order INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_section_sort ON items(section_key, sort_order);

CREATE TABLE IF NOT EXISTS courses (
  course_key TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  transcript_r2_key TEXT NOT NULL,
  transcript_sha256 TEXT NOT NULL,
  duration_ms INTEGER,
  has_timeline INTEGER NOT NULL CHECK (has_timeline IN (0, 1))
);

CREATE TABLE IF NOT EXISTS item_course_links (
  item_id TEXT NOT NULL REFERENCES items(item_id),
  course_key TEXT NOT NULL REFERENCES courses(course_key),
  relationship TEXT NOT NULL,
  PRIMARY KEY(item_id, course_key)
);

CREATE TABLE IF NOT EXISTS transcript_chunks (
  course_key TEXT NOT NULL REFERENCES courses(course_key),
  chunk_index INTEGER NOT NULL,
  start_ms INTEGER,
  end_ms INTEGER,
  text TEXT NOT NULL,
  topic TEXT,
  method_tags TEXT NOT NULL DEFAULT '[]',
  PRIMARY KEY(course_key, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_transcript_topic ON transcript_chunks(topic);

CREATE TABLE IF NOT EXISTS learning_events (
  event_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  evidence_hash TEXT,
  base_version INTEGER,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_user_created ON learning_events(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS learner_state (
  user_id TEXT NOT NULL,
  state_key TEXT NOT NULL,
  version INTEGER NOT NULL,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(user_id, state_key)
);

CREATE TABLE IF NOT EXISTS questions (
  question_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL,
  item_id TEXT,
  question TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS answer_sources (
  item_id TEXT NOT NULL REFERENCES items(item_id),
  source_kind TEXT NOT NULL,
  source_version_id TEXT NOT NULL REFERENCES source_versions(id),
  answer_text TEXT NOT NULL,
  source_sha256 TEXT NOT NULL,
  PRIMARY KEY(item_id, source_kind, source_version_id)
);
