CREATE TABLE IF NOT EXISTS handout_sources (
  source_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  source_sha256 TEXT NOT NULL UNIQUE,
  page_count INTEGER NOT NULL,
  index_r2_key TEXT NOT NULL,
  ocr_provider TEXT NOT NULL,
  imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS handout_pages (
  source_id TEXT NOT NULL REFERENCES handout_sources(source_id),
  pdf_page INTEGER NOT NULL,
  printed_page INTEGER,
  page_role TEXT NOT NULL,
  headings_json TEXT NOT NULL DEFAULT '[]',
  ocr_text TEXT NOT NULL,
  ocr_text_sha256 TEXT NOT NULL,
  ocr_confidence REAL NOT NULL,
  visual_status TEXT NOT NULL,
  page_pack_r2_key TEXT NOT NULL,
  page_image_sha256 TEXT NOT NULL,
  PRIMARY KEY(source_id, pdf_page)
);
CREATE INDEX IF NOT EXISTS idx_handout_printed_page
  ON handout_pages(source_id, printed_page);

CREATE TABLE IF NOT EXISTS handout_course_links (
  source_id TEXT NOT NULL,
  pdf_page INTEGER NOT NULL,
  course_key TEXT NOT NULL REFERENCES courses(course_key),
  relationship TEXT NOT NULL,
  confidence TEXT NOT NULL,
  PRIMARY KEY(source_id, pdf_page, course_key),
  FOREIGN KEY(source_id, pdf_page) REFERENCES handout_pages(source_id, pdf_page)
);
CREATE INDEX IF NOT EXISTS idx_handout_course
  ON handout_course_links(course_key, source_id, pdf_page);
