# Bad Guy Blasters

A keyboard-controlled maze game that mixes action with math practice.

## Set up in VS Code

1. Open VS Code and choose **File > Open Folder**.
2. Select the folder containing this game's `main.py`.
3. Open **Terminal > New Terminal**.
4. Create a private Python environment for this project:

   ```bash
   python3 -m venv .venv
   ```

5. Activate it on macOS or Linux:

   ```bash
   source .venv/bin/activate
   ```

   On Windows PowerShell, use:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

6. Install the game library:

   ```bash
   python -m pip install -r requirements.txt
   ```

7. Run the game:

   ```bash
   python main.py
   ```

If VS Code asks for a Python interpreter, choose the one containing `.venv`.

## Play in a browser locally

With the project's Python environment activated, run:

```bash
python -m pip install -r requirements-web.txt
python build_web.py
python -m http.server 8000 --bind 127.0.0.1 --directory build/web
```

Open <http://127.0.0.1:8000> in your browser. The first load downloads the
Python/Pygame browser runtime from Pygbag's CDN and may take a little time.
Click the game to enable sound and keyboard input. This version requires a keyboard.
Press Control+C in the terminal to stop the preview server.

`build_web.py` packages `main.py`, `online.py`, and a generated `game_config.py` in a clean
temporary folder, then writes the website to `build/web`. Local environments,
secrets, and editor settings are excluded from the game package. Rebuild after
changing the source.

`main` is the stable Cloudflare production branch; its browser build hides and
disables Test Mode. `experimental-gameplay` is the development branch; its browser
build includes Test Mode automatically, both locally and in Cloudflare previews.
The build uses Cloudflare's `CF_PAGES_BRANCH` variable when available, or the
checked-out Git branch locally. Outside Git it defaults to hiding Test Mode.
Running `python main.py` locally always keeps Test Mode available. To explicitly
include it in another browser build, use `python build_web.py --include-test-mode`.

## Publish with Cloudflare Pages

Connect this GitHub repository to Cloudflare Pages and use:

| Setting | Value |
| --- | --- |
| Production branch | `main` |
| Framework preset | None |
| Build command | `python -m pip install -r requirements-web.txt && python build_web.py` |
| Build output directory | `build/web` |
| Root directory | Leave blank (repository root) |
| Environment variable | `PYTHON_VERSION` = `3.13.12` |

The build installs the packaging tools and generates the website; Cloudflare
publishes only `build/web`. After deployment, test movement, sound, and math
questions at the provided `pages.dev` address. Future pushes to `main` trigger
a new build and deployment.

## Controls

- New players can click **How to Play** on the opening screen for a four-page guide to controls, math, enemies, and items. Use **Previous/Next** or the arrow keys to browse; **Main Menu** or **Escape** returns to the opening screen.
- Press **Enter** on the opening screen when you are ready to begin.
- Move with **W A S D** or the **arrow keys**.
- **Space** always fires Basic bullets; **M** fires Mega bullets. Command does not fire.
- Press **Z** to launch a bomb in the direction you face (black world only).
- Click **Bag** or press **B** to view ammunition and use items. There is no Basic bullet selection button.
- Press **Tab** anywhere in the white world to enter its red store. Tab or Escape closes the store or Bag.
- Press either **Shift** key during gameplay to enter the **Hide Out**. Press Shift again to leave early.
- Type a math answer and press **Enter**.
- Use **Backspace** to fix an answer.
- Press **Escape** to close the game.

## Math Practice

Choose **Math Practice** on the opening menu, outside gameplay. Select **2 minutes**,
**4 minutes**, or **6 minutes** for the entire set of **15 different problems**.
The set mixes one- and two-digit addition/subtraction (operands up to 99),
multiplication with factors from 1 to 20 (up to 20 × 20), and division facts
with divisors and whole-number answers from 1 to 12. Subtraction answers are
nonnegative.

Type an answer, edit with Backspace, and press Enter or click Submit. Each
question allows one attempt. A wrong answer immediately shows **Incorrect** and
the correct answer; press Enter or click **Next** to continue. The total timer
keeps running during this feedback. Math Practice uses white backgrounds and
black text throughout. Finish all 15 or reach the time limit to see your
score out of 15 and review your answers, including correct answers for mistakes
and unanswered questions. Use Previous/Next to review all 15, Practice Again for
a new set, or Main Menu/Escape to leave. Practice is also available in public
builds without Test Mode. It does not change game lives, ammunition, or levels
and cannot be opened during a game.

## Test a game

Test Mode is available in the local Python game and optional development browser
builds. It is hidden and disabled in the public Cloudflare version.

Click **Test Mode** on the opening screen. Use the **+** and **-** buttons to choose a starting level (1–15), lives (1 or more), Basic bullets (0 or more), and Mega bullets (0 or more). Click **Poison's Yes/No button** to toggle whether you start with poison, then click **Start Test** (or press Enter).

Test games follow the normal game rules using your chosen starting values. Click **Main Menu** to return at any time, including during math questions or after winning or losing. Returning resets the normal game to level 1 with 3 lives, 3 Basic bullets, 2 Mega bullets, and no poison.

## Hide Out

The wooden house in the upper-left corner is the Hide Out. Both you and the robots can walk over it during normal play, so standing on or above the house does not protect you. Only Shift takes you inside from anywhere in the black world, for up to 10 seconds per visit. You get **two visits per game**, shared across all levels. Leaving early still uses one visit.

Inside, you see only the wooden interior and cannot move or shoot. Robots keep moving outside, cannot hurt you, and are kept away from the house and exit. After 10 seconds you automatically return beside the house with a brief protection period. Math questions wait while you are inside; finish an active math question before entering. The side panel shows your remaining visits. Test games also start with two visits.

## Store and Bag

The red building in the upper-right of the white world is the store. Store and Bag menus pause gameplay and all timers, including math, freezing, and speed boosts. Bag shows ammunition, ice, fire packs, and bombs; poison remains outside the Bag. Each store item shows its cost and lights up yellow when you have enough credits to buy it.

Click an item in the Bag to toggle it **Active** or **Inactive**. Active items are highlighted; the Bag stays open until you close it. Inactive Mega bullets cannot be fired with **M**, inactive bombs cannot be thrown with **Z**, and inactive ice cannot freeze enemies. Basic bullets still fire with **SPACE**. Mega bullets and bombs start enabled. Turning Fire off stops the speed boost and saves its remaining time; turning it back on resumes that time without spending another pack.

- **Ice gun:** costs 8 red kill credits. Choose **ice** in Bag to arm it, then touch a badguy (including a zombie) to freeze it for 4 seconds without taking contact damage. Each freeze consumes one ice gun. Frozen enemies cannot move or hurt you while frozen. You can shoot frozen robots under their usual bullet rules; blue robots still require Mega bullets, and zombies remain immune to bullets. The ice gun appears light blue.
- **Fire pack:** costs 5 red, 3 green, 2 blue, and 1 yellow kill credits earned without losing a life. Activate **fire** in Bag to consume one pack and move 30% faster for 10 seconds. An orange ring shows the boost. Once the saved boost time runs out, activating Fire consumes another pack.

- **Bomb:** costs 7 red, 4 green, 2 blue, and 2 yellow kill credits in its own balance, which survives losing a life. With Bomb active, press **Z** to throw a big round purple ball in the direction you face. It works only in the black world and passes through walls. On hitting a regular badguy, it explodes and defeats that badguy plus up to two nearest active badguys within 100 pixels, including shielded blue and green robots. It never hurts zombies or enemies in the other world. Bombs are single-use: each throw uses one bomb, and a miss still spends it. The Bag shows how many bombs remain. Bomb kills earn credits and defeated yellow robots give poison.

Kills from bullets, bombs, and poison count; green robots only count when fully defeated. Ice uses a red-kill balance, while Fire uses a separate streak balance. Purchases spend the relevant credits, so additional items require more kills. Losing any life resets unspent Fire credits, but keeps Ice credits and purchased items. Credits and items carry between levels and reset for a new game.

## Rules

### Portals and the white world

From level 2 onward, a white tornado portal appears in a random clear spot away from the Hide Out. Walk into it to enter the white world, which has a white background, brown fences, and trees. Walk out of the arrival portal and back into its black tornado to return. You can revisit freely; only your current world is visible.

Regular badguys can follow through the portal, with at most two in the white world at once in levels 2–10, and at most four in levels 11–15. They can also follow you back. Every level's white world starts with exactly four black zombies, separate from that limit, moving 75% slower than that level's red robots. Zombies stay in the white world, cannot be attacked with bullets or poison, and disappear after touching and taking one life from an unprotected player. They do not respawn on return visits. Regular badguys in both worlds count toward clearing the level; zombies do not.

The Hide Out is only available in the black world. Portals and zombies also appear when testing level 2 or higher.

### Lives and math

- The player starts with 3 lives, 3 Basic bullets, and 2 Mega bullets.
- Reaching level 5 gives one extra life, even if you still have all 3 starting lives.
- After completing level 10, a choice screen offers **1 extra life for 3 normal (Basic) bullets**, or **Continue without extra life**. The trade is available only if you already have at least 3 normal bullets; Mega bullets cannot pay for it. This is a one-time choice before level 11. Gameplay and any remaining Fire boost pause during the choice. Either choice starts level 11 and gives the usual 2 normal bullets for advancing.
- The robots freeze during each math problem.
- A bell rings when each new math question appears, including the second Mega question.
- Each level's first math round offers a Mega-question pair. Later rounds have a one-in-three chance of offering another pair. If a blue robot remains and you have no Mega bullets, you get another opportunity within three math rounds, even after failing a previous pair. The second question in a pair does not count as a new round. If you clear the robots before any math appears, the guaranteed opportunity appears before advancing.
- The side panel shows a yellow Basic bullet icon and a larger light-gray Mega bullet icon, each next to its ammunition total.
- One-digit multiplication and two-digit plus or minus one-digit problems give 10 seconds and earn 1 bullet.
- Two-digit plus or minus two-digit problems, two-digit times one-digit multiplication, and two-digit divided by one-digit division give 15 seconds and earn 2 bullets.
- The first problem appears 15 seconds after starting. Later problems are 30 seconds apart.
- Correct answers give 1–2 bullets. Harder problems give more.
- Earn an extra Mega bullet by correctly solving two 2-bullet problems back to back in 20 seconds total. After the first correct answer, the second question appears immediately and gameplay stays paused. Each problem allows one attempt; failing a problem resets progress. After the pair, gameplay resumes whether or not you earned a Mega. Each correct answer still earns its normal Basic bullets.
- Mega bullets deal twice the damage, are light gray, and are 50% larger in diameter than Basic bullets. They defeat any robot in one hit. Impacts create a firework in the robot's color, or white when no robot is hit; fireworks do not damage other robots.
- Every math problem allows only one attempt. A wrong answer or timeout ends the problem with no reward; existing ammunition is kept.
- Clear all robots to reach the next level. Win by clearing level 15.

## Robot colors

| Level | Red | Green | Blue | Yellow | Total |
| --- | --- | --- | --- | --- | --- |
| 1 | 3 | 0 | 0 | 0 | 3 |
| 2 | 2 | 1 | 0 | 0 | 3 |
| 3 | 3 | 1 | 0 | 0 | 4 |
| 4 | 4 | 1 | 1 | 0 | 6 |
| 5 | 4 | 2 | 1 | 0 | 7 |
| 6 | 5 | 2 | 1 | 1 | 9 |
| 7 | 6 | 2 | 2 | 1 | 11 |
| 8 | 6 | 3 | 3 | 1 | 13 |
| 9 | 7 | 3 | 3 | 2 | 15 |
| 10 | 8 | 3 | 3 | 2 | 16 |
| 11 | 8 | 4 | 4 | 2 | 18 |
| 12 | 9 | 5 | 4 | 2 | 20 |
| 13 | 10 | 5 | 5 | 2 | 22 |
| 14 | 10 | 6 | 5 | 3 | 24 |
| 15 | 11 | 6 | 6 | 3 | 26 |

- **Red:** the original robot; one bullet defeats it.
- **Green (level 2+):** has two lives. The first Basic bullet makes it vanish for 5 seconds, then it returns in a random safe spot. A second Basic bullet defeats it. One Mega defeats it immediately.
- **Blue (level 4+):** can be defeated with a Mega bullet or poison. Basic bullets cannot defeat it.
- **Yellow (level 6+):** moves at player speed and its touch costs 3 lives. With 4 lives, you survive with 1; with 3 or fewer, the game ends. Defeating it gives one poison potion. While holding the potion, touch any robot to defeat it and use the potion.

## Learning missions

Read and change just one small thing at a time:

1. **Variables:** Change `PLAYER_SPEED`, `EASY_MATH_TIME`, or `HARD_MATH_TIME` near the top of `main.py`.
2. **Colors:** Change one RGB color such as `GREEN = (80, 220, 130)`.
3. **Functions:** Read `make_math_problem()` and change the smallest addition number.
4. **If statements:** Find `if level >= 2` and decide when multiplication should begin.
5. **Lists:** Add another starting position to `enemy_starts`.
6. **Classes:** Change how the `Enemy` is drawn without changing how it moves.

After every change: predict what will happen, run the game, and compare the result.

## Play counts, timers, and the top 10

Normal browser games send a first-party request to `/api/start` when Enter starts
an actual game. Each run has random credentials; retrying the same start does not
increase the count. Page loads, Test Mode, Math Practice, and desktop games are not
counted. Counts begin when this feature is deployed, not retroactively.

Level and total timers include math-solving and Hide Out time. Bag/store menus,
level results, leaderboards, and the extra-life choice pause the clock. Losing a
life does not reset it. Each cleared level shows its own time and cumulative time,
with Continue and Leaderboard buttons. The final screen shows the run duration and
last-level time. Complete a normal run (win or lose) and submit a nickname to join
the top 10; a run must clear at least one level to rank. Use Play Again to restart.
Names are limited to 16 ASCII letters, digits, spaces, hyphens, or underscores.
The nickname box is prefilled with a system-generated name. Submit it as-is, or
type your own nickname to replace it. Click the box to select its text; use
Backspace to edit or Command/Ctrl+A to select all. The box locks after submission.

Ranking is most completed levels first, then lowest cumulative time through those
completed levels. Unfinished-level time is excluded from ranking. Production
(`classic-10-v1`) and experimental (`experimental-15-v1`) scores and play counts are
separate. Each submitted run can occupy one place; this does not identify people.
The game stores no raw IP addresses, cookies, or persistent visitor identifiers.
Times are reported by the client with server sanity checks: this is a casual
leaderboard, not a cheat-proof competition.

`functions/api/[[path]].js` provides the API. Cloudflare D1 stores runs, per-level
splits, and counters. `wrangler.toml` binds `GAME_DB` for both production and preview
and chooses the ruleset. Database IDs are public resource identifiers, not secrets.
Only `/api/*` invokes Functions; the game assets stay static.

Database schema setup (already applied to the project database):

```bash
npx wrangler d1 migrations apply bad-guy-blaster-scores --remote
```

To test the full browser/API connection with an isolated local database:

```bash
python build_web.py
npx wrangler d1 migrations apply bad-guy-blaster-scores --local
npx wrangler pages dev build/web --binding GAME_VARIANT=experimental-15-v1 --port 8030 --ip 127.0.0.1
```

Use `GAME_VARIANT=classic-10-v1` when testing the production checkout. Open
http://127.0.0.1:8030. A plain `python -m http.server` serves the game and timers,
but cannot run the database API. Desktop Python games also have local timers only.
Network errors never stop gameplay. Requests retry in order while the page remains
open; closing it can discard unsent requests. Online status is shown on results
and leaderboard screens. Pending results are not a guarantee of successful saving.

Checks: `python -m unittest discover -v` and `node --test tests/online_api.test.mjs`
(the API tests use Node 22.13+ with its built-in SQLite support and no live data).
