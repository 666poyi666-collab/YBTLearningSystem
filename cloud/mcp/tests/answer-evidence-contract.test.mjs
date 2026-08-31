import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { DatabaseSync } from 'node:sqlite'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function schema(name) {
  return readFileSync(resolve(root, 'migrations', name), 'utf8')
}

test('answer evidence migration is additive and legacy rows fail closed', () => {
  const db = new DatabaseSync(':memory:')
  db.exec('PRAGMA foreign_keys=ON')
  db.exec(schema('0001_initial.sql'))

  db.exec("INSERT INTO source_versions VALUES ('legacy-v1','legacy','manifest','2026-08-01T00:00:00Z')")
  db.exec("INSERT INTO chapters VALUES ('1','chapter','legacy-v1',1)")
  db.exec("INSERT INTO sections VALUES ('1.1','1','section','legacy/section.json',1)")
  db.exec("INSERT INTO items VALUES ('item-1','1.1','A1','exercise',NULL,'legacy/section.json','item-sha',1)")
  db.exec("INSERT INTO answer_sources VALUES ('item-1','original_answer_book','legacy-v1','legacy answer','legacy-sha')")

  db.exec(schema('0006_answer_evidence_contract.sql'))
  const requiredColumnCount = db.prepare("SELECT COUNT(*) AS count FROM pragma_table_info('answer_sources') WHERE name IN ('evidence_kind','confidence','review_required','automatic_grading_allowed','answer_text_kind','parse_status','source_pdf_name','source_pdf_sha256','source_pdf_page','source_page_image_sha256','source_page_r2_key','source_page_asset_key')").get().count
  assert.equal(requiredColumnCount, 12)
  const row = db.prepare('SELECT * FROM answer_sources WHERE item_id=?').get('item-1')
  assert.equal(row.answer_text, 'legacy answer')
  assert.equal(row.evidence_kind, 'legacy_answer_text')
  assert.equal(row.confidence, 'legacy_unreviewed')
  assert.equal(row.review_required, 1)
  assert.equal(row.automatic_grading_allowed, 0)
  assert.equal(row.source_pdf_sha256, null)
  assert.equal(row.source_page_r2_key, null)

  assert.throws(
    () => db.exec("UPDATE answer_sources SET automatic_grading_allowed=2 WHERE item_id='item-1'"),
    /CHECK constraint failed/,
  )
  assert.throws(
    () => db.exec("UPDATE answer_sources SET review_required=-1 WHERE item_id='item-1'"),
    /CHECK constraint failed/,
  )
  db.close()
})
