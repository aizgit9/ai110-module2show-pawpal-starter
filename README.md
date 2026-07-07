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

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

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

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
