"""PawPal+ logic layer.

Implements the classes designed in diagrams/uml.mmd.

Time convention: all times are stored internally as **minutes since midnight**
(an int, e.g. 8:00 -> 480). Use `format_time()` to render them for display.
Storing time as an int keeps scheduling math (start + duration = end, overlap
detection, sorting) simple and avoids repeated string parsing.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


# Recurrence values that spawn a follow-up task when completed.
RECURRING = ("daily", "weekly")


# Priority labels used by the UI, mapped to a sortable numeric score.
PRIORITY_SCORES = {"low": 1, "medium": 2, "high": 3}


def format_time(minutes_since_midnight: int) -> str:
    """Render minutes-since-midnight as a display string, e.g. 480 -> '08:00'."""
    hours, minutes = divmod(minutes_since_midnight, 60)
    return f"{hours:02d}:{minutes:02d}"


@dataclass
class Task:
    """A single pet-care activity (e.g. a morning walk)."""

    title: str
    duration_minutes: int
    priority: str = "medium"
    preferred_time: int | None = None  # minutes since midnight, optional
    recurrence: str | None = None
    category: str | None = None
    completed: bool = False

    def next_occurrence(self) -> "Task | None":
        """Return a fresh, un-completed copy for the next occurrence.

        Only daily/weekly tasks recur; one-off tasks return None. This model
        tracks time-of-day (``preferred_time``) but not calendar dates, so the
        "next occurrence" is an identical task ready to be scheduled again — the
        same time-of-day, priority, duration, and recurrence, reset to open.
        """
        if self.recurrence not in RECURRING:
            return None
        return replace(self, completed=False)

    def mark_complete(self) -> "Task | None":
        """Mark this task done and return its next occurrence, if it recurs.

        For a daily/weekly task, returns a fresh un-completed copy so the caller
        can add it back to the pet; returns None for one-off tasks.
        """
        self.completed = True
        return self.next_occurrence()

    def priority_score(self) -> int:
        """Return a sortable numeric score for this task's priority (unknown -> 0)."""
        return PRIORITY_SCORES.get(self.priority, 0)

    def sort_key(self) -> int:
        """Chronological sort key (minutes since midnight); untimed tasks sort last.

        Keeps the ``preferred_time is None`` guard in one place so callers can do
        ``sorted(tasks, key=Task.sort_key)`` without a lambda.
        """
        return self.preferred_time if self.preferred_time is not None else 24 * 60

    def summary(self) -> str:
        """Return a human-readable one-line description of the task."""
        return f"{self.title} ({self.duration_minutes} min) [priority: {self.priority}]"


@dataclass
class Pet:
    """A pet the owner cares for; owns a list of care tasks."""

    name: str
    species: str
    breed: str | None = None
    age: int | None = None
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        self.tasks.remove(task)

    def list_tasks(self) -> list[Task]:
        """Return all tasks belonging to this pet (a copy, so callers can't mutate)."""
        return list(self.tasks)


@dataclass
class Owner:
    """The app user; holds the day's time budget and scheduling preferences.

    `available_minutes` is the single source of truth for the day's time
    budget; the Scheduler reads it from the Owner rather than storing its own.
    """

    name: str
    available_minutes: int = 0
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner."""
        self.pets.remove(pet)

    def set_preference(self, key: str, value: object) -> None:
        """Set a scheduling preference (e.g. preferred start time)."""
        self.preferences[key] = value

    def get_available_time(self) -> int:
        """Return the total minutes available for the day."""
        return self.available_minutes

    def find_tasks(
        self, *, completed: bool | None = None, pet_name: str | None = None
    ) -> list[Task]:
        """Return this owner's tasks, optionally filtered by completion and/or pet name.

        Both filters are optional and keyword-only; passing both narrows to tasks
        matching *both* (logical AND). With no arguments, returns every task
        across all pets.
        """
        matches: list[Task] = []
        for pet in self.pets:
            if pet_name is not None and pet.name != pet_name:
                continue
            for task in pet.tasks:
                if completed is not None and task.completed != completed:
                    continue
                matches.append(task)
        return matches


@dataclass
class ScheduledTask:
    """A Task placed at a concrete time slot within a Plan.

    Carries a reference to the owning Pet so the plan can attribute each slot
    to a specific pet (e.g. "walk Mochi") in multi-pet setups.
    """

    task: Task
    pet: Pet
    start_time: int  # minutes since midnight
    end_time: int  # minutes since midnight
    bumped: bool = False  # True if a preferred_time couldn't be honored and the task was moved


@dataclass
class Plan:
    """The generated daily schedule and its reasoning."""

    items: list[ScheduledTask] = field(default_factory=list)
    included: list[Task] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    total_minutes: int = 0
    warnings: list[str] = field(default_factory=list)

    def explain(self) -> str:
        """Return a human-readable explanation of why tasks were chosen/skipped."""
        lines: list[str] = []
        if self.items:
            lines.append("Planned:")
            for item in self.items:
                when = f"{format_time(item.start_time)}-{format_time(item.end_time)}"
                line = f"  {when}  {item.task.title} (for {item.pet.name})"
                if item.bumped:
                    line += f"  [preferred {format_time(item.task.preferred_time)} unavailable, moved]"
                lines.append(line)
        else:
            lines.append("Nothing could be scheduled within the available time.")

        if self.skipped:
            lines.append("")
            lines.append("Skipped (didn't fit the day's time budget or ran past day's end):")
            for task in self.skipped:
                lines.append(f"  - {task.summary()}")

        if self.warnings:
            lines.append("")
            lines.append("[!] Conflicts:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        lines.append("")
        lines.append(f"Total scheduled time: {self.total_minutes} min")
        return "\n".join(lines)

    def to_table(self) -> list[dict]:
        """Return the plan as rows suitable for display (e.g. st.table)."""
        return [
            {
                "start": format_time(item.start_time),
                "end": format_time(item.end_time),
                "task": item.task.title,
                "pet": item.pet.name,
                "priority": item.task.priority,
                "duration_minutes": item.task.duration_minutes,
            }
            for item in self.items
        ]


class Scheduler:
    """Builds a daily Plan from an Owner's pets, tasks, and constraints.

    Takes the whole Owner (rather than pre-flattened primitives) so it retains
    access to per-task pet ownership and the owner's `preferences`. The three
    helper methods are **pure**: each takes a list of tasks and returns a new
    list, leaving `self` untouched, so `build_plan` can chain them predictably
    and each is testable in isolation.
    """

    def __init__(self, owner: Owner, start_time: int = 480, end_of_day: int = 24 * 60) -> None:
        """Create a scheduler for an owner, starting the day at start_time (min-since-midnight).

        `end_of_day` is a hard wall (default midnight, 1440): no task is laid out
        so that it ends after this, which keeps clock times from wrapping past
        24:00 in the display.
        """
        self.owner = owner
        self.start_time = start_time  # minutes since midnight (default 08:00)
        self.end_of_day = end_of_day

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered by priority (high first), then duration (short first)."""
        return sorted(tasks, key=lambda t: (-t.priority_score(), t.duration_minutes))

    def filter_tasks(self, tasks: list[Task]) -> list[Task]:
        """Greedily keep tasks that fit the owner's time budget, skipping non-positive durations."""
        budget = self.owner.available_minutes
        used = 0
        kept: list[Task] = []
        for task in tasks:
            if task.duration_minutes <= 0:
                continue
            if used + task.duration_minutes <= budget:
                kept.append(task)
                used += task.duration_minutes
        return kept

    def resolve_conflicts(self, tasks: list[Task]) -> list[Task]:
        """Order preferred-time tasks chronologically first, then the rest.

        This only fixes the *order* tasks are considered in; `build_plan` is what
        actually prevents overlap, by advancing a monotonic cursor so each slot
        starts no earlier than the previous one ended.

        Task.sort_key sends untimed tasks to the end (24*60), and sorted() is
        stable, so they keep their original relative order after the timed ones.

        Tradeoff: this single sort replaced an explicit "filter timed / filter
        untimed / concatenate" two-pass. We gained readability and one source of
        truth for the None-handling rule, but correctness now *depends on* two
        implicit facts — sort stability, and the 24*60 sentinel being strictly
        larger than any real preferred_time. A task with preferred_time >= 1440
        (a malformed past-midnight time) would interleave with untimed tasks
        here, whereas the old is-None split was immune to the sentinel's value.
        Reasonable because preferred_time is minutes-since-midnight (0..1439) by
        construction, but worth knowing if that invariant ever loosens.
        """
        return sorted(tasks, key=Task.sort_key)

    def detect_conflicts(self) -> list[str]:
        """Return warning strings for tasks whose requested time windows overlap.

        Lightweight and non-throwing: compares every pair of open tasks that
        request a specific ``preferred_time``, using each task's
        ``[preferred_time, preferred_time + duration)`` window. Overlaps within
        the same pet or across different pets are both reported. Returns an empty
        list when there are no conflicts.

        These are warnings about what the owner *requested* — ``build_plan``
        still resolves them by bumping the later task, so the program never
        crashes; the message just flags that two things were asked for at once.
        """
        # Gather (task, pet) for open tasks that request a specific time, sorted
        # by start so we only compare tasks that could actually overlap.
        timed: list[tuple[Task, Pet]] = sorted(
            (
                (task, pet)
                for pet in self.owner.pets
                for task in pet.tasks
                if not task.completed and task.preferred_time is not None
            ),
            key=lambda pair: pair[0].preferred_time,
        )

        warnings: list[str] = []
        for i, (task_a, pet_a) in enumerate(timed):
            a_end = task_a.preferred_time + max(task_a.duration_minutes, 0)
            for task_b, pet_b in timed[i + 1 :]:
                if task_b.preferred_time >= a_end:
                    break  # sorted by start: nothing later can overlap task_a
                same = "same pet" if pet_a is pet_b else "different pets"
                warnings.append(
                    f"'{task_a.title}' ({pet_a.name}) at {format_time(task_a.preferred_time)} "
                    f"overlaps '{task_b.title}' ({pet_b.name}) at "
                    f"{format_time(task_b.preferred_time)} [{same}]"
                )
        return warnings

    def build_plan(self) -> Plan:
        """Gather all pets' tasks, apply sort -> filter -> resolve, and lay them out as a Plan."""
        # Flatten tasks across pets while remembering which pet owns each one.
        # Keyed by id() so duplicate-looking tasks stay distinct. Completed tasks
        # are dropped up front so a finished chore doesn't consume today's budget.
        task_to_pet: dict[int, Pet] = {}
        all_tasks: list[Task] = []
        for pet in self.owner.pets:
            for task in pet.tasks:
                if task.completed:
                    continue
                task_to_pet[id(task)] = pet
                all_tasks.append(task)

        ordered = self.sort_tasks(all_tasks)
        fitted = self.filter_tasks(ordered)
        resolved = self.resolve_conflicts(fitted)

        plan = Plan()
        cursor = self.start_time
        for task in resolved:
            start = cursor
            bumped = False
            if task.preferred_time is not None:
                if task.preferred_time >= cursor:
                    start = task.preferred_time
                else:
                    # Preferred slot has already passed; pack at the cursor and
                    # record that we couldn't honor the request.
                    bumped = True
            end = start + task.duration_minutes
            if end > self.end_of_day:
                # Would run past the day's end; leave it out (falls into skipped).
                # Don't advance the cursor, so a later shorter task can still fit.
                continue
            plan.items.append(
                ScheduledTask(
                    task=task,
                    pet=task_to_pet[id(task)],
                    start_time=start,
                    end_time=end,
                    bumped=bumped,
                )
            )
            plan.included.append(task)
            cursor = end

        included_ids = {id(t) for t in plan.included}
        plan.skipped = [t for t in all_tasks if id(t) not in included_ids]
        plan.total_minutes = sum(t.duration_minutes for t in plan.included)
        plan.warnings = self.detect_conflicts()
        return plan
