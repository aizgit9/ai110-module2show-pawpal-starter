"""Tests for the PawPal+ logic layer.

Focus is on the scheduling behaviors that matter most: priority ordering,
fitting tasks to the time budget, honoring preferred times, and producing a
non-overlapping plan with correct pet attribution.
"""

import pytest

from pawpal_system import (
    Owner,
    Pet,
    Task,
    Scheduler,
    Plan,
    ScheduledTask,
    format_time,
    PRIORITY_SCORES,
)


def hhmm(hour, minute=0):
    return hour * 60 + minute


# --------------------------------------------------------------------------
# Task
# --------------------------------------------------------------------------
class TestTask:
    def test_priority_score_known_labels(self):
        assert Task("A", 10, "low").priority_score() == 1
        assert Task("A", 10, "medium").priority_score() == 2
        assert Task("A", 10, "high").priority_score() == 3

    def test_priority_score_unknown_label_defaults_to_zero(self):
        # Guarded lookup: an unexpected string must not raise.
        assert Task("A", 10, "urgent").priority_score() == 0

    def test_summary_is_human_readable(self):
        s = Task("Morning walk", 30, "high").summary()
        assert "Morning walk" in s
        assert "30" in s
        assert "high" in s


# --------------------------------------------------------------------------
# format_time
# --------------------------------------------------------------------------
class TestFormatTime:
    def test_formats_midnight(self):
        assert format_time(0) == "00:00"

    def test_formats_eight_am(self):
        assert format_time(hhmm(8)) == "08:00"

    def test_zero_pads_minutes(self):
        assert format_time(hhmm(9, 5)) == "09:05"


# --------------------------------------------------------------------------
# Pet
# --------------------------------------------------------------------------
class TestPet:
    def test_add_and_list_tasks(self):
        pet = Pet("Mochi", "dog")
        task = Task("Walk", 20)
        pet.add_task(task)
        assert pet.list_tasks() == [task]

    def test_list_tasks_returns_copy(self):
        pet = Pet("Mochi", "dog")
        pet.add_task(Task("Walk", 20))
        returned = pet.list_tasks()
        returned.clear()
        assert len(pet.list_tasks()) == 1  # internal list untouched

    def test_remove_task(self):
        pet = Pet("Mochi", "dog")
        task = Task("Walk", 20)
        pet.add_task(task)
        pet.remove_task(task)
        assert pet.list_tasks() == []


# --------------------------------------------------------------------------
# Owner
# --------------------------------------------------------------------------
class TestOwner:
    def test_add_and_remove_pet(self):
        owner = Owner("Jordan")
        pet = Pet("Mochi", "dog")
        owner.add_pet(pet)
        assert pet in owner.pets
        owner.remove_pet(pet)
        assert pet not in owner.pets

    def test_set_and_read_preference(self):
        owner = Owner("Jordan")
        owner.set_preference("quiet_hours", "22:00-07:00")
        assert owner.preferences["quiet_hours"] == "22:00-07:00"

    def test_get_available_time(self):
        assert Owner("Jordan", available_minutes=90).get_available_time() == 90

    def test_pets_default_is_not_shared(self):
        # Regression guard for the mutable-default dataclass trap.
        a, b = Owner("A"), Owner("B")
        a.add_pet(Pet("X", "dog"))
        assert b.pets == []


# --------------------------------------------------------------------------
# Scheduler helpers (pure functions)
# --------------------------------------------------------------------------
class TestSchedulerHelpers:
    def test_sort_by_priority_high_first(self):
        sched = Scheduler(Owner("J", available_minutes=999))
        tasks = [Task("low", 10, "low"), Task("high", 10, "high"), Task("med", 10, "medium")]
        titles = [t.title for t in sched.sort_tasks(tasks)]
        assert titles == ["high", "med", "low"]

    def test_sort_breaks_ties_by_shorter_duration(self):
        sched = Scheduler(Owner("J", available_minutes=999))
        tasks = [Task("long", 40, "high"), Task("short", 10, "high")]
        titles = [t.title for t in sched.sort_tasks(tasks)]
        assert titles == ["short", "long"]

    def test_sort_is_pure(self):
        sched = Scheduler(Owner("J", available_minutes=999))
        original = [Task("low", 10, "low"), Task("high", 10, "high")]
        sched.sort_tasks(original)
        assert [t.title for t in original] == ["low", "high"]  # unchanged

    def test_filter_drops_tasks_over_budget(self):
        sched = Scheduler(Owner("J", available_minutes=40))
        tasks = [Task("a", 30), Task("b", 20), Task("c", 5)]
        kept = [t.title for t in sched.filter_tasks(tasks)]
        assert kept == ["a", "c"]  # 30 + 5 fit; 20 would overflow before c

    def test_filter_skips_non_positive_durations(self):
        sched = Scheduler(Owner("J", available_minutes=100))
        tasks = [Task("zero", 0), Task("neg", -5), Task("ok", 10)]
        kept = [t.title for t in sched.filter_tasks(tasks)]
        assert kept == ["ok"]

    def test_resolve_conflicts_orders_preferred_times_chronologically(self):
        sched = Scheduler(Owner("J", available_minutes=999))
        tasks = [
            Task("late", 10, preferred_time=hhmm(17)),
            Task("no-pref", 10),
            Task("early", 10, preferred_time=hhmm(8)),
        ]
        titles = [t.title for t in sched.resolve_conflicts(tasks)]
        assert titles == ["early", "late", "no-pref"]  # preferred first, then rest


# --------------------------------------------------------------------------
# Scheduler.build_plan (integration)
# --------------------------------------------------------------------------
class TestBuildPlan:
    def _owner_with_tasks(self, available_minutes):
        owner = Owner("Jordan", available_minutes=available_minutes)
        mochi = Pet("Mochi", "dog")
        biscuit = Pet("Biscuit", "cat")
        mochi.add_task(Task("Walk", 30, "high", preferred_time=hhmm(8)))
        mochi.add_task(Task("Feed Mochi", 10, "high", preferred_time=hhmm(9)))
        biscuit.add_task(Task("Groom", 45, "low"))
        owner.add_pet(mochi)
        owner.add_pet(biscuit)
        return owner

    def test_returns_a_plan(self):
        plan = Scheduler(self._owner_with_tasks(120)).build_plan()
        assert isinstance(plan, Plan)

    def test_over_budget_task_is_skipped(self):
        # 30 + 10 + 45 = 85; budget 60 forces the low-priority 45-min groom out.
        plan = Scheduler(self._owner_with_tasks(60), start_time=hhmm(8)).build_plan()
        included = [t.title for t in plan.included]
        skipped = [t.title for t in plan.skipped]
        assert "Groom" in skipped
        assert "Walk" in included and "Feed Mochi" in included

    def test_total_minutes_matches_included(self):
        plan = Scheduler(self._owner_with_tasks(60)).build_plan()
        assert plan.total_minutes == sum(t.duration_minutes for t in plan.included)

    def test_slots_do_not_overlap(self):
        plan = Scheduler(self._owner_with_tasks(200), start_time=hhmm(8)).build_plan()
        for earlier, later in zip(plan.items, plan.items[1:]):
            assert earlier.end_time <= later.start_time

    def test_preferred_time_is_honored(self):
        plan = Scheduler(self._owner_with_tasks(200), start_time=hhmm(8)).build_plan()
        walk = next(i for i in plan.items if i.task.title == "Walk")
        assert walk.start_time == hhmm(8)

    def test_scheduled_task_attributed_to_correct_pet(self):
        plan = Scheduler(self._owner_with_tasks(200)).build_plan()
        walk = next(i for i in plan.items if i.task.title == "Walk")
        assert walk.pet.name == "Mochi"

    def test_end_time_is_start_plus_duration(self):
        plan = Scheduler(self._owner_with_tasks(200)).build_plan()
        for item in plan.items:
            assert item.end_time - item.start_time == item.task.duration_minutes

    def test_empty_owner_produces_empty_plan(self):
        plan = Scheduler(Owner("Empty", available_minutes=100)).build_plan()
        assert plan.items == []
        assert plan.total_minutes == 0

    def test_completed_tasks_are_not_scheduled_or_skipped(self):
        # A finished chore should disappear entirely: not planned, not in the
        # skipped list, and not counted against the day's budget.
        owner = Owner("Jordan", available_minutes=200)
        pet = Pet("Mochi", "dog")
        done = Task("Morning walk", 30, "high")
        done.mark_complete()
        pet.add_task(done)
        pet.add_task(Task("Feed", 10, "high"))
        owner.add_pet(pet)

        plan = Scheduler(owner, start_time=hhmm(8)).build_plan()
        titles = [t.title for t in plan.included]
        assert "Morning walk" not in titles
        assert "Morning walk" not in [t.title for t in plan.skipped]
        assert plan.total_minutes == 10  # only the un-completed Feed counts

    def test_task_running_past_end_of_day_is_skipped(self):
        # Budget is generous, but the day ends at midnight; a task that would
        # end after that is dropped rather than wrapping to "25:xx".
        owner = Owner("Jordan", available_minutes=999)
        pet = Pet("Mochi", "dog")
        pet.add_task(Task("Late feeding", 60, preferred_time=hhmm(23, 30)))
        owner.add_pet(pet)

        plan = Scheduler(owner, start_time=hhmm(8), end_of_day=hhmm(24)).build_plan()
        assert "Late feeding" in [t.title for t in plan.skipped]
        assert plan.items == []

    def test_bumped_flag_set_when_preferred_time_already_passed(self):
        # Two tasks both prefer the same slot; the second can't get it and is
        # packed after the first, with bumped=True recorded.
        owner = Owner("Jordan", available_minutes=999)
        pet = Pet("Mochi", "dog")
        pet.add_task(Task("Walk", 30, "high", preferred_time=hhmm(8)))
        pet.add_task(Task("Play", 30, "high", preferred_time=hhmm(8)))
        owner.add_pet(pet)

        plan = Scheduler(owner, start_time=hhmm(8)).build_plan()
        second = next(i for i in plan.items if i.task.title == "Play")
        assert second.bumped is True
        assert second.start_time >= hhmm(8, 30)  # moved to after the Walk
        assert "unavailable, moved" in plan.explain()


# --------------------------------------------------------------------------
# Two simple behavior checks
# --------------------------------------------------------------------------
def test_mark_complete_changes_status():
    """Calling mark_complete() flips the task's status to done."""
    task = Task("Walk", 20)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    """Adding a task to a Pet increases that pet's task count."""
    pet = Pet("Mochi", "dog")
    assert len(pet.tasks) == 0
    pet.add_task(Task("Walk", 20))
    assert len(pet.tasks) == 1
