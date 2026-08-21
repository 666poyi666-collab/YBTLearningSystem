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

async function requiredScope(request: Request): Promise<Scope> {
  const headerName = request.headers.get('mcp-name')
  if (headerName) return headerName.startsWith('math_record_') || headerName.startsWith('math_mark_') || headerName === 'math_sync_progress_snapshot'
    ? WRITE_SCOPE
    : READ_SCOPE
  try {
    const rpc = await request.clone().json<{ method?: string; params?: { name?: string } }>()
    const name = rpc.params?.name ?? ''
    return rpc.method === 'tools/call' && (name.startsWith('math_record_') || name.startsWith('math_mark_') || name === 'math_sync_progress_snapshot')
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

async function systemStatus(env: Env) {
  const row = await env.DB.prepare(`
    SELECT
      (SELECT COUNT(*) FROM chapters) AS chapters,
      (SELECT COUNT(*) FROM sections) AS sections,
      (SELECT COUNT(*) FROM items) AS items,
      (SELECT COUNT(*) FROM courses) AS courses,
      (SELECT COUNT(*) FROM transcript_chunks) AS transcript_chunks,
      (SELECT COUNT(*) FROM learning_events WHERE user_id = ?) AS learning_events
  `).bind(USER_ID).first<Record<string, number | string>>()
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
  if (!replayed && eventType !== 'progress_snapshot_synced') {
    await projectEventState(env, eventType, subjectType, subjectId, payload, baseVersion, createdAt)
  }
  return {
    ok: true,
    eventId: stored.event_id,
    requestId,
    replayed,
    createdAt: stored.created_at,
  }
}

async function projectEventState(
  env: Env,
  eventType: string,
  subjectType: string,
  subjectId: string,
  payload: JsonRecord,
  baseVersion: number | undefined,
  updatedAt: string,
) {
  const stateKey = `${subjectType}:${subjectId}`
  const existing = await env.DB.prepare(`SELECT version FROM learner_state WHERE user_id = ? AND state_key = ?`)
    .bind(USER_ID, stateKey).first<{ version: number | string }>()
  const currentVersion = Number(existing?.version ?? 0)
  if (baseVersion !== undefined && currentVersion !== baseVersion) throw new Error('version_conflict')
  const value = {
    ...payload,
    status: eventType,
    subjectType,
    subjectId,
    source: 'cloud_mcp_event_projection',
  }
  await env.DB.prepare(`
    INSERT INTO learner_state (user_id, state_key, version, value_json, updated_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(user_id, state_key) DO UPDATE SET
      version = excluded.version,
      value_json = excluded.value_json,
      updated_at = excluded.updated_at
  `).bind(USER_ID, stateKey, currentVersion + 1, JSON.stringify(value), updatedAt).run()
}

function createServer(env: Env, scopes: readonly string[]): McpServer {
  const server = new McpServer(PROJECT, {
    instructions:
      '这是一本通数学学习系统。讲题前先调用 math_get_section_overview 定位节次，再调用 math_get_item_content 获取完整题面和题图、math_get_course_transcript 获取完整老师文稿，最后读取真实学习进度；课程覆盖、用户已学、题目已通过和冷复测是不同状态。不要只凭标题或 R2 键猜题目，不要输出未请求的答案，不要把内部模拟进度当成真实用户进度。',
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
    const row = await env.DB.prepare(`SELECT COUNT(*) AS count FROM sqlite_master WHERE type = 'table' AND name IN ('source_versions','items','courses','transcript_chunks','learning_events','learner_state','questions')`).first<{ count: number | string }>()
    const configured = oauthConfig(env) !== null
    const ready = Number(row?.count ?? 0) === 7 && configured
    return Response.json({ ok: ready, service: 'math-learning-mcp', storage: Number(row?.count ?? 0) === 7 ? 'ready' : 'migration_required', oauth: configured ? 'configured' : 'not_configured' }, { status: ready ? 200 : 503 })
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
