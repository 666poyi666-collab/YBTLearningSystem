#!/usr/bin/env node

/** Build idempotent SQL from facts already confirmed in the user's snapshot/chat. */

import { createHash } from 'node:crypto'
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const cloudRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const repoRoot = resolve(cloudRoot, '..', '..')
const output = join(repoRoot, 'tmp', 'backfill-confirmed-learning.sql')
const userId = 'poyi-owner'
const snapshotRequestId = '9a1e8f2c-6b73-4a5d-9c10-2f7e6d8b4a31'
const createdAt = new Date().toISOString()

function s(value) {
  if (value === null || value === undefined) return 'NULL'
  return `'${String(value).replaceAll("'", "''")}'`
}

function confirmedSnapshotExists() {
  return `EXISTS (SELECT 1 FROM learning_events WHERE user_id = ${s(userId)} AND request_id = ${s(snapshotRequestId)} AND event_type = 'progress_snapshot_synced')`
}

const wrongQuestions = [
  {
    requestId: 'db8e64b7-8e26-4b48-a842-67ac02f6e409',
    diagnosticId: '8cf22a4d-b477-4c03-ab4b-5aa4d6ac0371',
    classificationId: 'b8a6646e-b6e1-4f80-b052-c24a8a1a6311',
    itemId: '8915857a2181490b', sectionKey: '1.1',
    errorType: '运算结构与括号拆分', errorDirection: '代入向量恒等式时对括号、系数和正负号的保留不稳定',
    evidenceText: '例9第2问曾卡在括号与向量拆分，随后已理解并完成核对。',
    userCorrection: '代入前先完整保留括号和外部系数，再逐项分配并合并同类向量。',
    finalStatus: 'confirmed_correct', clusterTitle: '空间向量线性运算与拆分',
    basis: '核心动作是按线性运算顺序处理括号、系数和同类向量。', confidence: 'high',
  },
  {
    requestId: '9f3b4718-fc3e-402a-bff3-fc87fb029953',
    diagnosticId: 'bb038f59-7c3d-42af-8204-bf8ebf405ec7',
    classificationId: '98ee173d-ce62-4e5a-89f6-97d2fc0c252d',
    itemId: '1bc60321129e778d', sectionKey: '1.1',
    errorType: '概念辨析', errorDirection: '零向量共线特例、向量平行与直线平行的条件曾混淆',
    evidenceText: '例4出现概念错误，已在对话中纠正并确认掌握相关边界。',
    userCorrection: '分别判断向量共线、向量平行和所在直线平行，单独检查零向量特例。',
    finalStatus: 'confirmed_correct', clusterTitle: '空间向量共线概念辨析',
    basis: '题目考查定义边界和零向量特例，而不是单纯计算。', confidence: 'high',
  },
  {
    requestId: 'ef3216f8-cbd6-4d03-a8fe-518d1b2b1710',
    diagnosticId: '7f128b19-5c33-4f11-a1b8-437e11e16fac',
    classificationId: '0bfb823c-2333-40d9-8be7-2ff9fda29438',
    itemId: 'Q-c71c166fd308bd39', sectionKey: '1.1',
    errorType: '符号错误与方法辨析', errorDirection: '将负二分之一 EI 误作正号，并一度把中点向量恒等式与极化恒等式混淆',
    evidenceText: 'B10在提示后用两种方法完成；对话核对到 GH 中 EI 前负号遗漏，并纠正四面体对棱相交的错误理解。',
    userCorrection: '统一到共起点三基底，保留每一步符号；中点向量恒等式只涉及线性运算，不等同于涉及数量积和模长平方的极化恒等式。',
    finalStatus: 'confirmed_correct', clusterTitle: '四面体中点向量与共起点三基底',
    basis: '通过中点向量关系和共起点基底证明三点共线或中点结论。', confidence: 'high',
  },
]

const memories = [
  ['14bfe7df-e245-47df-9189-b11263a646d2', '44c3ebfc-f1a3-4833-86a6-26aac060277b', 'Q-c71c166fd308bd39', '代入前保留负号与括号', '遇到 -1/2·EI 这类式子，先原样写出外部负号和系数，再代入 EI 的表达式，最后逐项化简。', 'B10 已出现一次负号遗漏，属于可迁移的计算检查点。'],
  ['96bc89f7-d178-4cfb-9c2a-9d814b9a2b98', '5a3938dc-dafa-4317-b44e-e8b266e5ea08', 'Q-c71c166fd308bd39', '中点向量恒等式不等于极化恒等式', '2MN=AC+BD=AD+BC 是中点向量的线性恒等式；极化恒等式涉及数量积和模长平方。', '对话中曾把两类恒等式混淆，需要长期区分。'],
  ['12f082d6-d64b-47ac-b048-c151640206a8', '314bf04a-33a2-41e0-a148-c883a27e1787', 'Q-c71c166fd308bd39', '四面体对棱通常异面', '四面体中的 AC 与 BD 等对棱通常是异面直线，不应因为中点向量恒等式成立就认为它们相交。', '这是空间几何图形关系的关键边界。'],
]

const statements = []
for (const row of wrongQuestions) {
  statements.push(`INSERT INTO learner_diagnostics (diagnostic_id, request_id, user_id, item_id, section_key, error_type, error_direction, evidence_text, user_correction, final_status, created_at) SELECT ${s(row.diagnosticId)}, ${s(row.requestId)}, ${s(userId)}, ${s(row.itemId)}, ${s(row.sectionKey)}, ${s(row.errorType)}, ${s(row.errorDirection)}, ${s(row.evidenceText)}, ${s(row.userCorrection)}, ${s(row.finalStatus)}, ${s(createdAt)} WHERE ${confirmedSnapshotExists()} ON CONFLICT(request_id) DO NOTHING;`)
  statements.push(`INSERT INTO type_classifications (classification_id, request_id, user_id, item_id, section_key, cluster_title, basis, confidence, created_at) SELECT ${s(row.classificationId)}, ${s(row.requestId)}, ${s(userId)}, ${s(row.itemId)}, ${s(row.sectionKey)}, ${s(row.clusterTitle)}, ${s(row.basis)}, ${s(row.confidence)}, ${s(createdAt)} WHERE ${confirmedSnapshotExists()} ON CONFLICT(request_id) DO NOTHING;`)
}
for (const [memoryId, requestId, itemId, title, content, reason] of memories) {
  statements.push(`INSERT INTO memory_items (memory_id, request_id, user_id, item_id, section_key, title, content, reason, priority, user_requested, status, created_at) SELECT ${s(memoryId)}, ${s(requestId)}, ${s(userId)}, ${s(itemId)}, '1.1', ${s(title)}, ${s(content)}, ${s(reason)}, 'high', 0, 'active', ${s(createdAt)} WHERE ${confirmedSnapshotExists()} ON CONFLICT(request_id) DO NOTHING;`)
}

const deferRequestId = '3ecb111a-15a5-4502-bc32-5ed5cd04322f'
const deferEventId = 'ab2cdf36-8b07-41bd-b2f8-a8489d1d3e49'
const deferPayload = {
  title: '空间向量等值面法', status: 'deferred', reason: '用户明确说“先跳过这个循环”', userConfirmed: true,
  nextTask: { cycle: '1.1-cycle-4', title: '共面证明', courseKey: 'coplanar' },
}
const evidenceHash = createHash('sha256').update('先跳过这个循环').digest('hex')
statements.push(`INSERT INTO learning_events (event_id, request_id, user_id, event_type, subject_type, subject_id, payload_json, evidence_hash, base_version, created_at) VALUES (${s(deferEventId)}, ${s(deferRequestId)}, ${s(userId)}, 'cycle_deferred', 'cycle', '1.1-cycle-3', ${s(JSON.stringify(deferPayload))}, ${s(evidenceHash)}, NULL, ${s(createdAt)}) ON CONFLICT(request_id) DO NOTHING;`)
statements.push(`INSERT INTO learner_state (user_id, state_key, version, value_json, updated_at) VALUES (${s(userId)}, 'cycle:1.1-cycle-3', 1, ${s(JSON.stringify({ ...deferPayload, subjectType: 'cycle', subjectId: '1.1-cycle-3', source: 'cloud_mcp_confirmed_backfill', sourceRequestId: deferRequestId }))}, ${s(createdAt)}) ON CONFLICT(user_id, state_key) DO UPDATE SET version = learner_state.version + CASE WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${s(deferRequestId)} THEN 0 ELSE 1 END, value_json = CASE WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${s(deferRequestId)} THEN learner_state.value_json ELSE excluded.value_json END, updated_at = CASE WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${s(deferRequestId)} THEN learner_state.updated_at ELSE excluded.updated_at END;`)
statements.push(`INSERT INTO learner_state (user_id, state_key, version, value_json, updated_at) VALUES (${s(userId)}, 'current_task', 1, ${s(JSON.stringify({ chapter: '1', section: '1.1', cycle: '1.1-cycle-4', title: '共面证明', courseKey: 'coplanar', status: 'not_started', deferredCycle: '1.1-cycle-3', source: 'cloud_mcp_confirmed_backfill', sourceRequestId: deferRequestId }))}, ${s(createdAt)}) ON CONFLICT(user_id, state_key) DO UPDATE SET version = learner_state.version + CASE WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${s(deferRequestId)} THEN 0 ELSE 1 END, value_json = CASE WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${s(deferRequestId)} THEN learner_state.value_json ELSE excluded.value_json END, updated_at = CASE WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${s(deferRequestId)} THEN learner_state.updated_at ELSE excluded.updated_at END;`)
statements.push(`INSERT INTO learner_state (user_id, state_key, version, value_json, updated_at) VALUES (${s(userId)}, 'section:1.1', 1, ${s(JSON.stringify({ chapter: '1', section: '1.1', status: 'in_progress', completedCycleCount: 2, deferredCycles: ['1.1-cycle-3'], currentCycle: '1.1-cycle-4', source: 'cloud_mcp_confirmed_backfill', sourceRequestId: deferRequestId }))}, ${s(createdAt)}) ON CONFLICT(user_id, state_key) DO UPDATE SET version = learner_state.version + CASE WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${s(deferRequestId)} THEN 0 ELSE 1 END, value_json = CASE WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${s(deferRequestId)} THEN learner_state.value_json ELSE excluded.value_json END, updated_at = CASE WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${s(deferRequestId)} THEN learner_state.updated_at ELSE excluded.updated_at END;`)

await mkdir(dirname(output), { recursive: true })
await writeFile(output, `${statements.join('\n')}\n`, 'utf8')
console.log(output)
