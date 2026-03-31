# Silicon Valley Trail

A replayable CLI resource-management simulation inspired by *The Oregon Trail*. A startup team travels from San Jose to San Francisco to pitch for Series A funding — managing constrained resources, resolving events, and making trade-offs under uncertainty.

Designed to feel like a series of small, stressful decisions — similar to real startup life. The core idea: **every decision has a cost**. Solving one problem creates pressure elsewhere. There is no safe path — only better and worse trade-offs.

---

## Quick Start

```bash
git clone https://github.com/Ligo-code/PetProject.git
cd PetProject
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python cli.py
```

**Offline / mock mode** (no network calls):

```bash
MOCK_APIS=true python cli.py
```

No API keys required. Copy `.env.example` to `.env` if needed — all values default to `false`.

---

## Example Commands

```bash
# Run with live APIs
python cli.py

# Run fully offline
MOCK_APIS=true python cli.py

# Run tests
pytest silicon_valley_trail/tests/ -v

# Run specific test file
pytest silicon_valley_trail/tests/test_integration.py -v
```

---

## Game Loop

Each turn:
1. Choose an action (travel, rest, fix bugs, marketing push, knowledge share, buy supplies)
2. Resolve a location event — weighted random, conditional on current state
3. Apply passive effects (coffee drain, bug growth, morale pressure)
4. Check win/lose conditions

Win: reach San Francisco. Lose: any resource crosses its threshold.

---

## Resources

| Resource | Lose condition |
|---|---|
| 💰 Cash | Hits $0 |
| 😊 Morale | Hits 0 — drains -1/day when coffee < 15 |
| ☕ Coffee | 2 consecutive days at 0 |
| 🐛 Bugs | Reaches 20 — grows +1 every 3 days passively |
| 📢 Hype | No direct lose condition — required for VC pitches to succeed |

---

## Team Roles

Three roles with mechanical impact — not just flavor text:

- **Backend** — bug fixes are 60% more effective; protected from poaching
- **Frontend** — marketing costs 20% less, generates higher hype
- **Product** — unlocks Knowledge Share action; higher burnout risk

Team members can burn out (temporarily inactive) or be permanently poached. Losing a role changes which actions are effective.

---

## API Integration

All APIs are free, keyless, and fail gracefully.

| API | Why chosen | Gameplay effect |
|---|---|---|
| [Open-Meteo](https://open-meteo.com/) | No key, real coordinates per location, reliable | Rain: -10 morale and +5 coffee cost on travel. Heat: +1 bug that turn |
| [HN Algolia](https://hn.algolia.com/api/v1) | No key, reflects real tech sentiment | Trending keyword: +5–10 hype on marketing push, triggers hype spike event |

Both APIs inject data into `GameState` fields before each turn. Game logic reads those fields — it never calls APIs directly. This means `MOCK_APIS=true` requires zero code changes to the game engine.

---

## Testing

```bash
pytest silicon_valley_trail/tests/ -v
```

93 tests across unit, action, event, and integration levels. Integration tests validate full turn cycles — `action → tick_day → check_game_status` — without mocking internal state. This tests game behavior as a system, not individual functions in isolation.

---

## Architecture

```
silicon_valley_trail/
├── models/         # GameState, TeamMember, Location, Event — pure data
├── engine/         # actions.py, events.py, game_loop.py — all game logic
├── services/       # weather_api.py, hn_api.py — external data with fallback
└── tests/          # unit + integration
storage.py          # JSON save/load (~/.silicon_valley_trail_save.json)
cli.py              # entry point
```

**Dependencies:** `requests`, `pytest`. No frameworks.

The architecture is intentionally structured so new actions, events, or APIs can be added without modifying existing game logic — only extending registries or services.

---

## Data Modeling

**`GameState`** is the single source of truth — a dataclass holding all resources, progress, flags, and team state. Actions and events mutate it through `apply_effects()`, which clamps values and returns *actual* deltas so messages always reflect reality.

**`TeamMember`** tracks individual morale separately from team morale. Team morale reflects atmosphere; individual morale drives burnout and poaching logic per role.

**`Event` / `EventChoice`** are plain dataclasses with callable `effect` fields. No inheritance — the `EventRegistry` in the engine layer owns weighting and selection logic.

**Persistence** is manual JSON serialization in `storage.py`. Only resource fields are saved; API data is re-fetched on load.

---

## Error Handling

All network calls are wrapped in `try/except Exception` with a 3–5s timeout. On any failure — timeout, bad status, malformed JSON — the service returns mock data while preserving previous state where possible, and the game continues without interruption. The game loop never branches on API availability. HN is fetched once per session to avoid rate limits; weather is fetched once per turn.

---

## Design Notes

**Win takes priority over lose.** If a player reaches San Francisco on the same turn their cash hits zero, it's a win. Reaching the goal takes precedence over resource state at arrival — this is an explicit product decision, not an oversight.

**State mutations return actual deltas.** `apply_effects()` clamps resource values and returns what actually changed. If morale is 98 and an event adds +10, the message says `+2 morale` — not `+10`. The game never lies to the player.

**One-time events respect narrative.** Events that promise a fix set a flag in `GameState` and are excluded from future draws. If the text says "we fixed it", it stays fixed.

**Services are injected, not coupled.** This keeps game logic testable, deterministic, and independent from external failures. The engine doesn't know or care whether data came from an API or a mock.

---

## Tradeoffs

- **CLI over web UI** — focused effort on game logic, architecture, and API integration rather than frontend complexity
- **Dataclasses over full OOP hierarchy** — avoided over-engineering; the domain is flat enough that inheritance would add noise
- **Centralized `GameState`** over distributed state — simplifies reasoning, testing, and serialization significantly
- **Manual JSON serialization** over a library like `dataclasses-json` — zero extra dependencies, full control over what gets saved
- **Two lightweight APIs** over one complex one — each API affects a different resource axis; combined they create more varied gameplay without tight coupling

---

## Game Design Philosophy

The game is built around **resource tension**:

- Every action solves one problem but creates pressure elsewhere (fixing bugs costs coffee and morale; marketing costs cash)
- Passive decay (coffee drain, bug growth, morale pressure) ensures the player can't just sit still
- Randomness is constrained by state — events only appear when their conditions are met, so bad luck feels earned, not arbitrary
- Role mechanics mean losing a team member genuinely changes strategy, not just stats

The goal: make optimal play **situational**, not deterministic.

---

## Tech Choice

Python was chosen for fast iteration, readability, and ease of modeling game state and simulation logic. `dataclasses` provide lightweight, typed state without boilerplate; `requests` handles all HTTP with minimal overhead.

---

## How AI Was Used

Claude (Anthropic) was used as a collaborative tool throughout — for architectural feedback, code review, and design tradeoff discussions. All decisions, implementations, and balancing were made and reviewed by me. Game design and scenarios draw from personal experience.

---

## If I Had More Time

- OpenSky Network API — aircraft-triggered supply drops based on real flight data near current coordinates
- REST API layer (`POST /action`, `GET /state`) to support a web or mobile frontend
- Difficulty modes: Bootstrapped (less cash, more pressure) vs VC-backed (more cash, hype requirement to win)
- Escalating event weights and cost multipliers closer to San Francisco
