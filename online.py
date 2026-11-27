"""Shared timers, optional online scores, and results UI for both game versions."""

from collections import deque
import json
import sys
import uuid

import pygame

ONLINE_HELP_PAGE = ("Times and leaderboard", (
    "Level time measures this level; Total time measures the whole run.",
    "Math questions and Hide Out visits count toward your time.",
    "Bag, store, level results, and leaderboards pause the clock.",
    "After a level, see your times and choose Continue or Leaderboard.",
    "After winning or losing, type a nickname and Submit Result.",
    "Top 10 ranks most levels completed, then fastest cumulative time.",
    "Production and experimental games have separate leaderboards.",
    "Test Mode runs show timers but are not counted or ranked.",
    "Leaderboard on the main menu also shows how many games started.",
    "Only normal hosted browser games can count or submit results.",
))


def format_time(milliseconds):
    tenths = max(0, int(milliseconds)) // 100
    seconds, tenth = divmod(tenths, 10)
    minutes, second = divmod(seconds, 60)
    return f"{minutes}:{second:02d}.{tenth}"


class RunClock:
    def __init__(self):
        self.started = False
        self.test = False
        self.saved = 0
        self.resumed_at = None
        self.level_base = 0
        self.splits = []

    def start(self, now, test=False):
        self.started = True
        self.test = test
        self.resumed_at = now

    def total(self, now):
        return self.saved + (max(0, now - self.resumed_at) if self.resumed_at is not None else 0)

    def pause(self, now):
        self.saved = self.total(now)
        self.resumed_at = None

    def resume(self, now):
        if self.started and self.resumed_at is None:
            self.resumed_at = now

    def next_level(self, now):
        self.level_base = self.total(now)

    def complete(self, level, now):
        self.pause(now)
        split = {"level": level, "level_ms": self.saved - self.level_base, "total_ms": self.saved}
        if not self.splits or self.splits[-1]["level"] != level:
            self.splits.append(split)
        return split


class ScoresClient:
    """Nonblocking, ordered requests: a repeated start never counts twice."""
    def __init__(self):
        self.pending = deque()
        self.current = None
        self.retry_at = 0
        self.board = []
        self.plays = None
        self.submissions = {}
        self.status = "Online scores load in the browser. Local games are not counted."
        self.enabled = sys.platform == "emscripten"
        self.bridge = None

    def send(self, path, body=None):
        if self.enabled:
            self.pending.append({"path": path, "body": body, "attempt": 0})
            if path == "finish":
                self.submissions[body["id"]] = {"state": "pending",
                    "message": f"Saving as {body['nickname']}... Keep this page open."}

    def update(self, now):
        if not self.enabled:
            return
        try:
            if self.bridge is None:
                import platform
                self.bridge = platform.window.gameScores
            if self.current:
                raw = str(self.bridge.poll(self.current[0]))
                if not raw:
                    return
                item = self.current[1]
                self.current = None
                response = json.loads(raw)
                if response["ok"]:
                    self.status = "Connected."
                    if item["path"] == "board":
                        self.board = response["data"]["board"]
                        self.plays = response["data"]["plays"]
                    elif item["path"] == "finish":
                        saved = response["data"]
                        name = saved["nickname"]
                        if not saved["eligible"]:
                            message = f"Saved as {name}. Clear at least 1 level to enter the top 10."
                        elif saved["rank"] <= 10:
                            message = f"Saved as {name}. Leaderboard rank: #{saved['rank']}."
                        else:
                            message = f"Saved as {name}. Rank #{saved['rank']} (outside the top 10)."
                        self.submissions[item["body"]["id"]] = {"state": "saved", "message": message}
                        self.status = message
                        self.send("board")
                elif response["status"] in (0, 429, 503):
                    item["attempt"] += 1
                    self.pending.appendleft(item)
                    self.retry_at = now + min(30_000, 1000 * 2 ** min(item["attempt"], 5))
                    self.status = "Scores offline; retrying. Gameplay can continue."
                    if item["path"] == "finish":
                        self.submissions[item["body"]["id"]] = {"state": "pending",
                            "message": "Result not saved yet; retrying. Keep this page open."}
                else:
                    self.status = response["data"].get("error", "Result could not be saved.")
                    if item["path"] == "finish":
                        self.submissions[item["body"]["id"]] = {"state": "failed",
                            "message": "Not saved: " + self.status}
            if not self.current and self.pending and now >= self.retry_at:
                item = self.pending.popleft()
                payload = json.dumps(item["body"]) if item["body"] is not None else ""
                self.current = (int(self.bridge.request(item["path"], payload)), item)
        except Exception:
            self.bridge = None
            self.status = "Online scores unavailable. Gameplay can continue."


def with_online_features(base):
    """Extend either ruleset through the same game lifecycle methods."""
    class OnlineGame(base):
        def reset_game(self):
            if not hasattr(self, "scores"):
                self.scores = ScoresClient()
                self.scores.send("board")
            self.run_clock = RunClock()
            self.run_credentials = None
            self.result_submitted = False
            self.nickname = ""
            self.nickname_focused = True
            self.nickname_selected = True
            self.leaderboard_return = "ready"
            super().reset_game()

        def _sync_timer(self):
            now = pygame.time.get_ticks()
            if self.game_state == "playing" and not self.overlay:
                self.run_clock.resume(now)
            else:
                self.run_clock.pause(now)

        def _start_run(self, test=False):
            self.run_clock.start(pygame.time.get_ticks(), test)
            self.nickname = "Player-" + uuid.uuid4().hex[:6]
            if not test:
                self.run_credentials = {"id": str(uuid.uuid4()), "token": str(uuid.uuid4())}
                from game_config import ONLINE_VARIANT
                self.scores.send("start", dict(self.run_credentials, variant=ONLINE_VARIANT))

        def start_test(self):
            super().start_test()
            if self.test_mode:
                self._start_run(test=True)

        def start_level(self, *args, **kwargs):
            super().start_level(*args, **kwargs)
            self.run_clock.next_level(pygame.time.get_ticks())

        def open_overlay(self, name):
            super().open_overlay(name)
            self._sync_timer()

        def close_overlay(self):
            super().close_overlay()
            self._sync_timer()

        def lose_life(self, damage=1):
            super().lose_life(damage)
            if self.game_state == "lost":
                self._sync_timer()

        def _last_level(self):
            # The two branches intentionally have different level counts.
            return len(sys.modules[base.__module__].LEVEL_ENEMIES)

        def _continue_level(self):
            now = pygame.time.get_ticks()
            if self.fire_until:
                self.fire_until += now - self.summary_started
            if self.level == 10 and self._last_level() > 10:
                self.game_state = "life_offer"
                self.life_offer_started = now
            elif hasattr(self, "advance_level"):
                self.advance_level()
            else:
                self.level += 1
                if self.level == 5:
                    self.lives += 1
                self.bullets_left += 2
                self.game_state = "playing"
                self.start_level()
                self.message = "Level 5! +1 life!" if self.level == 5 else f"Level {self.level}!"
                self.message_until = now + 1800
            self._sync_timer()

        def _submit_result(self):
            if self.result_submitted or self.run_clock.test or not self.run_credentials:
                return
            if not self.scores.enabled:
                self.scores.status = "Local times only. Open the hosted browser game to submit."
                return
            name = self.nickname.strip()
            if not name:
                self.scores.status = "Enter a nickname first."
                return
            self.scores.send("finish", dict(self.run_credentials, nickname=name))
            self.result_submitted = True
            self.scores.status = "Result queued. Keep the game open until it is saved."

        def _submission(self):
            if not self.run_credentials:
                return None
            return self.scores.submissions.get(self.run_credentials["id"])

        def _result_status(self):
            submission = self._submission()
            return submission["message"] if submission else self.scores.status

        def menu_buttons(self):
            state = self.game_state
            if state == "level_summary":
                return {"online_continue": pygame.Rect(200, 560, 270, 55),
                        "online_board": pygame.Rect(530, 560, 270, 55)}
            if state == "leaderboard":
                return {"online_return": pygame.Rect(200, 620, 270, 50),
                        "online_refresh": pygame.Rect(530, 620, 270, 50)}
            buttons = super().menu_buttons()
            if state == "ready":
                buttons["online_board"] = pygame.Rect(390, 655, 220, 38)
            elif state in ("won", "lost"):
                buttons["online_board"] = pygame.Rect(530, 590, 300, 50)
                buttons["online_again"] = pygame.Rect(390, 650, 220, 40)
                if not self.run_clock.test:
                    buttons["online_submit"] = pygame.Rect(170, 590, 300, 50)
                    buttons["online_nickname"] = pygame.Rect(330, 475, 340, 48)
            return buttons

        def handle_click(self, position):
            action = next((name for name, rect in self.menu_buttons().items()
                           if name.startswith("online_") and rect.collidepoint(position)), None)
            if action == "online_nickname":
                if not self.result_submitted:
                    self.nickname_focused = True
                    self.nickname_selected = True
                return
            if self.game_state in ("won", "lost"):
                self.nickname_focused = False
                self.nickname_selected = False
            if action == "online_board":
                self.leaderboard_return = self.game_state
                self.game_state = "leaderboard"
                self.scores.send("board")
            elif action == "online_return":
                self.game_state = self.leaderboard_return
            elif action == "online_refresh":
                self.scores.send("board")
            elif action == "online_continue":
                self._continue_level()
            elif action == "online_submit":
                self._submit_result()
            elif action == "online_again":
                self.reset_game()
            else:
                super().handle_click(position)
            self._sync_timer()

        def handle_key(self, event):
            if self.game_state == "leaderboard":
                if event.key == pygame.K_ESCAPE:
                    self.game_state = self.leaderboard_return
                return
            if self.game_state == "level_summary":
                if event.key == pygame.K_RETURN:
                    self._continue_level()
                return
            if self.game_state in ("won", "lost"):
                if event.key == pygame.K_RETURN:
                    self._submit_result()
                elif not self.result_submitted and self.nickname_focused:
                    char = getattr(event, "unicode", "")
                    shortcut = getattr(event, "mod", 0) & (pygame.KMOD_CTRL | pygame.KMOD_META)
                    if event.key == pygame.K_a and shortcut:
                        self.nickname_selected = True
                    elif event.key == pygame.K_BACKSPACE:
                        self.nickname = "" if self.nickname_selected else self.nickname[:-1]
                        self.nickname_selected = False
                    elif not shortcut and char and char.isascii() and (char.isalnum() or char in " _-"):
                        if self.nickname_selected:
                            self.nickname = ""
                            self.nickname_selected = False
                        if len(self.nickname) >= 16:
                            return
                        self.nickname += char
                return
            before = self.game_state
            super().handle_key(event)
            if before == "ready" and self.game_state == "playing":
                self._start_run()
            self._sync_timer()

        def offer_level_summary(self, now):
            if self.run_clock.started and self.mega_pair_offered and not self.math_active:
                split = self.run_clock.complete(self.level, now)
                if not self.run_clock.test and self.run_credentials:
                    self.scores.send("progress", dict(self.run_credentials, level=self.level,
                                                      total_ms=max(1, split["total_ms"])))
                if self.level == self._last_level():
                    self.game_state = "won"
                else:
                    self.game_state = "level_summary"
                    self.summary_started = now
                return True
            return False

        def update(self):
            now = pygame.time.get_ticks()
            self.scores.update(now)
            submission = self._submission()
            if submission and submission["state"] == "failed" and self.result_submitted:
                self.result_submitted = False
                self.nickname_focused = True
                self.nickname_selected = True
            self._sync_timer()
            if self.game_state in ("leaderboard", "level_summary"):
                return
            super().update()
            self._sync_timer()

        def _text(self, text, y, big=False, color=(245, 245, 245)):
            surface = (self.big_font if big else self.small_font).render(text, True, color)
            self.screen.blit(surface, surface.get_rect(center=(500, y)))

        def draw_panel(self):
            super().draw_panel()
            now = pygame.time.get_ticks()
            total = self.run_clock.total(now)
            # Replace the lower instructions with the always-visible run timers.
            pygame.draw.rect(self.screen, (22, 28, 52), (745, 535, 255, 105))
            for text, y in [("Level time: " + format_time(total - self.run_clock.level_base), 550),
                            ("Total time: " + format_time(total), 580),
                            ("Test run - not ranked" if self.run_clock.test else "Timed normal game", 610)]:
                self.screen.blit(self.small_font.render(text, True, (245, 245, 245)), (750, y))

        def draw(self):
            state = self.game_state
            if state in ("leaderboard", "level_summary"):
                self.screen.fill((8, 12, 32))
                if state == "level_summary":
                    split = self.run_clock.splits[-1]
                    self._text(f"LEVEL {self.level} COMPLETE!", 120, True)
                    self._text("Level time: " + format_time(split["level_ms"]), 240)
                    self._text("Total through this level: " + format_time(split["total_ms"]), 295)
                    self._text("The clock is paused. Continue when you are ready.", 390)
                    if self.run_clock.test:
                        self._text("Test Mode: these times will not be ranked.", 440)
                    self.draw_button(self.menu_buttons()["online_continue"], "Continue")
                    self.draw_button(self.menu_buttons()["online_board"], "Leaderboard")
                else:
                    self._text("TOP 10", 55, True)
                    from game_config import ONLINE_VARIANT
                    title = "Production: 10 levels" if ONLINE_VARIANT == "classic-10-v1" else "Experimental: 15 levels"
                    self._text(title + " | Furthest level, then fastest total", 110)
                    count = str(self.scores.plays) if self.scores.plays is not None else "Unavailable"
                    self._text("Games started: " + count, 150)
                    def cell(label, x, y):
                        surface = self.small_font.render(str(label), True, (245, 245, 245))
                        self.screen.blit(surface, (x, y))
                    for label, x in [("Rank", 95), ("Nickname", 180), ("Levels completed", 500), ("Total time", 775)]:
                        cell(label, x, 190)
                    for index, row in enumerate(self.scores.board[:10]):
                        y = 230 + index * 31
                        for label, x in [(index + 1, 95), (row['nickname'], 180),
                                         (row['completed'], 550), (format_time(row['total_ms']), 775)]:
                            cell(label, x, y)
                    if not self.scores.board:
                        self._text("No qualifying results yet. Clear at least 1 level.", 300)
                    self._text(self._result_status(), 585)
                    self.draw_button(self.menu_buttons()["online_return"], "Back")
                    self.draw_button(self.menu_buttons()["online_refresh"], "Refresh")
                pygame.display.flip()
                return
            super().draw()
            if state == "ready":
                self.draw_button(self.menu_buttons()["online_board"], "Leaderboard")
            elif state in ("won", "lost"):
                pygame.draw.rect(self.screen, (8, 12, 32), (100, 340, 800, 305))
                self._text("Run time: " + format_time(self.run_clock.total(pygame.time.get_ticks())), 365)
                completed = self.run_clock.splits[-1]["level"] if self.run_clock.splits else 0
                self._text(f"Completed levels: {completed}. Ranked by completed-level time.", 405)
                if self.run_clock.splits:
                    self._text("Last level time: " + format_time(self.run_clock.splits[-1]["level_ms"]), 435)
                if self.run_clock.test:
                    self._text("Test run: no play count or leaderboard entry.", 480)
                else:
                    self._text("Type a nickname, or keep the system-generated nickname below.", 455)
                    field = self.menu_buttons()["online_nickname"]
                    pygame.draw.rect(self.screen, (235, 235, 235) if self.result_submitted else (255, 255, 255), field, border_radius=6)
                    border = (70, 180, 255) if self.nickname_focused and not self.result_submitted else (145, 155, 180)
                    pygame.draw.rect(self.screen, border, field, 3, border_radius=6)
                    selected = self.nickname_selected and self.nickname_focused and not self.result_submitted
                    color = (255, 255, 255) if selected else (0, 0, 0)
                    name = self.font.render(self.nickname, True, color)
                    name_rect = name.get_rect(midleft=(field.left + 12, field.centery))
                    if name_rect.right > field.right - 12:
                        name_rect.right = field.right - 12
                    previous_clip = self.screen.get_clip()
                    self.screen.set_clip(field.inflate(-16, -8))
                    if selected and self.nickname:
                        pygame.draw.rect(self.screen, (35, 90, 210), name_rect.inflate(4, 4))
                    self.screen.blit(name, name_rect)
                    if self.nickname_focused and not self.result_submitted and not selected and pygame.time.get_ticks() % 1000 < 500:
                        pygame.draw.line(self.screen, (0, 0, 0), (name_rect.right + 2, field.top + 10), (name_rect.right + 2, field.bottom - 10), 2)
                    self.screen.set_clip(previous_clip)
                    self._text("Submit uses the name above. Clear at least 1 level to qualify.", 535)
                    submission = self._submission()
                    label = "Result Saved" if submission and submission["state"] == "saved" else "Saving..." if self.result_submitted else "Submit Result"
                    self.draw_button(self.menu_buttons()["online_submit"], label)
                self.draw_button(self.menu_buttons()["online_board"], "Leaderboard")
                self._text(self._result_status(), 565)
                # Restart is a button, leaving all letters available for nicknames.
                self.draw_button(self.menu_buttons()["online_again"], "Play Again")
            pygame.display.flip()

    return OnlineGame
