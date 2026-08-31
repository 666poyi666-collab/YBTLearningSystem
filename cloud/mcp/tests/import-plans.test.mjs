import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { DatabaseSync } from 'node:sqlite'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const cloudRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const repoRoot = resolve(cloudRoot, '..', '..')

function runDry(script, args = []) {
  const result = spawnSync(process.execPath, [resolve(cloudRoot, 'scripts', script), ...args], {
    cwd: cloudRoot,
    encoding: 'utf8',
    windowsHide: true,
  })
  assert.equal(result.status, 0, result.stderr || result.stdout)
  return result.stdout
}

function planFromOutput(output, kind) {
  const pattern = kind === 'content'
    ? /"sourceVersionId":\s*"([^"]+)"/
    : /"version":\s*"([^"]+)"/
  const version = output.match(pattern)?.[1]
  assert.ok(version, `missing ${kind} version in output`)
  const directory = kind === 'content' ? 'math-cloud-import' : kind === 'practice' ? 'math-practice-import' : 'math-handout-import'
  return JSON.parse(readFileSync(resolve(repoRoot, 'tmp', directory, version, 'plan.json'), 'utf8'))
}

function executePlan(db, plan, field) {
  for (const path of plan[field]) db.exec(readFileSync(path, 'utf8'))
}

function scalar(db, sql) {
  return Number(db.prepare(sql).get().value)
}

test('generated import plans are compact, exact, idempotent, and preserve user-bound stale rows', () => {
  const contentPlan = planFromOutput(runDry('import_content.mjs', ['--dry-run']), 'content')
  const practicePlan = planFromOutput(runDry('import_practice_book.mjs', ['--index', resolve(repoRoot, 'tmp', 'practice-book-index', 'index.json')]), 'practice')
  const handoutPlan = planFromOutput(runDry('import_handouts.mjs', ['--index', resolve(repoRoot, 'tmp', 'handout-index', 'index.json')]), 'handout')

  assert.ok(contentPlan.sql.length <= 12, `content SQL chunks=${contentPlan.sql.length}`)
  assert.ok(practicePlan.sqlPaths.length <= 3, `practice SQL chunks=${practicePlan.sqlPaths.length}`)
  assert.equal(handoutPlan.sqlPaths.length, 1)
  assert.equal(contentPlan.links, 5097)
  assert.equal(contentPlan.answerSources, 546)
  assert.deepEqual(contentPlan.answerEvidence, {
    total: 546,
    automatic: 473,
    reviewRequiredText: 51,
    sourcePageVisual: 22,
    blocked: 0,
  })
  assert.equal(contentPlan.answerPagePacks, 38)
  assert.ok(contentPlan.answerPageAssets >= 38)
  const answerPageObjects = contentPlan.r2.filter((object) => object.key.includes('/answer-pages/'))
  assert.equal(answerPageObjects.length, 38)
  for (const object of answerPageObjects) {
    const pack = JSON.parse(readFileSync(object.path, 'utf8'))
    assert.equal(pack.schema_version, 'ybt-cloud-answer-page-pack-v1')
    assert.equal(pack.consumer_guard, 'GRADER_ONLY_SOURCE_EVIDENCE')
    assert.ok(Object.keys(pack.pages).length > 0)
    for (const page of Object.values(pack.pages)) {
      assert.match(page.sha256, /^[0-9a-f]{64}$/)
      assert.match(page.mimeType, /^image\//)
      assert.ok(page.data.length > 100)
    }
  }

  const db = new DatabaseSync(':memory:')
  db.exec('PRAGMA foreign_keys=ON')
  for (const file of readdirSync(resolve(cloudRoot, 'migrations')).filter((name) => name.endsWith('.sql')).sort()) {
    db.exec(readFileSync(resolve(cloudRoot, 'migrations', file), 'utf8'))
  }

  executePlan(db, contentPlan, 'sql')
  executePlan(db, practicePlan, 'sqlPaths')
  executePlan(db, handoutPlan, 'sqlPaths')

  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM chapters'), 5)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM sections'), 38)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM items'), 1209)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM courses'), 170)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM item_course_links'), 5097)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM transcript_chunks'), 19234)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM answer_sources'), 546)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM answer_sources WHERE automatic_grading_allowed=1 AND review_required=0'), 473)
  assert.equal(scalar(db, "SELECT COUNT(*) AS value FROM answer_sources WHERE evidence_kind='parsed_answer_text' AND review_required=1"), 51)
  assert.equal(scalar(db, "SELECT COUNT(*) AS value FROM answer_sources WHERE evidence_kind='source_page_visual' AND automatic_grading_allowed=0"), 22)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM answer_sources WHERE source_pdf_sha256 IS NULL OR source_pdf_page IS NULL OR source_page_image_sha256 IS NULL OR source_page_r2_key IS NULL'), 0)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM practice_pages'), 106)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM practice_items'), 727)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM practice_route_links'), 3020)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM handout_pages'), 562)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM handout_course_links'), 142)

  db.exec("INSERT INTO items SELECT 'stale-content',section_key,label,item_type,concept_key,'old/content.json',source_sha256,sort_order FROM items LIMIT 1")
  db.exec("INSERT INTO item_course_links VALUES ('stale-content',(SELECT course_key FROM courses LIMIT 1),'cycle_course')")
  db.exec("INSERT INTO items SELECT 'protected-content',section_key,label,item_type,concept_key,'old/protected.json',source_sha256,sort_order FROM items LIMIT 1")
  db.exec(`INSERT INTO answer_sources (item_id,source_kind,source_version_id,answer_text,source_sha256) VALUES ('protected-content','original_answer_book','${contentPlan.sourceVersionId}','kept','${'a'.repeat(64)}')`)
  db.exec("INSERT INTO transcript_chunks VALUES ((SELECT course_key FROM courses LIMIT 1),999999,NULL,NULL,'stale',NULL,'[]')")
  executePlan(db, contentPlan, 'sql')
  assert.equal(scalar(db, "SELECT COUNT(*) AS value FROM items WHERE item_id='stale-content'"), 0)
  assert.equal(scalar(db, "SELECT COUNT(*) AS value FROM items WHERE item_id='protected-content'"), 1)
  assert.equal(scalar(db, 'SELECT COUNT(*) AS value FROM transcript_chunks WHERE chunk_index=999999'), 0)

  db.exec("INSERT INTO practice_items SELECT 'stale-practice',source_id,pdf_page,printed_page,question_number,occurrence,label,chapter_key,section_key,unit_key,unit_title,source_type_title,practice_level,cadence,ocr_excerpt,ocr_excerpt_sha256,visual_status,answer_status FROM practice_items LIMIT 1")
  db.exec("INSERT INTO practice_route_links VALUES ('stale-practice','section','stale','after_section','test')")
  db.exec("INSERT INTO practice_items SELECT 'protected-practice',source_id,pdf_page,printed_page,question_number,occurrence,label,chapter_key,section_key,unit_key,unit_title,source_type_title,practice_level,cadence,ocr_excerpt,ocr_excerpt_sha256,visual_status,answer_status FROM practice_items LIMIT 1")
  db.exec("INSERT INTO practice_attempts VALUES ('attempt-protected','request-protected','poyi-owner','protected-practice','incorrect',0,'none','test',NULL,'2026-08-30T00:00:00Z')")
  executePlan(db, practicePlan, 'sqlPaths')
  assert.equal(scalar(db, "SELECT COUNT(*) AS value FROM practice_items WHERE item_id='stale-practice'"), 0)
  assert.equal(scalar(db, "SELECT COUNT(*) AS value FROM practice_items WHERE item_id='protected-practice'"), 1)

  db.close()
})
