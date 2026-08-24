#!/usr/bin/env node

/** Import the private course-handout page index and rendered source pages. */

import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const cloudRoot = resolve(scriptDir, '..')
const repoRoot = resolve(cloudRoot, '..', '..')
const args = process.argv.slice(2)
const remote = args.includes('--remote')
const indexArg = args.indexOf('--index')
const indexPath = resolve(indexArg >= 0 ? args[indexArg + 1] : join(repoRoot, 'tmp', 'handout-index', 'index.json'))
const indexRoot = dirname(indexPath)
const bucket = 'math-learning-content'
const database = 'math-learning'

function sha256(value) {
  return createHash('sha256').update(value).digest('hex')
}

function sqlString(value) {
  if (value === null || value === undefined) return 'NULL'
  return `'${String(value).replaceAll("'", "''")}'`
}

function sqlNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'NULL'
  return String(Number(value))
}

function chunkStatements(statements, maxBytes = 70000) {
  const chunks = []
  let current = []
  let bytes = 0
  for (const statement of statements) {
    const size = Buffer.byteLength(statement, 'utf8') + 2
    if (current.length && bytes + size > maxBytes) {
      chunks.push(current.join('\n'))
      current = []
      bytes = 0
    }
    current.push(statement)
    bytes += size
  }
  if (current.length) chunks.push(current.join('\n'))
  return chunks
}

function run(command, commandArgs, options = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, commandArgs, {
      cwd: options.cwd ?? repoRoot,
      stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
      shell: process.platform === 'win32',
      windowsHide: true,
    })
    let stdout = ''
    let stderr = ''
    child.stdout?.on('data', (chunk) => { stdout += chunk.toString() })
    child.stderr?.on('data', (chunk) => { stderr += chunk.toString() })
    child.on('error', reject)
    child.on('close', (code) => code === 0
      ? resolvePromise(options.capture ? stdout : '')
      : reject(new Error(`${command} ${commandArgs.join(' ')} failed with ${code}\n${stderr}`)))
  })
}

async function runWithRetry(command, commandArgs, options = {}, attempts = 5) {
  let error
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await run(command, commandArgs, options)
    } catch (candidate) {
      error = candidate
      if (attempt === attempts) break
      const waitMs = 1000 * 2 ** (attempt - 1)
      console.warn(`retry ${attempt}/${attempts - 1} after ${waitMs}ms`)
      await new Promise((resolvePromise) => setTimeout(resolvePromise, waitMs))
    }
  }
  throw error
}

async function main() {
  const raw = await readFile(indexPath)
  const index = JSON.parse(raw.toString('utf8'))
  if (index.schema_version !== 'math-course-handout-index-v1') throw new Error('unsupported handout index')
  const fingerprint = JSON.stringify(index.books.map((book) => ({
    book: book.book,
    source: book.source_pdf_sha256,
    pages: book.pages.map((page) => [
      page.pdf_page, page.printed_page, page.page_role, page.ocr_text_sha256,
      page.page_image_sha256, page.heading_candidates, page.course_candidates,
    ]),
  })))
  const version = `handouts-v1-${sha256(fingerprint).slice(0, 16)}`
  const outputRoot = join(repoRoot, 'tmp', 'math-handout-import', version)
  await mkdir(outputRoot, { recursive: true })

  const objects = []
  const statements = []
  const compactIndex = {
    schema_version: index.schema_version,
    version,
    generated_at: index.generated_at,
    evidence_policy: {
      text_is_search_aid_only: true,
      visual_review_required: true,
      source_page_is_formula_and_diagram_authority: true,
    },
    books: [],
  }

  for (const book of index.books) {
    const sourceId = `course-handout-${book.book}-${book.source_pdf_sha256.slice(0, 12)}`
    const sourceTitle = book.book === 'upper' ? '高二数学精讲精练（上）' : '高二数学精讲精练（下）'
    const indexKey = `handouts/${version}/index.json`
    statements.push(`INSERT INTO handout_sources (source_id, title, source_sha256, page_count, index_r2_key, ocr_provider, imported_at) VALUES (${sqlString(sourceId)}, ${sqlString(sourceTitle)}, ${sqlString(book.source_pdf_sha256)}, ${sqlNumber(book.page_count)}, ${sqlString(indexKey)}, ${sqlString(book.ocr_provider)}, ${sqlString(new Date().toISOString())}) ON CONFLICT(source_id) DO UPDATE SET title = excluded.title, source_sha256 = excluded.source_sha256, page_count = excluded.page_count, index_r2_key = excluded.index_r2_key, ocr_provider = excluded.ocr_provider, imported_at = excluded.imported_at;`)
    const compactBook = { source_id: sourceId, title: sourceTitle, source_sha256: book.source_pdf_sha256, page_count: book.page_count, pages: [] }
    const packSize = 20
    for (let offset = 0; offset < book.pages.length; offset += packSize) {
      const pageSlice = book.pages.slice(offset, offset + packSize)
      const packNumber = Math.floor(offset / packSize) + 1
      const packKey = `handouts/${version}/${book.book}/pages-${String(packNumber).padStart(3, '0')}.json`
      const pack = { schema_version: 'math-course-handout-page-pack-v1', version, source_id: sourceId, pages: {} }
      for (const page of pageSlice) {
        const imagePath = resolve(indexRoot, page.page_image_path)
        const imageBytes = await readFile(imagePath)
        if (sha256(imageBytes) !== page.page_image_sha256) throw new Error(`page image hash mismatch: ${imagePath}`)
        pack.pages[`${sourceId}:${page.pdf_page}`] = { mimeType: 'image/jpeg', sha256: page.page_image_sha256, data: imageBytes.toString('base64') }
        statements.push(`DELETE FROM handout_course_links WHERE source_id = ${sqlString(sourceId)} AND pdf_page = ${sqlNumber(page.pdf_page)};`)
        statements.push(`INSERT INTO handout_pages (source_id, pdf_page, printed_page, page_role, headings_json, ocr_text, ocr_text_sha256, ocr_confidence, visual_status, page_pack_r2_key, page_image_sha256) VALUES (${sqlString(sourceId)}, ${sqlNumber(page.pdf_page)}, ${sqlNumber(page.printed_page)}, ${sqlString(page.page_role)}, ${sqlString(JSON.stringify(page.heading_candidates ?? []))}, ${sqlString(page.ocr_text)}, ${sqlString(page.ocr_text_sha256)}, ${sqlNumber(page.ocr_confidence)}, ${sqlString(page.visual_status)}, ${sqlString(packKey)}, ${sqlString(page.page_image_sha256)}) ON CONFLICT(source_id, pdf_page) DO UPDATE SET printed_page = excluded.printed_page, page_role = excluded.page_role, headings_json = excluded.headings_json, ocr_text = excluded.ocr_text, ocr_text_sha256 = excluded.ocr_text_sha256, ocr_confidence = excluded.ocr_confidence, visual_status = excluded.visual_status, page_pack_r2_key = excluded.page_pack_r2_key, page_image_sha256 = excluded.page_image_sha256;`)
        if (page.page_role === 'content') {
          for (const candidate of page.course_candidates ?? []) {
            statements.push(`INSERT OR IGNORE INTO handout_course_links (source_id, pdf_page, course_key, relationship, confidence) VALUES (${sqlString(sourceId)}, ${sqlNumber(page.pdf_page)}, ${sqlString(candidate.course_key)}, ${sqlString(candidate.match_type)}, 'candidate');`)
          }
        }
        compactBook.pages.push({
          pdf_page: page.pdf_page,
          printed_page: page.printed_page,
          page_role: page.page_role,
          headings: page.heading_candidates,
          course_candidates: page.course_candidates,
          ocr_text_sha256: page.ocr_text_sha256,
          page_image_sha256: page.page_image_sha256,
          visual_status: page.visual_status,
          page_pack_r2_key: packKey,
        })
      }
      const packPath = join(outputRoot, `${book.book}-pages-${String(packNumber).padStart(3, '0')}.json`)
      await writeFile(packPath, JSON.stringify(pack), 'utf8')
      objects.push({ key: packKey, path: packPath })
    }
    compactIndex.books.push(compactBook)
  }

  const compactIndexPath = join(outputRoot, 'index.json')
  await writeFile(compactIndexPath, JSON.stringify(compactIndex), 'utf8')
  objects.unshift({ key: `handouts/${version}/index.json`, path: compactIndexPath })
  const sqlPaths = []
  for (const [indexNumber, sql] of chunkStatements(statements).entries()) {
    const path = join(outputRoot, 'sql', `${String(indexNumber + 1).padStart(3, '0')}.sql`)
    await mkdir(dirname(path), { recursive: true })
    await writeFile(path, `${sql}\n`, 'utf8')
    sqlPaths.push(path)
  }
  const plan = {
    schema_version: 'math-course-handout-import-plan-v1',
    version,
    sources: index.books.length,
    pages: index.books.reduce((count, book) => count + book.pages.length, 0),
    candidateLinks: index.books.reduce((count, book) => count + book.pages.filter((page) => page.page_role === 'content').reduce((subtotal, page) => subtotal + (page.course_candidates?.length ?? 0), 0), 0),
    r2Objects: objects.length,
    sqlChunks: sqlPaths.length,
    objects,
    sqlPaths,
  }
  await writeFile(join(outputRoot, 'plan.json'), JSON.stringify(plan, null, 2), 'utf8')
  console.log(JSON.stringify({ ...plan, objects: undefined, sqlPaths: undefined }, null, 2))
  if (!remote) return

  const wrangler = process.platform === 'win32' ? 'npx.cmd' : 'npx'
  for (const object of objects) {
    await runWithRetry(wrangler, ['wrangler', 'r2', 'object', 'put', `${bucket}/${object.key}`, '--file', object.path, '--content-type', 'application/json', '--remote', '-y'], { cwd: cloudRoot })
  }
  for (const path of sqlPaths) {
    await runWithRetry(wrangler, ['wrangler', 'd1', 'execute', database, '--remote', '--file', path, '--yes'], { cwd: cloudRoot })
  }
  console.log(`handout import complete: ${version}`)
}

main().catch((error) => {
  console.error(error.stack ?? error)
  process.exitCode = 1
})
