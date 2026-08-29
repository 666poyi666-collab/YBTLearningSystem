#!/usr/bin/env node

/**
 * Build and import the complete 选择性必修1 library snapshot.
 *
 * The source of truth remains the repository. R2 receives a small number of
 * immutable versioned packs (section packets, transcript pack and image pack),
 * while D1 receives query indexes and the initial not-started learner state.
 * Re-running the same source version is idempotent and never deletes learner
 * events or replaces an existing learner state snapshot.
 */

import { createHash } from 'node:crypto'
import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { existsSync, readFileSync } from 'node:fs'
import { basename, dirname, join, resolve, win32 } from 'node:path'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const cloudRoot = resolve(scriptDir, '..')
const repoRoot = resolve(cloudRoot, '..', '..')
const dataRoot = join(repoRoot, 'data')
const importRoot = join(repoRoot, 'tmp', 'math-cloud-import')
const wranglerCli = join(cloudRoot, 'node_modules', 'wrangler', 'bin', 'wrangler.js')
const MAX_SQL_CHUNK_BYTES = 1_000_000

const argv = new Set(process.argv.slice(2))
const dryRun = argv.has('--dry-run') || !argv.has('--remote')
const remote = argv.has('--remote')
const bucket = 'math-learning-content'
const database = 'math-learning'

function json(path) {
  return readFile(path, 'utf8').then(JSON.parse)
}

function sha256(value) {
  return createHash('sha256').update(value).digest('hex')
}

function stableJson(value) {
  return JSON.stringify(value)
}

function sqlString(value) {
  if (value === null || value === undefined) return 'NULL'
  return `'${String(value).replaceAll("'", "''")}'`
}

function sqlJson(value) {
  return sqlString(stableJson(value))
}

function sqlNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'NULL'
  return String(Math.trunc(Number(value)))
}

function pathBase(value) {
  return basename(String(value ?? '').replaceAll('\\', '/')) || win32.basename(String(value ?? ''))
}

function normalizeLabel(value) {
  return String(value ?? '').replaceAll(' ', '').replaceAll('　', '')
}

function courseIdFromKey(courseKey, fallback) {
  const match = String(courseKey ?? '').match(/^\d+(?:\.\d+)+(?:\.[a-z])?/) 
  return match?.[0] ?? fallback ?? courseKey
}

function mimeType(fileName) {
  const ext = fileName.toLowerCase().split('.').pop()
  return ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg'
}

async function readCurrentCommit() {
  try {
    const output = await run('git', ['rev-parse', 'HEAD'], { cwd: repoRoot, capture: true })
    return output.trim()
  } catch {
    return 'working-tree'
  }
}

function run(command, args, options = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd ?? repoRoot,
      stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
      shell: false,
      windowsHide: true,
    })
    let stdout = ''
    let stderr = ''
    child.stdout?.on('data', (chunk) => { stdout += chunk.toString() })
    child.stderr?.on('data', (chunk) => { stderr += chunk.toString() })
    child.on('error', reject)
    child.on('close', (code) => {
      if (code === 0) return resolvePromise(options.capture ? stdout : '')
      reject(new Error(`${command} ${args.join(' ')} failed with ${code}\n${stderr}`))
    })
  })
}

async function runWithRetry(command, args, options = {}, attempts = 4) {
  let lastError
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await run(command, args, options)
    } catch (error) {
      lastError = error
      if (attempt === attempts) break
      const delayMs = 1000 * 2 ** (attempt - 1)
      console.warn(`retrying ${command} (${attempt}/${attempts - 1}) after ${delayMs}ms`)
      await new Promise((resolvePromise) => setTimeout(resolvePromise, delayMs))
    }
  }
  throw lastError
}

function wranglerArgs(args) {
  return [wranglerCli, ...args]
}

async function writeObject(path, value) {
  await mkdir(dirname(path), { recursive: true })
  await writeFile(path, `${JSON.stringify(value)}\n`, 'utf8')
}

function chunkStatements(statements, maxBytes = MAX_SQL_CHUNK_BYTES) {
  const chunks = []
  let current = []
  let currentBytes = 0
  for (const statement of statements) {
    const bytes = Buffer.byteLength(statement, 'utf8') + 2
    if (current.length && currentBytes + bytes > maxBytes) {
      chunks.push(current.join('\n'))
      current = []
      currentBytes = 0
    }
    current.push(statement)
    currentBytes += bytes
  }
  if (current.length) chunks.push(current.join('\n'))
  return chunks
}

function imageDirForChapter(chapter) {
  const directory = chapter === 1
    ? 'first_chapter_69'
    : chapter === 2
      ? 'second_chapter_109'
      : chapter === 3
        ? 'third_chapter_180'
        : chapter === 4
          ? 'chapter4_100'
          : 'chapter5_95'
  return join(dataRoot, 'ocr_live_current', directory, 'imgs')
}

async function buildImageIndex() {
  const index = new Map()
  for (const chapter of [1, 2, 3, 4, 5]) {
    const dir = imageDirForChapter(chapter)
    if (!existsSync(dir)) throw new Error(`missing image directory: ${dir}`)
    for (const file of await readdir(dir)) {
      const filePath = join(dir, file)
      index.set(`${chapter}:${file}`, { filePath, chapter, file })
    }
  }
  return index
}

async function main() {
  const auditPath = join(dataRoot, 'chatgpt_context', 'chapter12_complete_audit.json')
  const auditBytes = await readFile(auditPath)
  const audit = JSON.parse(auditBytes.toString('utf8'))
  const catalogPath = join(dataRoot, 'all_chapters_course_catalog.json')
  const catalogBytes = await readFile(catalogPath)
  const catalog = JSON.parse(catalogBytes.toString('utf8'))
  const catalogByKey = new Map((catalog.courses ?? []).map((course) => [course.course_key, course]))
  const libraryChapters = [1, 2, 3, 4, 5]
  const imageIndex = await buildImageIndex()
  const chapterManifests = new Map()
  const rawManifestBytes = []
  for (const chapter of libraryChapters) {
    const path = join(repoRoot, `chapter${chapter}_manifest.json`)
    const bytes = await readFile(path)
    rawManifestBytes.push(bytes)
    chapterManifests.set(chapter, JSON.parse(bytes.toString('utf8')))
  }
  const packetBindingBytes = []
  for (const chapter of libraryChapters) {
    for (const section of chapterManifests.get(chapter).sections ?? []) {
      const packetFolder = String(section.id).replaceAll('+', '_')
      for (const file of ['student_learning_items.json', 'student_packet.json', 'answer_sidecar.json']) {
        packetBindingBytes.push(await readFile(join(dataRoot, 'packets', packetFolder, file)))
      }
    }
  }
  const manifestSha = sha256(Buffer.concat([...rawManifestBytes, auditBytes, catalogBytes, ...packetBindingBytes]))
  const version = `v1-${manifestSha.slice(0, 16)}`
  const sourceVersionId = version
  const currentCommit = await readCurrentCommit()
  const outputRoot = join(importRoot, version)
  await rm(outputRoot, { recursive: true, force: true })
  await mkdir(outputRoot, { recursive: true })

  const imagePack = {}
  const sectionPacks = []
  const courses = new Map()
  const sections = []
  const chapters = []
  const items = []
  const links = []
  const answerSources = []

  async function registerCourse(courseKey, metadata = {}) {
    if (courses.has(courseKey)) return
    const catalogEntry = catalogByKey.get(courseKey)
    if (!catalogEntry) throw new Error(`course missing from catalog: ${courseKey}`)
    const transcriptFile = pathBase(catalogEntry.transcript_file ?? metadata.transcript_path)
    const transcriptPath = join(dataRoot, 'course_transcripts', transcriptFile)
    const transcriptBytes = await readFile(transcriptPath)
    const transcript = JSON.parse(transcriptBytes.toString('utf8'))
    const sentences = Array.isArray(transcript.sentences) ? transcript.sentences.filter((s) => Number.isFinite(Number(s.start)) && Number.isFinite(Number(s.end)) && typeof s.text === 'string') : []
    courses.set(courseKey, {
      courseKey,
      courseNumber: metadata.course_number ?? catalogEntry.course_id ?? courseIdFromKey(courseKey),
      title: metadata.title ?? catalogEntry.title ?? courseKey,
      durationMs: Math.round(Number(transcript.duration_s ?? catalogEntry.duration_s ?? 0) * 1000),
      hasTimeline: sentences.length > 0,
      sourceSha256: sha256(transcriptBytes),
      textSha256: catalogEntry.transcript_text_sha256 ?? null,
      fullText: transcript.full_text ?? '',
      sentences,
      provenance: 'repository transcript JSON; source video path omitted from cloud payload',
    })
  }

  function imageRefsFor(chapter, refs) {
    return (refs ?? []).map((ref) => {
      const file = pathBase(ref.path ?? ref.ref)
      const source = imageIndex.get(`${chapter}:${file}`)
      if (!source) throw new Error(`missing image asset for chapter ${chapter}: ${file}`)
      const bytes = requireBuffer(source.filePath)
      const imageKey = `${version}/images/chapter-${chapter}/${file}`
      if (!imagePack[imageKey]) {
        imagePack[imageKey] = {
          mimeType: mimeType(file),
          sha256: sha256(bytes),
          data: bytes.toString('base64'),
        }
      }
      return { ref: ref.ref ?? `imgs/${file}`, key: imageKey, sha256: imagePack[imageKey].sha256, mimeType: imagePack[imageKey].mimeType }
    })
  }

  // Image packs are small and this helper keeps the object-building loop
  // deterministic while the surrounding source files remain async.
  function requireBuffer(path) {
    return readFileSync(path)
  }

  for (const chapter of libraryChapters) {
    const manifest = chapterManifests.get(chapter)
    chapters.push({ chapterKey: String(chapter), title: manifest.target_identity?.chapter ?? `第${chapter}章`, sortOrder: chapter })
  }

  const librarySections = libraryChapters.flatMap((chapter) => {
    const manifest = chapterManifests.get(chapter)
    return (manifest.sections ?? []).map((section) => {
      // Course keys are authoritative here.  A single numbered lesson may
      // have multiple variants (for example a base and an advanced lesson),
      // so deduplicating by course_id can silently drop one referenced course.
      const courseKeys = [...new Set([
        ...(section.required_course_keys ?? []),
        ...(section.support_course_keys ?? []),
      ])]
      const courses = courseKeys.map((courseKey) => {
        const catalogEntry = catalog.courses.find((course) => course.course_key === courseKey)
        const courseId = catalogEntry?.course_id ?? courseIdFromKey(courseKey, courseKey)
        return {
          course_key: courseKey,
          course_number: courseId,
          title: catalogEntry?.title ?? courseKey,
          transcript_path: catalogEntry?.transcript_file ?? null,
        }
      })
      return {
        chapter,
        section: section.id,
        title: section.label,
        manifest_path: `chapter${chapter}_manifest.json`,
        packet_manifest_path: `data/packets/${String(section.id).replaceAll('+', '_')}/manifest.json`,
        courses,
      }
    })
  })

  for (const auditSection of librarySections) {
    const chapter = Number(auditSection.chapter)
    const manifest = chapterManifests.get(chapter)
    const manifestSection = manifest.sections.find((section) => section.id === auditSection.section)
    if (!manifestSection) throw new Error(`section ${auditSection.section} missing in chapter ${chapter} manifest`)
    const packetFolder = pathBase(dirname(auditSection.packet_manifest_path))
    const learning = await json(join(dataRoot, 'packets', packetFolder, 'student_learning_items.json'))
    const packet = await json(join(dataRoot, 'packets', packetFolder, 'student_packet.json'))
    const packetManifest = await json(join(dataRoot, 'packets', packetFolder, 'manifest.json'))
    const answerPath = join(dataRoot, 'packets', packetFolder, 'answer_sidecar.json')
    const answerPack = existsSync(answerPath) ? await json(answerPath) : { answers: [] }
    const cycleByLabel = new Map()
    const cycleByExample = new Map()
    for (const cycle of manifestSection.learning_cycles ?? []) {
      for (const number of cycle.example_numbers ?? []) cycleByExample.set(Number(number), cycle)
      for (const key of cycle.exercise_keys ?? []) cycleByLabel.set(normalizeLabel(key), cycle)
    }

    const sectionItems = []
    const addItem = (raw, kind, label, conceptKey, parentExampleNumber = null) => {
      const imageRefs = imageRefsFor(chapter, raw.image_refs)
      const sourceDocs = raw.source_docs ?? (raw.source_anchor?.ocr_doc !== undefined ? [raw.source_anchor.ocr_doc] : [])
      const item = {
        item_id: raw.item_id ?? raw.qid,
        section: auditSection.section,
        kind,
        label,
        example_number: raw.example_number ?? null,
        parent_example_number: parentExampleNumber ?? raw.parent_example_number ?? null,
        role: raw.role ?? 'exercise',
        role_ref: conceptKey ?? raw.role_ref ?? null,
        source_docs: sourceDocs,
        source_anchor: raw.source_anchor ? { ocr_doc: raw.source_anchor.ocr_doc ?? null, pdf_page: raw.source_anchor.pdf_page ?? null } : null,
        question_text: raw.question_text,
        image_refs: imageRefs,
        visual_status: raw.visual_status ?? 'READY_TEXT_ONLY',
        visual_evidence: raw.vision_sidecar ?? null,
        evidence: raw.evidence ?? [],
      }
      if (!item.item_id || !item.question_text) throw new Error(`incomplete item in ${auditSection.section}: ${label}`)
      sectionItems.push(item)
      const cycle = kind === 'direct_variant'
        ? cycleByExample.get(Number(parentExampleNumber))
        : kind === 'worked_example'
          ? cycleByExample.get(Number(raw.example_number))
          : cycleByLabel.get(normalizeLabel(label))
      if (cycle) {
        for (const key of cycle.course_keys ?? []) links.push({ itemId: item.item_id, courseKey: key, relationship: 'cycle_course' })
        for (const key of cycle.prerequisite_course_keys ?? []) links.push({ itemId: item.item_id, courseKey: key, relationship: 'prerequisite_course' })
        for (const key of cycle.optional_course_keys ?? []) links.push({ itemId: item.item_id, courseKey: key, relationship: 'optional_course' })
      }
      return item
    }

    const examplesByNumber = new Map()
    for (const raw of learning.worked_examples ?? []) {
      const item = addItem(raw, 'worked_example', normalizeLabel(raw.label), raw.role_ref)
      examplesByNumber.set(Number(raw.example_number), item)
    }
    for (const raw of learning.direct_variants ?? []) {
      addItem(raw, 'direct_variant', normalizeLabel(raw.label), examplesByNumber.get(Number(raw.parent_example_number))?.role_ref ?? null, raw.parent_example_number)
    }
    for (const raw of packet.questions ?? []) {
      const label = `${raw.group}${raw.number}`
      addItem(raw, 'exercise', label, cycleByLabel.get(label)?.knowledge_refs?.[0] ?? null)
    }

    for (const answer of answerPack.answers ?? []) {
      const label = `${answer.group ?? ''}${answer.number ?? ''}`
      const item = sectionItems.find((candidate) => candidate.label === label)
      const answerText = typeof answer.answer_text === 'string' ? answer.answer_text.trim() : ''
      if (item && answerText) {
        answerSources.push({
          itemId: item.item_id,
          sourceKind: 'original_answer_book',
          sourceVersionId,
          answerText,
          sourceSha256: sha256(Buffer.from(answerText, 'utf8')),
        })
      }
    }

    sectionItems.sort((a, b) => {
      const aDoc = Number(a.source_docs?.[0] ?? a.source_anchor?.ocr_doc ?? 0)
      const bDoc = Number(b.source_docs?.[0] ?? b.source_anchor?.ocr_doc ?? 0)
      return aDoc - bDoc || a.label.localeCompare(b.label, 'zh-CN')
    })
    const contentKey = `${version}/sections/${auditSection.section}.json`
    const sectionPack = {
      schema_version: 'ybt-cloud-section-pack-v1',
      source_version: sourceVersionId,
      chapter,
      section: auditSection.section,
      image_pack_key: `${version}/images.json`,
      transcript_pack_key: `${version}/transcripts.json`,
      packet_manifest: packetManifest,
      manifest: manifestSection,
      items: sectionItems,
    }
    const sectionPackPath = join(outputRoot, 'sections', `${auditSection.section}.json`)
    await writeObject(sectionPackPath, sectionPack)
    sectionPacks.push({ key: contentKey, path: sectionPackPath })
    sections.push({ sectionKey: auditSection.section, chapterKey: String(chapter), title: manifestSection.label, manifestR2Key: contentKey, sortOrder: sections.filter((s) => s.chapterKey === String(chapter)).length + 1 })
    for (const item of sectionItems) {
      items.push({ itemId: item.item_id, sectionKey: auditSection.section, label: item.label, itemType: item.kind, conceptKey: item.role_ref, contentR2Key: contentKey, sourceSha256: sha256(stableJson(item)), sortOrder: sectionItems.indexOf(item) + 1 })
    }
    for (const course of auditSection.courses ?? []) {
      await registerCourse(course.course_key, course)
    }
  }

  for (const catalogEntry of catalog.courses ?? []) await registerCourse(catalogEntry.course_key, catalogEntry)

  const transcriptPack = {
    schema_version: 'ybt-cloud-transcript-pack-v1',
    source_version: sourceVersionId,
    courses: Object.fromEntries([...courses.entries()]),
  }
  const transcriptPackPath = join(outputRoot, 'transcripts.json')
  await writeObject(transcriptPackPath, transcriptPack)
  const imagePackPath = join(outputRoot, 'images.json')
  await writeObject(imagePackPath, { schema_version: 'ybt-cloud-image-pack-v1', source_version: sourceVersionId, images: imagePack })

  const transcriptKey = `${version}/transcripts.json`
  const imageKey = `${version}/images.json`
  const courseRows = [...courses.values()].map((course) => ({ ...course, transcriptR2Key: transcriptKey }))
  const statements = []
  statements.push(`INSERT OR REPLACE INTO source_versions (id, git_commit, manifest_sha256, imported_at) VALUES (${sqlString(sourceVersionId)}, ${sqlString(currentCommit)}, ${sqlString(manifestSha)}, ${sqlString(new Date().toISOString())});`)
  for (const chapter of chapters) statements.push(`INSERT OR REPLACE INTO chapters (chapter_key, title, source_version_id, sort_order) VALUES (${sqlString(chapter.chapterKey)}, ${sqlString(chapter.title)}, ${sqlString(sourceVersionId)}, ${sqlNumber(chapter.sortOrder)});`)
  for (const section of sections) statements.push(`INSERT OR REPLACE INTO sections (section_key, chapter_key, title, manifest_r2_key, sort_order) VALUES (${sqlString(section.sectionKey)}, ${sqlString(section.chapterKey)}, ${sqlString(section.title)}, ${sqlString(section.manifestR2Key)}, ${sqlNumber(section.sortOrder)});`)
  for (const course of courseRows) statements.push(`INSERT OR REPLACE INTO courses (course_key, title, transcript_r2_key, transcript_sha256, duration_ms, has_timeline) VALUES (${sqlString(course.courseKey)}, ${sqlString(`${course.courseNumber} ${course.title}`.trim())}, ${sqlString(course.transcriptR2Key)}, ${sqlString(course.sourceSha256)}, ${sqlNumber(course.durationMs)}, ${course.hasTimeline ? 1 : 0});`)
  for (const item of items) statements.push(`INSERT OR REPLACE INTO items (item_id, section_key, label, item_type, concept_key, content_r2_key, source_sha256, sort_order) VALUES (${sqlString(item.itemId)}, ${sqlString(item.sectionKey)}, ${sqlString(item.label)}, ${sqlString(item.itemType)}, ${sqlString(item.conceptKey)}, ${sqlString(item.contentR2Key)}, ${sqlString(item.sourceSha256)}, ${sqlNumber(item.sortOrder)});`)
  for (const answer of answerSources) statements.push(`INSERT OR REPLACE INTO answer_sources (item_id, source_kind, source_version_id, answer_text, source_sha256) VALUES (${sqlString(answer.itemId)}, ${sqlString(answer.sourceKind)}, ${sqlString(answer.sourceVersionId)}, ${sqlString(answer.answerText)}, ${sqlString(answer.sourceSha256)});`)
  const relationshipPriority = { optional_course: 1, prerequisite_course: 2, cycle_course: 3 }
  const uniqueLinks = new Map()
  for (const link of links) {
    const key = `${link.itemId}:${link.courseKey}`
    const previous = uniqueLinks.get(key)
    if (!previous || relationshipPriority[link.relationship] > relationshipPriority[previous.relationship]) uniqueLinks.set(key, link)
  }
  for (const item of items) statements.push(`DELETE FROM item_course_links WHERE item_id = ${sqlString(item.itemId)};`)
  for (const link of uniqueLinks.values()) statements.push(`INSERT OR IGNORE INTO item_course_links (item_id, course_key, relationship) VALUES (${sqlString(link.itemId)}, ${sqlString(link.courseKey)}, ${sqlString(link.relationship)});`)
  const chunks = []
  for (const course of courseRows) {
    const transcript = courses.get(course.courseKey)
    const sentenceList = transcript.sentences
    if (!sentenceList.length) {
      const text = transcript.fullText || ''
      for (let offset = 0, chunkIndex = 0; offset < text.length; offset += 7000, chunkIndex += 1) {
        chunks.push({ courseKey: course.courseKey, chunkIndex, startMs: null, endMs: null, text: text.slice(offset, offset + 7000) })
      }
      if (!text) chunks.push({ courseKey: course.courseKey, chunkIndex: 0, startMs: null, endMs: null, text: '' })
      continue
    }
    let current = []
    let firstStart = null
    let lastEnd = null
    let chunkIndex = 0
    const flush = () => {
      if (!current.length) return
      chunks.push({ courseKey: course.courseKey, chunkIndex, startMs: firstStart, endMs: lastEnd, text: current.join(' ') })
      chunkIndex += 1
      current = []
      firstStart = null
      lastEnd = null
    }
    for (const sentence of sentenceList) {
      const start = Number(sentence.start)
      const end = Number(sentence.end)
      if (firstStart === null) firstStart = start
      current.push(sentence.text.trim())
      lastEnd = end
      if (end - firstStart >= 12000 || current.join(' ').length >= 1800) flush()
    }
    flush()
  }
  for (const course of courseRows) statements.push(`DELETE FROM transcript_chunks WHERE course_key = ${sqlString(course.courseKey)};`)
  for (const chunk of chunks) statements.push(`INSERT OR REPLACE INTO transcript_chunks (course_key, chunk_index, start_ms, end_ms, text, topic, method_tags) VALUES (${sqlString(chunk.courseKey)}, ${sqlNumber(chunk.chunkIndex)}, ${sqlNumber(chunk.startMs)}, ${sqlNumber(chunk.endMs)}, ${sqlString(chunk.text)}, NULL, '[]');`)

  const desiredItemIds = items.map((item) => sqlString(item.itemId)).join(',')
  const managedSections = sections.map((section) => sqlString(section.sectionKey)).join(',')
  if (desiredItemIds && managedSections) {
    const staleItemFilter = `section_key IN (${managedSections}) AND item_id NOT IN (${desiredItemIds}) AND NOT EXISTS (SELECT 1 FROM answer_sources a WHERE a.item_id = items.item_id)`
    statements.push(`DELETE FROM item_course_links WHERE item_id IN (SELECT item_id FROM items WHERE ${staleItemFilter});`)
    statements.push(`DELETE FROM items WHERE ${staleItemFilter};`)
  }

  const initialStates = []
  for (const chapter of libraryChapters) {
    const chapterSections = sections.filter((section) => section.chapterKey === String(chapter))
    initialStates.push({ key: `chapter:${chapter}`, value: { chapter, status: 'not_started', source: 'repository_snapshot', sectionCount: chapterSections.length } })
    for (const section of chapterSections) initialStates.push({ key: `section:${section.sectionKey}`, value: { chapter, section: section.sectionKey, status: 'not_started', source: 'repository_snapshot' } })
  }
  initialStates.push({ key: 'current_task', value: { chapter: 1, section: '1.1', cycle: '1.1-cycle-1', status: 'not_started', source: 'repository_snapshot' } })
  for (const state of initialStates) statements.push(`INSERT OR IGNORE INTO learner_state (user_id, state_key, version, value_json, updated_at) VALUES ('poyi-owner', ${sqlString(state.key)}, 0, ${sqlJson(state.value)}, ${sqlString(new Date().toISOString())});`)

  const sqlChunks = chunkStatements(statements)
  const sqlPaths = []
  for (let index = 0; index < sqlChunks.length; index += 1) {
    const path = join(outputRoot, 'sql', `${String(index + 1).padStart(3, '0')}.sql`)
    await mkdir(dirname(path), { recursive: true })
    await writeFile(path, `${sqlChunks[index]}\n`, 'utf8')
    sqlPaths.push(path)
  }
  const plan = {
    schema_version: 'ybt-cloud-import-plan-v1', sourceVersionId, manifestSha, currentCommit,
    library: '选择性必修1', chapters: chapters.length, sections: sections.length, items: items.length, courses: courses.size,
    links: uniqueLinks.size, transcriptChunks: chunks.length, imageObjects: Object.keys(imagePack).length,
    r2: [{ key: imageKey, path: imagePackPath }, { key: transcriptKey, path: transcriptPackPath }, ...sectionPacks],
    sql: sqlPaths,
  }
  await writeObject(join(outputRoot, 'plan.json'), plan)
  console.log(JSON.stringify(plan, null, 2))
  if (dryRun) {
    console.log('dry-run: generated packs and SQL only; pass --remote to import into Cloudflare')
    return
  }
  if (!remote) throw new Error('remote import requires --remote')
  for (const object of plan.r2) {
    await runWithRetry(process.execPath, wranglerArgs(['r2', 'object', 'put', `${bucket}/${object.key}`, '--file', object.path, '--content-type', 'application/json', '--remote', '-y']), { cwd: cloudRoot })
  }
  for (const path of sqlPaths) {
    await runWithRetry(process.execPath, wranglerArgs(['d1', 'execute', database, '--remote', '--file', path, '--yes']), { cwd: cloudRoot })
  }
  console.log(`import complete: ${sourceVersionId}`)
}

main().catch((error) => {
  console.error(error.stack ?? error)
  process.exitCode = 1
})
