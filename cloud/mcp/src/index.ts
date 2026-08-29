import { McpServer } from '@modelcontextprotocol/server'
import { createMcpHandler } from 'agents/mcp/server'
import { z } from 'zod'

interface OAuthIntrospection {
  active?: boolean
  iss?: string
  aud?: string | string[]
  resource?: string
  scope?: string
  sub?: string
  client_id?: string
  exp?: number
}

interface Env {
  DB: D1Database
  CONTENT: R2Bucket
  OAUTH_ISSUER?: string
  OAUTH_AUDIENCE?: string
  OAUTH_INTROSPECTION_URL?: string
  OAUTH_RS_CLIENT_ID?: string
  OAUTH_RS_CLIENT_SECRET?: string
  OAUTH_HTTP?: Fetcher
}

type Scope = 'math:read' | 'math:write'
type JsonRecord = Record<string, unknown>
type ImageContent = { type: 'image'; data: string; mimeType: string }
type HandwritingStep = {
  line: number
  status: 'correct' | 'first_wrong' | 'uncertain' | 'downstream_contaminated'
  explanation: string
  bbox?: [number, number, number, number]
  latex?: string
  label?: string
}

const READ_SCOPE: Scope = 'math:read'
const WRITE_SCOPE: Scope = 'math:write'
const PROJECT = { name: 'poyi-math-learning', version: '0.1.0' }
const USER_ID = 'poyi-owner'

function result(payload: unknown, extraContent: ImageContent[] = []) {
  return {
    content: [{ type: 'text' as const, text: JSON.stringify(payload, null, 2) }, ...extraContent],
    structuredContent: payload as JsonRecord,
  }
}

function failure(code: string, message: string, details: JsonRecord = {}) {
  const payload = { ok: false, error: { code, message, details } }
  return {
    ...result(payload),
    isError: true,
  }
}

function exactEndpoint(value: string | undefined, requiredPath?: string): string | null {
  if (!value) return null
  try {
    const url = new URL(value)
    const loopback = url.hostname === 'localhost' || url.hostname === '127.0.0.1'
    if (url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback)) return null
    if (url.username || url.password || url.search || url.hash) return null
    if (requiredPath && url.pathname !== requiredPath) return null
    return url.href.replace(/\/$/, '')
  } catch {
    return null
  }
}

function oauthConfig(env: Env) {
  const issuer = exactEndpoint(env.OAUTH_ISSUER)
  const audience = exactEndpoint(env.OAUTH_AUDIENCE, '/mcp')
  const introspection = exactEndpoint(env.OAUTH_INTROSPECTION_URL, '/introspect')
  const clientId = env.OAUTH_RS_CLIENT_ID?.trim()
  const clientSecret = env.OAUTH_RS_CLIENT_SECRET
  if (!issuer || !audience || !introspection || !clientId || !clientSecret || clientSecret.length < 32) return null
  return { issuer, audience, introspection, clientId, clientSecret }
}

function bearer(request: Request): string | null {
  const match = /^Bearer ([A-Za-z0-9._~-]+)$/.exec(request.headers.get('authorization') ?? '')
  return match?.[1] ?? null
}

function hasAudience(value: unknown, expected: string): boolean {
  return value === expected || (Array.isArray(value) && value.length === 1 && value[0] === expected)
}

async function authorize(request: Request, env: Env, requiredScope: Scope) {
  const config = oauthConfig(env)
  const token = bearer(request)
  if (!config) return { ok: false as const, status: 503, code: 'oauth_not_configured' }
  if (!token) return { ok: false as const, status: 401, code: 'missing_token' }
  const body = new URLSearchParams({ token, token_type_hint: 'access_token' })
  let response: Response
  try {
    const authorization = `Basic ${btoa(`${config.clientId}:${config.clientSecret}`)}`
    const call = env.OAUTH_HTTP
      ? (input: RequestInfo | URL, init?: RequestInit) => env.OAUTH_HTTP!.fetch(input, init)
      : fetch
    response = await call(config.introspection, {
      method: 'POST',
      headers: {
        accept: 'application/json',
        authorization,
        'content-type': 'application/x-www-form-urlencoded',
      },
      body,
      redirect: 'manual',
    })
  } catch {
    return { ok: false as const, status: 503, code: 'oauth_unavailable' }
  }
  if (!response.ok) return { ok: false as const, status: 503, code: 'oauth_unavailable' }
  const value = await response.json<OAuthIntrospection>()
  const scopes = typeof value.scope === 'string' ? [...new Set(value.scope.split(/\s+/).filter(Boolean))] : []
  const valid = value.active === true
    && value.iss === config.issuer
    && value.resource === config.audience
    && hasAudience(value.aud, config.audience)
    && value.sub === USER_ID
    && typeof value.client_id === 'string'
    && typeof value.exp === 'number'
    && value.exp > Math.floor(Date.now() / 1000)
  if (!valid) return { ok: false as const, status: 401, code: 'invalid_token' }
  if (!scopes.includes(requiredScope)) return { ok: false as const, status: 403, code: 'insufficient_scope' }
  return { ok: true as const, scopes }
}

function isWriteToolName(name: string): boolean {
  return name.startsWith('math_record_') || name.startsWith('math_mark_')
    || name.startsWith('math_sync_') || name.startsWith('math_defer_')
}

async function requiredScope(request: Request): Promise<Scope> {
  const headerName = request.headers.get('mcp-name')
  if (headerName) return isWriteToolName(headerName) ? WRITE_SCOPE : READ_SCOPE
  try {
    const rpc = await request.clone().json<{ method?: string; params?: { name?: string } }>()
    const name = rpc.params?.name ?? ''
    return rpc.method === 'tools/call' && isWriteToolName(name)
      ? WRITE_SCOPE
      : READ_SCOPE
  } catch {
    return READ_SCOPE
  }
}

function parseJson(value: string | null): unknown {
  if (!value) return null
  try { return JSON.parse(value) } catch { return null }
}

function courseSortKey(value: string): string {
  const match = value.match(/(?:^|\s)(\d+(?:\.\d+){1,5})(?:\.([a-z]))?(?:\s|$)/i)
  if (!match) return `9999.${value}`
  const suffix = match[2] ? String(match[2].toLowerCase().charCodeAt(0) - 96).padStart(3, '0') : '000'
  const segment = value.includes('（上）') || value.includes('(上)') || value.includes('（基础）') || value.includes('(基础)') ? '001'
    : value.includes('（中）') || value.includes('(中)') || value.includes('（提高）') || value.includes('(提高)') ? '002'
      : value.includes('（下）') || value.includes('(下)') || value.includes('（进阶）') || value.includes('(进阶)') ? '003' : '000'
  return `${match[1].split('.').map((part) => part.padStart(4, '0')).join('.')}.${suffix}.${segment}.${value}`
}

function handwritingAnnotationSpec(
  imageEvidenceId: string,
  steps: HandwritingStep[],
  uncertainties: string[],
  clarificationRequest?: string,
) {
  return {
    schemaVersion: 'math-handwriting-annotation-v1',
    renderMode: 'transparent_svg_overlay',
    imageEvidenceId,
    sourceImageMustRemainUnchanged: true,
    fill: 'none',
    formulaRenderer: 'LaTeX/MathJax',
    uncertainties,
    clarificationRequest: clarificationRequest ?? null,
    userDisclosureRequired: uncertainties.length > 0,
    overlays: steps.filter((step) => step.bbox).map((step) => ({
      line: step.line,
      status: step.status,
      bbox: step.bbox,
      label: step.label ?? null,
      explanation: step.explanation,
      latex: step.latex ?? null,
    })),
    verification: ['source image hash matches imageEvidenceId', 'first_wrong line is unique', 'overlay boxes stay inside the source image and do not use fill', 'transcription and step line numbers match exactly', 'downstream lines are not re-attributed as new root errors', 'all low-confidence observations are disclosed to the user'],
  }
}

async function readContentJson(env: Env, key: string): Promise<JsonRecord | null> {
  const object = await env.CONTENT.get(key)
  if (!object) return null
  try {
    const value: unknown = JSON.parse(await object.text())
    return value && typeof value === 'object' && !Array.isArray(value) ? value as JsonRecord : null
  } catch {
    return null
  }
}

function recordArray(value: unknown): JsonRecord[] {
  return Array.isArray(value) ? value.filter((item): item is JsonRecord => Boolean(item && typeof item === 'object' && !Array.isArray(item))) : []
}

async function itemFromContent(env: Env, row: JsonRecord): Promise<{ item: JsonRecord; pack: JsonRecord } | null> {
  const key = typeof row.content_r2_key === 'string' ? row.content_r2_key : ''
  if (!key) return null
  const pack = await readContentJson(env, key)
  if (!pack) return null
  const itemId = String(row.item_id ?? '')
  const item = recordArray(pack.items).find((candidate) => String(candidate.item_id ?? '') === itemId)
  return item ? { item, pack } : null
}

async function itemImageContent(env: Env, pack: JsonRecord, item: JsonRecord): Promise<ImageContent[]> {
  const imagePackKey = typeof pack.image_pack_key === 'string' ? pack.image_pack_key : ''
  if (!imagePackKey) return []
  const imagePack = await readContentJson(env, imagePackKey)
  if (!imagePack || !imagePack.images || typeof imagePack.images !== 'object') return []
  const images = imagePack.images as JsonRecord
  const resultBlocks: ImageContent[] = []
  for (const ref of recordArray(item.image_refs)) {
    const key = typeof ref.key === 'string' ? ref.key : ''
    const asset = key && images[key] && typeof images[key] === 'object' ? images[key] as JsonRecord : null
    if (!asset || typeof asset.data !== 'string' || typeof asset.mimeType !== 'string') continue
    resultBlocks.push({ type: 'image', data: asset.data, mimeType: asset.mimeType })
  }
  return resultBlocks
}

async function handoutPageImageContent(env: Env, row: JsonRecord): Promise<ImageContent[]> {
  const key = typeof row.page_pack_r2_key === 'string' ? row.page_pack_r2_key : ''
  if (!key) return []
  const pack = await readContentJson(env, key)
  if (!pack || !pack.pages || typeof pack.pages !== 'object') return []
  const pages = pack.pages as JsonRecord
  const assetKey = `${row.source_id}:${row.pdf_page}`
  const asset = pages[assetKey] && typeof pages[assetKey] === 'object' ? pages[assetKey] as JsonRecord : null
  if (!asset || typeof asset.data !== 'string' || typeof asset.mimeType !== 'string') return []
  return [{ type: 'image', data: asset.data, mimeType: asset.mimeType }]
}

async function practicePageImageContent(env: Env, row: JsonRecord): Promise<ImageContent[]> {
  const key = typeof row.page_pack_r2_key === 'string' ? row.page_pack_r2_key : ''
  if (!key) return []
  const pack = await readContentJson(env, key)
  if (!pack || !pack.pages || typeof pack.pages !== 'object') return []
  const pages = pack.pages as JsonRecord
  const assetKey = `${row.source_id}:${row.pdf_page}`
  const asset = pages[assetKey] && typeof pages[assetKey] === 'object' ? pages[assetKey] as JsonRecord : null
  if (!asset || typeof asset.data !== 'string' || typeof asset.mimeType !== 'string') return []
  return [{ type: 'image', data: asset.data, mimeType: asset.mimeType }]
}

async function systemStatus(env: Env) {
  const row = await env.DB.prepare(`
    SELECT
      (SELECT COUNT(*) FROM chapters) AS chapters,
      (SELECT COUNT(*) FROM sections) AS sections,
      (SELECT COUNT(*) FROM items) AS items,
      (SELECT COUNT(*) FROM courses) AS courses,
      (SELECT COUNT(*) FROM transcript_chunks) AS transcript_chunks,
      (SELECT COUNT(*) FROM learning_events WHERE user_id = ?) AS learning_events,
      (SELECT COUNT(*) FROM learner_diagnostics WHERE user_id = ?) AS learner_diagnostics,
      (SELECT COUNT(*) FROM type_classifications WHERE user_id = ?) AS type_classifications,
      (SELECT COUNT(*) FROM handout_sources) AS handout_sources,
      (SELECT COUNT(*) FROM handout_pages) AS handout_pages,
      (SELECT COUNT(*) FROM practice_sources) AS practice_sources,
      (SELECT COUNT(*) FROM practice_items) AS practice_items,
      (SELECT COUNT(*) FROM practice_attempts WHERE user_id = ?) AS practice_attempts,
      (SELECT COUNT(*) FROM handwriting_analyses WHERE user_id = ?) AS handwriting_analyses
  `).bind(USER_ID, USER_ID, USER_ID, USER_ID, USER_ID).first<Record<string, number | string>>()
  const source = await env.DB.prepare(`
    SELECT id, git_commit, manifest_sha256, imported_at
    FROM source_versions ORDER BY imported_at DESC LIMIT 1
  `).first<Record<string, string>>()
  return {
    ok: true,
    service: 'math-learning-mcp',
    protocol: '2026-07-28',
    source: source ?? null,
    counts: Object.fromEntries(Object.entries(row ?? {}).map(([key, value]) => [key, Number(value)])),
  }
}

async function learningContext(env: Env, itemId: string) {
  const item = await env.DB.prepare(`
    SELECT i.item_id, i.label, i.item_type, i.concept_key, i.content_r2_key,
           i.source_sha256, s.section_key, s.title AS section_title,
           c.chapter_key, c.title AS chapter_title
    FROM items i
    JOIN sections s ON s.section_key = i.section_key
    JOIN chapters c ON c.chapter_key = s.chapter_key
    WHERE i.item_id = ?
  `).bind(itemId).first<JsonRecord>()
  if (!item) return null
  const courses = await env.DB.prepare(`
    SELECT c.course_key, c.title, c.duration_ms, c.has_timeline, l.relationship
    FROM item_course_links l JOIN courses c ON c.course_key = l.course_key
    WHERE l.item_id = ? ORDER BY c.course_key
  `).bind(itemId).all<JsonRecord>()
  const state = await env.DB.prepare(`
    SELECT state_key, version, value_json, updated_at FROM learner_state
    WHERE user_id = ? AND state_key IN (?, ?)
  `).bind(USER_ID, `item:${itemId}`, 'current_task').all<Record<string, string | number>>()
  return {
    item,
    courses: courses.results,
    learnerState: state.results.map((entry) => ({ ...entry, value: parseJson(String(entry.value_json)) })),
  }
}

async function recordLearningEvent(
  env: Env,
  requestId: string,
  eventType: string,
  subjectType: string,
  subjectId: string,
  payload: JsonRecord,
  evidenceHash?: string,
  baseVersion?: number,
) {
  const payloadJson = JSON.stringify(payload)
  const eventId = crypto.randomUUID()
  const createdAt = new Date().toISOString()
  await env.DB.prepare(`
    INSERT INTO learning_events (
      event_id, request_id, user_id, event_type, subject_type, subject_id,
      payload_json, evidence_hash, base_version, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(request_id) DO NOTHING
  `).bind(
    eventId, requestId, USER_ID, eventType, subjectType, subjectId,
    payloadJson, evidenceHash ?? null, baseVersion ?? null, createdAt,
  ).run()
  const stored = await env.DB.prepare(`
    SELECT event_id, event_type, subject_type, subject_id, payload_json,
           evidence_hash, base_version, created_at
    FROM learning_events WHERE request_id = ? AND user_id = ?
  `).bind(requestId, USER_ID).first<Record<string, string | number | null>>()
  if (!stored) throw new Error('event_not_persisted')
  if (
    stored.event_type !== eventType || stored.subject_type !== subjectType
    || stored.subject_id !== subjectId || stored.payload_json !== payloadJson
  ) throw new Error('idempotency_conflict')
  const replayed = stored.event_id !== eventId
  const projection = eventType === 'progress_snapshot_synced'
    ? await projectProgressSnapshot(env, requestId, payload, baseVersion, createdAt)
    : await projectEventState(env, requestId, eventType, subjectType, subjectId, payload, baseVersion, createdAt)
  return {
    ok: true,
    eventId: stored.event_id,
    requestId,
    replayed,
    createdAt: stored.created_at,
    projection,
  }
}

async function upsertLearnerState(
  env: Env,
  stateKey: string,
  value: JsonRecord,
  sourceRequestId: string,
  updatedAt: string,
  expectedVersion?: number,
) {
  const existing = await env.DB.prepare(`SELECT version, value_json FROM learner_state WHERE user_id = ? AND state_key = ?`)
    .bind(USER_ID, stateKey).first<Record<string, string | number>>()
  const currentVersion = Number(existing?.version ?? 0)
  const currentValue = parseJson(existing ? String(existing.value_json) : null)
  if (currentValue && typeof currentValue === 'object' && !Array.isArray(currentValue)
      && (currentValue as JsonRecord).sourceRequestId === sourceRequestId) {
    return { stateKey, version: currentVersion, replayed: true }
  }
  if (expectedVersion !== undefined && currentVersion !== expectedVersion) throw new Error('version_conflict')
  const nextVersion = currentVersion + 1
  const nextValue = JSON.stringify({ ...value, sourceRequestId })
  if (existing) {
    const update = await env.DB.prepare(`
      UPDATE learner_state SET version = ?, value_json = ?, updated_at = ?
      WHERE user_id = ? AND state_key = ? AND version = ?
    `).bind(nextVersion, nextValue, updatedAt, USER_ID, stateKey, currentVersion).run()
    if (Number(update.meta.changes ?? 0) !== 1) throw new Error('version_conflict')
  } else {
    const insert = await env.DB.prepare(`
      INSERT INTO learner_state (user_id, state_key, version, value_json, updated_at)
      VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id, state_key) DO NOTHING
    `).bind(USER_ID, stateKey, nextVersion, nextValue, updatedAt).run()
    if (Number(insert.meta.changes ?? 0) !== 1) throw new Error('version_conflict')
  }
  return { stateKey, version: nextVersion, replayed: false }
}

async function projectEventState(
  env: Env,
  requestId: string,
  eventType: string,
  subjectType: string,
  subjectId: string,
  payload: JsonRecord,
  baseVersion: number | undefined,
  updatedAt: string,
) {
  const stateKey = `${subjectType}:${subjectId}`
  const value = {
    ...payload,
    status: eventType,
    subjectType,
    subjectId,
    source: 'cloud_mcp_event_projection',
  }
  return upsertLearnerState(env, stateKey, value, requestId, updatedAt, baseVersion)
}

async function projectProgressSnapshot(
  env: Env,
  requestId: string,
  payload: JsonRecord,
  baseVersion: number | undefined,
  updatedAt: string,
) {
  const projections: JsonRecord[] = []
  const currentTask = payload.currentTask && typeof payload.currentTask === 'object' && !Array.isArray(payload.currentTask)
    ? payload.currentTask as JsonRecord
    : {}
  const chapterKey = String(payload.chapterKey ?? currentTask.chapterKey ?? '')
  const sectionKey = String(payload.sectionKey ?? currentTask.sectionKey ?? '')
  const currentTaskValue = {
    chapter: chapterKey || null,
    section: sectionKey || null,
    ...currentTask,
    source: 'cloud_mcp_progress_snapshot',
  }
  projections.push(await upsertLearnerState(env, 'current_task', currentTaskValue, requestId, updatedAt, baseVersion))

  for (const cycle of recordArray(payload.completedCycles)) {
    const cycleId = String(cycle.cycleId ?? cycle.cycle ?? '')
    if (!cycleId) continue
    projections.push(await upsertLearnerState(env, `cycle:${cycleId}`, {
      ...cycle,
      chapter: chapterKey || null,
      section: sectionKey || null,
      status: 'completed',
      source: 'cloud_mcp_progress_snapshot',
    }, requestId, updatedAt))
  }
  for (const course of recordArray(payload.completedCourses)) {
    const courseKey = String(course.courseKey ?? '')
    if (!courseKey) continue
    projections.push(await upsertLearnerState(env, `course:${courseKey}`, {
      ...course,
      status: 'course_listened',
      source: 'cloud_mcp_progress_snapshot',
    }, requestId, updatedAt))
  }
  if (sectionKey) {
    projections.push(await upsertLearnerState(env, `section:${sectionKey}`, {
      chapter: chapterKey || null,
      section: sectionKey,
      status: 'in_progress',
      completedCycleCount: recordArray(payload.completedCycles).length,
      currentCycle: currentTask.cycle ?? null,
      source: 'cloud_mcp_progress_snapshot',
    }, requestId, updatedAt))
  }
  return projections
}

async function learnerProfile(env: Env) {
  const diagnostics = await env.DB.prepare(`SELECT diagnostic_id, item_id, section_key, error_type, error_direction, evidence_text, user_correction, final_status, created_at FROM learner_diagnostics WHERE user_id = ? ORDER BY created_at DESC LIMIT 200`).bind(USER_ID).all<JsonRecord>()
  const memories = await env.DB.prepare(`SELECT memory_id, item_id, section_key, title, content, reason, priority, user_requested, status, created_at FROM memory_items WHERE user_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 200`).bind(USER_ID).all<JsonRecord>()
  const classifications = await env.DB.prepare(`SELECT classification_id, item_id, section_key, cluster_title, basis, confidence, created_at FROM type_classifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 200`).bind(USER_ID).all<JsonRecord>()
  return { ok: true, diagnostics: diagnostics.results, memories: memories.results, typeClassifications: classifications.results }
}

async function wrongQuestionExport(env: Env, sectionKey: string, format: string) {
  const generatedAt = new Date().toISOString()
  const rows = await env.DB.prepare(`
    SELECT d.item_id, d.section_key, d.error_type, d.error_direction,
           d.evidence_text, d.user_correction, d.final_status, d.created_at,
           i.label, i.item_type
    FROM learner_diagnostics d LEFT JOIN items i ON i.item_id = d.item_id
    WHERE d.user_id = ? AND (? = '' OR d.section_key = ?)
    ORDER BY d.created_at
  `).bind(USER_ID, sectionKey, sectionKey).all<JsonRecord>()
  const memories = await env.DB.prepare(`
    SELECT item_id, section_key, title, content, reason, priority, created_at
    FROM memory_items WHERE user_id = ? AND (? = '' OR section_key = ?)
      AND status = 'active' ORDER BY created_at
  `).bind(USER_ID, sectionKey, sectionKey).all<JsonRecord>()
  const classifications = await env.DB.prepare(`
    SELECT t.item_id, t.section_key, t.cluster_title, t.basis, t.confidence,
           t.created_at, i.label
    FROM type_classifications t LEFT JOIN items i ON i.item_id = t.item_id
    WHERE t.user_id = ? AND (? = '' OR t.section_key = ?)
    ORDER BY t.created_at
  `).bind(USER_ID, sectionKey, sectionKey).all<JsonRecord>()
  const handwriting = await env.DB.prepare(`
    SELECT analysis_id, item_kind, item_ref, section_key, first_wrong_step,
           error_type, reason, minimal_correction, downstream_status,
           confidence, analysis_status, created_at
    FROM handwriting_analyses
    WHERE user_id = ? AND (? = '' OR section_key = ?)
    ORDER BY created_at
  `).bind(USER_ID, sectionKey, sectionKey).all<JsonRecord>()
  const snapshot = await env.DB.prepare(`
    SELECT payload_json, created_at FROM learning_events
    WHERE user_id = ? AND event_type = 'progress_snapshot_synced'
      AND (? = '' OR subject_id = ?)
    ORDER BY created_at DESC LIMIT 1
  `).bind(USER_ID, sectionKey, `section:${sectionKey}`).first<Record<string, string>>()
  const snapshotValue = snapshot ? parseJson(snapshot.payload_json) : null
  const progress = snapshotValue && typeof snapshotValue === 'object' && !Array.isArray(snapshotValue)
    ? snapshotValue as JsonRecord
    : {}
  const currentTaskRow = await env.DB.prepare(`
    SELECT value_json, updated_at FROM learner_state
    WHERE user_id = ? AND state_key = 'current_task'
  `).bind(USER_ID).first<Record<string, string>>()
  const currentTaskValue = currentTaskRow ? parseJson(currentTaskRow.value_json) : null
  const currentTask = currentTaskValue && typeof currentTaskValue === 'object' && !Array.isArray(currentTaskValue)
    ? currentTaskValue as JsonRecord
    : progress.currentTask ?? null
  const currentTaskRecord: JsonRecord | null = currentTask && typeof currentTask === 'object' && !Array.isArray(currentTask)
    ? currentTask as JsonRecord
    : null
  const reportCurrentTask = currentTaskRecord
    ? {
        chapter: currentTaskRecord.chapter ?? null,
        section: currentTaskRecord.section ?? null,
        title: currentTaskRecord.title ?? null,
        courseKey: currentTaskRecord.courseKey ?? null,
        status: currentTaskRecord.status ?? null,
        deferredCycle: currentTaskRecord.deferredCycle ?? null,
      }
    : null
  const cyclePrefix = sectionKey ? `cycle:${sectionKey}-cycle-%` : 'cycle:%'
  const cycleRows = await env.DB.prepare(`
    SELECT state_key, value_json, updated_at FROM learner_state
    WHERE user_id = ? AND state_key LIKE ? ORDER BY state_key
  `).bind(USER_ID, cyclePrefix).all<Record<string, string>>()
  const liveCycles: JsonRecord[] = []
  for (const row of cycleRows.results) {
    const value = parseJson(row.value_json)
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      liveCycles.push({ ...(value as JsonRecord), stateKey: row.state_key, updatedAt: row.updated_at })
    }
  }
  const completedCycles = liveCycles.filter((cycle) => cycle.status === 'completed' || cycle.status === 'cycle_completed')
  const deferredCycles = liveCycles.filter((cycle) => cycle.status === 'deferred' || cycle.status === 'cycle_deferred')
  const fallbackCycles = recordArray(progress.completedCycles)
  const reportCompletedCycles = completedCycles.length ? completedCycles : fallbackCycles
  const classificationByItem = new Map(classifications.results
    .filter((row) => row.item_id)
    .map((row) => [String(row.item_id), row]))
  const summary = {
    total: rows.results.length,
    open: rows.results.filter((row) => row.final_status === 'open' || row.final_status === 'needs_review').length,
    corrected: rows.results.filter((row) => row.final_status === 'confirmed_correct').length,
    confirmedWrong: rows.results.filter((row) => row.final_status === 'confirmed_wrong').length,
    typeClassifications: classifications.results.length,
    memories: memories.results.length,
    handwritingAnalyses: handwriting.results.length,
    completedCycles: reportCompletedCycles.length,
    deferredCycles: deferredCycles.length,
  }
  const payload = {
    ok: true,
    format,
    generatedAt,
    freshness: 'live_cloud_d1',
    latestProgressAt: currentTaskRow?.updated_at ?? snapshot?.created_at ?? null,
    scope: sectionKey || 'all',
    currentTask: reportCurrentTask,
    completedCycles: reportCompletedCycles,
    deferredCycles,
    summary,
    wrongQuestions: rows.results,
    typeClassifications: classifications.results,
    memories: memories.results,
    handwritingAnalyses: handwriting.results,
  }
  if (format === 'json') return payload

  const lines = [
    '# 当前错题与题型整理', '',
    `> 实时生成：${generatedAt} · 云端进度：${snapshot?.created_at ?? '暂无同步快照'} · 范围：${sectionKey || '全部'}`, '',
    '## 当前学习位置', '',
    `- 当前任务：${reportCurrentTask?.title ?? '未记录'}${reportCurrentTask?.courseKey ? `（课程 ${reportCurrentTask.courseKey}）` : ''}`,
    `- 已完成循环：${reportCompletedCycles.map((cycle) => cycle.title ?? cycle.cycleId ?? cycle.stateKey).join('、') || '暂无'}`,
    `- 暂缓循环：${deferredCycles.map((cycle) => cycle.title ?? cycle.subjectId ?? cycle.stateKey).join('、') || '暂无'}`, '',
    '## 汇总', '',
    `- 错题/卡点记录：${summary.total} 项`,
    `- 待复核：${summary.open} 项`,
    `- 已纠正：${summary.corrected} 项`,
    `- 题型归类：${summary.typeClassifications} 项`,
    `- 记忆重点：${summary.memories} 项`, '',
    '## 错题与卡点', '',
  ]
  if (!rows.results.length) lines.push('暂无结构化错题记录。同步快照里的文字备注会列在“循环复盘”中，但不会冒充已核验错题。', '')
  for (const row of rows.results) {
    const classification = classificationByItem.get(String(row.item_id ?? ''))
    lines.push(
      `### ${row.label ?? '未绑定教材题号'}`,
      '',
      `- 题型：${classification?.cluster_title ?? '待归类'}`,
      `- 错误类型：${row.error_type}`,
      `- 错误方向：${row.error_direction ?? '待补充'}`,
      `- 错误表现：${row.evidence_text}`,
      `- 改正状态：${row.final_status}`,
      `- 下一步：${row.final_status === 'confirmed_correct' ? '进入独立近变式或冷复测' : '先提交独立过程，再判断是否通过'}`,
      '',
    )
  }
  lines.push('## 题型分类', '')
  if (!classifications.results.length) lines.push('暂无结构化题型归类。', '')
  for (const row of classifications.results) lines.push(
    `### ${row.cluster_title}`,
    '',
    `- 对应题目：${row.label ?? '未绑定教材题号'}`,
    `- 归类依据：${row.basis}`,
    `- 置信度：${row.confidence}`,
    '',
  )
  lines.push('## 手写过程批改', '')
  if (!handwriting.results.length) lines.push('暂无手写过程批改记录。', '')
  for (const row of handwriting.results) lines.push(
    `### ${row.item_ref}`,
    '',
    `- 第一处错误：${row.first_wrong_step ? `第 ${row.first_wrong_step} 行` : '未定位'}`,
    `- 错误类型：${row.error_type ?? '未分类'}`,
    `- 说明：${row.reason ?? '未记录'}`,
    `- 下游状态：${row.downstream_status ?? '未记录'}`,
    `- 最小修正：${row.minimal_correction ?? '未记录'}`,
    `- 分析状态：${row.analysis_status ?? '未记录'}（置信度 ${row.confidence ?? '未记录'}）`,
    '',
  )
  lines.push('## 循环复盘', '')
  if (!reportCompletedCycles.length) lines.push('暂无已同步循环。', '')
  for (const cycle of reportCompletedCycles) lines.push(
    `### ${cycle.title ?? cycle.cycleId ?? '未命名循环'}`,
    '',
    `- 状态：${cycle.status ?? '未记录'}`,
    `- 已确认题目：${Array.isArray(cycle.confirmedItems) ? cycle.confirmedItems.join('、') : '未记录'}`,
    `- 学习备注：${cycle.notes ?? '无'}`,
    '',
  )
  for (const cycle of deferredCycles) lines.push(
    `### ${cycle.title ?? cycle.subjectId ?? cycle.stateKey ?? '未命名循环'}`,
    '',
    '- 状态：暂缓（不计为完成）',
    `- 原因：${cycle.reason ?? '用户要求稍后再学'}`,
    '',
  )
  lines.push('## 记忆重点', '')
  if (!memories.results.length) lines.push('暂无主动保存的记忆重点。', '')
  for (const memory of memories.results) lines.push(
    `### ${memory.title}`,
    '',
    `${memory.content}`,
    '',
    `- 记忆理由：${memory.reason}`,
    `- 优先级：${memory.priority}`,
    '',
  )
  lines.push('---', '', '本报告只整理错因、题型、方法与复测动作；不写教材答案、正确选项或内部题目 ID。')
  return {
    ok: true,
    format: 'markdown',
    generatedAt,
    freshness: 'live_cloud_d1',
    latestProgressAt: currentTaskRow?.updated_at ?? snapshot?.created_at ?? null,
    scope: sectionKey || 'all',
    currentTask: reportCurrentTask,
    summary,
    content: lines.join('\n'),
  }
}

function createServer(env: Env, scopes: readonly string[]): McpServer {
  const server = new McpServer(PROJECT, {
    instructions:
      '这是课程顺序优先的数学学习系统。每门课先调用 math_get_course_learning_bundle，一次核对老师全文、讲义原页、对应一本通和已解锁必刷题；执行顺序是听课、一本通、必刷题基础、拔高、验收。讲义和必刷题 OCR 只用于定位，公式题面必须读取原页图；必刷题源 PDF 没有答案。用户上传手写过程时，先核对原题，再逐行转写并定位第一处分歧，用 math_record_handwriting_analysis 保存 proposed 分析；用户确认后才调用 math_record_wrong_question 写正式错题和题型。用户要求整理时调用 math_export_wrong_questions。课程覆盖、用户已学、题目已通过和冷复测是不同状态。不要输出未请求的答案，不要把内部模拟进度当成真实用户进度。',
  })
  const readAllowed = () => scopes.includes(READ_SCOPE)
  const writeAllowed = () => scopes.includes(WRITE_SCOPE)

  server.registerTool('math_get_system_status', {
    description: '读取教材、课程转写和学习事件的云端导入状态。',
    inputSchema: {},
  }, async () => readAllowed() ? result(await systemStatus(env)) : failure('insufficient_scope', READ_SCOPE))

  server.registerTool('math_get_current_task', {
    description: '读取真实用户当前学习任务，不读取内部模拟人格。',
    inputSchema: {},
  }, async () => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const row = await env.DB.prepare(`SELECT version, value_json, updated_at FROM learner_state WHERE user_id = ? AND state_key = 'current_task'`)
      .bind(USER_ID).first<Record<string, string | number>>()
    return result({ currentTask: row ? { version: Number(row.version), value: parseJson(String(row.value_json)), updatedAt: row.updated_at } : null })
  })

  server.registerTool('math_get_section_overview', {
    description: '读取某一节的完整学习大纲：知识点、类型题、循环顺序、课程编号、桥接项和教材项目索引；不返回答案侧车。',
    inputSchema: { sectionKey: z.string().min(1).max(80) },
  }, async ({ sectionKey }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const section = await env.DB.prepare(`
      SELECT s.section_key, s.chapter_key, s.title, s.manifest_r2_key,
             c.title AS chapter_title
      FROM sections s JOIN chapters c ON c.chapter_key = s.chapter_key
      WHERE s.section_key = ?
    `).bind(sectionKey).first<JsonRecord>()
    if (!section) return failure('not_found', '未找到节次', { sectionKey })
    const pack = await readContentJson(env, String(section.manifest_r2_key))
    if (!pack) return failure('content_unavailable', '节次内容包不可读', { sectionKey })
    const itemRows = await env.DB.prepare(`
      SELECT item_id, label, item_type, concept_key, sort_order
      FROM items WHERE section_key = ? ORDER BY sort_order
    `).bind(sectionKey).all<JsonRecord>()
    const manifest = pack.manifest && typeof pack.manifest === 'object' ? pack.manifest as JsonRecord : {}
    return result({
      ok: true,
      section,
      manifest,
      items: itemRows.results,
      packetManifest: pack.packet_manifest ?? null,
    })
  })

  server.registerTool('math_get_item_content', {
    description: '读取某一道教材项目的完整学生题面和题图。答案侧车永远不在返回内容中；题图以 MCP image blocks 返回。',
    inputSchema: { itemId: z.string().min(1).max(200) },
  }, async ({ itemId }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const row = await env.DB.prepare(`
      SELECT i.item_id, i.section_key, i.label, i.item_type, i.concept_key,
             i.content_r2_key, i.source_sha256, s.title AS section_title,
             c.chapter_key, c.title AS chapter_title
      FROM items i
      JOIN sections s ON s.section_key = i.section_key
      JOIN chapters c ON c.chapter_key = s.chapter_key
      WHERE i.item_id = ?
    `).bind(itemId).first<JsonRecord>()
    if (!row) return failure('not_found', '未找到教材项目', { itemId })
    const content = await itemFromContent(env, row)
    if (!content) return failure('content_unavailable', '教材项目内容包不可读', { itemId })
    const images = await itemImageContent(env, content.pack, content.item)
    return result({ ok: true, index: row, item: content.item, imageCount: images.length }, images)
  })

  server.registerTool('math_get_answer_sources', {
    description: '读取已导入的原书答案来源。返回原书答案与来源版本，不把模型推导冒充原书答案；模型解法由当前对话另行生成并标注。',
    inputSchema: { itemId: z.string().min(1).max(200) },
  }, async ({ itemId }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const rows = await env.DB.prepare(`
      SELECT item_id, source_kind, source_version_id, answer_text, source_sha256
      FROM answer_sources WHERE item_id = ? ORDER BY source_kind
    `).bind(itemId).all<JsonRecord>()
    return result({
      ok: true,
      itemId,
      sources: rows.results,
      modelSolutionPolicy: '模型解法必须单独标为 model_solution，并与原书答案分栏；推荐方案需说明选择理由。',
    })
  })

  server.registerTool('math_get_course_transcript', {
    description: '读取某门网课的完整老师文稿；若有可靠句段时间轴则可一并返回，否则明确标记 timelineAvailable=false。',
    inputSchema: {
      courseKey: z.string().min(1).max(200),
      includeTimeline: z.boolean().default(true),
    },
  }, async ({ courseKey, includeTimeline }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const row = await env.DB.prepare(`
      SELECT course_key, title, transcript_r2_key, transcript_sha256, duration_ms, has_timeline
      FROM courses WHERE course_key = ?
    `).bind(courseKey).first<JsonRecord>()
    if (!row) return failure('not_found', '未找到课程', { courseKey })
    const pack = await readContentJson(env, String(row.transcript_r2_key))
    const courses = pack?.courses && typeof pack.courses === 'object' ? pack.courses as JsonRecord : null
    const transcript = courses?.[courseKey] && typeof courses[courseKey] === 'object' ? courses[courseKey] as JsonRecord : null
    if (!transcript) return failure('content_unavailable', '课程文稿内容包不可读', { courseKey })
    const payload: JsonRecord = {
      ok: true,
      course: row,
      transcript: {
        courseKey,
        fullText: transcript.fullText ?? '',
        timelineAvailable: Number(row.has_timeline) === 1,
        sentences: includeTimeline && Number(row.has_timeline) === 1 ? transcript.sentences ?? [] : [],
        durationMs: transcript.durationMs ?? row.duration_ms ?? null,
        sourceSha256: transcript.sourceSha256 ?? row.transcript_sha256 ?? null,
        provenance: transcript.provenance ?? null,
      },
    }
    return result(payload)
  })

  server.registerTool('math_search_handout', {
    description: '搜索《高二数学精讲精练》讲义 OCR 索引。OCR 只用于定位；公式、图形和题面必须再读取原页图核对。',
    inputSchema: {
      query: z.string().min(1).max(200),
      courseKey: z.string().max(200).default(''),
      limit: z.number().int().min(1).max(30).default(10),
    },
  }, async ({ query, courseKey, limit }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const rows = await env.DB.prepare(`
      SELECT DISTINCT p.source_id, s.title AS source_title, p.pdf_page,
             p.printed_page, p.page_role, p.headings_json,
             substr(p.ocr_text, 1, 1600) AS ocr_excerpt,
             p.ocr_confidence, p.visual_status,
             l.course_key, l.relationship, l.confidence AS mapping_confidence
      FROM handout_pages p
      JOIN handout_sources s ON s.source_id = p.source_id
      LEFT JOIN handout_course_links l
        ON l.source_id = p.source_id AND l.pdf_page = p.pdf_page
      WHERE p.ocr_text LIKE ? AND (? = '' OR l.course_key = ?)
      ORDER BY p.source_id, p.pdf_page LIMIT ?
    `).bind(`%${query}%`, courseKey, courseKey, limit).all<JsonRecord>()
    return result({
      ok: true,
      query,
      courseKey: courseKey || null,
      matches: rows.results.map((row) => ({ ...row, headings: parseJson(String(row.headings_json)) })),
      evidencePolicy: 'OCR 只负责检索定位；讲解前调用 math_get_handout_page 查看原页图，未视觉复核的公式不得当成确定事实。',
    })
  })

  server.registerTool('math_get_course_handout', {
    description: '读取某门网课在《高二数学精讲精练》中的候选讲义页；候选映射与已视觉核验映射会明确区分。',
    inputSchema: {
      courseKey: z.string().min(1).max(200),
      limit: z.number().int().min(1).max(50).default(20),
    },
  }, async ({ courseKey, limit }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const rows = await env.DB.prepare(`
      SELECT p.source_id, s.title AS source_title, p.pdf_page, p.printed_page,
             p.page_role, p.headings_json, p.ocr_confidence, p.visual_status,
             l.relationship, l.confidence AS mapping_confidence
      FROM handout_course_links l
      JOIN handout_pages p ON p.source_id = l.source_id AND p.pdf_page = l.pdf_page
      JOIN handout_sources s ON s.source_id = p.source_id
      WHERE l.course_key = ? ORDER BY p.source_id, p.pdf_page LIMIT ?
    `).bind(courseKey, limit).all<JsonRecord>()
    return result({
      ok: true,
      courseKey,
      pages: rows.results.map((row) => ({ ...row, headings: parseJson(String(row.headings_json)) })),
      mappingPolicy: 'candidate 表示 OCR/标题候选；verified 才表示原页视觉已确认。',
    })
  })

  server.registerTool('math_get_handout_page', {
    description: '返回讲义指定 PDF 页的 OCR 定位文本和原页图。原页图是公式、图形和题面的最终核对依据。',
    inputSchema: {
      sourceId: z.string().min(1).max(80),
      pdfPage: z.number().int().min(1).max(1000),
      includeImage: z.boolean().default(true),
    },
  }, async ({ sourceId, pdfPage, includeImage }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const row = await env.DB.prepare(`
      SELECT p.*, s.title AS source_title, s.source_sha256
      FROM handout_pages p JOIN handout_sources s ON s.source_id = p.source_id
      WHERE p.source_id = ? AND p.pdf_page = ?
    `).bind(sourceId, pdfPage).first<JsonRecord>()
    if (!row) return failure('not_found', '未找到讲义页', { sourceId, pdfPage })
    const links = await env.DB.prepare(`
      SELECT course_key, relationship, confidence FROM handout_course_links
      WHERE source_id = ? AND pdf_page = ? ORDER BY course_key
    `).bind(sourceId, pdfPage).all<JsonRecord>()
    const images = includeImage ? await handoutPageImageContent(env, row) : []
    return result({
      ok: true,
      page: { ...row, headings: parseJson(String(row.headings_json)), headings_json: undefined },
      courseLinks: links.results,
      imageCount: images.length,
      evidencePolicy: Number(images.length) === 1
        ? '请以返回原页图核对公式、图形和题面；OCR 文本仅作搜索辅助。'
        : '原页图当前不可读，不得仅凭 OCR 断言公式或图形。',
    }, images)
  })

  server.registerTool('math_search_practice', {
    description: '搜索《高中必刷题·选择性必修第一册》OCR 索引。OCR 只用于定位，题干、公式和图形必须再读取原页图。',
    inputSchema: {
      query: z.string().min(1).max(200),
      chapterKey: z.string().max(20).default(''),
      sectionKey: z.string().max(80).default(''),
      limit: z.number().int().min(1).max(40).default(12),
    },
  }, async ({ query, chapterKey, sectionKey, limit }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const rows = await env.DB.prepare(`
      SELECT i.item_id, i.label, i.chapter_key, i.section_key, i.unit_key,
             i.unit_title, i.source_type_title, i.practice_level, i.cadence, i.printed_page, i.pdf_page,
             substr(i.ocr_excerpt, 1, 1400) AS ocr_excerpt,
             i.visual_status, i.answer_status, s.title AS source_title
      FROM practice_items i JOIN practice_sources s ON s.source_id = i.source_id
      WHERE i.ocr_excerpt LIKE ? AND (? = '' OR i.chapter_key = ?)
        AND (? = '' OR i.section_key = ?)
      ORDER BY CAST(i.chapter_key AS INTEGER), i.printed_page, i.question_number, i.occurrence LIMIT ?
    `).bind(`%${query}%`, chapterKey, chapterKey, sectionKey, sectionKey, limit).all<JsonRecord>()
    return result({
      ok: true, query, matches: rows.results,
      evidencePolicy: '搜索结果不是可直接作答的完整题面；先调用 math_get_practice_page 查看原页图。该 PDF 不含答案，模型解法必须标为 model_solution。',
    })
  })

  server.registerTool('math_get_practice_page', {
    description: '读取必刷题指定 PDF 页的题号索引、OCR 定位文本和原页图；原页图是题干、公式和图形的最终依据。',
    inputSchema: {
      sourceId: z.string().min(1).max(100),
      pdfPage: z.number().int().min(1).max(1000),
      includeImage: z.boolean().default(true),
    },
  }, async ({ sourceId, pdfPage, includeImage }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const row = await env.DB.prepare(`
      SELECT p.*, s.title AS source_title, s.source_sha256, s.answer_status
      FROM practice_pages p JOIN practice_sources s ON s.source_id = p.source_id
      WHERE p.source_id = ? AND p.pdf_page = ?
    `).bind(sourceId, pdfPage).first<JsonRecord>()
    if (!row) return failure('not_found', '未找到必刷题页面', { sourceId, pdfPage })
    const items = await env.DB.prepare(`
      SELECT item_id, label, question_number, occurrence, chapter_key, section_key,
             unit_key, unit_title, source_type_title, practice_level, cadence, visual_status, answer_status
      FROM practice_items WHERE source_id = ? AND pdf_page = ?
      ORDER BY question_number, occurrence
    `).bind(sourceId, pdfPage).all<JsonRecord>()
    const images = includeImage ? await practicePageImageContent(env, row) : []
    return result({
      ok: true,
      page: { ...row, headings: parseJson(String(row.headings_json)), headings_json: undefined },
      items: items.results,
      imageCount: images.length,
      evidencePolicy: images.length === 1
        ? '必须以返回原页图核对题号、公式和图形；OCR 文本仅作定位。源 PDF 不含答案。'
        : '原页图不可读，不得只凭 OCR 讲题或判题。',
    }, images)
  })

  server.registerTool('math_get_practice_route', {
    description: '按课程、循环、节次和练习节奏读取必刷题题号与印刷/PDF页码，并根据真实云端进度标出是否解锁。',
    inputSchema: {
      courseKey: z.string().max(200).default(''),
      cycleId: z.string().max(200).default(''),
      sectionKey: z.string().max(80).default(''),
      cadence: z.enum(['', 'after_course', 'after_section', 'after_chapter']).default(''),
      limit: z.number().int().min(1).max(200).default(80),
    },
  }, async ({ courseKey, cycleId, sectionKey, cadence, limit }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    if (!courseKey && !cycleId && !sectionKey) return failure('route_filter_required', '至少提供 courseKey、cycleId 或 sectionKey')
    const rows = await env.DB.prepare(`
      SELECT i.item_id, i.label, i.chapter_key, i.section_key, i.unit_key,
             i.unit_title, i.source_type_title, i.practice_level, i.cadence, i.printed_page, i.pdf_page,
             i.visual_status, i.answer_status,
             group_concat(l.route_type || ':' || l.route_key, '|') AS route_keys,
             (SELECT a.result FROM practice_attempts a
               WHERE a.user_id = ? AND a.practice_item_id = i.item_id
               ORDER BY a.created_at DESC LIMIT 1) AS latest_result
      FROM practice_items i
      LEFT JOIN practice_route_links l ON l.item_id = i.item_id
      WHERE (? = '' OR EXISTS (SELECT 1 FROM practice_route_links x WHERE x.item_id=i.item_id AND x.route_type='course' AND x.route_key=?))
        AND (? = '' OR EXISTS (SELECT 1 FROM practice_route_links x WHERE x.item_id=i.item_id AND x.route_type='cycle' AND x.route_key=?))
        AND (? = '' OR i.section_key = ?)
        AND (? = '' OR i.cadence = ?)
      GROUP BY i.item_id
      ORDER BY i.printed_page, i.question_number, i.occurrence LIMIT ?
    `).bind(USER_ID, courseKey, courseKey, cycleId, cycleId, sectionKey, sectionKey, cadence, cadence, limit).all<JsonRecord>()
    const states = await env.DB.prepare(`
      SELECT state_key, value_json FROM learner_state WHERE user_id = ?
        AND (state_key LIKE 'course:%' OR state_key LIKE 'cycle:%'
          OR state_key LIKE 'section:%' OR state_key LIKE 'chapter:%')
    `).bind(USER_ID).all<Record<string, string>>()
    const completed = new Set(states.results.filter((row) => {
      const value = parseJson(row.value_json)
      if (!value || typeof value !== 'object' || Array.isArray(value)) return false
      const status = String((value as JsonRecord).status ?? '')
      return ['completed', 'course_listened', 'cycle_completed', 'item_passed'].includes(status)
    }).map((row) => row.state_key))
    const items = rows.results.map((row) => {
      const routeKeys = String(row.route_keys ?? '').split('|').filter(Boolean)
      const courseRequirements = routeKeys.filter((key) => key.startsWith('course:'))
      const cycleRequirements = routeKeys.filter((key) => key.startsWith('cycle:'))
      const sectionRequirements = routeKeys.filter((key) => key.startsWith('section:'))
      const chapterRequirements = routeKeys.filter((key) => key.startsWith('chapter:'))
      let requirements: string[] = []
      if (row.cadence === 'after_course') requirements = courseRequirements.length ? courseRequirements : cycleRequirements
      else if (row.cadence === 'after_section') requirements = sectionRequirements
      else if (row.cadence === 'after_chapter') requirements = chapterRequirements
      const completedCount = requirements.filter((key) => completed.has(key)).length
      const unlockStatus = requirements.length === 0 ? 'manual_review'
        : completedCount === requirements.length ? 'unlocked'
          : completedCount > 0 ? 'partially_unlocked' : 'locked'
      return {
        ...row,
        routeKeys,
        requirements,
        unlockStatus: row.cadence === 'after_course'
          ? courseRequirements.length && completedCount === requirements.length ? 'optional_available' : 'optional_after_course'
          : unlockStatus,
        optional: true,
        blocksYbtProgress: false,
      }
    })
    return result({
      ok: true,
      routePolicy: '课程顺序优先：听课 -> 对应一本通 -> 可选必刷题基础题；节次综合和章节检测后置。必刷题永远不阻塞一本通主线，页内按题号顺序。',
      practiceIsOptional: true,
      practiceDoesNotBlockYbtProgress: true,
      items,
    })
  })

  server.registerTool('math_get_course_learning_bundle', {
    description: '一次读取一门课的老师文稿、讲义候选原页、对应一本通项目、必刷题题号页码和真实课程状态，作为课程优先学习入口。',
    inputSchema: { courseKey: z.string().min(1).max(200), practiceLimit: z.number().int().min(1).max(100).default(40) },
  }, async ({ courseKey, practiceLimit }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const course = await env.DB.prepare(`SELECT course_key,title,transcript_r2_key,transcript_sha256,duration_ms,has_timeline FROM courses WHERE course_key=?`).bind(courseKey).first<JsonRecord>()
    if (!course) return failure('not_found', '未找到课程', { courseKey })
    const transcriptPack = await readContentJson(env, String(course.transcript_r2_key))
    const packedCourses = transcriptPack?.courses && typeof transcriptPack.courses === 'object' ? transcriptPack.courses as JsonRecord : {}
    const transcript = packedCourses[courseKey] && typeof packedCourses[courseKey] === 'object' ? packedCourses[courseKey] as JsonRecord : {}
    const ybtItems = await env.DB.prepare(`
      SELECT i.item_id,i.label,i.item_type,i.section_key,i.concept_key,l.relationship
      FROM item_course_links l JOIN items i ON i.item_id=l.item_id
      WHERE l.course_key=? ORDER BY i.section_key,i.sort_order
    `).bind(courseKey).all<JsonRecord>()
    const handoutPages = await env.DB.prepare(`
      SELECT p.source_id,p.pdf_page,p.printed_page,p.visual_status,l.confidence
      FROM handout_course_links l JOIN handout_pages p ON p.source_id=l.source_id AND p.pdf_page=l.pdf_page
      WHERE l.course_key=? ORDER BY p.source_id,p.pdf_page LIMIT 30
    `).bind(courseKey).all<JsonRecord>()
    const practiceItems = await env.DB.prepare(`
      SELECT i.item_id,i.label,i.printed_page,i.pdf_page,i.unit_title,i.source_type_title,i.practice_level,i.cadence,i.visual_status,i.answer_status
      FROM practice_route_links l JOIN practice_items i ON i.item_id=l.item_id
      WHERE l.route_type='course' AND l.route_key=? ORDER BY i.printed_page,i.question_number,i.occurrence LIMIT ?
    `).bind(courseKey, practiceLimit).all<JsonRecord>()
    const state = await env.DB.prepare(`SELECT version,value_json,updated_at FROM learner_state WHERE user_id=? AND state_key=?`).bind(USER_ID, `course:${courseKey}`).first<Record<string, string | number>>()
    const courseState = state ? parseJson(String(state.value_json)) : null
    const courseUnlocked = Boolean(courseState && typeof courseState === 'object' && !Array.isArray(courseState)
      && ['course_listened', 'completed', 'simulated_completed'].includes(String((courseState as JsonRecord).status ?? '')))
    return result({
      ok: true,
      executionOrder: ['course_transcript', 'teacher_handout_source_page', 'ybt_items', 'practice_basic', 'practice_advanced', 'acceptance'],
      course,
      transcript: {
        fullText: transcript.fullText ?? '',
        timelineAvailable: Number(course.has_timeline) === 1,
        durationMs: transcript.durationMs ?? course.duration_ms ?? null,
        sourceSha256: transcript.sourceSha256 ?? course.transcript_sha256 ?? null,
      },
      handoutPages: handoutPages.results,
      ybtItems: ybtItems.results,
      practiceItems: practiceItems.results.map((item) => ({
        ...item,
        unlockStatus: courseUnlocked ? 'optional_available' : 'optional_after_course',
        optional: true,
        blocksYbtProgress: false,
      })),
      learnerState: state ? { version: Number(state.version), value: parseJson(String(state.value_json)), updatedAt: state.updated_at } : null,
      evidencePolicy: '老师文稿决定讲法顺序；讲义与必刷题 OCR 仅定位，公式题面必须读原页图；必刷题源 PDF 不含答案。',
    })
  })

  server.registerTool('math_get_course_first_route', {
    description: '按课程编号生成整章执行顺序；每门课后列出对应一本通和必刷题数量，课程内部保持教材/题号原顺序。',
    inputSchema: { chapterKey: z.string().min(1).max(20) },
  }, async ({ chapterKey }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const rows = await env.DB.prepare(`
      SELECT c.course_key, c.title, c.duration_ms, c.has_timeline,
        (SELECT COUNT(DISTINCT i.item_id)
          FROM item_course_links il JOIN items i ON i.item_id=il.item_id
          JOIN sections s ON s.section_key=i.section_key
          WHERE il.course_key=c.course_key AND s.chapter_key=?) AS ybt_item_count,
        (SELECT COUNT(DISTINCT pi.item_id)
          FROM practice_route_links pl JOIN practice_items pi ON pi.item_id=pl.item_id
          WHERE pl.route_type='course' AND pl.route_key=c.course_key
            AND pi.chapter_key=?) AS practice_item_count,
        (SELECT value_json FROM learner_state
          WHERE user_id=? AND state_key='course:' || c.course_key) AS state_json,
        (SELECT updated_at FROM learner_state
          WHERE user_id=? AND state_key='course:' || c.course_key) AS state_updated_at
      FROM courses c
      WHERE EXISTS (
        SELECT 1 FROM item_course_links il JOIN items i ON i.item_id=il.item_id
        JOIN sections s ON s.section_key=i.section_key
        WHERE il.course_key=c.course_key AND s.chapter_key=?
      ) OR EXISTS (
        SELECT 1 FROM practice_route_links pl JOIN practice_items pi ON pi.item_id=pl.item_id
        WHERE pl.route_type='course' AND pl.route_key=c.course_key AND pi.chapter_key=?
      )
      ORDER BY c.title
    `).bind(chapterKey, chapterKey, USER_ID, USER_ID, chapterKey, chapterKey).all<Record<string, string | number | null>>()
    const orderedCourses = [...rows.results].sort((left, right) =>
      courseSortKey(`${String(left.title ?? '')} ${String(left.course_key ?? '')}`)
        .localeCompare(courseSortKey(`${String(right.title ?? '')} ${String(right.course_key ?? '')}`), 'en'))
    return result({
      ok: true,
      chapterKey,
      policy: {
        primaryOrder: 'course_number',
        perCourse: ['listen_course', 'read_teacher_handout_source_page', 'complete_ybt_items', 'optionally_complete_practice_basic', 'optionally_complete_practice_advanced'],
        checkpoints: ['after_section', 'after_chapter'],
        invariant: '每个一本通项目只出现一次；必刷题是选做，不阻塞一本通主线；同一课程内保持教材原顺序，不能为了课程顺序重排题目内部结构。',
      },
      courses: orderedCourses.map((row, index) => ({
        order: index + 1,
        courseKey: row.course_key,
        title: row.title,
        durationMs: row.duration_ms,
        timelineAvailable: Number(row.has_timeline) === 1,
        ybtItemCount: Number(row.ybt_item_count),
        practiceItemCount: Number(row.practice_item_count),
        learnerState: parseJson(row.state_json ? String(row.state_json) : null),
        stateUpdatedAt: row.state_updated_at,
      })),
    })
  })

  server.registerTool('math_get_handwriting_history', {
    description: '读取已保存的手写过程分析。proposed 表示模型初判，只有后续用户确认才可转为正式错题画像。',
    inputSchema: { itemRef: z.string().max(200).default(''), limit: z.number().int().min(1).max(100).default(20) },
  }, async ({ itemRef, limit }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const rows = await env.DB.prepare(`
      SELECT analysis_id,item_kind,item_ref,section_key,image_evidence_id,
             question_source_verified,transcription_json,steps_json,
             first_wrong_step,error_type,reason,minimal_correction,
             downstream_status,confidence,analysis_status,uncertainties_json,
             clarification_request,annotation_spec_json,created_at
      FROM handwriting_analyses WHERE user_id=? AND (?='' OR item_ref=?)
      ORDER BY created_at DESC LIMIT ?
    `).bind(USER_ID, itemRef, itemRef, limit).all<Record<string, string | number | null>>()
    return result({ analyses: rows.results.map((row) => ({
      ...row,
      transcription: parseJson(String(row.transcription_json)),
      steps: parseJson(String(row.steps_json)),
      uncertainties: parseJson(String(row.uncertainties_json)),
      annotationSpec: parseJson(row.annotation_spec_json ? String(row.annotation_spec_json) : null),
    })) })
  })

  server.registerTool('math_get_learning_context', {
    description: '一次读取题目索引、教材位置、对应课程与真实用户状态。完整题面按返回的 R2 内容键受控获取。',
    inputSchema: { itemId: z.string().min(1).max(200) },
  }, async ({ itemId }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const context = await learningContext(env, itemId)
    return context ? result(context) : failure('not_found', '未找到题目索引', { itemId })
  })

  server.registerTool('math_get_progress', {
    description: '读取真实用户的章节、节次、题目和课程进度状态。',
    inputSchema: { prefix: z.string().max(200).default('') },
  }, async ({ prefix }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const rows = await env.DB.prepare(`
      SELECT state_key, version, value_json, updated_at FROM learner_state
      WHERE user_id = ? AND state_key LIKE ? ORDER BY state_key LIMIT 500
    `).bind(USER_ID, `${prefix}%`).all<Record<string, string | number>>()
    return result({ states: rows.results.map((row) => ({ key: row.state_key, version: Number(row.version), value: parseJson(String(row.value_json)), updatedAt: row.updated_at })) })
  })

  server.registerTool('math_get_learner_profile', {
    description: '读取持续学习者的错题画像、记忆重点和题型归类，不读取内部模拟人格。',
    inputSchema: {},
  }, async () => readAllowed() ? result(await learnerProfile(env)) : failure('insufficient_scope', READ_SCOPE))

  server.registerTool('math_get_type_clusters', {
    description: '读取某节教材已有题型清单及用户新增题型归类记录。',
    inputSchema: { sectionKey: z.string().min(1).max(80) },
  }, async ({ sectionKey }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const row = await env.DB.prepare(`SELECT manifest_r2_key FROM sections WHERE section_key = ?`).bind(sectionKey).first<JsonRecord>()
    if (!row) return failure('not_found', '未找到节次', { sectionKey })
    const pack = await readContentJson(env, String(row.manifest_r2_key))
    const manifest = pack?.manifest && typeof pack.manifest === 'object' ? pack.manifest as JsonRecord : {}
    const userRows = await env.DB.prepare(`SELECT cluster_title, basis, confidence, item_id, created_at FROM type_classifications WHERE user_id = ? AND section_key = ? ORDER BY created_at DESC`).bind(USER_ID, sectionKey).all<JsonRecord>()
    return result({ ok: true, sectionKey, textbookTypes: manifest.type_labels ?? manifest.type_training ?? [], userClassifications: userRows.results })
  })

  server.registerTool('math_export_wrong_questions', {
    description: '根据当前云端错题、题型、记忆点和最新循环快照，实时生成错题与题型整理文档。输出 markdown 或机器 JSON，不包含教材答案或内部题目 ID。',
    inputSchema: { sectionKey: z.string().max(80).default(''), format: z.enum(['markdown', 'json']).default('markdown') },
  }, async ({ sectionKey, format }) => readAllowed() ? result(await wrongQuestionExport(env, sectionKey, format)) : failure('insufficient_scope', READ_SCOPE))

  server.registerTool('math_get_teacher_method', {
    description: '读取某门课程与知识点相关的网课老师讲法和大概时间段。',
    inputSchema: {
      courseKey: z.string().min(1).max(200),
      topic: z.string().max(200).default(''),
      limit: z.number().int().min(1).max(20).default(8),
    },
  }, async ({ courseKey, topic, limit }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const rows = await env.DB.prepare(`
      SELECT chunk_index, start_ms, end_ms, text, topic, method_tags
      FROM transcript_chunks
      WHERE course_key = ? AND (? = '' OR topic LIKE ? OR text LIKE ?)
      ORDER BY chunk_index LIMIT ?
    `).bind(courseKey, topic, `%${topic}%`, `%${topic}%`, limit).all<Record<string, string | number | null>>()
    return result({ courseKey, chunks: rows.results.map((row) => ({ ...row, methodTags: parseJson(String(row.method_tags)) })) })
  })

  server.registerTool('math_search_teacher_timeline', {
    description: '跨课程搜索老师讲解片段；没有可靠时间轴时 startMs/endMs 返回 null。',
    inputSchema: { query: z.string().min(1).max(200), limit: z.number().int().min(1).max(30).default(10) },
  }, async ({ query, limit }) => {
    if (!readAllowed()) return failure('insufficient_scope', READ_SCOPE)
    const rows = await env.DB.prepare(`
      SELECT t.course_key, c.title AS course_title, t.chunk_index, t.start_ms, t.end_ms, t.text, t.topic
      FROM transcript_chunks t JOIN courses c ON c.course_key = t.course_key
      WHERE t.text LIKE ? OR t.topic LIKE ? ORDER BY t.course_key, t.chunk_index LIMIT ?
    `).bind(`%${query}%`, `%${query}%`, limit).all<JsonRecord>()
    return result({ query, matches: rows.results })
  })

  const eventSchema = {
    requestId: z.uuid(),
    subjectId: z.string().min(1).max(200),
    payload: z.record(z.string(), z.unknown()).default({}),
    evidenceHash: z.string().regex(/^[0-9a-f]{64}$/).optional(),
    baseVersion: z.number().int().nonnegative().optional(),
  }

  for (const definition of [
    ['math_record_course_listened', 'course_listened', 'course'],
    ['math_record_attempt', 'item_attempted', 'item'],
    ['math_record_hint_usage', 'hint_used', 'item'],
    ['math_mark_cycle_completed', 'cycle_completed', 'cycle'],
    ['math_sync_progress_snapshot', 'progress_snapshot_synced', 'progress'],
  ] as const) {
    server.registerTool(definition[0], {
      description: `记录 ${definition[1]} 事件；相同 requestId 只执行一次。`,
      inputSchema: eventSchema,
    }, async ({ requestId, subjectId, payload, evidenceHash, baseVersion }) => {
      if (!writeAllowed()) return failure('insufficient_scope', WRITE_SCOPE)
      try {
        return result(await recordLearningEvent(env, requestId, definition[1], definition[2], subjectId, payload, evidenceHash, baseVersion))
      } catch (error) {
        return failure(error instanceof Error ? error.message : 'write_failed', '学习事件写入失败')
      }
    })
  }

  server.registerTool('math_defer_cycle', {
    description: '在用户明确要求跳过或暂缓当前循环后记录状态，并推进到用户指定的下一循环；不会把暂缓冒充完成。',
    inputSchema: {
      requestId: z.uuid(),
      cycleId: z.string().min(1).max(200),
      cycleTitle: z.string().min(1).max(200),
      reason: z.string().min(1).max(1000),
      nextCycleId: z.string().min(1).max(200),
      nextCycleTitle: z.string().min(1).max(200),
      nextCourseKey: z.string().max(200).optional(),
      currentTaskBaseVersion: z.number().int().nonnegative(),
      userConfirmed: z.boolean(),
    },
  }, async ({ requestId, cycleId, cycleTitle, reason, nextCycleId, nextCycleTitle, nextCourseKey, currentTaskBaseVersion, userConfirmed }) => {
    if (!writeAllowed()) return failure('insufficient_scope', WRITE_SCOPE)
    if (!userConfirmed) return failure('confirmation_required', '暂缓循环需要用户明确确认')
    try {
      const existingTaskRow = await env.DB.prepare(`
        SELECT value_json FROM learner_state WHERE user_id = ? AND state_key = 'current_task'
      `).bind(USER_ID).first<Record<string, string>>()
      const existingTaskValue = existingTaskRow ? parseJson(existingTaskRow.value_json) : null
      const existingTask = existingTaskValue && typeof existingTaskValue === 'object' && !Array.isArray(existingTaskValue)
        ? existingTaskValue as JsonRecord
        : {}
      const event = await recordLearningEvent(env, requestId, 'cycle_deferred', 'cycle', cycleId, {
        title: cycleTitle, status: 'deferred', reason, userConfirmed: true,
        nextTask: { cycle: nextCycleId, title: nextCycleTitle, courseKey: nextCourseKey ?? null },
      })
      const currentTask = await upsertLearnerState(env, 'current_task', {
        chapter: existingTask.chapter ?? null,
        section: existingTask.section ?? null,
        cycle: nextCycleId,
        title: nextCycleTitle,
        courseKey: nextCourseKey ?? null,
        status: 'not_started',
        deferredCycle: cycleId,
        source: 'cloud_mcp_cycle_deferred',
      }, requestId, String(event.createdAt), currentTaskBaseVersion)
      return result({ ok: true, event, currentTask })
    } catch (error) {
      return failure(error instanceof Error ? error.message : 'write_failed', '暂缓循环写入失败')
    }
  })

  server.registerTool('math_record_question', {
    description: '记录用户针对题目的疑问，不自动判定题目通过。',
    inputSchema: { requestId: z.uuid(), itemId: z.string().max(200).optional(), question: z.string().min(1).max(4000) },
  }, async ({ requestId, itemId, question }) => {
    if (!writeAllowed()) return failure('insufficient_scope', WRITE_SCOPE)
    const questionId = crypto.randomUUID()
    const createdAt = new Date().toISOString()
    await env.DB.prepare(`INSERT INTO questions (question_id, request_id, user_id, item_id, question, status, created_at) VALUES (?, ?, ?, ?, ?, 'open', ?) ON CONFLICT(request_id) DO NOTHING`)
      .bind(questionId, requestId, USER_ID, itemId ?? null, question, createdAt).run()
    const stored = await env.DB.prepare(`SELECT question_id, item_id, question, status, created_at FROM questions WHERE request_id = ? AND user_id = ?`)
      .bind(requestId, USER_ID).first<JsonRecord>()
    if (!stored || stored.question !== question || stored.item_id !== (itemId ?? null)) return failure('idempotency_conflict', 'requestId 已用于不同问题')
    return result({ ok: true, question: stored, replayed: stored.question_id !== questionId })
  })

  server.registerTool('math_record_diagnostic', {
    description: '记录一道题的错误类型、错误方向、证据和用户更正；允许将语音误识别撤销为 confirmed_correct。',
    inputSchema: {
      requestId: z.uuid(), itemId: z.string().max(200).optional(), sectionKey: z.string().max(80).optional(),
      errorType: z.string().min(1).max(120), errorDirection: z.string().max(500).optional(), evidenceText: z.string().min(1).max(4000),
      userCorrection: z.string().max(2000).optional(), finalStatus: z.enum(['open', 'confirmed_wrong', 'confirmed_correct', 'needs_review']).default('open'),
    },
  }, async ({ requestId, itemId, sectionKey, errorType, errorDirection, evidenceText, userCorrection, finalStatus }) => {
    if (!writeAllowed()) return failure('insufficient_scope', WRITE_SCOPE)
    const id = crypto.randomUUID(); const createdAt = new Date().toISOString()
    await env.DB.prepare(`INSERT INTO learner_diagnostics (diagnostic_id, request_id, user_id, item_id, section_key, error_type, error_direction, evidence_text, user_correction, final_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(request_id) DO NOTHING`).bind(id, requestId, USER_ID, itemId ?? null, sectionKey ?? null, errorType, errorDirection ?? null, evidenceText, userCorrection ?? null, finalStatus, createdAt).run()
    const stored = await env.DB.prepare(`SELECT diagnostic_id, item_id, section_key, error_type, error_direction, evidence_text, user_correction, final_status, created_at FROM learner_diagnostics WHERE request_id = ? AND user_id = ?`).bind(requestId, USER_ID).first<JsonRecord>()
    return stored ? result({ ok: true, diagnostic: stored, replayed: stored.diagnostic_id !== id }) : failure('write_failed', '错题画像写入失败')
  })

  server.registerTool('math_record_wrong_question', {
    description: '实时记录一道已确认错题或提示后卡点，并同时完成题型归类；相同 requestId 幂等。不要把语音误识别或未确认猜测写成错题。',
    inputSchema: {
      requestId: z.uuid(),
      itemId: z.string().max(200).optional(),
      sectionKey: z.string().min(1).max(80),
      errorType: z.string().min(1).max(120),
      errorDirection: z.string().min(1).max(500),
      evidenceText: z.string().min(1).max(4000),
      userCorrection: z.string().max(2000).optional(),
      finalStatus: z.enum(['open', 'confirmed_wrong', 'confirmed_correct', 'needs_review']).default('open'),
      clusterTitle: z.string().min(1).max(200),
      classificationBasis: z.string().min(1).max(2000),
      classificationConfidence: z.enum(['high', 'medium', 'low']).default('medium'),
    },
  }, async ({
    requestId, itemId, sectionKey, errorType, errorDirection, evidenceText,
    userCorrection, finalStatus, clusterTitle, classificationBasis, classificationConfidence,
  }) => {
    if (!writeAllowed()) return failure('insufficient_scope', WRITE_SCOPE)
    const createdAt = new Date().toISOString()
    const diagnosticId = crypto.randomUUID()
    const classificationId = crypto.randomUUID()
    await env.DB.prepare(`
      INSERT INTO learner_diagnostics (
        diagnostic_id, request_id, user_id, item_id, section_key, error_type,
        error_direction, evidence_text, user_correction, final_status, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(request_id) DO NOTHING
    `).bind(
      diagnosticId, requestId, USER_ID, itemId ?? null, sectionKey, errorType,
      errorDirection, evidenceText, userCorrection ?? null, finalStatus, createdAt,
    ).run()
    await env.DB.prepare(`
      INSERT INTO type_classifications (
        classification_id, request_id, user_id, item_id, section_key,
        cluster_title, basis, confidence, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(request_id) DO NOTHING
    `).bind(
      classificationId, requestId, USER_ID, itemId ?? null, sectionKey,
      clusterTitle, classificationBasis, classificationConfidence, createdAt,
    ).run()
    const diagnostic = await env.DB.prepare(`
      SELECT diagnostic_id, item_id, section_key, error_type, error_direction,
             evidence_text, user_correction, final_status, created_at
      FROM learner_diagnostics WHERE request_id = ? AND user_id = ?
    `).bind(requestId, USER_ID).first<JsonRecord>()
    const classification = await env.DB.prepare(`
      SELECT classification_id, item_id, section_key, cluster_title, basis,
             confidence, created_at FROM type_classifications
      WHERE request_id = ? AND user_id = ?
    `).bind(requestId, USER_ID).first<JsonRecord>()
    const same = diagnostic?.item_id === (itemId ?? null)
      && diagnostic?.section_key === sectionKey
      && diagnostic?.error_type === errorType
      && diagnostic?.error_direction === errorDirection
      && diagnostic?.evidence_text === evidenceText
      && diagnostic?.user_correction === (userCorrection ?? null)
      && diagnostic?.final_status === finalStatus
      && classification?.item_id === (itemId ?? null)
      && classification?.section_key === sectionKey
      && classification?.cluster_title === clusterTitle
      && classification?.basis === classificationBasis
      && classification?.confidence === classificationConfidence
    if (!diagnostic || !classification) return failure('write_failed', '错题或题型归类写入不完整')
    if (!same) return failure('idempotency_conflict', 'requestId 已用于不同错题记录')
    return result({
      ok: true,
      diagnostic,
      classification,
      replayed: diagnostic.diagnostic_id !== diagnosticId || classification.classification_id !== classificationId,
    })
  })

  server.registerTool('math_record_practice_attempt', {
    description: '记录必刷题真实作答。baseVersion 等于该题已有尝试数；相同 requestId 幂等，不把看答案后完成标为独立通过。',
    inputSchema: {
      requestId: z.uuid(),
      practiceItemId: z.string().min(1).max(240),
      result: z.enum(['correct', 'incorrect', 'partial', 'skipped', 'needs_review']),
      independent: z.boolean(),
      hintLevel: z.enum(['none', 'minimal', 'method', 'solution_seen']).default('none'),
      processEvidence: z.string().min(1).max(4000),
      evidenceHash: z.string().regex(/^[0-9a-f]{64}$/).optional(),
      baseVersion: z.number().int().nonnegative(),
    },
  }, async ({ requestId, practiceItemId, result: attemptResult, independent, hintLevel, processEvidence, evidenceHash, baseVersion }) => {
    if (!writeAllowed()) return failure('insufficient_scope', WRITE_SCOPE)
    const existing = await env.DB.prepare(`SELECT attempt_id,practice_item_id,result,independent,hint_level,process_evidence,evidence_hash,created_at FROM practice_attempts WHERE request_id=? AND user_id=?`).bind(requestId, USER_ID).first<JsonRecord>()
    if (existing) {
      const same = existing.practice_item_id === practiceItemId && existing.result === attemptResult
        && Number(existing.independent) === (independent ? 1 : 0) && existing.hint_level === hintLevel
        && existing.process_evidence === processEvidence && existing.evidence_hash === (evidenceHash ?? null)
      return same ? result({ ok: true, attempt: existing, replayed: true }) : failure('idempotency_conflict', 'requestId 已用于不同练习尝试')
    }
    const item = await env.DB.prepare(`SELECT item_id,label,answer_status FROM practice_items WHERE item_id=?`).bind(practiceItemId).first<JsonRecord>()
    if (!item) return failure('not_found', '未找到必刷题项目', { practiceItemId })
    const count = await env.DB.prepare(`SELECT COUNT(*) AS count FROM practice_attempts WHERE user_id=? AND practice_item_id=?`).bind(USER_ID, practiceItemId).first<{ count: number | string }>()
    if (Number(count?.count ?? 0) !== baseVersion) return failure('version_conflict', '练习题尝试版本已变化', { expected: baseVersion, actual: Number(count?.count ?? 0) })
    if (hintLevel === 'solution_seen' && independent) return failure('invalid_independence', '看过完整解法后不能标为独立作答')
    const attemptId = crypto.randomUUID(); const createdAt = new Date().toISOString()
    await env.DB.prepare(`INSERT INTO practice_attempts (attempt_id,request_id,user_id,practice_item_id,result,independent,hint_level,process_evidence,evidence_hash,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)`).bind(attemptId, requestId, USER_ID, practiceItemId, attemptResult, independent ? 1 : 0, hintLevel, processEvidence, evidenceHash ?? null, createdAt).run()
    return result({ ok: true, attempt: { attemptId, practiceItemId, result: attemptResult, independent, hintLevel, createdAt }, version: baseVersion + 1, replayed: false })
  })

  server.registerTool('math_record_handwriting_analysis', {
    description: '保存手写过程逐行核对结果：先转写，再定位第一处分歧，并返回可生成透明 SVG/LaTeX HTML 的标注规范。初判保持 proposed；用户确认后再用 math_record_wrong_question 写入正式错题画像。',
    inputSchema: {
      requestId: z.uuid(),
      itemKind: z.enum(['ybt', 'practice', 'teacher_handout', 'other']),
      itemRef: z.string().min(1).max(240),
      sectionKey: z.string().max(80).optional(),
      imageEvidenceId: z.string().min(1).max(300),
      questionSourceVerified: z.boolean(),
      transcription: z.array(z.object({ line: z.number().int().min(1).max(100), text: z.string().min(1).max(1000), legibility: z.enum(['clear', 'partial', 'uncertain']) })).min(1).max(100),
      steps: z.array(z.object({
        line: z.number().int().min(1).max(100),
        status: z.enum(['correct', 'first_wrong', 'uncertain', 'downstream_contaminated']),
        explanation: z.string().min(1).max(1500),
        bbox: z.tuple([z.number().min(0).max(1), z.number().min(0).max(1), z.number().gt(0).max(1), z.number().gt(0).max(1)]).optional(),
        latex: z.string().max(4000).optional(),
        label: z.string().max(100).optional(),
      })).min(1).max(100),
      firstWrongStep: z.number().int().min(1).max(100).optional(),
      errorType: z.string().max(160).optional(),
      reason: z.string().max(3000).optional(),
      minimalCorrection: z.string().max(3000).optional(),
      downstreamStatus: z.enum(['clean', 'contaminated_after_first_error', 'uncertain']),
      confidence: z.enum(['high', 'medium', 'low']),
      analysisStatus: z.enum(['proposed', 'no_error', 'needs_clarification']).default('proposed'),
      uncertainties: z.array(z.string().min(1).max(1000)).max(20).default([]),
      clarificationRequest: z.string().max(1500).optional(),
      baseVersion: z.number().int().nonnegative(),
    },
  }, async ({ requestId, itemKind, itemRef, sectionKey, imageEvidenceId, questionSourceVerified, transcription, steps, firstWrongStep, errorType, reason, minimalCorrection, downstreamStatus, confidence, analysisStatus, uncertainties, clarificationRequest, baseVersion }) => {
    if (!writeAllowed()) return failure('insufficient_scope', WRITE_SCOPE)
    if (!questionSourceVerified && analysisStatus !== 'needs_clarification') return failure('question_source_required', '未核对原题时只能标记 needs_clarification')
    if (analysisStatus === 'proposed' && firstWrongStep === undefined) return failure('first_wrong_step_required', '发现错误时必须定位第一处错误行')
    if (analysisStatus === 'proposed' && steps.filter((step) => step.status === 'first_wrong').length !== 1) return failure('unique_first_wrong_required', 'proposed 分析必须且只能标记一处第一错误')
    if (firstWrongStep !== undefined && !steps.some((step) => step.line === firstWrongStep && step.status === 'first_wrong')) return failure('step_mismatch', 'firstWrongStep 必须对应 first_wrong 行')
    const hasUncertainLine = transcription.some((line) => line.legibility === 'uncertain') || steps.some((step) => step.status === 'uncertain')
    if ((confidence === 'low' || analysisStatus === 'needs_clarification' || hasUncertainLine) && uncertainties.length === 0) {
      return failure('uncertainty_disclosure_required', '存在低置信或看不清内容时，必须向用户列出具体不确定项')
    }
    if (analysisStatus === 'needs_clarification' && !clarificationRequest?.trim()) {
      return failure('clarification_request_required', '需要澄清时必须明确告诉用户补充什么')
    }
    const transcriptionLines = [...new Set(transcription.map((line) => line.line))].sort((a, b) => a - b)
    const stepLines = [...new Set(steps.map((step) => step.line))].sort((a, b) => a - b)
    if (transcriptionLines.length !== transcription.length || stepLines.length !== steps.length || JSON.stringify(transcriptionLines) !== JSON.stringify(stepLines)) {
      return failure('line_mapping_mismatch', '转写行与批改步骤必须使用唯一且完全相同的行号')
    }
    for (const step of steps) {
      if (!step.bbox) continue
      const [x, y, width, height] = step.bbox
      if (x + width > 1 || y + height > 1) return failure('bbox_out_of_bounds', '标注框必须完整位于原图范围内', { line: step.line, bbox: step.bbox })
    }
    const annotationSpec = handwritingAnnotationSpec(imageEvidenceId, steps as HandwritingStep[], uncertainties, clarificationRequest)
    const transcriptionJson = JSON.stringify(transcription); const stepsJson = JSON.stringify(steps)
    const uncertaintiesJson = JSON.stringify(uncertainties); const annotationSpecJson = JSON.stringify(annotationSpec)
    const existing = await env.DB.prepare(`SELECT * FROM handwriting_analyses WHERE request_id=? AND user_id=?`).bind(requestId, USER_ID).first<JsonRecord>()
    if (existing) {
      const same = existing.item_kind === itemKind && existing.item_ref === itemRef
        && existing.image_evidence_id === imageEvidenceId && existing.transcription_json === transcriptionJson
        && existing.steps_json === stepsJson && Number(existing.first_wrong_step ?? -1) === Number(firstWrongStep ?? -1)
        && existing.analysis_status === analysisStatus
        && String(existing.uncertainties_json ?? '[]') === uncertaintiesJson
        && (existing.clarification_request ?? null) === (clarificationRequest ?? null)
      return same ? result({ ok: true, analysis: existing, annotationSpec, replayed: true }) : failure('idempotency_conflict', 'requestId 已用于不同手写分析')
    }
    const count = await env.DB.prepare(`SELECT COUNT(*) AS count FROM handwriting_analyses WHERE user_id=? AND item_ref=?`).bind(USER_ID, itemRef).first<{ count: number | string }>()
    if (Number(count?.count ?? 0) !== baseVersion) return failure('version_conflict', '手写分析版本已变化', { expected: baseVersion, actual: Number(count?.count ?? 0) })
    const analysisId = crypto.randomUUID(); const createdAt = new Date().toISOString()
    await env.DB.prepare(`INSERT INTO handwriting_analyses (analysis_id,request_id,user_id,item_kind,item_ref,section_key,image_evidence_id,question_source_verified,transcription_json,steps_json,first_wrong_step,error_type,reason,minimal_correction,downstream_status,confidence,analysis_status,uncertainties_json,clarification_request,annotation_spec_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(analysisId, requestId, USER_ID, itemKind, itemRef, sectionKey ?? null, imageEvidenceId, questionSourceVerified ? 1 : 0, transcriptionJson, stepsJson, firstWrongStep ?? null, errorType ?? null, reason ?? null, minimalCorrection ?? null, downstreamStatus, confidence, analysisStatus, uncertaintiesJson, clarificationRequest ?? null, annotationSpecJson, createdAt).run()
    return result({
      ok: true,
      analysis: { analysisId, itemKind, itemRef, firstWrongStep: firstWrongStep ?? null, errorType: errorType ?? null, minimalCorrection: minimalCorrection ?? null, confidence, analysisStatus, createdAt },
      annotationSpec,
      version: baseVersion + 1,
      replayed: false,
    })
  })

  server.registerTool('math_record_memory', {
    description: '记录用户明确要求记忆或模型判断具有长期复用价值的数学记忆点。',
    inputSchema: {
      requestId: z.uuid(), itemId: z.string().max(200).optional(), sectionKey: z.string().max(80).optional(),
      title: z.string().min(1).max(200), content: z.string().min(1).max(4000), reason: z.string().min(1).max(1000),
      priority: z.enum(['high', 'normal', 'low']).default('normal'), userRequested: z.boolean().default(false),
    },
  }, async ({ requestId, itemId, sectionKey, title, content, reason, priority, userRequested }) => {
    if (!writeAllowed()) return failure('insufficient_scope', WRITE_SCOPE)
    const id = crypto.randomUUID(); const createdAt = new Date().toISOString()
    await env.DB.prepare(`INSERT INTO memory_items (memory_id, request_id, user_id, item_id, section_key, title, content, reason, priority, user_requested, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?) ON CONFLICT(request_id) DO NOTHING`).bind(id, requestId, USER_ID, itemId ?? null, sectionKey ?? null, title, content, reason, priority, userRequested ? 1 : 0, createdAt).run()
    const stored = await env.DB.prepare(`SELECT memory_id, item_id, section_key, title, content, reason, priority, user_requested, status, created_at FROM memory_items WHERE request_id = ? AND user_id = ?`).bind(requestId, USER_ID).first<JsonRecord>()
    return stored ? result({ ok: true, memory: stored, replayed: stored.memory_id !== id }) : failure('write_failed', '记忆点写入失败')
  })

  server.registerTool('math_record_type_classification', {
    description: '把一本通之外的新题归入已有题型，或记录一个经过解释的新题型。',
    inputSchema: { requestId: z.uuid(), itemId: z.string().max(200).optional(), sectionKey: z.string().max(80).optional(), clusterTitle: z.string().min(1).max(200), basis: z.string().min(1).max(2000), confidence: z.enum(['high', 'medium', 'low']).default('medium') },
  }, async ({ requestId, itemId, sectionKey, clusterTitle, basis, confidence }) => {
    if (!writeAllowed()) return failure('insufficient_scope', WRITE_SCOPE)
    const id = crypto.randomUUID(); const createdAt = new Date().toISOString()
    await env.DB.prepare(`INSERT INTO type_classifications (classification_id, request_id, user_id, item_id, section_key, cluster_title, basis, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(request_id) DO NOTHING`).bind(id, requestId, USER_ID, itemId ?? null, sectionKey ?? null, clusterTitle, basis, confidence, createdAt).run()
    const stored = await env.DB.prepare(`SELECT classification_id, item_id, section_key, cluster_title, basis, confidence, created_at FROM type_classifications WHERE request_id = ? AND user_id = ?`).bind(requestId, USER_ID).first<JsonRecord>()
    return stored ? result({ ok: true, classification: stored, replayed: stored.classification_id !== id }) : failure('write_failed', '题型归类写入失败')
  })

  server.registerTool('math_mark_item_passed', {
    description: '在具备冻结尝试证据且用户确认后记录题目通过；模型不能自行判定。',
    inputSchema: {
      requestId: z.uuid(),
      itemId: z.string().min(1).max(200),
      evidenceHash: z.string().regex(/^[0-9a-f]{64}$/),
      userConfirmed: z.boolean(),
      baseVersion: z.number().int().nonnegative(),
    },
  }, async ({ requestId, itemId, evidenceHash, userConfirmed, baseVersion }) => {
    if (!writeAllowed()) return failure('insufficient_scope', WRITE_SCOPE)
    if (!userConfirmed) return failure('confirmation_required', '题目通过需要用户确认')
    try {
      return result(await recordLearningEvent(env, requestId, 'item_passed', 'item', itemId, { userConfirmed: true }, evidenceHash, baseVersion))
    } catch (error) {
      return failure(error instanceof Error ? error.message : 'write_failed', '题目通过记录失败')
    }
  })

  return server
}

function protectedResourceMetadata(env: Env): Response {
  const config = oauthConfig(env)
  if (!config) return Response.json({ error: 'oauth_not_configured' }, { status: 503 })
  return Response.json({
    resource: config.audience,
    resource_name: 'Poyi Math Learning MCP',
    authorization_servers: [config.issuer],
    scopes_supported: [READ_SCOPE, WRITE_SCOPE],
    bearer_methods_supported: ['header'],
  }, { headers: { 'Cache-Control': 'public, max-age=300' } })
}

async function readiness(env: Env): Promise<Response> {
  try {
    const row = await env.DB.prepare(`SELECT COUNT(*) AS count FROM sqlite_master WHERE type = 'table' AND name IN ('source_versions','chapters','sections','items','courses','item_course_links','transcript_chunks','learning_events','learner_state','questions','answer_sources','learner_diagnostics','memory_items','type_classifications','wrong_question_exports','handout_sources','handout_pages','handout_course_links','practice_sources','practice_pages','practice_items','practice_route_links','practice_attempts','handwriting_analyses')`).first<{ count: number | string }>()
    const configured = oauthConfig(env) !== null
    const storageReady = Number(row?.count ?? 0) === 24
    const ready = storageReady && configured
    return Response.json({ ok: ready, service: 'math-learning-mcp', storage: storageReady ? 'ready' : 'migration_required', oauth: configured ? 'configured' : 'not_configured' }, { status: ready ? 200 : 503 })
  } catch {
    return Response.json({ ok: false, service: 'math-learning-mcp', storage: 'unavailable' }, { status: 503 })
  }
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url)
    if (request.method === 'GET' && url.pathname === '/healthz') {
      return Response.json({ ok: true, service: 'math-learning-mcp', protocol: '2026-07-28' })
    }
    if (request.method === 'GET' && url.pathname === '/readyz') return readiness(env)
    if (request.method === 'GET' && (url.pathname === '/.well-known/oauth-protected-resource/mcp' || url.pathname === '/.well-known/oauth-protected-resource')) {
      return protectedResourceMetadata(env)
    }
    if (url.pathname !== '/mcp') return Response.json({ error: 'not_found' }, { status: 404 })
    const scope = await requiredScope(request)
    const authorization = await authorize(request, env, scope)
    if (!authorization.ok) {
      const metadata = `${url.origin}/.well-known/oauth-protected-resource/mcp`
      return Response.json({ error: authorization.code }, {
        status: authorization.status,
        headers: {
          'Cache-Control': 'no-store',
          'WWW-Authenticate': `Bearer resource_metadata="${metadata}", error="${authorization.code}"`,
        },
      })
    }
    const handler = createMcpHandler(() => createServer(env, authorization.scopes), {
      route: '/mcp',
      legacy: 'stateless',
      allowedHostnames: [new URL(env.OAUTH_AUDIENCE!).hostname, 'localhost', '127.0.0.1'],
    })
    return handler(request, env, ctx)
  },
} satisfies ExportedHandler<Env>
