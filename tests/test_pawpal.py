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

    def test_mark_complete_returns_none_for_one_off_task(self):
        task = Task("Vet visit", 60)  # no recurrence
        assert task.mark_complete() is None
        assert task.completed is True

    @pytest.mark.parametrize("recurrence", ["daily", "weekly"])
    def test_mark_complete_spawns_next_occurrence(self, recurrence):
        task = Task("Walk", 30, "high", preferred_time=hhmm(8), recurrence=recurrence)
        nxt = task.mark_complete()

        assert task.completed is True  # original is done
        assert nxt is not None
        assert nxt is not task  # a distinct new instance
        assert nxt.completed is False  # next occurrence starts open
        # Everything else carries over unchanged.
        assert (nxt.title, nxt.duration_minutes, nxt.priority) == ("Walk", 30, "high")
        assert nxt.preferred_time == hhmm(8)
        assert nxt.recurrence == recurrence

    def test_next_occurrence_none_for_non_recurring(self):
        assert Task("One-off", 10).next_occurrence() is None


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

    def _owner_two_pets(self):
        owner = Owner("Jordan")
        mochi = Pet("Mochi", "dog")
        biscuit = Pet("Biscuit", "cat")
        walk = Task("Walk", 30)
        walk.mark_complete()
        mochi.add_task(walk)
        mochi.add_task(Task("Feed Mochi", 10))
        biscuit.add_task(Task("Groom", 45))
        owner.add_pet(mochi)
        owner.add_pet(biscuit)
        return owner

    def test_find_tasks_no_filters_returns_all(self):
        titles = [t.title for t in self._owner_two_pets().find_tasks()]
        assert sorted(titles) == ["Feed Mochi", "Groom", "Walk"]

    def test_find_tasks_by_pet_name(self):
        titles = [t.title for t in self._owner_two_pets().find_tasks(pet_name="Mochi")]
        assert sorted(titles) == ["Feed Mochi", "Walk"]

    def test_find_tasks_by_completion_status(self):
        owner = self._owner_two_pets()
        assert [t.title for t in owner.find_tasks(completed=True)] == ["Walk"]
        assert sorted(t.title for t in owner.find_tasks(completed=False)) == [
            "Feed Mochi",
            "Groom",
        ]

    def test_find_tasks_combines_both_filters(self):
        owner = self._owner_two_pets()
        # Only Mochi's still-open tasks.
        titles = [t.title for t in owner.find_tasks(pet_name="Mochi", completed=False)]
        assert titles == ["Feed Mochi"]

    def test_find_tasks_unknown_pet_returns_empty(self):
        assert self._owner_two_pets().find_tasks(pet_name="Nobody") == []


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

    def test_detect_conflicts_none_when_times_dont_overlap(self):
        owner = Owner("J")
        pet = Pet("Mochi", "dog")
        pet.add_task(Task("Walk", 30, preferred_time=hhmm(8)))  # 08:00-08:30
        pet.add_task(Task("Feed", 10, preferred_time=hhmm(9)))  # 09:00-09:10
        owner.add_pet(pet)
        assert Scheduler(owner).detect_conflicts() == []

    def test_detect_conflicts_flags_overlap_across_pets(self):
        owner = Owner("J")
        mochi, biscuit = Pet("Mochi", "dog"), Pet("Biscuit", "cat")
        mochi.add_task(Task("Walk", 30, preferred_time=hhmm(8)))  # 08:00-08:30
        biscuit.add_task(Task("Vet call", 20, preferred_time=hhmm(8, 15)))  # overlaps
        owner.add_pet(mochi)
        owner.add_pet(biscuit)
        conflicts = Scheduler(owner).detect_conflicts()
        assert len(conflicts) == 1
        assert "Walk" in conflicts[0] and "Vet call" in conflicts[0]
        assert "different pets" in conflicts[0]

    def test_detect_conflicts_flags_same_pet_overlap(self):
        owner = Owner("J")
        pet = Pet("Mochi", "dog")
        pet.add_task(Task("Walk", 30, preferred_time=hhmm(8)))
        pet.add_task(Task("Play", 15, preferred_time=hhmm(8)))  # same slot
        owner.add_pet(pet)
        conflicts = Scheduler(owner).detect_conflicts()
        assert len(conflicts) == 1
        assert "same pet" in conflicts[0]

    def test_detect_conflicts_ignores_completed_tasks(self):
        owner = Owner("J")
        pet = Pet("Mochi", "dog")
        done = Task("Walk", 30, preferred_time=hhmm(8))
        done.mark_complete()
        pet.add_task(done)
        pet.add_task(Task("Play", 15, preferred_time=hhmm(8)))
        owner.add_pet(pet)
        assert Scheduler(owner).detect_conflicts() == []

    def test_build_plan_populates_warnings(self):
        owner = Owner("J", available_minutes=999)
        mochi, biscuit = Pet("Mochi", "dog"), Pet("Biscuit", "cat")
        mochi.add_task(Task("Walk", 30, preferred_time=hhmm(8)))
        biscuit.add_task(Task("Vet call", 20, preferred_time=hhmm(8)))
        owner.add_pet(mochi)
        owner.add_pet(biscuit)
        plan = Scheduler(owner).build_plan()
        assert plan.warnings  # conflict surfaced on the plan
        assert "Conflicts" in plan.explain()

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
