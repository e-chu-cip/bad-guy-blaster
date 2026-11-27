import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
import {onRequest} from '../functions/api/[[path]].js';

function service(variant = 'classic-10-v1') {
  const db = new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('../migrations/0001_scores.sql', import.meta.url), 'utf8'));
  class Statement {
    constructor(sql, values = []) { this.sql = sql; this.values = values; }
    bind(...values) { return new Statement(this.sql, values); }
    async first() { return db.prepare(this.sql).get(...this.values) || null; }
    async all() { return {results: db.prepare(this.sql).all(...this.values)}; }
    async run() { return db.prepare(this.sql).run(...this.values); }
  }
  const env = {GAME_VARIANT: variant, GAME_DB: {
    prepare: sql => new Statement(sql),
    async batch(statements) {
      db.exec('BEGIN');
      try { const results = []; for (const statement of statements) results.push(await statement.run()); db.exec('COMMIT'); return results; }
      catch (error) { db.exec('ROLLBACK'); throw error; }
    }
  }};
  async function request(path, body, origin = 'https://bad-guy-blaster.pages.dev') {
    const options = body ? {method: 'POST', body: JSON.stringify(body), headers: {'Origin': origin}} : {};
    const response = await onRequest({request: new Request(`https://bad-guy-blaster.pages.dev/api/${path}`, options), env});
    return {status: response.status, data: await response.json()};
  }
  const credentials = () => ({id: randomUUID(), token: randomUUID(), variant});
  return {db, request, credentials};
}

test('start retries count once; authentication and origin are checked', async () => {
  const {db, request, credentials} = service();
  const run = credentials();
  assert.equal((await request('start', run)).status, 200);
  assert.equal((await request('start', run)).status, 200);
  assert.equal((await request('board')).data.plays, 1);
  assert.equal((await request('progress', {...run, token: randomUUID(), level: 1, total_ms: 1000})).status, 403);
  assert.equal((await request('start', credentials(), 'https://other.example')).status, 403);
  db.close();
});

test('ordered checkpoints, exact retries, elapsed sanity checks and immutable submissions', async () => {
  const {db, request, credentials} = service();
  const run = credentials();
  await request('start', run);
  assert.equal((await request('progress', {...run, level: 2, total_ms: 2000})).status, 409);
  assert.equal((await request('progress', {...run, level: 1, total_ms: -5})).status, 400);
  assert.equal((await request('progress', {...run, level: 1, total_ms: 999999})).status, 400);
  assert.equal((await request('progress', {...run, level: 1, total_ms: 1000})).status, 200);
  assert.equal((await request('progress', {...run, level: 1, total_ms: 1000})).status, 200);
  assert.equal((await request('progress', {...run, level: 1, total_ms: 500})).status, 409);
  assert.equal((await request('finish', {...run, nickname: '<script>'})).status, 400);
  assert.equal((await request('finish', {...run, nickname: 'Rocket'})).status, 200);
  await request('finish', {...run, nickname: 'Changed'});
  assert.equal((await request('board')).data.board[0].nickname, 'Rocket');
  assert.equal((await request('progress', {...run, level: 2, total_ms: 2000})).status, 409);
  assert.equal(db.prepare('SELECT COUNT(*) AS count FROM splits').get().count, 1);
  db.close();
});

test('top ten orders by progress then time; unfinished and zero-progress runs stay private', async () => {
  const {db, request, credentials} = service();
  for (let i = 0; i < 13; i++) {
    const run = credentials();
    await request('start', run);
    for (let level = 1; level <= (i % 3) + 1; level++) {
      assert.equal((await request('progress', {...run, level, total_ms: level * (1000 + i * 10)})).status, 200);
    }
    if (i < 12) await request('finish', {...run, nickname: `Player-${i}`});
  }
  const zero = credentials();
  await request('start', zero); await request('finish', {...zero, nickname: 'NoLevels'});
  const result = (await request('board')).data;
  assert.equal(result.plays, 14);
  assert.equal(result.board.length, 10);
  assert.equal(result.board[0].nickname, 'Player-2');
  for (let i = 1; i < result.board.length; i++) {
    const a = result.board[i - 1], b = result.board[i];
    assert.ok(a.completed > b.completed || (a.completed === b.completed && a.total_ms <= b.total_ms));
  }
  assert.ok(!result.board.some(row => ['Player-12', 'NoLevels'].includes(row.nickname)));
  db.close();
});

test('experimental and production versions cannot mix scores', async () => {
  const {db, request, credentials} = service('experimental-15-v1');
  assert.equal((await request('start', {...credentials(), variant: 'classic-10-v1'})).status, 400);
  assert.equal((await request('board')).data.variant, 'experimental-15-v1');
  db.close();
});

test('custom nickname is acknowledged and appears on the leaderboard after clearing a level', async () => {
  const {db, request, credentials} = service();
  const run = credentials();
  await request('start', run);
  await request('progress', {...run, level: 1, total_ms: 1000});
  const saved = await request('finish', {...run, nickname: 'TURTLE'});
  assert.deepEqual(saved.data, {ok: true, nickname: 'TURTLE', completed: 1, eligible: true, rank: 1});
  assert.equal((await request('board')).data.board[0].nickname, 'TURTLE');
  const retried = await request('finish', {...run, nickname: 'Different'});
  assert.equal(retried.data.nickname, 'TURTLE');
  db.close();
});

test('zero-level custom submission is saved but explicitly reported as not eligible', async () => {
  const {db, request, credentials} = service();
  const run = credentials();
  await request('start', run);
  const saved = await request('finish', {...run, nickname: 'testing123'});
  assert.deepEqual(saved.data, {ok: true, nickname: 'testing123', completed: 0, eligible: false, rank: null});
  assert.equal(db.prepare('SELECT nickname FROM runs WHERE id = ?').get(run.id).nickname, 'testing123');
  assert.equal((await request('board')).data.board.length, 0);
  db.close();
});

test('saved run outside top ten receives its true rank', async () => {
  const {db, request, credentials} = service();
  for (let i = 0; i < 11; i++) {
    const run = credentials();
    await request('start', run);
    await request('progress', {...run, level: 1, total_ms: 1000 + i});
    const saved = await request('finish', {...run, nickname: `Custom-${i}`});
    assert.equal(saved.data.rank, i + 1);
  }
  assert.equal((await request('board')).data.board.length, 10);
  db.close();
});
