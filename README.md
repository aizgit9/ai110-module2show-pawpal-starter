# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## ✨ Features

The implemented scheduling algorithms (all in `pawpal_system.py`):

- **Priority-first planning** — tasks ordered high→low priority, ties broken by shorter duration (`Scheduler.sort_tasks()`).
- **Sorting by time** — the chosen tasks are laid out in clock order, with untimed tasks placed last (`Task.sort_key()`, used by `Scheduler.resolve_conflicts()`).
- **Time-budget filtering** — greedily keeps only the tasks that fit the owner's available minutes, skipping non-positive durations (`Scheduler.filter_tasks()`).
- **Filtering by pet or completion status** — query tasks across all pets, combinable with AND (`Owner.find_tasks()`).
- **Completed-task exclusion** — finished chores are dropped and never consume the day's budget (`Scheduler.build_plan()`).
- **End-of-day cutoff** — tasks that would run past the day's end are skipped rather than producing invalid past-midnight times.
- **Conflict warnings** — non-crashing detection of overlapping requested times, labeled *same pet* vs. *different pets* (`Scheduler.detect_conflicts()`).
- **Preferred-time bumping** — when two tasks want the same slot, the later one is moved instead of overlapping, and flagged (`ScheduledTask.bumped`).
- **Daily/weekly recurrence** — completing a recurring task spawns a fresh occurrence for next time (`Task.mark_complete()`, `Task.next_occurrence()`).
- **Plan explanation** — a human-readable breakdown of what was planned, skipped, and why (`Plan.explain()`).

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Running `python main.py` produces the following daily schedule in the terminal:

```
============================================
Today's Schedule for Jordan
============================================
Planned:
  08:00-08:30  Morning walk (for Mochi)
  09:00-09:10  Feeding (for Mochi)
  09:30-09:40  Feeding (for Biscuit)
  17:00-17:20  Fetch / play (for Mochi)
  19:00-19:25  Grooming (for Biscuit)
  19:25-19:30  Litter box (for Biscuit)

Total scheduled time: 100 min
============================================
```

## 🧪 Testing PawPal+

Run the full test suite from the project root:

```bash
python -m pytest
```

### What the tests cover

The suite (`tests/test_pawpal.py`, 49 tests) exercises the logic layer in
`pawpal_system.py` across four areas:

- **Data model** — `Task`, `Pet`, and `Owner` basics: priority scoring (including
  the unknown-label fallback), human-readable summaries, `format_time`, adding/
  removing/listing tasks and pets, `list_tasks()` returning a defensive copy, and
  `Owner.find_tasks()` filtering by pet and/or completion status.
- **Sorting** — priority ordering (high first, shorter-duration tie-break) and
  chronological ordering, including that the finished plan reads top-to-bottom in
  clock order with untimed tasks placed last.
- **Filtering & budget** — greedy fit within the owner's available minutes and
  skipping of non-positive durations; completed tasks are dropped and never
  consume the day's budget; tasks running past the end-of-day wall are skipped.
- **Conflict detection** — pairwise overlap warnings for open, timed tasks,
  labeled *same pet* vs. *different pets*, including exact duplicate times, with
  completed tasks ignored.
- **Recurrence** — completing a `daily`/`weekly` task spawns a fresh, distinct,
  open occurrence (carrying priority, duration, and time-of-day), while one-off
  tasks return `None`; the full complete → re-attach-to-pet lifecycle is verified.
- **Plan assembly (`build_plan`)** — non-overlapping slots, honored preferred
  times, the `bumped` flag when a slot is unavailable, correct pet attribution,
  `total_minutes` matching included tasks, and empty-owner handling.

### Sample test output

```
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
rootdir: c:\Users\asher\repos\ai110-module2show-pawpal-starter
plugins: anyio-4.14.1
collected 49 items

tests\test_pawpal.py .................................................   [100%]

============================= 49 passed in 0.09s ==============================
```

### Confidence Level

**★★★★☆ (4 / 5)**

All 49 tests pass and cover the core scheduling behaviors — sorting, budget
filtering, recurrence, conflict detection, and non-overlapping plan assembly —
including their most important edge cases. One star is held back because the
tests exercise the logic layer only (not the Streamlit UI in `app.py`), and a
known interaction remains untested: a task admitted by `filter_tasks` can still
be dropped by the end-of-day wall in `build_plan`, having already "spent" budget
that a lower-priority task might otherwise have used. Solid for the logic layer;
not yet a full end-to-end guarantee.

## 📐 Smarter Scheduling

Beyond the basic plan, PawPal+ implements four "smarter scheduling" behaviors.
Each is a small, pure, independently testable method in `pawpal_system.py`.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Sorting | `Task.sort_key()`, `Scheduler.sort_tasks()` | Chronological vs. priority ordering |
| Filtering | `Owner.find_tasks()`, `Scheduler.filter_tasks()` | By pet / completion, and by time budget |
| Conflict detection | `Scheduler.detect_conflicts()` | Warns on overlapping requested times |
| Recurring tasks | `Task.mark_complete()`, `Task.next_occurrence()` | Daily/weekly tasks respawn when done |

### Sorting behavior

Two complementary orderings:

- **`Task.sort_key()`** returns a chronological sort key (minutes since midnight),
  sending untimed tasks to the end. Callers sort with `sorted(tasks, key=Task.sort_key)` —
  used by `Scheduler.resolve_conflicts()` to lay tasks out in clock order.
- **`Scheduler.sort_tasks()`** orders by priority (high first), breaking ties by
  shorter duration, so the day's time budget is spent on what matters most first.

### Filtering behavior

- **`Owner.find_tasks(completed=None, pet_name=None)`** returns tasks filtered by
  completion status and/or pet name (both optional, combined with AND). Completed
  chores are also dropped automatically inside `Scheduler.build_plan()` so a
  finished task never consumes the day's budget.
- **`Scheduler.filter_tasks()`** greedily keeps tasks that fit the owner's
  available-minutes budget, skipping any with non-positive durations.

### Conflict detection logic

- **`Scheduler.detect_conflicts()`** is a lightweight, non-throwing pairwise scan
  of open tasks that request a specific time. It compares each task's
  `[preferred_time, preferred_time + duration)` window and returns a list of
  warning strings (labeled *same pet* vs. *different pets*), rather than raising.
  `build_plan()` stores these on `Plan.warnings`, and `Plan.explain()` surfaces
  them. The plan still resolves overlaps by bumping the later task (see the
  `bumped` flag on `ScheduledTask`), so a conflict warns without breaking the plan.

### Recurring task logic

- **`Task.mark_complete()`** marks a task done and, if it recurs, returns the next
  occurrence. **`Task.next_occurrence()`** produces that fresh, un-completed copy
  for `daily`/`weekly` tasks (and `None` for one-offs). The owning `Pet` re-adds
  the returned task, so a daily walk reappears for next time the moment it's
  checked off.

## 📸 Demo Walkthrough

PawPal+ runs two ways: an interactive **Streamlit UI** (`streamlit run app.py`) for
day-to-day use, and a **command-line demo** (`python main.py`) that prints a full
scheduling run to the terminal.

### The UI at a glance

The Streamlit app is a single scrolling page with three areas:

- **Owner & pet** — enter the owner's name, the pet's name, and species. These
  persist across reruns, so tasks you add aren't lost.
- **Tasks** — add a care task with a title, duration, priority, and an optional
  preferred hour (leave at `-1` for "any time"). The current tasks show in a table
  sorted chronologically, with a `done` column. A **Mark done** control lets you
  complete a task without deleting it — and if it's a daily/weekly task, its next
  occurrence is added back automatically.
- **Build Schedule** — set the day's available minutes and start hour, then click
  **Generate schedule**. The app shows the ordered plan, a success summary, any
  conflict warnings, tasks that were moved off their preferred time, tasks skipped
  for lack of budget, and an expandable "Why this plan?" reasoning panel.

### Example workflow

1. Enter the owner (**Jordan**) and a pet (**Mochi**, a dog).
2. Add a few tasks — e.g. a high-priority *Morning walk* (30 min) preferred at 08:00,
   a *Feeding* (10 min) at 09:00, and a *Fetch / play* (20 min) at 17:00.
3. Add a second pet's task that wants the same 08:00 slot (e.g. Biscuit's *Vet call*)
   to see conflict handling.
4. Set **Time available today** to 120 minutes and **Start the day at** to hour 8.
5. Click **Generate schedule** and read today's plan, warnings, and reasoning.
6. Click **Mark done** on the walk — because it's a daily task, tomorrow's walk
   reappears in the task list.

### Key Scheduler behaviors you'll see

- **Priority-first + time sorting** — high-priority tasks win the budget, and the
  final plan reads top-to-bottom in clock order (`Scheduler.sort_tasks()`, `Task.sort_key()`).
- **Conflict warnings** — two tasks requesting 08:00 raise a non-fatal warning
  naming both tasks and whether they belong to the *same* or *different* pets
  (`Scheduler.detect_conflicts()`).
- **Preferred-time bumping** — the plan still resolves the overlap by moving the
  later task and flagging it as *moved* (`ScheduledTask.bumped`).
- **Budget filtering & end-of-day cutoff** — tasks that don't fit the available
  minutes, or that would run past the day's end, are listed as skipped.
- **Recurrence** — completing a daily/weekly task spawns its next occurrence
  (`Task.mark_complete()`).

### Sample CLI output

Running `python main.py` walks through sorting, filtering, recurrence, conflict
detection, and the final schedule:

```
====================================================
All tasks, sorted chronologically by preferred time
====================================================
      08:00  Morning walk (30 min) [priority: high]
      08:00  Vet call (20 min) [priority: high]
      09:00  Feeding (10 min) [priority: high]
      09:30  Feeding (10 min) [priority: high]
      17:00  Fetch / play (20 min) [priority: medium]
      19:00  Grooming (25 min) [priority: low]
  (no time)  Litter box (5 min) [priority: medium]

====================================================
Filter: only Mochi's tasks (sorted by time)
====================================================
      08:00  Morning walk (30 min) [priority: high]
      09:00  Feeding (10 min) [priority: high]
      17:00  Fetch / play (20 min) [priority: medium]

====================================================
Filter: open vs. completed tasks
====================================================
  Open (6):
    - Fetch / play (20 min) [priority: medium]
    - Morning walk (30 min) [priority: high]
    - Feeding (10 min) [priority: high]
    - Litter box (5 min) [priority: medium]
    - Feeding (10 min) [priority: high]
    - Vet call (20 min) [priority: high]
  Completed (1):
    - Grooming (25 min) [priority: low]

====================================================
Recurrence: complete Mochi's daily walk
====================================================
  Marked 'Morning walk' done (recurrence=daily).
  Spawned next occurrence: open=True, same time=08:00
  Mochi's open task count: 3 -> 3 (unchanged: one done, one fresh)

====================================================
Conflict detection
====================================================
  [!] 'Morning walk' (Mochi) at 08:00 overlaps 'Vet call' (Biscuit) at 08:00 [different pets]

====================================================
Today's Schedule for Jordan
====================================================
Planned:
  08:00-08:20  Vet call (for Biscuit)
  08:20-08:50  Morning walk (for Mochi)  [preferred 08:00 unavailable, moved]
  09:00-09:10  Feeding (for Mochi)
  09:30-09:40  Feeding (for Biscuit)
  17:00-17:20  Fetch / play (for Mochi)
  17:20-17:25  Litter box (for Biscuit)

[!] Conflicts:
  - 'Morning walk' (Mochi) at 08:00 overlaps 'Vet call' (Biscuit) at 08:00 [different pets]

Total scheduled time: 95 min
====================================================
```
