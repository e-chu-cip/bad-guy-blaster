const headers = {"Content-Type": "application/json", "Cache-Control": "no-store"};
const reply = (data, status = 200) => new Response(JSON.stringify(data), {status, headers});
const idPattern = /^[a-f0-9-]{36}$/;

async function hash(value) {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value))))
    .map(x => x.toString(16).padStart(2, "0")).join("");
}

export async function onRequest({request, env}) {
  const url = new URL(request.url);
  const action = url.pathname.split("/").filter(Boolean).at(-1);
  const variant = env.GAME_VARIANT || (url.hostname === "bad-guy-blaster.pages.dev"
    ? "classic-10-v1" : "experimental-15-v1");
  const maxLevel = variant === "classic-10-v1" ? 10 : 15;
  if (!env.GAME_DB) return reply({error: "Online scores are not configured yet."}, 503);
  if (request.headers.get("Origin") && request.headers.get("Origin") !== url.origin)
    return reply({error: "Cross-site requests are not allowed."}, 403);
  try {
    if (action === "board" && request.method === "GET") {
      const count = await env.GAME_DB.prepare("SELECT plays FROM play_counts WHERE variant = ?").bind(variant).first();
      const board = await env.GAME_DB.prepare(`SELECT nickname, completed, total_ms FROM runs
        WHERE variant = ? AND finished = 1 AND completed > 0
        ORDER BY completed DESC, total_ms ASC, finished_at ASC, id ASC LIMIT 10`).bind(variant).all();
      return reply({variant, plays: count?.plays || 0, board: board.results});
    }
    if (request.method !== "POST" || !["start", "progress", "finish"].includes(action))
      return reply({error: "Not found."}, 404);
    const raw = await request.text();
    if (raw.length > 2048) return reply({error: "Request too large."}, 413);
    const body = JSON.parse(raw);
    if (!idPattern.test(body.id || "") || !idPattern.test(body.token || ""))
      return reply({error: "Invalid run credentials."}, 400);
    const tokenHash = await hash(body.token);
    const now = Date.now();
    if (action === "start") {
      if (body.variant !== variant) return reply({error: "This game uses a different leaderboard."}, 400);
      await env.GAME_DB.prepare(`INSERT INTO runs(id, token_hash, variant, started_at)
        VALUES (?, ?, ?, ?) ON CONFLICT(id) DO NOTHING`).bind(body.id, tokenHash, variant, now).run();
    }
    const run = await env.GAME_DB.prepare("SELECT * FROM runs WHERE id = ?").bind(body.id).first();
    if (!run || run.token_hash !== tokenHash || run.variant !== variant)
      return reply({error: "Unknown run."}, 403);
    if (action === "start") return reply({ok: true});
    if (action === "progress") {
      const level = body.level, total = body.total_ms;
      if (!Number.isInteger(level) || level < 1 || level > maxLevel || !Number.isInteger(total)
          || total < 1 || total > 86_400_000 || total > now - run.started_at + 10_000)
        return reply({error: "Invalid level time."}, 400);
      const existing = await env.GAME_DB.prepare("SELECT total_ms FROM splits WHERE run_id = ? AND level = ?")
        .bind(body.id, level).first();
      if (existing) return existing.total_ms === total ? reply({ok: true}) : reply({error: "Level already recorded."}, 409);
      if (run.finished || level !== run.completed + 1 || total <= run.total_ms)
        return reply({error: "Levels must be completed in order."}, 409);
      await env.GAME_DB.batch([
        env.GAME_DB.prepare(`INSERT INTO splits(run_id, level, level_ms, total_ms)
          SELECT id, ?, ? - total_ms, ? FROM runs WHERE id = ? AND completed = ? AND finished = 0
          ON CONFLICT(run_id, level) DO NOTHING`).bind(level, total, total, body.id, level - 1),
        env.GAME_DB.prepare(`UPDATE runs SET completed = ?, total_ms = ?
          WHERE id = ? AND completed = ? AND finished = 0`).bind(level, total, body.id, level - 1),
      ]);
      return reply({ok: true});
    }
    const nickname = typeof body.nickname === "string" ? body.nickname.trim() : "";
    if (!/^[A-Za-z0-9 _-]{1,16}$/.test(nickname)) return reply({error: "Use a nickname of 1-16 letters, numbers, spaces, _ or -."}, 400);
    if (!run.finished) await env.GAME_DB.prepare(`UPDATE runs SET finished = 1, nickname = ?, finished_at = ? WHERE id = ? AND finished = 0`)
      .bind(nickname, now, body.id).run();
    const saved = await env.GAME_DB.prepare("SELECT nickname, completed, total_ms, finished_at FROM runs WHERE id = ?")
      .bind(body.id).first();
    let rank = null;
    if (saved.completed > 0) {
      const ahead = await env.GAME_DB.prepare(`SELECT COUNT(*) AS count FROM runs
        WHERE variant = ? AND finished = 1 AND completed > 0 AND (
          completed > ? OR (completed = ? AND total_ms < ?) OR
          (completed = ? AND total_ms = ? AND finished_at < ?) OR
          (completed = ? AND total_ms = ? AND finished_at = ? AND id < ?))`)
        .bind(variant, saved.completed, saved.completed, saved.total_ms,
          saved.completed, saved.total_ms, saved.finished_at,
          saved.completed, saved.total_ms, saved.finished_at, body.id).first();
      rank = ahead.count + 1;
    }
    return reply({ok: true, nickname: saved.nickname, completed: saved.completed,
      eligible: saved.completed > 0, rank});
  } catch (error) {
    if (error instanceof SyntaxError) return reply({error: "Invalid JSON."}, 400);
    console.error("Game scores service failed", error.message);
    return reply({error: "Scores are temporarily unavailable. Your game can continue."}, 503);
  }
}
