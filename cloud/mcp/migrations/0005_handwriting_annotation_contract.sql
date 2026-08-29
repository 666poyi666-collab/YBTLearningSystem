ALTER TABLE handwriting_analyses ADD COLUMN uncertainties_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE handwriting_analyses ADD COLUMN clarification_request TEXT;
ALTER TABLE handwriting_analyses ADD COLUMN annotation_spec_json TEXT;
