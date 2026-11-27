CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  token_hash TEXT NOT NULL,
  variant TEXT NOT NULL,
  started_at INTEGER NOT NULL,
  completed INTEGER NOT NULL DEFAULT 0,
  total_ms INTEGER NOT NULL DEFAULT 0,
  finished INTEGER NOT NULL DEFAULT 0,
  nickname TEXT NOT NULL DEFAULT 'Player',
  finished_at INTEGER
);
CREATE TABLE IF NOT EXISTS splits (
  run_id TEXT NOT NULL REFERENCES runs(id),
  level INTEGER NOT NULL,
  level_ms INTEGER NOT NULL,
  total_ms INTEGER NOT NULL,
  PRIMARY KEY (run_id, level)
);
CREATE TABLE IF NOT EXISTS play_counts (variant TEXT PRIMARY KEY, plays INTEGER NOT NULL DEFAULT 0);
CREATE TRIGGER IF NOT EXISTS count_new_game AFTER INSERT ON runs BEGIN
  INSERT INTO play_counts(variant, plays) VALUES (NEW.variant, 1)
  ON CONFLICT(variant) DO UPDATE SET plays = plays + 1;
END;
CREATE INDEX IF NOT EXISTS leaderboard_order
  ON runs(variant, finished, completed DESC, total_ms, finished_at);
