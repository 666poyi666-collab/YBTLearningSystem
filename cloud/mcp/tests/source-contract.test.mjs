import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const [source, packageText, schema, config] = await Promise.all([
  readFile(resolve(root, 'src/index.ts'), 'utf8'),
  readFile(resolve(root, 'package.json'), 'utf8'),
  readFile(resolve(root, 'migrations/0001_initial.sql'), 'utf8'),
  readFile(resolve(root, 'wrangler.jsonc'), 'utf8'),
])
const packageJson = JSON.parse(packageText)

test('uses the MCP 2026 stateless server path', () => {
  assert.match(source, /createMcpHandler/)
  assert.match(source, /@modelcontextprotocol\/server/)
  assert.doesNotMatch(source, /McpAgent|agents\/mcp['"]/)
  assert.equal(packageJson.dependencies['@modelcontextprotocol/server'], '2.0.0')
  assert.ok(Number(packageJson.dependencies.agents.match(/\d+\.\d+/)?.[0]) >= 0.2)
})

test('declares separate read and write scopes and idempotent writes', () => {
  assert.match(source, /math:read/)
  assert.match(source, /math:write/)
  assert.match(source, /ON CONFLICT\(request_id\) DO NOTHING/)
  assert.match(schema, /request_id TEXT NOT NULL UNIQUE/)
})

test('keeps content, state and authentication boundaries explicit', () => {
  assert.match(config, /"binding": "CONTENT"/)
  assert.match(config, /"binding": "DB"/)
  assert.match(config, /"OAUTH_RS_CLIENT_ID": "math-learning-mcp"/)
  assert.doesNotMatch(config, /OAUTH_RS_CLIENT_SECRET|Bearer\s+[A-Za-z0-9]/)
})
