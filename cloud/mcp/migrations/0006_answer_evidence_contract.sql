-- Additive answer-evidence metadata. Existing answer rows remain available,
-- but legacy rows default to manual review and can never grade automatically.
ALTER TABLE answer_sources ADD COLUMN evidence_kind TEXT NOT NULL DEFAULT 'legacy_answer_text';
ALTER TABLE answer_sources ADD COLUMN confidence TEXT NOT NULL DEFAULT 'legacy_unreviewed';
ALTER TABLE answer_sources ADD COLUMN review_required INTEGER NOT NULL DEFAULT 1 CHECK (review_required IN (0, 1));
ALTER TABLE answer_sources ADD COLUMN automatic_grading_allowed INTEGER NOT NULL DEFAULT 0 CHECK (automatic_grading_allowed IN (0, 1));
ALTER TABLE answer_sources ADD COLUMN answer_text_kind TEXT NOT NULL DEFAULT 'legacy_unreviewed_text';
ALTER TABLE answer_sources ADD COLUMN parse_status TEXT NOT NULL DEFAULT 'legacy_unreviewed';
ALTER TABLE answer_sources ADD COLUMN source_pdf_name TEXT;
ALTER TABLE answer_sources ADD COLUMN source_pdf_sha256 TEXT;
ALTER TABLE answer_sources ADD COLUMN source_pdf_page INTEGER;
ALTER TABLE answer_sources ADD COLUMN source_page_image_sha256 TEXT;
ALTER TABLE answer_sources ADD COLUMN source_page_r2_key TEXT;
ALTER TABLE answer_sources ADD COLUMN source_page_asset_key TEXT;

CREATE INDEX IF NOT EXISTS idx_answer_sources_review
  ON answer_sources(review_required, automatic_grading_allowed, evidence_kind);
