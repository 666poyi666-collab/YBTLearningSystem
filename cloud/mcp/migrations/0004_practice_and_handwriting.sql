CREATE TABLE IF NOT EXISTS practice_sources (
  source_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  source_sha256 TEXT NOT NULL UNIQUE,
  page_count INTEGER NOT NULL,
  index_r2_key TEXT NOT NULL,
  ocr_provider TEXT NOT NULL,
  answer_status TEXT NOT NULL,
  imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS practice_pages (
  source_id TEXT NOT NULL REFERENCES practice_sources(source_id),
  pdf_page INTEGER NOT NULL,
  printed_page INTEGER,
  chapter_key TEXT,
  section_key TEXT,
  unit_key TEXT,
  unit_title TEXT,
  cadence TEXT,
  headings_json TEXT NOT NULL DEFAULT '[]',
  ocr_text TEXT NOT NULL,
  ocr_text_sha256 TEXT NOT NULL,
  ocr_confidence REAL NOT NULL,
  visual_status TEXT NOT NULL,
  page_pack_r2_key TEXT NOT NULL,
  page_image_sha256 TEXT NOT NULL,
  PRIMARY KEY(source_id, pdf_page)
);
CREATE INDEX IF NOT EXISTS idx_practice_page_route
  ON practice_pages(chapter_key, section_key, printed_page);

CREATE TABLE IF NOT EXISTS practice_items (
  item_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES practice_sources(source_id),
  pdf_page INTEGER NOT NULL,
  printed_page INTEGER NOT NULL,
  question_number INTEGER NOT NULL,
  occurrence INTEGER NOT NULL DEFAULT 1,
  label TEXT NOT NULL,
  chapter_key TEXT NOT NULL,
  section_key TEXT NOT NULL,
  unit_key TEXT NOT NULL,
  unit_title TEXT NOT NULL,
  source_type_title TEXT NOT NULL,
  practice_level TEXT NOT NULL,
  cadence TEXT NOT NULL,
  ocr_excerpt TEXT NOT NULL,
  ocr_excerpt_sha256 TEXT NOT NULL,
  visual_status TEXT NOT NULL,
  answer_status TEXT NOT NULL,
  FOREIGN KEY(source_id, pdf_page) REFERENCES practice_pages(source_id, pdf_page)
);
CREATE INDEX IF NOT EXISTS idx_practice_item_route
  ON practice_items(chapter_key, section_key, printed_page, question_number, occurrence);

CREATE TABLE IF NOT EXISTS practice_route_links (
  item_id TEXT NOT NULL REFERENCES practice_items(item_id),
  route_type TEXT NOT NULL,
  route_key TEXT NOT NULL,
  cadence TEXT NOT NULL,
  confidence TEXT NOT NULL,
  PRIMARY KEY(item_id, route_type, route_key)
);
CREATE INDEX IF NOT EXISTS idx_practice_route_lookup
  ON practice_route_links(route_type, route_key, cadence);

CREATE TABLE IF NOT EXISTS practice_attempts (
  attempt_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL,
  practice_item_id TEXT NOT NULL REFERENCES practice_items(item_id),
  result TEXT NOT NULL,
  independent INTEGER NOT NULL DEFAULT 0,
  hint_level TEXT NOT NULL DEFAULT 'none',
  process_evidence TEXT NOT NULL,
  evidence_hash TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_practice_attempt_user_created
  ON practice_attempts(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS handwriting_analyses (
  analysis_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL,
  item_kind TEXT NOT NULL,
  item_ref TEXT NOT NULL,
  section_key TEXT,
  image_evidence_id TEXT NOT NULL,
  question_source_verified INTEGER NOT NULL DEFAULT 0,
  transcription_json TEXT NOT NULL,
  steps_json TEXT NOT NULL,
  first_wrong_step INTEGER,
  error_type TEXT,
  reason TEXT,
  minimal_correction TEXT,
  downstream_status TEXT NOT NULL,
  confidence TEXT NOT NULL,
  analysis_status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_handwriting_user_created
  ON handwriting_analyses(user_id, created_at DESC);
