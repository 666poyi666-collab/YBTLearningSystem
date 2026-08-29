#!/usr/bin/env node

/** Import the source-page-backed supplementary practice book into R2 and D1. */

import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve, join } from 'node:path'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const cloudRoot = resolve(scriptDir, '..')
const repoRoot = resolve(cloudRoot, '..', '..')
const args = process.argv.slice(2)
const remote = args.includes('--remote')
const indexFlag = args.indexOf('--index')
const indexPath = resolve(indexFlag >= 0 ? args[indexFlag + 1] : join(repoRoot, 'tmp', 'practice-book-index', 'index.json'))
const indexRoot = dirname(indexPath)
const bucket = 'math-learning-content'
const database = 'math-learning'

function sha256(value) { return createHash('sha256').update(value).digest('hex') }
function sqlString(value) {
  if (value === null || value === undefined) return 'NULL'
  return `'${String(value).replaceAll("'", "''")}'`
}
function sqlNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'NULL'
  return String(Number(value))
}
function chunkStatements(statements, maxBytes = 70000) {
  const chunks = []; let current = []; let bytes = 0
  for (const statement of statements) {
    const size = Buffer.byteLength(statement, 'utf8') + 2
    if (current.length && bytes + size > maxBytes) { chunks.push(current.join('\n')); current = []; bytes = 0 }
    current.push(statement); bytes += size
  }
  if (current.length) chunks.push(current.join('\n'))
  return chunks
}
function run(command, commandArgs, options = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, commandArgs, {
      cwd: options.cwd ?? repoRoot,
      stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
      shell: process.platform === 'win32', windowsHide: true,
    })
    let stdout = ''; let stderr = ''
    child.stdout?.on('data', (chunk) => { stdout += chunk.toString() })
    child.stderr?.on('data', (chunk) => { stderr += chunk.toString() })
    child.on('error', reject)
    child.on('close', (code) => code === 0
      ? resolvePromise(options.capture ? stdout : '')
      : reject(new Error(`${command} ${commandArgs.join(' ')} failed with ${code}\n${stderr}`)))
  })
}
async function runWithRetry(command, commandArgs, options = {}, attempts = 5) {
  let lastError
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try { return await run(command, commandArgs, options) } catch (error) {
      lastError = error
      if (attempt === attempts) break
      const delayMs = 1000 * 2 ** (attempt - 1)
      console.warn(`retry ${attempt}/${attempts - 1} after ${delayMs}ms`)
      await new Promise((resolvePromise) => setTimeout(resolvePromise, delayMs))
    }
  }
  throw lastError
}

async function main() {
  const raw = await readFile(indexPath)
  const index = JSON.parse(raw.toString('utf8'))
  if (index.schema_version !== 'math-practice-book-index-v1') throw new Error('unsupported practice index')
  const fingerprint = JSON.stringify({
    source: index.source_pdf_sha256,
    pages: index.pages.map((page) => [page.pdf_page, page.ocr_text_sha256, page.page_image_sha256, page.unit, page.course_keys, page.cycle_ids]),
    items: index.items.map((item) => [item.item_id, item.ocr_excerpt_sha256, item.course_keys, item.cycle_ids, item.cadence]),
  })
  const version = `practice-v1-${sha256(fingerprint).slice(0, 16)}`
  const outputRoot = join(repoRoot, 'tmp', 'math-practice-import', version)
  await mkdir(outputRoot, { recursive: true })
  const indexKey = `practice/${version}/index.json`
  const statements = []
  const objects = []
  statements.push(`INSERT INTO practice_sources (source_id, title, source_sha256, page_count, index_r2_key, ocr_provider, answer_status, imported_at) VALUES (${sqlString(index.source_id)}, ${sqlString(index.title)}, ${sqlString(index.source_pdf_sha256)}, ${sqlNumber(index.page_count)}, ${sqlString(indexKey)}, ${sqlString(index.ocr_provider)}, ${sqlString(index.answer_status)}, ${sqlString(new Date().toISOString())}) ON CONFLICT(source_id) DO UPDATE SET title=excluded.title, source_sha256=excluded.source_sha256, page_count=excluded.page_count, index_r2_key=excluded.index_r2_key, ocr_provider=excluded.ocr_provider, answer_status=excluded.answer_status, imported_at=excluded.imported_at;`)

  const compactIndex = {
    schema_version: index.schema_version,
    version,
    source_id: index.source_id,
    title: index.title,
    source_pdf_sha256: index.source_pdf_sha256,
    answer_status: index.answer_status,
    evidence_policy: {
      text_is_search_aid_only: true,
      source_page_is_question_authority: true,
      no_source_answers_available: true,
    },
    route_policy: index.route_policy,
    units: index.units,
    pages: [],
    items: index.items,
  }

  const packSize = 5
  for (let offset = 0; offset < index.pages.length; offset += packSize) {
    const slice = index.pages.slice(offset, offset + packSize)
    const number = Math.floor(offset / packSize) + 1
    const packKey = `practice/${version}/pages-${String(number).padStart(3, '0')}.json`
    const pack = { schema_version: 'math-practice-page-pack-v1', version, source_id: index.source_id, pages: {} }
    for (const page of slice) {
      const imagePath = resolve(indexRoot, page.page_image_path)
      const image = await readFile(imagePath)
      if (sha256(image) !== page.page_image_sha256) throw new Error(`practice page hash mismatch: ${imagePath}`)
      pack.pages[`${index.source_id}:${page.pdf_page}`] = { mimeType: 'image/jpeg', sha256: page.page_image_sha256, data: image.toString('base64') }
      statements.push(`INSERT INTO practice_pages (source_id,pdf_page,printed_page,chapter_key,section_key,unit_key,unit_title,cadence,headings_json,ocr_text,ocr_text_sha256,ocr_confidence,visual_status,page_pack_r2_key,page_image_sha256) VALUES (${sqlString(index.source_id)},${sqlNumber(page.pdf_page)},${sqlNumber(page.printed_page)},${sqlString(page.chapter)},${sqlString(page.section)},${sqlString(page.unit)},${sqlString(page.unit_title)},${sqlString(page.cadence)},${sqlString(JSON.stringify(page.heading_candidates ?? []))},${sqlString(page.ocr_text)},${sqlString(page.ocr_text_sha256)},${sqlNumber(page.ocr_confidence)},${sqlString(page.visual_status)},${sqlString(packKey)},${sqlString(page.page_image_sha256)}) ON CONFLICT(source_id,pdf_page) DO UPDATE SET printed_page=excluded.printed_page,chapter_key=excluded.chapter_key,section_key=excluded.section_key,unit_key=excluded.unit_key,unit_title=excluded.unit_title,cadence=excluded.cadence,headings_json=excluded.headings_json,ocr_text=excluded.ocr_text,ocr_text_sha256=excluded.ocr_text_sha256,ocr_confidence=excluded.ocr_confidence,visual_status=excluded.visual_status,page_pack_r2_key=excluded.page_pack_r2_key,page_image_sha256=excluded.page_image_sha256;`)
      compactIndex.pages.push({
        pdf_page: page.pdf_page, printed_page: page.printed_page, chapter: page.chapter,
        section: page.section, unit: page.unit, unit_title: page.unit_title,
        cadence: page.cadence, course_keys: page.course_keys, cycle_ids: page.cycle_ids,
        headings: page.heading_candidates, question_item_ids: page.question_item_ids,
        ocr_text_sha256: page.ocr_text_sha256, page_image_sha256: page.page_image_sha256,
        visual_status: page.visual_status, page_pack_r2_key: packKey,
      })
    }
    const packPath = join(outputRoot, `pages-${String(number).padStart(3, '0')}.json`)
    await writeFile(packPath, JSON.stringify(pack), 'utf8')
    objects.push({ key: packKey, path: packPath })
  }

  for (const item of index.items) {
    statements.push(`DELETE FROM practice_route_links WHERE item_id=${sqlString(item.item_id)};`)
    statements.push(`INSERT INTO practice_items (item_id,source_id,pdf_page,printed_page,question_number,occurrence,label,chapter_key,section_key,unit_key,unit_title,source_type_title,practice_level,cadence,ocr_excerpt,ocr_excerpt_sha256,visual_status,answer_status) VALUES (${sqlString(item.item_id)},${sqlString(index.source_id)},${sqlNumber(item.pdf_page)},${sqlNumber(item.printed_page)},${sqlNumber(item.question_number)},${sqlNumber(item.occurrence ?? 1)},${sqlString(item.label)},${sqlString(item.chapter)},${sqlString(item.section)},${sqlString(item.unit)},${sqlString(item.title)},${sqlString(item.source_type_title)},${sqlString(item.practice_level)},${sqlString(item.cadence)},${sqlString(item.ocr_excerpt)},${sqlString(item.ocr_excerpt_sha256)},${sqlString(item.visual_status)},${sqlString(item.answer_status)}) ON CONFLICT(item_id) DO UPDATE SET pdf_page=excluded.pdf_page,printed_page=excluded.printed_page,question_number=excluded.question_number,occurrence=excluded.occurrence,label=excluded.label,chapter_key=excluded.chapter_key,section_key=excluded.section_key,unit_key=excluded.unit_key,unit_title=excluded.unit_title,source_type_title=excluded.source_type_title,practice_level=excluded.practice_level,cadence=excluded.cadence,ocr_excerpt=excluded.ocr_excerpt,ocr_excerpt_sha256=excluded.ocr_excerpt_sha256,visual_status=excluded.visual_status,answer_status=excluded.answer_status;`)
    for (const key of item.course_keys ?? []) statements.push(`INSERT OR IGNORE INTO practice_route_links (item_id,route_type,route_key,cadence,confidence) VALUES (${sqlString(item.item_id)},'course',${sqlString(key)},${sqlString(item.cadence)},'source_range_candidate');`)
    for (const key of item.cycle_ids ?? []) statements.push(`INSERT OR IGNORE INTO practice_route_links (item_id,route_type,route_key,cadence,confidence) VALUES (${sqlString(item.item_id)},'cycle',${sqlString(key)},${sqlString(item.cadence)},'source_range_candidate');`)
    statements.push(`INSERT OR IGNORE INTO practice_route_links (item_id,route_type,route_key,cadence,confidence) VALUES (${sqlString(item.item_id)},'section',${sqlString(item.section)},${sqlString(item.cadence)},'verified_toc_range');`)
    statements.push(`INSERT OR IGNORE INTO practice_route_links (item_id,route_type,route_key,cadence,confidence) VALUES (${sqlString(item.item_id)},'chapter',${sqlString(item.chapter)},${sqlString(item.cadence)},'verified_toc_range');`)
  }

  const compactPath = join(outputRoot, 'index.json')
  await writeFile(compactPath, JSON.stringify(compactIndex), 'utf8')
  objects.unshift({ key: indexKey, path: compactPath })
  const sqlPaths = []
  for (const [number, sql] of chunkStatements(statements).entries()) {
    const path = join(outputRoot, 'sql', `${String(number + 1).padStart(3, '0')}.sql`)
    await mkdir(dirname(path), { recursive: true })
    await writeFile(path, `${sql}\n`, 'utf8')
    sqlPaths.push(path)
  }
  const plan = {
    schema_version: 'math-practice-import-plan-v1', version,
    sourceId: index.source_id, pages: index.pages.length, items: index.items.length,
    routeLinks: index.items.reduce((count, item) => count + 2 + (item.course_keys?.length ?? 0) + (item.cycle_ids?.length ?? 0), 0),
    r2Objects: objects.length, sqlChunks: sqlPaths.length,
  }
  await writeFile(join(outputRoot, 'plan.json'), JSON.stringify({ ...plan, objects, sqlPaths }, null, 2), 'utf8')
  console.log(JSON.stringify(plan, null, 2))
  if (!remote) return
  const wrangler = process.platform === 'win32' ? 'npx.cmd' : 'npx'
  for (const object of objects) await runWithRetry(wrangler, ['wrangler','r2','object','put',`${bucket}/${object.key}`,'--file',object.path,'--content-type','application/json','--remote','-y'], { cwd: cloudRoot })
  for (const path of sqlPaths) await runWithRetry(wrangler, ['wrangler','d1','execute',database,'--remote','--file',path,'--yes'], { cwd: cloudRoot })
  console.log(`practice import complete: ${version}`)
}

main().catch((error) => { console.error(error.stack ?? error); process.exitCode = 1 })
