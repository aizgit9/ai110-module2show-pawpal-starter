"""PawPal+ logic layer.

Class skeletons generated from diagrams/uml.mmd. These are stubs only:
attributes are defined, but method bodies are left unimplemented so the
scheduling logic can be built up incrementally (and tested) in later steps.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Priority labels used by the UI, mapped to a sortable numeric score.
PRIORITY_SCORES = {"low": 1, "medium": 2, "high": 3}


@dataclass
class Task:
    """A single pet-care activity (e.g. a morning walk)."""

    title: str
    duration_minutes: int
    priority: str = "medium"
    preferred_time: str | None = None
    recurrence: str | None = None
    category: str | None = None

    def priority_score(self) -> int:
        """Return a sortable numeric score for this task's priority."""
        raise NotImplementedError

    def summary(self) -> str:
        """Return a human-readable one-line description of the task."""
        raise NotImplementedError


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
        raise NotImplementedError

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        raise NotImplementedError

    def list_tasks(self) -> list[Task]:
        """Return all tasks belonging to this pet."""
        raise NotImplementedError


@dataclass
class Owner:
    """The app user; holds the day's time budget and scheduling preferences."""

    name: str
    available_minutes: int = 0
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        raise NotImplementedError

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner."""
        raise NotImplementedError

    def set_preference(self, key: str, value: object) -> None:
        """Set a scheduling preference (e.g. preferred start time)."""
        raise NotImplementedError

    def get_available_time(self) -> int:
        """Return the total minutes available for the day."""
        raise NotImplementedError


@dataclass
class ScheduledTask:
    """A Task placed at a concrete time slot within a Plan."""

    task: Task
    start_time: str
    end_time: str


@dataclass
class Plan:
    """The generated daily schedule and its reasoning."""

    items: list[ScheduledTask] = field(default_factory=list)
    included: list[Task] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    total_minutes: int = 0

    def explain(self) -> str:
        """Return a human-readable explanation of why tasks were chosen/skipped."""
        raise NotImplementedError

    def to_table(self) -> list[dict]:
        """Return the plan as rows suitable for display (e.g. st.table)."""
        raise NotImplementedError


class Scheduler:
    """Builds a daily Plan from tasks and the owner's constraints."""

    def __init__(
        self,
        tasks: list[Task],
        available_minutes: int,
        start_time: str = "08:00",
    ) -> None:
        self.tasks = tasks
        self.available_minutes = available_minutes
        self.start_time = start_time

    def sort_tasks(self) -> list[Task]:
        """Return tasks ordered by priority (then duration)."""
        raise NotImplementedError

    def filter_tasks(self) -> list[Task]:
        """Drop tasks that do not fit within the available time budget."""
        raise NotImplementedError

    def resolve_conflicts(self) -> list[Task]:
        """Handle overlapping/preferred time slots among tasks."""
        raise NotImplementedError

    def build_plan(self) -> Plan:
        """Produce the final daily Plan. Main entry point for the UI."""
        raise NotImplementedError
