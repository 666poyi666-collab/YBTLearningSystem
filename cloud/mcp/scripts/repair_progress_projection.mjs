#!/usr/bin/env node

/**
 * One-time, idempotent repair for snapshots written before progress projection
 * was implemented.  It never alters learning_events; it derives learner_state
 * rows from the latest confirmed progress snapshot and tags them with that
 * event's request_id so replaying this repair is a no-op.
 */

import { readFile, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const cloudRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const repoRoot = resolve(cloudRoot, '..', '..')
const output = join(repoRoot, 'tmp', 'repair-progress-projection.sql')

const requestId = '9a1e8f2c-6b73-4a5d-9c10-2f7e6d8b4a31'
const eventId = '22122224-1aee-46af-b3c1-928dac779bbc'
const snapshotCreatedAt = '2026-08-23T06:08:12.597Z'

function sqlString(value) {
  if (value === null || value === undefined) return 'NULL'
  return `'${String(value).replaceAll("'", "''")}'`
}

function stateStatement(key, value) {
  const json = JSON.stringify({ ...value, sourceRequestId: requestId })
  return `
INSERT INTO learner_state (user_id, state_key, version, value_json, updated_at)
SELECT 'poyi-owner', ${sqlString(key)}, 1, ${sqlString(json)}, ${sqlString(snapshotCreatedAt)}
WHERE EXISTS (
  SELECT 1 FROM learning_events
  WHERE user_id = 'poyi-owner' AND event_id = ${sqlString(eventId)}
    AND request_id = ${sqlString(requestId)}
)
ON CONFLICT(user_id, state_key) DO UPDATE SET
  version = learner_state.version + CASE
    WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${sqlString(requestId)} THEN 0 ELSE 1 END,
  value_json = CASE
    WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${sqlString(requestId)} THEN learner_state.value_json ELSE excluded.value_json END,
  updated_at = CASE
    WHEN json_extract(learner_state.value_json, '$.sourceRequestId') = ${sqlString(requestId)} THEN learner_state.updated_at ELSE excluded.updated_at END;
`.trim()
}

const states = [
  ['current_task', {
    chapter: '1', section: '1.1', cycle: '1.1-cycle-3', status: 'not_started',
    title: '空间向量等值面法', source: 'cloud_mcp_progress_snapshot_repair',
  }],
  ['cycle:1.1-cycle-1', {
    cycleId: '1.1-cycle-1', chapter: '1', section: '1.1',
    title: '空间向量概念与线性运算', status: 'completed',
    confirmedItems: ['例1', '例2', '例3', '例9', '例10', 'A1', 'A2', 'A3'],
    notes: '例题与A组均已核对正确；例9第2问曾卡在括号与向量拆分，已理解。',
    source: 'cloud_mcp_progress_snapshot_repair',
  }],
  ['cycle:1.1-cycle-2', {
    cycleId: '1.1-cycle-2', chapter: '1', section: '1.1',
    title: '共线概念与向量拆分', status: 'completed',
    confirmedItems: ['例4', '例11', '例11变式1', '例11变式2', 'B10'],
    notes: '例4概念错误已纠正；已掌握零向量共线特例、向量平行与直线平行区别、三点共线的向量判定、共起点三基底表示及四面体中点题。B10在提示后已能用两种方法完成。',
    source: 'cloud_mcp_progress_snapshot_repair',
  }],
  ['course:space_vector_ops', {
    courseKey: 'space_vector_ops', title: '3.1.1.1 空间向量的运算',
    status: 'course_listened', source: 'cloud_mcp_progress_snapshot_repair',
  }],
  ['course:decomposition', {
    courseKey: 'decomposition', title: '3.1.2.1 空间向量拆分法',
    status: 'course_listened', source: 'cloud_mcp_progress_snapshot_repair',
  }],
  ['section:1.1', {
    chapter: '1', section: '1.1', status: 'in_progress', completedCycleCount: 2,
    currentCycle: '1.1-cycle-3', source: 'cloud_mcp_progress_snapshot_repair',
  }],
]

const sql = `${states.map(([key, value]) => stateStatement(key, value)).join('\n\n')}\n`
await writeFile(output, sql, 'utf8')
const check = await readFile(output, 'utf8')
if (!check.includes(requestId) || !check.includes('1.1-cycle-3')) throw new Error('repair SQL validation failed')
console.log(output)
